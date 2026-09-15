"""
Oracolo dell'Oro - pagina riassuntiva in linguaggio semplice.

Cosa fa, in ordine:
  1. Scarica il prezzo reale dell'oro e del dollaro (Yahoo Finance).
  2. Scarica notizie di oggi per 5 categorie di eventi geopolitici
     (Google News).
  3. Per ogni categoria, confronta con una lista di eventi storici reali
     (eventi_storici.py) e calcola cosa ha fatto davvero l'oro nei 3
     giorni successivi a ciascuno (dati reali, non simulati), con un
     test statistico rigoroso contro un campione di date casuali
     (statistiche.py, stesso metodo di event_study.py).
  4. Calcola un modello di volatilita' generale (statistiche.py) e lo
     disegna in un grafico.
  5. Scrive tutto in una pagina HTML leggibile, il gergo statistico solo
     dove serve ed e' comunque spiegato in una riga.

NON e' consulenza finanziaria. I casi storici sono pochi (compilati a
mano) e l'oro dipende da moltissimi fattori oltre alla geopolitica:
vanno letti come spunti informativi, non come previsioni affidabili.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

from event_study import abnormal_returns, ESTIM_WINDOW, ESTIM_GAP
from eventi_storici import load_eventi_storici
from trend_storici import load_trend
from dati_mercato import carica_prezzi_reali, stato_mercato
from notizie_live import notizie_recenti_per_categoria
from grafico import svg_andamento_oro, svg_volatilita, svg_confronto, colore_trend
from statistiche import volatilita_generale, volatilita_mobile, test_statistico_categoria
from previsioni import calcola_previsioni
import memoria

HORIZON = 3

NOME_CATEGORIA = {
    "escalation_militare": "Escalation militare",
    "deescalation_militare": "De-escalation militare",
    "sanzioni": "Sanzioni",
    "shock_energetico": "Shock energetico",
    "instabilita_politica": "Instabilita' politica",
    "politica_monetaria": "Politica monetaria",
    "crisi_finanziaria": "Crisi finanziaria",
}

DESC_CATEGORIA = {
    "escalation_militare": "attacchi, raid, offensive militari",
    "deescalation_militare": "tregue, cessate il fuoco, ritiri",
    "sanzioni": "nuove sanzioni, embargo, restrizioni commerciali",
    "shock_energetico": "eventi che minacciano l'offerta di energia",
    "instabilita_politica": "colpi di stato, crisi di governo, elezioni",
    "politica_monetaria": "decisioni sui tassi, mosse delle banche centrali",
    "crisi_finanziaria": "fallimenti bancari, crolli di mercato",
}


def prezzo_a(gold_close, data):
    idx = gold_close.index
    pos = min(idx.searchsorted(data), len(idx) - 1)
    return float(gold_close.iloc[pos]), idx[pos]


def calcola_grandi_trend(gold_close):
    trend_df = load_trend()
    righe = []
    for i, (_, t) in enumerate(trend_df.iterrows()):
        p_ini, d_ini = prezzo_a(gold_close, t["inizio"])
        p_fin, d_fin = prezzo_a(gold_close, t["fine"])
        variazione = (p_fin / p_ini - 1) * 100
        righe.append({
            "n": i + 1, "colore": colore_trend(i),
            "titolo": t["titolo"], "causa": t["causa"],
            "d_ini": d_ini, "d_fin": d_fin,
            "p_ini": p_ini, "p_fin": p_fin, "variazione": variazione,
        })
    return trend_df, righe


def render_grandi_trend(righe):
    blocchi = []
    for r in righe:
        colore, segno = badge_colore(r["variazione"] / 100)
        blocchi.append(f"""
        <div class="trend-riga">
          <div class="trend-num" style="background:{r['colore']}">{r['n']}</div>
          <div>
            <h3 class="trend-titolo">{html.escape(r['titolo'])}</h3>
            <p class="muted">
              {r['d_ini'].strftime('%m/%Y')} &ndash; {r['d_fin'].strftime('%m/%Y')} &middot;
              da ${r['p_ini']:,.0f} a ${r['p_fin']:,.0f} &middot;
              <b style="color:{colore}">{segno}{r['variazione']:.0f}%</b>
            </p>
            <p>{html.escape(r['causa'])}</p>
          </div>
        </div>
        """)
    return "".join(blocchi)


def calcola_casi_storici(prices):
    eventi = load_eventi_storici()
    per_categoria = {}
    for cat, gruppo in eventi.groupby("class"):
        casi = []
        for _, ev in gruppo.iterrows():
            ar = abnormal_returns(prices, ev["date"], HORIZON)
            if ar is not None:
                casi.append({"data": ev["date"], "descrizione": ev["descrizione"], "ar": ar})
        per_categoria[cat] = sorted(casi, key=lambda c: c["data"])
    return per_categoria


def riassumi(casi):
    if not casi:
        return None
    n = len(casi)
    saliti = sum(1 for c in casi if c["ar"] > 0)
    media = sum(c["ar"] for c in casi) / n
    return {"n": n, "saliti": saliti, "media": media}


def badge_colore(ar):
    if ar > 0:
        return "#1a7f37", "+"
    if ar < 0:
        return "#cf222e", ""
    return "#57606a", ""


def render_casi(casi):
    righe = []
    for c in casi:
        colore, segno = badge_colore(c["ar"])
        righe.append(f"""
          <li>
            <span class="data-storica">{c['data'].strftime('%d/%m/%Y')}</span>
            {html.escape(c['descrizione'])}
            <span class="var" style="color:{colore}">{segno}{c['ar']*100:.1f}%</span>
          </li>""")
    return "".join(righe)


def render_notizie(notizie):
    if not notizie:
        return '<p class="muted">Nessuna notizia recente trovata per questa categoria.</p>'
    righe = []
    for n in notizie:
        data_str = n["data"].strftime("%d/%m %H:%M") if n["data"] else ""
        righe.append(f"""
          <li>
            <a href="{html.escape(n['link'])}" target="_blank">{html.escape(n['titolo'])}</a>
            <span class="muted">{data_str}</span>
          </li>""")
    return "<ul class='notizie'>" + "".join(righe) + "</ul>"


def render_verdetto_statistico(test):
    if test is None:
        return '<p class="muted">Troppi pochi casi per un test statistico affidabile.</p>'
    if test["significativo"]:
        return f"""
          <p class="verdetto verdetto-si">
            <b>Test statistico: segnale distinguibile dal rumore casuale</b>
            (confrontato con {test['n']} casi vs. date scelte a caso, p={test['p']:.3f}).
            Va comunque preso con cautela: il campione resta piccolo.
          </p>"""
    return f"""
      <p class="verdetto verdetto-no">
        <b>Test statistico: NON distinguibile dal rumore casuale</b>
        (p={test['p']:.3f}). Con soli {test['n']} casi servirebbe una variazione media
        di almeno &plusmn;{test['mde']*100:.1f}% per essere sicuri che non sia frutto del caso.
      </p>"""


def render_sezione(cat, notizie, casi, test):
    riassunto = riassumi(casi)
    if riassunto is None:
        blocco_storico = '<p class="muted">Nessun caso storico disponibile per questa categoria nel periodo coperto dai dati.</p>'
    else:
        colore, segno = badge_colore(riassunto["media"])
        blocco_storico = f"""
          <p class="sintesi">
            In <b>{riassunto['saliti']} casi su {riassunto['n']}</b> passati di questo tipo,
            l'oro e' <b>salito</b> nei {HORIZON} giorni successivi.
            Variazione media reale: <b style="color:{colore}">{segno}{riassunto['media']*100:.1f}%</b>.
          </p>
          <ul class="storico">{render_casi(casi)}</ul>
          {render_verdetto_statistico(test)}
          <p class="muted">Campione piccolo ({riassunto['n']} casi): da leggere con cautela.</p>
        """

    return f"""
    <section class="categoria">
      <h2>{NOME_CATEGORIA[cat]}</h2>
      <p class="muted">{DESC_CATEGORIA[cat]}</p>

      <h3>Notizie di oggi</h3>
      {render_notizie(notizie)}

      <h3>Casi simili nel passato (dati reali)</h3>
      {blocco_storico}
    </section>
    """


def _nota_calibrazione(dettaglio):
    if dettaglio is None:
        return ""
    if not dettaglio["attivo"]:
        return f'<p class="muted">Autocorrezione non ancora attiva (servono {memoria.SOGLIA_MINIMA_CALIBRAZIONE} previsioni verificate, per ora {dettaglio["n_verificate"]}).</p>'
    return (f'<p class="muted">Autocorretto: finora ha indovinato la direzione il '
            f'{dettaglio["hit_rate"]*100:.0f}% delle volte (n={dettaglio["n_verificate"]}) '
            f'&rarr; fiducia scalata di conseguenza.</p>')


def _riga_previsione(stima, dettaglio=None):
    p, n = stima["p_su"], stima["n"]
    if p is None:
        return '<div class="prev-riga muted">dati insufficienti</div>'
    colore = "#1a7f37" if p >= 0.5 else "#cf222e"
    return f"""
      <div class="prev-riga">
        <div class="prev-barra"><div class="prev-riempi" style="width:{p*100:.0f}%; background:{colore}"></div></div>
        <div><b style="color:{colore}">{p*100:.0f}% probabilita' di salita</b>
          <span class="muted">({(1-p)*100:.0f}% di discesa &middot; n={n})</span></div>
        {_nota_calibrazione(dettaglio)}
      </div>"""


def render_previsioni(previsioni_calibrate, dettagli_calibrazione, categorie_attive):
    if categorie_attive:
        elenco_cat = ", ".join(NOME_CATEGORIA[c] for c in categorie_attive)
        nota_geo = f"Categorie con notizie attive oggi: {elenco_cat}."
    else:
        nota_geo = "Nessuna categoria con notizie rilevanti oggi: questo modello non ha un segnale da dare."

    riquadri = [
        ("geopolitica", "1. Solo geopolitica", "Basato solo sui casi storici reali delle categorie con notizie oggi.", nota_geo),
        ("oscillazioni", "2. Solo oscillazioni storiche", "Tasso di base dell'oro sui 10 anni, senza guardare nessuna notizia.", None),
        ("combinato", "3. Combinato", "Media pesata delle prime due: con pochi casi storici prevale il tasso di base.", None),
    ]

    blocchi = []
    for modello, titolo, sotto, nota in riquadri:
        stime = previsioni_calibrate[modello]
        righe = "".join(
            f'<h4>{orizzonte}</h4>{_riga_previsione(stime[orizzonte], dettagli_calibrazione[modello][orizzonte])}'
            for orizzonte in stime
        )
        nota_html = f'<p class="muted">{nota}</p>' if nota else ""
        blocchi.append(f"""
        <div class="prev-card">
          <h3>{titolo}</h3>
          <p class="muted">{sotto}</p>
          {nota_html}
          {righe}
        </div>""")

    return f"""
    <section class="categoria">
      <h2>Probabilita' che l'oro salga</h2>
      <p class="muted">Tre stime diverse, a 1 giorno e a 1 settimana. Sono probabilita' storiche approssimative su un campione reale ma piccolo, non certezze.</p>
      <div class="prev-grid">{''.join(blocchi)}</div>
    </section>
    """


def render_affidabilita(affidabilita, n_verificate_ora):
    nomi_modello = {"geopolitica": "Solo geopolitica", "oscillazioni": "Solo oscillazioni", "combinato": "Combinato"}
    if not affidabilita:
        return """
        <section class="categoria">
          <h2>Quanto ci ha azzeccato finora</h2>
          <p class="muted">Ancora nessuna previsione passata verificata: torna a controllare tra qualche giorno di utilizzo.</p>
        </section>
        """

    righe = []
    for modello in ("geopolitica", "oscillazioni", "combinato"):
        oriz_dict = affidabilita.get(modello, {})
        celle = []
        for orizzonte in ("1 giorno", "1 settimana"):
            info = oriz_dict.get(orizzonte)
            if not info or info["n"] == 0:
                celle.append("<td>n/d</td>")
            else:
                celle.append(f"<td>{info['hit_rate']*100:.0f}% corrette (n={info['n']})</td>")
        righe.append(f"<tr><td><b>{nomi_modello[modello]}</b></td>{''.join(celle)}</tr>")

    nota = f'<p class="muted">{n_verificate_ora} nuove previsioni verificate in questo aggiornamento.</p>' if n_verificate_ora else ""

    return f"""
    <section class="categoria">
      <h2>Quanto ci ha azzeccato finora</h2>
      <p class="muted">Confronto tra le previsioni passate e cosa ha fatto davvero l'oro dopo.</p>
      <table class="affidabilita">
        <tr><th></th><th>1 giorno</th><th>1 settimana</th></tr>
        {''.join(righe)}
      </table>
      {nota}
    </section>
    """


def genera_pagina(output_path="index.html"):
    print("Scarico prezzi reali di oro e dollaro...")
    prices, gold_close, dxy_close, oggi = carica_prezzi_reali()
    prezzo_oggi = float(oggi["attuale"])
    prezzo_ieri = float(oggi["chiusura_precedente"])
    variazione_oggi = (prezzo_oggi / prezzo_ieri - 1) * 100
    min_oggi, max_oggi, apertura_oggi = oggi["minimo"], oggi["massimo"], oggi["apertura"]
    variazione_min_oggi = (min_oggi / prezzo_ieri - 1) * 100
    variazione_max_oggi = (max_oggi / prezzo_ieri - 1) * 100
    variazione_apertura = (apertura_oggi / prezzo_ieri - 1) * 100

    mercato_aperto, ora_ny = stato_mercato()
    if mercato_aperto:
        stato_mercato_testo = f"Mercato aperto (ora di New York {ora_ny.strftime('%H:%M')})"
    else:
        stato_mercato_testo = f"Mercato chiuso, riapre presto (ora di New York {ora_ny.strftime('%H:%M')})"

    print("Scarico le notizie di oggi...")
    notizie_per_categoria = notizie_recenti_per_categoria()
    categorie_attive = [cat for cat, lst in notizie_per_categoria.items() if lst]

    print("Calcolo le tre stime di probabilita'...")
    previsioni = calcola_previsioni(prices, categorie_attive)

    print("Verifico le previsioni passate e calcolo l'autocorrezione...")
    storico = memoria.carica_storico()
    storico, n_verificate_ora = memoria.verifica_previsioni(storico, gold_close)
    affidabilita = memoria.calcola_affidabilita(storico)

    previsioni_calibrate, dettagli_calibrazione = {}, {}
    for modello, oriz_dict in previsioni.items():
        previsioni_calibrate[modello], dettagli_calibrazione[modello] = {}, {}
        for orizzonte, stima in oriz_dict.items():
            info = affidabilita.get(modello, {}).get(orizzonte, {})
            p_cal, attivo, _ = memoria.calibra(stima["p_su"], info.get("hit_rate"), info.get("n", 0))
            previsioni_calibrate[modello][orizzonte] = {"p_su": p_cal, "n": stima["n"]}
            dettagli_calibrazione[modello][orizzonte] = {
                "attivo": attivo, "hit_rate": info.get("hit_rate"), "n_verificate": info.get("n", 0),
            }

    data_oggi_str = gold_close.index[-1].strftime("%Y-%m-%d")
    storico = memoria.registra_previsione(storico, data_oggi_str, previsioni)
    memoria.salva_storico(storico)

    sezione_previsioni = render_previsioni(previsioni_calibrate, dettagli_calibrazione, categorie_attive)
    sezione_affidabilita = render_affidabilita(affidabilita, n_verificate_ora)

    print("Calcolo i grandi trend storici dell'oro...")
    trend_df, righe_trend = calcola_grandi_trend(gold_close)
    grafico_svg = svg_andamento_oro(gold_close, trend_df)
    sezione_trend = render_grandi_trend(righe_trend)

    print("Confronto oro e dollaro...")
    grafico_confronto_svg = svg_confronto(
        gold_close, "Oro", "#b8860b",
        dxy_close, "Dollaro (indice DXY)", "#2274a5",
    )

    print("Calcolo il modello statistico delle oscillazioni...")
    vol_generale = volatilita_generale(prices, gold_close)
    vol_mobile = volatilita_mobile(prices)
    grafico_vol_svg = svg_volatilita(vol_mobile, trend_df)

    print("Calcolo i casi storici reali per categoria...")
    casi_per_categoria = calcola_casi_storici(prices)
    test_per_categoria = {
        cat: test_statistico_categoria(prices, [c["ar"] for c in casi], HORIZON)
        for cat, casi in casi_per_categoria.items()
    }

    aggiornato = datetime.now().strftime("%d/%m/%Y alle %H:%M")

    sezioni = "".join(
        render_sezione(cat, notizie_per_categoria.get(cat, []),
                        casi_per_categoria.get(cat, []), test_per_categoria.get(cat))
        for cat in NOME_CATEGORIA
    )

    sezione_volatilita = f"""
    <section class="categoria">
      <h2>Quanto oscilla l'oro</h2>
      <p class="muted">Modello statistico sulle oscillazioni giornaliere, dati reali degli ultimi 10 anni.</p>
      <p class="sintesi">
        In un giorno "normale" l'oro oscilla di circa
        <b>{vol_generale['vol_annua']/ (252**0.5):.2f}%</b> (volatilita' annualizzata:
        <b>{vol_generale['vol_annua']:.0f}%</b>).
      </p>
      <p>
        Il giorno peggiore: <b>{vol_generale['peggior_valore']:+.1f}%</b> il
        {vol_generale['peggior_data'].strftime('%d/%m/%Y')}.
        Il giorno migliore: <b>{vol_generale['miglior_valore']:+.1f}%</b> il
        {vol_generale['miglior_data'].strftime('%d/%m/%Y')}.
      </p>
      <p>
        Il calo piu' profondo rispetto al massimo storico del momento e' stato
        <b>{vol_generale['dd_peggiore_valore']:.1f}%</b>
        (toccato il {vol_generale['dd_peggiore_data'].strftime('%d/%m/%Y')}).
        Oggi l'oro e' a <b>{vol_generale['dd_attuale']:.1f}%</b> dal suo massimo storico.
      </p>
      <h3>Volatilita' mobile (finestra di 30 giorni, annualizzata)</h3>
      {grafico_vol_svg}
      <p class="muted">I picchi coincidono spesso con i grandi trend segnati sopra: piu' alta la linea, piu' nervoso il mercato in quel momento.</p>
      <p class="muted">Se una delle date qui sopra e' successiva a gennaio 2026, e' oltre il mio limite di conoscenza: il dato e' reale ma non conosco la causa specifica di quel movimento.</p>
    </section>
    """

    colore_var = "#1a7f37" if variazione_oggi >= 0 else "#cf222e"
    segno_var = "+" if variazione_oggi >= 0 else ""

    pagina = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Oracolo dell'Oro</title>
<style>
  body {{
    font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
    max-width: 780px; margin: 0 auto; padding: 24px 16px 60px;
    background: #fbfaf7; color: #1f2328; line-height: 1.5;
  }}
  h1 {{ font-size: 1.6em; margin-bottom: 4px; }}
  .riga-intestazione {{
    display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
    gap: 8px; margin-bottom: 24px;
  }}
  .aggiornato {{ color: #57606a; font-size: 0.9em; }}
  .blocco-aggiorna {{ display: flex; align-items: center; gap: 10px; }}
  #btn-aggiorna {{
    background: #1f2328; color: #fff; border: none; border-radius: 8px;
    padding: 8px 14px; font-size: 0.9em; cursor: pointer;
  }}
  #btn-aggiorna:hover {{ background: #33393f; }}
  #btn-aggiorna:disabled {{ background: #9a9a9a; cursor: default; }}
  #stato-aggiorna {{ font-size: 0.85em; }}
  .prezzo {{
    background: #fff; border: 1px solid #e6e0d4; border-radius: 12px;
    padding: 18px 20px; margin-bottom: 28px;
  }}
  .prezzo .valore {{ font-size: 2em; font-weight: 600; }}
  .prezzo .var {{ font-size: 1.1em; font-weight: 600; }}
  .prezzo .range-oggi {{ margin-top: 4px; }}
  section.categoria {{
    background: #fff; border: 1px solid #e6e0d4; border-radius: 12px;
    padding: 20px 22px; margin-bottom: 20px;
  }}
  h2 {{ margin-top: 0; margin-bottom: 2px; }}
  h3 {{ font-size: 1em; color: #444; margin-bottom: 8px; margin-top: 18px; }}
  .muted {{ color: #57606a; font-size: 0.9em; }}
  ul.notizie {{ list-style: none; padding: 0; margin: 0; }}
  ul.notizie li {{ margin-bottom: 8px; }}
  ul.notizie a {{ color: #0969da; text-decoration: none; }}
  ul.notizie a:hover {{ text-decoration: underline; }}
  ul.notizie .muted {{ display: block; font-size: 0.8em; }}
  .sintesi {{ font-size: 1.02em; }}
  ul.storico {{ padding-left: 18px; margin-top: 6px; }}
  ul.storico li {{ margin-bottom: 6px; }}
  .data-storica {{ color: #57606a; margin-right: 6px; }}
  .var {{ font-weight: 600; margin-left: 6px; }}
  .trend-riga {{ display: flex; gap: 14px; margin-bottom: 20px; }}
  .trend-riga:last-child {{ margin-bottom: 0; }}
  .trend-num {{
    flex: 0 0 26px; width: 26px; height: 26px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 600; font-size: 0.9em; margin-top: 2px;
  }}
  .trend-titolo {{ margin: 0 0 2px; font-size: 1.02em; }}
  .trend-riga p {{ margin: 4px 0; }}
  .verdetto {{ padding: 10px 12px; border-radius: 8px; margin: 10px 0; font-size: 0.92em; }}
  .verdetto-si {{ background: #daf5e0; }}
  .verdetto-no {{ background: #f3f2ee; }}
  .prev-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-top: 14px; }}
  .prev-card {{ background: #fbfaf7; border: 1px solid #e6e0d4; border-radius: 10px; padding: 14px 16px; }}
  .prev-card h3 {{ margin: 0 0 4px; font-size: 0.98em; }}
  .prev-card h4 {{ margin: 12px 0 4px; font-size: 0.85em; color: #444; }}
  .prev-riga {{ margin-bottom: 4px; }}
  .prev-barra {{ background: #e6e0d4; border-radius: 6px; height: 8px; overflow: hidden; margin-bottom: 4px; }}
  .prev-riempi {{ height: 100%; }}
  table.affidabilita {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
  table.affidabilita th, table.affidabilita td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #e6e0d4; font-size: 0.92em; }}
  table.affidabilita th {{ color: #57606a; font-weight: 500; }}
  footer {{
    margin-top: 32px; padding-top: 16px; border-top: 1px solid #e6e0d4;
    color: #57606a; font-size: 0.85em;
  }}
</style>
</head>
<body>
  <h1>Oracolo dell'Oro</h1>
  <div class="riga-intestazione">
    <div class="aggiornato">Aggiornato il {aggiornato}</div>
    <div class="blocco-aggiorna">
      <button id="btn-aggiorna" onclick="aggiornaDati()" style="display:none">&#8635; Aggiorna dati</button>
      <span id="stato-aggiorna" class="muted"></span>
      <span id="nota-auto" class="muted" style="display:none">Si aggiorna da solo ogni 30 minuti circa</span>
    </div>
  </div>

  <div class="prezzo">
    <div class="muted">Prezzo oro (future COMEX, USD/oncia)</div>
    <div class="valore">${prezzo_oggi:,.2f}</div>
    <div class="var" style="color:{colore_var}">{segno_var}{variazione_oggi:.2f}% oggi</div>
    <div class="range-oggi muted">Range odierno: {variazione_min_oggi:+.2f}% / {variazione_max_oggi:+.2f}% (${min_oggi:,.2f} &ndash; ${max_oggi:,.2f})</div>
    <div class="range-oggi muted">Apertura: ${apertura_oggi:,.2f} ({variazione_apertura:+.2f}%) &middot; Chiusura precedente: ${prezzo_ieri:,.2f}</div>
    <div class="range-oggi muted">{stato_mercato_testo}</div>
  </div>

  {sezione_previsioni}

  {sezione_affidabilita}

  <section class="categoria">
    <h2>Andamento a 10 anni</h2>
    <p class="muted">I numeri colorati indicano i grandi periodi di trend descritti sotto.</p>
    {grafico_svg}
  </section>

  <section class="categoria">
    <h2>Oro vs Dollaro</h2>
    <p class="muted">Entrambi indicizzati a 100 all'inizio del periodo, per confrontare l'andamento relativo. Quando il dollaro sale, l'oro tende a scendere e viceversa: si vede spesso nei grandi trend qui sotto.</p>
    {grafico_confronto_svg}
  </section>

  <section class="categoria">
    <h2>I grandi trend dell'oro</h2>
    <p class="muted">Le cause sono una sintesi interpretativa: i movimenti dei mercati hanno sempre piu' fattori insieme.</p>
    {sezione_trend}
  </section>

  {sezione_volatilita}

  {sezioni}

  <footer>
    <b>Non e' consulenza finanziaria.</b> I "casi simili nel passato" e i
    "grandi trend" si basano su eventi e periodi reali ricostruiti a memoria
    dall'assistente (non un database esaustivo): possono contenere
    imprecisioni di data, e le cause indicate per ogni trend sono una
    sintesi semplificata, non l'unica spiegazione possibile. Il campione
    resta piccolo per essere una prova statistica solida. Le notizie di
    oggi sono classificate con semplici parole chiave e possono contenere
    articoli non pertinenti. I prezzi (oro e dollaro) vengono da Yahoo
    Finance e possono avere qualche minuto di ritardo. L'oro e' influenzato
    da tassi di interesse, inflazione, dollaro e molti altri fattori oltre
    alla geopolitica. Le probabilita' di salita/discesa sono frequenze
    storiche calcolate su questi stessi dati (non un modello previsivo
    validato): il modello "solo geopolitica" in particolare si basa su
    pochissimi casi per categoria, quindi puo' oscillare molto da un
    giorno all'altro a seconda di quali notizie sono uscite.
  </footer>

  <script>
    // il pulsante "Aggiorna" funziona solo in locale (parla con server.py):
    // su un sito pubblicato (es. GitHub Pages) non c'e' un server dietro,
    // quindi mostriamo invece la nota sull'aggiornamento automatico.
    if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {{
      document.getElementById('btn-aggiorna').style.display = 'inline-block';
    }} else {{
      document.getElementById('nota-auto').style.display = 'inline';
    }}

    async function aggiornaDati() {{
      const btn = document.getElementById('btn-aggiorna');
      const stato = document.getElementById('stato-aggiorna');
      btn.disabled = true;
      stato.textContent = 'Aggiornamento in corso... (10-20 secondi)';

      let resp;
      try {{
        resp = await fetch('/aggiorna', {{method: 'POST'}});
      }} catch (e) {{
        stato.textContent = "Impossibile contattare il server. Assicurati di aver aperto la pagina con \\"Apri Oracolo Oro.command\\" (non aprendo il file .html direttamente).";
        btn.disabled = false;
        return;
      }}

      if (resp.ok) {{
        location.reload();
        return;
      }}

      const testo = await resp.text();
      const ultimaRiga = testo.trim().split('\\n').pop();
      stato.textContent = 'Errore durante l\\'aggiornamento: ' + ultimaRiga + ' (riprova tra poco)';
      btn.disabled = false;
    }}
  </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(pagina)
    print(f"Fatto: {output_path}")
    return output_path


if __name__ == "__main__":
    genera_pagina()
