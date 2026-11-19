"""Agrupa relatos do mesmo problema: distância geográfica ou mesmo endereço normalizado."""
import math
from typing import Optional

from src.nlp import normalize


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def same_place(a_lat: Optional[float], a_lon: Optional[float], a_addr: Optional[str],
               b_lat: Optional[float], b_lon: Optional[float], b_addr: Optional[str],
               radius_m: float) -> bool:
    if None not in (a_lat, a_lon, b_lat, b_lon):
        return haversine_m(a_lat, a_lon, b_lat, b_lon) <= radius_m
    if a_addr and b_addr:
        return normalize(a_addr) == normalize(b_addr)
    return False
