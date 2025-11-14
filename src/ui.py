# ui.py – Benutzeroberfläche für das Studien-Dashboard
#
# Anzeige mit Streamlit:
#   - Onboarding (Name & Studiengang)
#   - Eingaben (ECTS, Startdatum, Note)
#   - Kennzahlen & Ampelanzeige
#   - Donut-Diagramme (SOLL / IST)
#
# Änderungen (11/2025):
#   - ECTS-Eingabe nur in 5er-Schritten
#   - ASCII-sichere Darstellung (keine Emojis)

from __future__ import annotations
import os
from datetime import date, datetime
import streamlit as st
from controller import DashboardController
from services import ProgressService, GradeService
from store import JsonStore

# ---------------------- Pfade ---------------------- #
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "basic_config.json")

st.set_page_config(page_title="Studien-Dashboard", layout="wide")

controller = DashboardController(JsonStore(CONFIG_PATH),
                                 ProgressService(),
                                 GradeService())

# ---------------------- Hilfsfunktionen ---------------------- #
def _parse_date_or_today(val: str | date | None) -> date:
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val).date()
        except Exception:
            pass
    return date.today()


def dot_span(color_hex: str, margin_left_px: int = 6) -> str:
    """Erzeugt kleinen farbigen Kreis (HTML-Span)."""
    return (f"<span style='display:inline-block;width:10px;height:10px;"
            f"border-radius:50%;background:{color_hex};"
            f"margin-left:{margin_left_px}px;'></span>")


def status_dot(color_hex: str, label: str) -> None:
    """Zeigt Punkt + Label in einer Zeile."""
    html = f"{dot_span(color_hex, 6)} <b>{label}</b>"
    st.markdown(html, unsafe_allow_html=True)


def donut_chart(percent: float, title: str, scale: float = 0.5):
    """Einfaches Donut-Diagramm."""
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    BG, RING_BG, RING_FG = "#0E1117", "#6B7280", "#1E90FF"
    mpl.rcParams.update({"text.color": "white",
                         "axes.facecolor": BG,
                         "figure.facecolor": BG})
    size = 3.0 * scale
    fig, ax = plt.subplots(figsize=(size, size), dpi=200)
    val = max(0.0, min(1.0, float(percent)))
    ax.pie([1], startangle=90, colors=[RING_BG], radius=1.0,
           wedgeprops=dict(width=0.40, edgecolor=BG))
    if val > 0:
        ax.pie([val, 1-val], startangle=90, colors=[RING_FG, (0,0,0,0)],
               radius=1.0,
               wedgeprops=dict(width=0.40, edgecolor=BG, linewidth=0.5))
    ax.set_aspect("equal")
    ax.set_title(f"{title}\n{val*100:.0f}%", fontsize=7, pad=4)
    return fig

# ---------------------- Hauptfunktion ---------------------- #
def main() -> None:
    cfg = controller.get_cfg()

    # ---------- Onboarding ---------- #
    if "profile_done" not in st.session_state:
        st.session_state.profile_done = controller.onboarding_done()
    if not st.session_state.profile_done:
        st.title("Willkommen! Bitte Profil ausfüllen")
        program = st.text_input("Studiengang", value=cfg.get("program", ""))
        name = st.text_input("Name", value=cfg.get("name", ""))
        if st.button("Speichern & weiter"):
            if program.strip() and name.strip():
                controller.update_cfg(program=program.strip(), name=name.strip())
                st.session_state.profile_done = True
                st.rerun()
            else:
                st.warning("Bitte **Studiengang** und **Name** ausfüllen.")
        st.stop()

    # ---------- Kopfbereich ---------- #
    col_h1, col_h2, col_h3 = st.columns([4, 2, 1])
    with col_h1:
        st.subheader(f"Studiengang: {cfg.get('program','')}")
        st.caption(f"Name: {cfg.get('name','')}")
    with col_h3:
        if st.button("Profil ändern"):
            st.session_state.profile_done = False
            st.rerun()

    # ---------- Seitenleiste ---------- #
    st.sidebar.header("Eingaben")

    ects_total_val = int(cfg.get("ects_total", 180))
    ects_done_val = int(cfg.get("ects_done", 0))
    ects_total_val = min(max(ects_total_val, 1), 180)
    ects_done_val = min(max(ects_done_val, 0), ects_total_val)

    # Nur 5er-Schritte erlaubt
    ects_total = st.sidebar.number_input(
        "ECTS gesamt", min_value=1, max_value=180,
        value=ects_total_val, step=5)
    ects_done = st.sidebar.number_input(
        "ECTS erreicht", min_value=0, max_value=int(ects_total),
        value=ects_done_val, step=5)

    start = st.sidebar.date_input(
        "Studienstart (SOLL 4,5 Jahre)",
        value=_parse_date_or_today(cfg.get("start")))
    avg_grade = st.sidebar.number_input(
        "Durchschnittsnote (gewichtet)",
        min_value=1.0, max_value=5.0,
        value=float(cfg.get("avg_grade", 3.0)),
        step=0.1, format="%.2f")

    if st.sidebar.button("Eingaben speichern"):
        controller.update_cfg(ects_total=int(ects_total),
                              ects_done=int(ects_done),
                              start=start.isoformat(),
                              avg_grade=float(avg_grade))
        st.sidebar.success("Gespeichert.")
    st.sidebar.caption("Hinweis: ECTS nur in 5er-Schritten, max. 180 ECTS.")

    # ---------- Kennzahlen ---------- #
    vm = controller.compute_viewmodel(today=date.today())
    st.markdown("### Kennzahlen")
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)

        st.markdown("**Abschluss innerhalb von 4,5 Jahren**")
        if vm["ampel_color"] == "green":
            status_dot("#16A34A", "im Plan")
        elif vm["ampel_color"] == "yellow":
            status_dot("#CA8A04", "etwas hinten dran")
        else:
            status_dot("#DC2626", "deutlich verzögert")
        st.caption(f"IST {vm['ist_pct']*100:.0f}% • SOLL {vm['soll_pct']*100:.0f}%")

        st.markdown("**Studienfortschritt gesamt in %**")
        st.markdown(f"<b>{vm['ist_pct']*100:.0f}%</b>", unsafe_allow_html=True)
        st.caption(f"ECTS: {vm['ects_done']}/{vm['ects_total']}")

        st.markdown("**Durchschnittsnote**")
        grade_color = "#16A34A" if vm["grade_ok"] else "#DC2626"
        st.markdown(
            f"<b>{vm['avg_grade']:.2f}</b>{dot_span(grade_color,8)}",
            unsafe_allow_html=True)
        st.caption("Richtwert: grün ≤ 3,0")

        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # ---------- Diagramme ---------- #
    st.markdown("### Zeitplan (visuell)")
    left_spacer, c1, c2, right_spacer = st.columns([1.1, 3, 3, 3.9])
    with c1:
        st.pyplot(donut_chart(vm["soll_pct"],
                              "SOLL Zeitplan % \nErwarteter Fortschritt", 0.5))
    with c2:
        st.pyplot(donut_chart(vm["ist_pct"],
                              "IST Zeitplan % \nTatsächlicher Fortschritt", 0.5))


if __name__ == "__main__":
    main()


