# services.py – Berechnungs-Logik für Fortschritt und Noten
#
# Enthält:
#   - ProgressService: Fortschritt, Ampel-Bewertung
#   - GradeService: Bewertung der Durchschnittsnote
#
# Änderungen (11/2025):
#   - ECTS-Maximalwert 180 bleibt fix.
#   - Ampelbewertung nutzt ECTS-Differenz:
#         Rückstand ≤ 10 ECTS  → gelb
#         Rückstand > 10 ECTS  → rot

from __future__ import annotations
from datetime import date

DURATION_MONTHS = 54
ECTS_MAX = 180


class ProgressService:
    """Berechnet Studienfortschritt und Ampelstatus."""

    # ------------------- Hilfsfunktionen ------------------- #
    @staticmethod
    def _clamp_int(x: int, lo: int, hi: int) -> int:
        try:
            v = int(x)
        except Exception:
            v = lo
        return max(lo, min(hi, v))

    @staticmethod
    def _clamp_float(x: float, lo: float, hi: float) -> float:
        try:
            v = float(x)
        except Exception:
            v = lo
        return max(lo, min(hi, v))

    # ------------------- öffentliche API ------------------- #
    @staticmethod
    def months_since(start: date, today: date) -> int:
        """Berechnet Monate seit Studienstart."""
        return max(0, (today.year - start.year) * 12 + (today.month - start.month))

    @staticmethod
    def progress_ist(ects_done: int, ects_total: int) -> float:
        """Berechnet IST-Fortschritt (0.0-1.0)."""
        ects_total = ProgressService._clamp_int(ects_total, 1, ECTS_MAX)
        ects_done = ProgressService._clamp_int(ects_done, 0, ects_total)
        return ects_done / ects_total if ects_total else 0.0

    @staticmethod
    def progress_soll(start: date, today: date,
                      duration_months: int = DURATION_MONTHS) -> float:
        """Berechnet SOLL-Fortschritt (0.0-1.0)."""
        duration_months = ProgressService._clamp_int(duration_months, 1, 9999)
        m = ProgressService.months_since(start, today)
        return min(m / duration_months, 1.0)

    @staticmethod
    def ampel(ist: float, soll: float, ects_total: int = 180) -> tuple[str, str]:
        """Bewertet Fortschritt nach Ampellogik.

        - Grün:   im Plan
        - Gelb:   Rückstand ≤ 10 ECTS
        - Rot:    Rückstand > 10 ECTS
        """
        ist = ProgressService._clamp_float(ist, 0.0, 1.0)
        soll = ProgressService._clamp_float(soll, 0.0, 1.0)
        ects_total = ProgressService._clamp_int(ects_total, 1, ECTS_MAX)

        diff_ects = abs((soll - ist) * ects_total)

        if ist >= soll:
            return "green", "im Plan"
        if diff_ects <= 10:
            return "yellow", "etwas hinten dran"
        return "red", "deutlich verzögert"


class GradeService:
    """Prüft, ob die Durchschnittsnote akzeptabel ist."""

    @staticmethod
    def is_ok(avg_grade: float, threshold: float = 3.0) -> bool:
        """True, wenn Note ≤ threshold."""
        try:
            g = float(avg_grade)
        except Exception:
            g = 5.0
        return g <= threshold
