"""
Scarica prezzi reali di oro e dollaro da Yahoo Finance.

Usiamo DUE fonti per l'oro, per due scopi diversi:
  - GLD (ETF fisico): per la STORIA a 10 anni e tutte le statistiche
    (event study, trend, volatilita'). Il future "continuo" GC=F salta
    da un contratto scaduto al successivo e puo' mostrare variazioni
    giornaliere finte in quei giorni (artefatto di "rollover"); GLD,
    scambiato come un'azione, non ha questo problema.
  - GC=F (future): solo per il prezzo "di oggi" mostrato in cima alla
    pagina. Il vero mercato dell'oro (future, oro fisico nel mondo) e'
    aperto quasi 24 ore su 24 dal lunedi' al venerdi' (piu' un pezzo di
    domenica sera), mentre GLD segue gli orari della Borsa di New York
    (9:30-16:00): usando solo GLD anche per "oggi", il prezzo restava
    fermo fuori da quell'orario nonostante il mercato vero fosse aperto.

GLD viene riscalato con un fattore fisso cosi' i prezzi mostrati
restano in dollari/oncia riconoscibili e coerenti con GC=F.
"""

import numpy as np
import pandas as pd
import urllib.request
import json
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

YF_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_}&interval=1d"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def _scarica_serie(symbol: str, range_: str = "10y") -> pd.Series:
    url = YF_URL.format(symbol=symbol, range_=range_)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)

    result = data["chart"]["result"][0]
    ts = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    idx = pd.to_datetime(ts, unit="s").normalize()
    s = pd.Series(closes, index=idx).dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s


def _scarica_ohlc(symbol: str, range_: str = "5d") -> pd.DataFrame:
    url = YF_URL.format(symbol=symbol, range_=range_)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)

    result = data["chart"]["result"][0]
    ts = result["timestamp"]
    q = result["indicators"]["quote"][0]
    idx = pd.to_datetime(ts, unit="s").normalize()
    df = pd.DataFrame({"open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"]}, index=idx).dropna()
    return df[~df.index.duplicated(keep="last")].sort_index()


def carica_prezzi_reali(range_: str = "10y"):
    """Ritorna (prices, prezzo_oro, prezzo_dollaro, oggi):
      - prices: gold_ret e dxy_ret (rendimenti log giornalieri, da GLD)
      - prezzo_oro, prezzo_dollaro: serie di livello (da GLD, per i grafici storici)
      - oggi: dict con apertura/minimo/massimo/attuale/chiusura_precedente,
        presi dal future GC=F (quasi in tempo reale)
    """
    gld = _scarica_serie("GLD", range_)
    dxy = _scarica_serie("DX-Y.NYB", range_)

    gc_ohlc = _scarica_ohlc("GC=F", "5d")
    riga_oggi = gc_ohlc.iloc[-1]
    riga_ieri = gc_ohlc.iloc[-2]

    fattore = riga_oggi["close"] / gld.iloc[-1]
    gold_equivalente = gld * fattore

    oggi = {
        "apertura": riga_oggi["open"],
        "minimo": riga_oggi["low"],
        "massimo": riga_oggi["high"],
        "attuale": riga_oggi["close"],
        "chiusura_precedente": riga_ieri["close"],
    }

    df = pd.DataFrame({"gold": gold_equivalente, "dxy": dxy}).dropna()
    prices = pd.DataFrame({
        "gold_ret": np.log(df["gold"]).diff(),
        "dxy_ret": np.log(df["dxy"]).diff(),
    }).dropna()
    return prices, df["gold"], df["dxy"], oggi


def stato_mercato():
    """Stato approssimativo dei future sull'oro (CME Globex): aperti quasi
    24 ore su 24, dalla domenica sera alle 18:00 (ora di New York) al
    venerdi' alle 17:00, con una pausa di un'ora ogni sera (17:00-18:00)
    dal lunedi' al giovedi'. Non tiene conto delle festivita' USA."""
    ora_ny = datetime.now(ZoneInfo("America/New_York"))
    giorno, ora = ora_ny.weekday(), ora_ny.time()  # lunedi'=0 ... domenica=6
    chiusura_giornaliera, riapertura_giornaliera = dtime(17, 0), dtime(18, 0)

    if giorno == 5:  # sabato
        aperto = False
    elif giorno == 6:  # domenica: riapre alle 18:00
        aperto = ora >= riapertura_giornaliera
    elif giorno == 4:  # venerdi': chiude alle 17:00 e non riapre
        aperto = ora < chiusura_giornaliera
    else:  # lunedi'-giovedi': aperto tutto il giorno tranne la pausa 17-18
        aperto = not (chiusura_giornaliera <= ora < riapertura_giornaliera)

    return aperto, ora_ny
