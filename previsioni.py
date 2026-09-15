"""
Tre stime di probabilita' che l'oro salga, a 1 giorno e a 1 settimana:

  1. SOLO GEOPOLITICA: guarda solo i casi storici reali delle categorie
     di evento che hanno notizie attive oggi.
  2. SOLO OSCILLAZIONI: tasso di base storico dell'oro sui 10 anni,
     senza guardare nessuna notizia (quanto spesso l'oro sale in un
     giorno/settimana qualsiasi).
  3. COMBINATO: media pesata delle due. Il segnale della geopolitica
     conta in proporzione a quanti casi storici abbiamo davvero; con
     pochi casi il tasso di base pesa di piu' (shrinkage bayesiano).

Sono stime empiriche su un campione reale ma piccolo (specialmente il
modello 1): probabilita' storiche approssimative, non certezze e non
consigli di investimento.
"""

import numpy as np

from event_study import abnormal_returns
from eventi_storici import load_eventi_storici

ORIZZONTI = {"1 giorno": 1, "1 settimana": 5}
K_PRIOR = 15  # forza del tasso di base nella combinazione: piu' alto = piu' peso al tasso di base


def _p_su(valori):
    valori = [v for v in valori if v is not None]
    if not valori:
        return None, 0
    arr = np.array(valori)
    return float((arr > 0).mean()), len(arr)


def tasso_di_base(prices):
    """Modello 2: solo oscillazioni storiche, nessuna notizia."""
    ret = prices["gold_ret"]
    out = {}
    for nome, h in ORIZZONTI.items():
        blocchi = [float(ret.iloc[i:i + h].sum()) for i in range(0, len(ret) - h, h)]
        p, n = _p_su(blocchi)
        out[nome] = {"p_su": p, "n": n}
    return out


def segnale_geopolitico(prices, categorie_attive):
    """Modello 1: solo eventi storici delle categorie con notizie oggi."""
    eventi = load_eventi_storici()
    if categorie_attive:
        eventi = eventi[eventi["class"].isin(categorie_attive)]
    else:
        eventi = eventi.iloc[0:0]

    out = {}
    for nome, h in ORIZZONTI.items():
        ars = [abnormal_returns(prices, d, h) for d in eventi["date"]]
        p, n = _p_su(ars)
        out[nome] = {"p_su": p, "n": n}
    return out


def combinato(base, geo):
    """Modello 3: media pesata (shrinkage bayesiano verso il tasso di base)."""
    out = {}
    for nome in ORIZZONTI:
        p_base = base[nome]["p_su"]
        p_geo, n_geo = geo[nome]["p_su"], geo[nome]["n"]
        if p_geo is None or n_geo == 0 or p_base is None:
            out[nome] = {"p_su": p_base, "n": n_geo}
            continue
        p = (n_geo * p_geo + K_PRIOR * p_base) / (n_geo + K_PRIOR)
        out[nome] = {"p_su": p, "n": n_geo}
    return out


def calcola_previsioni(prices, categorie_attive):
    base = tasso_di_base(prices)
    geo = segnale_geopolitico(prices, categorie_attive)
    comb = combinato(base, geo)
    return {"geopolitica": geo, "oscillazioni": base, "combinato": comb}
