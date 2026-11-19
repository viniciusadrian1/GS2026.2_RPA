"""Orquestrador: inbox -> validação -> NLP -> ML -> prioridade -> dedup -> protocolo -> robô no portal -> relatório."""
import time
from collections import Counter
from pathlib import Path

from config import settings
from src import assistant, attachments, nlp, priority
from src.classifier import Classifier
from src.ingest import InvalidReport, load_file
from src.protocol import Store, make_protocol
from src.utils.logger import get_logger
from src.utils.resilience import safe_step

log = get_logger("pipeline")


class Pipeline:
    def __init__(self, store: Store, classifier: Classifier, robot=None):
        self.store, self.clf, self.robot = store, classifier, robot
        self.events: list = []
        self.counts: Counter = Counter()

    # ------------------------------------------------------------------ util
    def _event(self, arquivo, resultado, protocolo=None, detalhe=None):
        self.counts[resultado] += 1
        self.events.append({"arquivo": arquivo, "resultado": resultado, "protocolo": protocolo, "detalhe": detalhe})
        log.info("%s -> %s %s %s", arquivo, resultado, protocolo or "", detalhe or "")

    def _comprovante(self, protocolo, categoria, prio, status, texto, motivo=None):
        d = settings.OUTPUT_DIR / "comprovantes"
        d.mkdir(parents=True, exist_ok=True)
        orient = assistant.answer(texto)["resposta"]
        linhas = [f"PROTOCOLO: {protocolo}", f"Categoria: {categoria}", f"Prioridade: {prio}", f"Situação: {status}"]
        if motivo:
            linhas.append(f"Observação: um atendente vai analisar seu relato ({motivo}).")
        temporary = d / f"{protocolo}.tmp"
        temporary.write_text("\n".join(linhas) + "\n\nOrientação:\n" + orient + "\n", encoding="utf-8")
        temporary.replace(d / f"{protocolo}.txt")

    def _recover_receipts(self):
        """Conclui a saída independentemente de a entrada ainda existir na inbox."""
        for row in self.store.all_reports():
            protocolo = row["protocolo"]
            path = settings.OUTPUT_DIR / "comprovantes" / f"{protocolo}.txt"
            try:
                if path.exists() and path.stat().st_size:
                    continue
                status = "em análise por atendente" if row["status"] == "em_revisao" else "em andamento"
                self._comprovante(protocolo, row["categoria"], row["prioridade"], status,
                                  row["texto_mascarado"], row["motivo_revisao"])
                self._event(protocolo, "comprovante_gerado", protocolo)
            except Exception as exc:
                log.exception("Comprovante pendente: %s", protocolo)
                self._event(protocolo, "comprovante_pendente", protocolo, str(exc))

    # ------------------------------------------------------------- um relato
    def process_file(self, path: Path):
        nome = Path(path).name
        try:
            rep = load_file(path)
        except InvalidReport as exc:
            return self._event(nome, "rejeitado", detalhe=str(exc))

        text = nlp.mask_pii(rep.text)          # LGPD: antes de qualquer outra etapa
        reasons = []

        for att in rep.attachments:
            src = Path(path).parent / att.path
            if att.kind == "audio" and len(text) < 10:
                try:
                    text = nlp.mask_pii(attachments.transcribe_audio(src))
                except Exception as exc:  # noqa: BLE001 - qualquer falha de ASR -> revisão humana
                    log.warning("%s: áudio não transcrito (%s)", nome, exc)
                    reasons.append("audio_sem_transcricao")
            elif att.kind == "foto":
                try:
                    attachments.sanitize_image(src, settings.OUTPUT_DIR / "anexos_sanitizados")
                except Exception as exc:  # noqa: BLE001
                    log.warning("%s: foto ignorada (%s)", nome, exc)

        tnorm = nlp.normalize(text)
        endereco = rep.address or nlp.extract_address(text)
        if rep.lat is None and not endereco:
            reasons.append("sem_localizacao")

        cat, conf, origem = self.clf.predict(tnorm) if tnorm else ("outros", 0.0, "vazio")
        prio, _ = priority.prioritize(cat, text)
        protocolo = make_protocol(rep.id, tnorm)

        if self.store.get_report(protocolo):
            return self._event(nome, "ja_processado", protocolo, "idempotência: nada duplicado")

        if conf < settings.CONFIDENCE_THRESHOLD:
            reasons.append(f"baixa_confianca({conf:.2f})")
        if cat == "outros":
            reasons.append("fora_do_escopo")

        row = dict(protocolo=protocolo, relato_id=rep.id, ocorrencia_id=None, categoria=cat, confianca=conf,
                   origem=origem, prioridade=prio, status="", motivo_revisao=None, endereco=endereco,
                   lat=rep.lat, lon=rep.lon, texto_mascarado=text, criado_em=rep.created_at)

        if reasons:
            row.update(status="em_revisao", motivo_revisao=";".join(reasons))
            self.store.insert_report(row)
            return self._event(nome, "revisao_humana", protocolo, row["motivo_revisao"])

        occ = self.store.find_occurrence(cat, rep.lat, rep.lon, endereco)
        if occ:
            occ = self.store.add_to_occurrence(occ["id"])
            oid, novo = occ["id"], False
        else:
            oid, novo = self.store.create_occurrence(protocolo, cat, prio, rep.lat, rep.lon, endereco, rep.created_at), True
        row.update(ocorrencia_id=oid, status="em_andamento")
        self.store.insert_report(row)
        self._event(nome, "ocorrencia_nova" if novo else "agrupado_em_existente", protocolo,
                    f"{oid} cat={cat} conf={conf:.2f} prio={prio}")

    # ------------------------------------------------------------ portal/RPA
    def _push_to_portal(self):
        """Registra ocorrências pendentes no portal. Disjuntor: se o portal esgotar as tentativas uma vez,
        as demais ficam pendentes sem novas tentativas nesta execução (não adianta martelar um portal fora)."""
        if not self.robot:
            return
        send = safe_step("portal", fallback=lambda *a, **k: None)(self.robot.register)
        disjuntor_aberto = False
        for occ in self.store.pending_portal():
            ticket = None if disjuntor_aberto else send(
                {"protocolo": occ["id"], "categoria": occ["categoria"], "prioridade": occ["prioridade"],
                 "endereco": occ["endereco"], "descricao": self.store.representative_text(occ["id"])})
            if ticket:
                self.store.set_ticket(occ["id"], ticket)
                self._event(occ["id"], "portal_registrado", detalhe=ticket)
            else:
                if not disjuntor_aberto:
                    log.error("Disjuntor aberto: portal indisponível; demais ocorrências ficam pendentes")
                disjuntor_aberto = True
                self._event(occ["id"], "portal_pendente", detalhe="será reenviado na próxima execução")

    # ---------------------------------------------------------------- lote
    def run(self, inbox: Path = settings.INBOX_DIR):
        t0 = time.time()
        files = sorted(Path(inbox).glob("*.json"))
        log.info("Iniciando lote: %d arquivo(s) em %s", len(files), inbox)
        for f in files:
            try:
                self.process_file(f)
            except Exception as exc:  # noqa: BLE001 - nenhum relato derruba o lote
                log.exception("Erro inesperado em %s", f.name)
                self._event(f.name, "erro_inesperado", detalhe=repr(exc))
        self._push_to_portal()
        self._recover_receipts()
        summary = {"arquivos_lidos": len(files), **{k: v for k, v in sorted(self.counts.items())},
                   "modo_robo": getattr(self.robot, "mode", "desligado") if self.robot else "desligado",
                   "duracao_s": round(time.time() - t0, 2)}
        return summary, self.events
