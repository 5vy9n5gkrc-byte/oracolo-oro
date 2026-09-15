"""
Grafici a linee in puro SVG (nessuna libreria esterna, funzionano anche
offline): andamento del prezzo dell'oro e della sua volatilita' mobile,
entrambi sugli ultimi 10 anni di dati reali, con le fasce colorate dei
grandi periodi di trend.
"""

import pandas as pd

LARGHEZZA = 720
ALTEZZA = 340
PAD_SX = 60
PAD_DX = 20
PAD_TOP = 30
PAD_BOTTOM = 30

PALETTE = ["#8ecae6", "#ffb703", "#c9ada7", "#a3c4bc", "#bde0fe", "#ffc8dd", "#cdb4db"]


def colore_trend(i: int) -> str:
    return PALETTE[i % len(PALETTE)]


def _scale(serie: pd.Series):
    x0, x1 = PAD_SX, LARGHEZZA - PAD_DX
    y_basso, y_alto = ALTEZZA - PAD_BOTTOM, PAD_TOP

    d_min, d_max = serie.index.min(), serie.index.max()
    v_min, v_max = float(serie.min()), float(serie.max())
    margine = (v_max - v_min) * 0.05
    v_min, v_max = v_min - margine, v_max + margine
    d_span = (d_max - d_min).days

    def x(data):
        frac = (data - d_min).days / d_span
        return x0 + frac * (x1 - x0)

    def y(valore):
        frac = (valore - v_min) / (v_max - v_min)
        return y_basso - frac * (y_basso - y_alto)

    return x, y, d_min, d_max, v_min, v_max


def _griglia(y, v_min, v_max, formato):
    parti = []
    for frac in (0, 1 / 3, 2 / 3, 1.0):
        valore = v_min + frac * (v_max - v_min)
        yy = y(valore)
        parti.append(
            f'<line x1="{PAD_SX}" y1="{yy:.1f}" x2="{LARGHEZZA-PAD_DX}" y2="{yy:.1f}" '
            f'stroke="#e6e0d4" stroke-width="1"/>'
        )
        parti.append(
            f'<text x="{PAD_SX-8}" y="{yy+3:.1f}" font-size="10" text-anchor="end" '
            f'fill="#57606a">{formato(valore)}</text>'
        )
    return parti


def _fasce_trend(x, trend_df, d_min, d_max):
    parti = []
    for i, (_, t) in enumerate(trend_df.iterrows()):
        colore = colore_trend(i)
        inizio = max(t["inizio"], d_min)
        fine = min(t["fine"], d_max)
        x_ini, x_fin = x(inizio), x(fine)
        cx = (x_ini + x_fin) / 2
        parti.append(
            f'<rect x="{x_ini:.1f}" y="{PAD_TOP}" width="{max(x_fin-x_ini,1):.1f}" '
            f'height="{ALTEZZA-PAD_BOTTOM-PAD_TOP}" fill="{colore}" opacity="0.30"/>'
        )
        parti.append(f'<circle cx="{cx:.1f}" cy="{PAD_TOP+12}" r="10" fill="{colore}" stroke="#fff" stroke-width="1.5"/>')
        parti.append(
            f'<text x="{cx:.1f}" y="{PAD_TOP+16}" font-size="11" font-weight="600" '
            f'text-anchor="middle" fill="#1f2328">{i+1}</text>'
        )
    return parti


def _etichette_anni(x, d_min, d_max):
    parti = []
    for anno in range(d_min.year, d_max.year + 1):
        d = pd.Timestamp(year=anno, month=1, day=1)
        if d < d_min or d > d_max:
            continue
        parti.append(
            f'<text x="{x(d):.1f}" y="{ALTEZZA-10}" font-size="10" text-anchor="middle" '
            f'fill="#57606a">{anno}</text>'
        )
    return parti


def _svg(serie: pd.Series, trend_df, formato_y, colore_linea):
    x, y, d_min, d_max, v_min, v_max = _scale(serie)
    settimanale = serie.resample("W").last().dropna()
    punti = " ".join(f"{x(d):.1f},{y(v):.1f}" for d, v in settimanale.items())

    parti = []
    parti += _griglia(y, v_min, v_max, formato_y)
    if trend_df is not None:
        parti += _fasce_trend(x, trend_df, d_min, d_max)
    parti.append(f'<polyline points="{punti}" fill="none" stroke="{colore_linea}" stroke-width="1.8"/>')
    parti += _etichette_anni(x, d_min, d_max)

    return f"""
    <svg viewBox="0 0 {LARGHEZZA} {ALTEZZA}" width="100%" style="max-width:{LARGHEZZA}px; height:auto;">
      {''.join(parti)}
    </svg>
    """


