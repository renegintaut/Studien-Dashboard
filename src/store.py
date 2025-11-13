# store.py – Speichern und Laden der Basisdaten (cfg)
#
# Ziel:
# - Einfache, robuste JSON-Persistenz.
# - Nur *Basisdaten* werden gespeichert (keine abgeleiteten Werte!):
#   program, name, ects_total, ects_done, start (ISO-String), avg_grade
# - Einsteigerfreundlich, gut kommentiert.
#
# Wichtige Regeln:
# - Maximal 180 ECTS (Bachelor).
# - ects_done ∈ [0, ects_total], ects_total ∈ [1, 180]
# - avg_grade ∈ [1.0, 5.0]
# - start wird als ISO-String gespeichert (YYYY-MM-DD)

from __future__ import annotations

import os
import json
from datetime import date, datetime
from typing import Dict, Any


class DataStore:
    """Abstrakte Basis für verschiedene Speicherarten (Interface)."""

    def load(self) -> dict:
        """Lädt gespeicherte Daten und gibt sie als Dict zurück."""
        raise NotImplementedError

    def save(self, cfg: dict) -> None:
        """Speichert die übergebenen Daten."""
        raise NotImplementedError


class JsonStore(DataStore):
    """Einfache JSON-Datei als Speicher-Backend."""

    # Erlaubte Schlüssel (Whitelisting, damit nichts „wildes“ gespeichert wird)
    _ALLOWED_KEYS = {"program", "name", "ects_total", "ects_done", "start", "avg_grade"}

    def __init__(self, path: str) -> None:
        """Legt den Speicher an und sorgt bei Bedarf für den Ordner.

        Args:
            path: Pfad zur JSON-Datei, z. B. "data/basic_config.json".
        """
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    # --------------------------- Defaults --------------------------------- #
    def _defaults(self) -> Dict[str, Any]:
        """Standardwerte, falls Datei fehlt/beschädigt ist."""
        return {
            "program": "",
            "name": "",
            "ects_total": 180,
            "ects_done": 0,
            "start": date.today().isoformat(),  # ISO-String
            "avg_grade": 3.0,
        }

    # ---------------------------- Helpers --------------------------------- #
    @staticmethod
    def _clamp_int(x: Any, lo: int, hi: int) -> int:
        """Ganzzahl in [lo, hi] klemmen (robust)."""
        try:
            v = int(x)
        except Exception:
            v = lo
        return max(lo, min(hi, v))

    @staticmethod
    def _clamp_float(x: Any, lo: float, hi: float) -> float:
        """Float in [lo, hi] klemmen (robust)."""
        try:
            v = float(x)
        except Exception:
            v = lo
        return max(lo, min(hi, v))

    @staticmethod
    def _iso_or_today(x: Any) -> str:
        """Gibt einen ISO-String 'YYYY-MM-DD' zurück. Bei Fehler → heute."""
        if isinstance(x, date):
            return x.isoformat()
        if isinstance(x, str):
            try:
                return datetime.fromisoformat(x).date().isoformat()
            except Exception:
                pass
        return date.today().isoformat()

    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Bereinigt eingehende Daten gemäß Fachregeln & Whitelist.

        - Entfernt unbekannte Keys.
        - Klemmt Werte in sinnvolle Bereiche.
        - Stellt ISO-Format für Datum sicher.
        """
        d = self._defaults()

        # Strings
        d["program"] = str(data.get("program", d["program"])).strip()
        d["name"] = str(data.get("name", d["name"])).strip()

        # ECTS-Regeln
        ects_total = self._clamp_int(data.get("ects_total", d["ects_total"]), 1, 180)
        ects_done = self._clamp_int(data.get("ects_done", d["ects_done"]), 0, ects_total)

        d["ects_total"] = ects_total
        d["ects_done"] = ects_done

        # Datum
        d["start"] = self._iso_or_today(data.get("start", d["start"]))

        # Note
        d["avg_grade"] = self._clamp_float(data.get("avg_grade", d["avg_grade"]), 1.0, 5.0)

        # Nur erlaubte Keys zurückgeben (Whitelisting)
        return {k: d[k] for k in self._ALLOWED_KEYS}

    # ------------------------------ API ----------------------------------- #
    def load(self) -> Dict[str, Any]:
        """Lädt Daten aus JSON. Bei Fehlern werden Defaults genutzt."""
        if not os.path.exists(self.path) or os.stat(self.path).st_size == 0:
            return self._defaults()

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            # Beschädigte Datei: auf Nummer sicher gehen
            return self._defaults()

        # Fehlende Felder auffüllen + Werte bereinigen
        return self._sanitize(raw if isinstance(raw, dict) else {})

    def save(self, cfg: Dict[str, Any]) -> None:
        """Speichert bereinigte Daten als JSON (UTF-8, hübsch eingerückt)."""
        clean = self._sanitize(cfg if isinstance(cfg, dict) else {})
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)
