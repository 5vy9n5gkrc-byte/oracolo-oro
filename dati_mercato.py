"""
Scarica prezzi reali di oro e dollaro da Yahoo Finance e li trasforma in
rendimenti giornalieri, nello stesso formato che si aspetta
event_study.py (colonne gold_ret, dxy_ret).

Per l'oro usiamo l'ETF fisico GLD invece del future GC=F: il future
"continuo" salta da un contratto scaduto al successivo e puo' mostrare
variazioni giornaliere finte in quei giorni (artefatto di "rollover").
GLD, essendo scambiato come un'azione, non ha questo problema e segue
molto da vicino il prezzo dell'oro fisico. Lo riscaliamo con un fattore
fisso cosi' i prezzi mostrati restano in dollari/oncia riconoscibili.
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
      - prices: gold_ret e dxy_ret (rendimenti log giornalieri)
      - prezzo_oro, prezzo_dollaro: serie di livello
      - oggi: dict con apertura, minimo, massimo del prezzo dell'oro di oggi
    """
    gld = _scarica_serie("GLD", range_)
    dxy = _scarica_serie("DX-Y.NYB", range_)
    spot_oggi = _scarica_serie("GC=F", "5d").iloc[-1]

    fattore = spot_oggi / gld.iloc[-1]
    gold_equivalente = gld * fattore

    gld_ohlc_oggi = _scarica_ohlc("GLD", "5d").iloc[-1]
    oggi = {
        "apertura": gld_ohlc_oggi["open"] * fattore,
        "minimo": gld_ohlc_oggi["low"] * fattore,
        "massimo": gld_ohlc_oggi["high"] * fattore,
    }

    df = pd.DataFrame({"gold": gold_equivalente, "dxy": dxy}).dropna()
    prices = pd.DataFrame({
        "gold_ret": np.log(df["gold"]).diff(),
        "dxy_ret": np.log(df["dxy"]).diff(),
    }).dropna()
    return prices, df["gold"], df["dxy"], oggi


def stato_mercato():
    """Stato approssimativo della borsa dove viene scambiato GLD (NYSE Arca):
    aperta 9:30-16:00 ora di New York, dal lunedi' al venerdi'. Non tiene
    conto delle festivita' USA, solo di orario e giorno della settimana."""
    ora_ny = datetime.now(ZoneInfo("America/New_York"))
    apertura, chiusura = dtime(9, 30), dtime(16, 0)
    feriale = ora_ny.weekday() < 5
    aperto = feriale and apertura <= ora_ny.time() < chiusura
    return aperto, ora_ny
