"""Datové struktury pro vertebrální body a analýzu"""

from dataclasses import dataclass, field


@dataclass
class Point:
    """Souřadnice bodu s labelem"""
    x: float = 0.0
    y: float = 0.0
    label: str = ""  # Plný label (např. "C2 top left")
    original_x: float = 0.0  # Phase 3.3: Původní ML koordináta
    original_y: float = 0.0  # Phase 3.3: Původní ML koordináta


@dataclass
class VertebralPoints:
    """Body jednoho obratle - dynamické podle dat"""
    name: str  # C2, C3, C4, ...
    points: list[Point] = field(default_factory=list)  # Všechny body pro tento obratel
