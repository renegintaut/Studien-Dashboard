# models.py – Entity-Klassen für das Studien-Dashboard
#
# Ziel:
# - Reine Daten-Objekte mit kleinen, klaren Hilfsmethoden.
# - Keine Business-Logik (die liegt in services.py).
# - Entspricht dem UML (Phase 2): Pruefungsleistung, Modul, Semester, Studiengang.
#
# Hinweise:
# - Enums: ExamType, ExamStatus (und optional AmpelStatus für Typisierungen).
# - Kardinalität: Ein Modul hat 0..3 Prüfungsleistungen (Versuche).
# - Ein Modul gilt als "abgeschlossen", sobald eine Prüfungsleistung bestanden ist.

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum, auto
from typing import List, Optional


# --------------------------------------------------------------------------- #
# Enums (gemäß Feedback: Strings vermeiden)
# --------------------------------------------------------------------------- #

class ExamType(Enum):
    """Art der Prüfungsleistung."""
    KLAUSUR = auto()
    WORKBOOK = auto()
    PROJEKT = auto()


class ExamStatus(Enum):
    """Status einer Prüfungsleistung."""
    BESTANDEN = auto()
    NICHT_BESTANDEN = auto()


class AmpelStatus(Enum):
    """Ampelstatus für den Zeitplan (optional für Typisierungen in Services/UI)."""
    IM_PLAN = auto()
    HINTEN = auto()
    VERZOEGERT = auto()


# --------------------------------------------------------------------------- #
# Entities
# --------------------------------------------------------------------------- #

@dataclass
class Pruefungsleistung:
    """Eine einzelne Prüfungsleistung (Versuch) zu einem Modul."""
    typ: ExamType
    datum: Optional[date] = None
    status: Optional[ExamStatus] = None
    note: Optional[float] = None  # Optional: nur falls Note vergeben wurde

    def ist_bestanden(self) -> bool:
        """True, wenn diese Prüfungsleistung bestanden ist."""
        return self.status == ExamStatus.BESTANDEN


@dataclass
class Modul:
    """Ein Modul mit bis zu 3 Prüfungsleistungen (Versuchen)."""
    code: str
    titel: str
    ects: int
    pruefungen: List[Pruefungsleistung] = field(default_factory=list)

    def fuege_pruefung_hinzu(self, p: Pruefungsleistung) -> None:
        """Fügt eine Prüfungsleistung hinzu (max. 3 Versuche)."""
        if len(self.pruefungen) >= 3:
            # Einsteigerfreundlich: ValueError statt komplexer Fehlerklassen
            raise ValueError("Maximal 3 Prüfungsleistungen pro Modul erlaubt (0..3).")
        self.pruefungen.append(p)

    def abgeschlossen(self) -> bool:
        """True, wenn mindestens eine Prüfungsleistung bestanden wurde."""
        return any(p.ist_bestanden() for p in self.pruefungen)

    def beste_note(self) -> Optional[float]:
        """Gibt die beste (niedrigste) Note einer bestandenen Prüfungsleistung zurück, sonst None."""
        noten = [p.note for p in self.pruefungen if p.ist_bestanden() and p.note is not None]
        return min(noten) if noten else None


@dataclass
class Semester:
    """Ein Semester umfasst mehrere Module und hat (idealerweise) Start/Ende."""
    nummer: int
    start: Optional[date] = None
    ende: Optional[date] = None
    module: List[Modul] = field(default_factory=list)

    def berechne_ende(self) -> Optional[date]:
        """Leichte Heuristik: Wenn 'start' gesetzt ist und 'ende' fehlt, rechne 6 Monate drauf.

        Hinweis: Das ist nur eine einfache Hilfsfunktion für das UML.
        Die echte Zeitplanlogik (SOLL/IST) liegt in den Services.
        """
        if self.ende is not None:
            return self.ende
        if self.start is None:
            return None

        # 6 Monate ≈ 182 Tage; für einen Prototyp genügt diese Vereinfachung.
        return self.start.fromordinal(self.start.toordinal() + 182)

    def ects_abgeschlossen(self) -> int:
        """ECTS-Summe der abgeschlossenen Module in diesem Semester."""
        return sum(m.ects for m in self.module if m.abgeschlossen())


@dataclass
class Studiengang:
    """Der komplette Studiengang mit allen Semestern."""
    name: str
    ects_gesamt: int
    start_datum: date
    semester: List[Semester] = field(default_factory=list)

    # Hinweis: Die folgenden Methoden sind kleine Aggregationen, keine Business-Logik.

    def ects_ist(self) -> int:
        """Aktuell erreichte ECTS (Summe abgeschlossener Module)."""
        return sum(s.ects_abgeschlossen() for s in self.semester)

    def ist_prozent(self) -> float:
        """Anteil (0..1) der bereits erreichten ECTS an 'ects_gesamt'."""
        if self.ects_gesamt <= 0:
            return 0.0
        return self.ects_ist() / self.ects_gesamt

