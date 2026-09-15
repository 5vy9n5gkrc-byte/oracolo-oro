"""
Modello statistico delle oscillazioni dell'oro sui dati reali a 10 anni:
  - volatilita' generale (quanto si muove l'oro in un giorno normale)
  - punti di massimo stress (giorno migliore/peggiore, massimo ribasso)
  - test statistico rigoroso per categoria di evento: confronta i casi
    storici reali con un campione di date casuali (placebo), lo stesso
    metodo usato in event_study.py sui dati sintetici.
"""

import numpy as np
import pandas as pd
from scipy import stats

from event_study import placebo_distribution, min_detectable_effect

GIORNI_ANNO = 252


def volatilita_generale(prices: pd.DataFrame, gold_close: pd.Series):
    ret = prices["gold_ret"]
    vol_annua = ret.std() * np.sqrt(GIORNI_ANNO) * 100

    peggior_data = ret.idxmin()
    peggior_valore = ret.min() * 100
    miglior_data = ret.idxmax()
    miglior_valore = ret.max() * 100

    massimo_progressivo = gold_close.cummax()
    drawdown = gold_close / massimo_progressivo - 1
    dd_peggiore_data = drawdown.idxmin()
    dd_peggiore_valore = drawdown.min() * 100
    dd_attuale = drawdown.iloc[-1] * 100

    return {
        "vol_annua": vol_annua,
        "peggior_data": peggior_data, "peggior_valore": peggior_valore,
        "miglior_data": miglior_data, "miglior_valore": miglior_valore,
        "dd_peggiore_data": dd_peggiore_data, "dd_peggiore_valore": dd_peggiore_valore,
        "dd_attuale": dd_attuale,
    }


def volatilita_mobile(prices: pd.DataFrame, finestra: int = 30) -> pd.Series:
    """Volatilita' annualizzata su finestra mobile di 'finestra' giorni."""
    return prices["gold_ret"].rolling(finestra).std() * np.sqrt(GIORNI_ANNO) * 100


def test_statistico_categoria(prices: pd.DataFrame, ars_categoria, horizon: int = 3):
    """
    Confronta i rendimenti anomali reali della categoria con un campione
    di date casuali (placebo): stesso test usato in event_study.py.
    """
    ars = np.array([a for a in ars_categoria if a is not None])
    if len(ars) < 5:
        return None

    placebo = placebo_distribution(prices, horizon)
    t, p = stats.ttest_ind(ars, placebo, equal_var=False)
    mde = min_detectable_effect(placebo.std(), len(ars))
    media = float(ars.mean())
    significativo = bool(p < 0.05 and abs(media) > mde)

    return {
        "n": len(ars), "media": media, "t": float(t), "p": float(p),
        "mde": mde, "significativo": significativo,
    }
