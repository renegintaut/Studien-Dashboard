# controller.py – Steuerung für das Studien-Dashboard
#
# Der Controller verbindet:
#   - die Datenhaltung (DataStore)
#   - die Logik (ProgressService, GradeService)
#   - und die Anzeige (UI).
#
# Aufgaben:
#   1. Laden & Speichern der Konfiguration
#   2. Übergabe der Daten an die Services
#   3. Bereitstellung eines ViewModels für die UI
#
# Wichtige Prinzipien:
#   - Keine Logik in der UI
#   - Keine abgeleiteten Werte im Speicher (nur Basisdaten)
#   - Robuste Typ- und Werteprüfung

from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict
from services import ProgressService, GradeService, DURATION_MONTHS
from store import DataStore


class DashboardController:
    """Zentrale Steuerung zwischen Daten, Logik und Anzeige."""

    def __init__(self, store: DataStore,
                 psvc: ProgressService,
                 gsvc: GradeService) -> None:
        """Initialisiert Controller und lädt aktuelle Konfiguration."""
        self.store = store
        self.psvc = psvc
        self.gsvc = gsvc
        self.cfg: Dict[str, Any] = self.store.load()

    # ------------------------------------------------------------------ #
    # Konfigurationszugriff
    # ------------------------------------------------------------------ #
    def get_cfg(self) -> Dict[str, Any]:
        """Gibt eine Kopie der gespeicherten Konfiguration zurück."""
        return dict(self.cfg)

    def update_cfg(self, **kwargs: Any) -> None:
        """Aktualisiert Werte in der Konfiguration und speichert sie."""
        allowed = {"program", "name", "ects_total", "ects_done",
                   "start", "avg_grade"}
        for k, v in kwargs.items():
            if k in allowed:
                self.cfg[k] = v
        self.store.save(self.cfg)

    def onboarding_done(self) -> bool:
        """Prüft, ob Name & Studiengang eingetragen sind."""
        return bool(self.cfg.get("program")) and bool(self.cfg.get("name"))

    # ------------------------------------------------------------------ #
    # ViewModel-Berechnung für die UI
    # ------------------------------------------------------------------ #
    def compute_viewmodel(self, today: date | None = None) -> Dict[str, Any]:
        """Berechnet alle Werte, die im Dashboard angezeigt werden."""
        if today is None:
            today = date.today()

        ects_total = self._as_int(self.cfg.get("ects_total", 180), 1, 180)
        ects_done = self._as_int(self.cfg.get("ects_done", 0), 0, ects_total)
        avg_grade = self._as_float(self.cfg.get("avg_grade", 3.0), 1.0, 5.0)
        start_dt = self._parse_date(self.cfg.get("start"), today)

        # Fortschritt & Status berechnen
        ist_pct = self.psvc.progress_ist(ects_done, ects_total)
        soll_pct = self.psvc.progress_soll(start_dt, today, DURATION_MONTHS)
        color, label = self.psvc.ampel(ist_pct, soll_pct, ects_total)
        grade_ok = self.gsvc.is_ok(avg_grade)

        return {
            "ects_total": ects_total,
            "ects_done": ects_done,
            "avg_grade": avg_grade,
            "start": start_dt,
            "ist_pct": ist_pct,
            "soll_pct": soll_pct,
            "ampel_color": color,
            "ampel_label": label,
            "grade_ok": grade_ok,
        }

    # ------------------------------------------------------------------ #
    # Hilfsfunktionen
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_date(val: Any, fallback: date) -> date:
        try:
            if isinstance(val, date):
                return val
            if isinstance(val, str):
                return datetime.fromisoformat(val).date()
        except Exception:
            pass
        return fallback

    @staticmethod
    def _as_int(val: Any, lo: int, hi: int) -> int:
        try:
            x = int(val)
        except Exception:
            x = lo
        return max(lo, min(hi, x))

    @staticmethod
    def _as_float(val: Any, lo: float, hi: float) -> float:
        try:
            x = float(val)
        except Exception:
            x = lo
        return max(lo, min(hi, x))