def svg_andamento_oro(gold_close: pd.Series, trend_df: pd.DataFrame) -> str:
    return _svg(gold_close, trend_df, formato_y=lambda v: f"${v:,.0f}", colore_linea="#b8860b")


def svg_volatilita(vol_mobile: pd.Series, trend_df: pd.DataFrame) -> str:
    return _svg(vol_mobile.dropna(), trend_df, formato_y=lambda v: f"{v:.0f}%", colore_linea="#6a4c93")


def svg_confronto(serie_a: pd.Series, nome_a: str, colore_a: str,
                   serie_b: pd.Series, nome_b: str, colore_b: str) -> str:
    """
    Le due serie indicizzate a 100 dal primo giorno in comune. Usano due
    assi verticali indipendenti (uno per ciascuna) invece di uno unico:
    se le due serie si sono mosse di quantita' molto diverse (es. l'oro
    x4 contro il dollaro +-20%), un asse condiviso schiaccerebbe quella
    piu' piccola rendendola illeggibile.
    """
    inizio = max(serie_a.index.min(), serie_b.index.min())
    a = serie_a[serie_a.index >= inizio]
    b = serie_b[serie_b.index >= inizio]
    a_idx = a / a.iloc[0] * 100
    b_idx = b / b.iloc[0] * 100

    pad_top = PAD_TOP + 14  # spazio per la legenda
    pad_dx = PAD_DX + 34  # spazio per le etichette dell'asse destro
    x0, x1 = PAD_SX, LARGHEZZA - pad_dx
    y_basso, y_alto = ALTEZZA - PAD_BOTTOM, pad_top

    d_min = min(a_idx.index.min(), b_idx.index.min())
    d_max = max(a_idx.index.max(), b_idx.index.max())
    d_span = (d_max - d_min).days

    def con_margine(v_min, v_max):
        m = (v_max - v_min) * 0.08
        return v_min - m, v_max + m

    a_min, a_max = con_margine(float(a_idx.min()), float(a_idx.max()))
    b_min, b_max = con_margine(float(b_idx.min()), float(b_idx.max()))

    def x(data):
        return x0 + (data - d_min).days / d_span * (x1 - x0)

    def y_frazione(frac):
        return y_basso - frac * (y_basso - y_alto)

    def y_a(v):
        return y_frazione((v - a_min) / (a_max - a_min))

    def y_b(v):
        return y_frazione((v - b_min) / (b_max - b_min))

    parti = []
    for frac in (0, 1 / 3, 2 / 3, 1.0):
        yy = y_frazione(frac)
        val_a = a_min + frac * (a_max - a_min)
        val_b = b_min + frac * (b_max - b_min)
        parti.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" stroke="#e6e0d4" stroke-width="1"/>')
        parti.append(f'<text x="{x0-8}" y="{yy+3:.1f}" font-size="10" text-anchor="end" fill="{colore_a}">{val_a:.0f}</text>')
        parti.append(f'<text x="{x1+8}" y="{yy+3:.1f}" font-size="10" text-anchor="start" fill="{colore_b}">{val_b:.0f}</text>')

    for serie, y_fn, colore in ((a_idx, y_a, colore_a), (b_idx, y_b, colore_b)):
        settimanale = serie.resample("W").last().dropna()
        punti = " ".join(f"{x(d):.1f},{y_fn(v):.1f}" for d, v in settimanale.items())
        parti.append(f'<polyline points="{punti}" fill="none" stroke="{colore}" stroke-width="1.8"/>')

    parti += _etichette_anni(x, d_min, d_max)

    legenda = f"""
      <circle cx="{x0+4}" cy="16" r="4" fill="{colore_a}"/>
      <text x="{x0+12}" y="20" font-size="11" fill="#1f2328">{nome_a} (asse sx)</text>
      <circle cx="{x0+150}" cy="16" r="4" fill="{colore_b}"/>
      <text x="{x0+158}" y="20" font-size="11" fill="#1f2328">{nome_b} (asse dx)</text>
    """

    return f"""
    <svg viewBox="0 0 {LARGHEZZA} {ALTEZZA}" width="100%" style="max-width:{LARGHEZZA}px; height:auto;">
      {legenda}
      {''.join(parti)}
    </svg>
    """
