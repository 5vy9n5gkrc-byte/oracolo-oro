"""
Memoria delle previsioni passate.

Ogni apertura del programma:
  1. salva le probabilita' appena calcolate in storico_previsioni.json
  2. verifica le previsioni abbastanza vecchie confrontandole con il
     prezzo reale che si e' poi verificato
  3. calcola, per ciascuno dei 3 modelli, quante volte la direzione
     prevista (salita/discesa) e' risultata corretta
  4. usa questo "tasso di azzeccamento" per scalare (mai amplificare)
     la fiducia delle prossime stime: se un modello ha avuto ragione
     poco piu' della meta' delle volte, le sue probabilita' vengono
     riportate piu' vicino al 50/50, finche' non dimostra di fare
     meglio del caso.

La correzione si attiva solo dopo un numero minimo di previsioni
verificate (SOGLIA_MINIMA_CALIBRAZIONE): con pochi casi sarebbe solo
rumore travestito da imparare.
"""

import json
import os
import pandas as pd

FILE_STORICO = "storico_previsioni.json"
SOGLIA_MINIMA_CALIBRAZIONE = 10


def carica_storico(path=FILE_STORICO):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def salva_storico(storico, path=FILE_STORICO):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(storico, f, ensure_ascii=False, indent=2)


def registra_previsione(storico, data_oggi: str, previsioni: dict):
    """Salva le previsioni di oggi (sovrascrive se gia' presenti per la stessa data)."""
    storico = [r for r in storico if r["data"] != data_oggi]
    record = {
        "data": data_oggi,
        "previsioni": {
            modello: {oriz: {"p_su": v["p_su"]} for oriz, v in oriz_dict.items()}
            for modello, oriz_dict in previsioni.items()
        },
        "esito": {},
    }
    storico.append(record)
    return storico


def verifica_previsioni(storico, gold_close: pd.Series):
    """Riempie l'esito reale delle previsioni per cui e' passato abbastanza tempo."""
    idx = gold_close.index
    aggiornate = 0

    for record in storico:
        if record["esito"].get("1 giorno") and record["esito"].get("1 settimana"):
            continue

        try:
            data_prev = pd.Timestamp(record["data"])
        except (ValueError, TypeError):
            continue

        pos = idx.searchsorted(data_prev)
        if pos >= len(idx) or idx[pos] != data_prev:
            continue
        prezzo_base = float(gold_close.iloc[pos])

        for nome, offset in (("1 giorno", 1), ("1 settimana", 5)):
            if record["esito"].get(nome) is not None:
                continue
            pos_target = pos + offset
            if pos_target >= len(idx):
                continue
            prezzo_target = float(gold_close.iloc[pos_target])
            record["esito"][nome] = {
                "salita": prezzo_target > prezzo_base,
                "variazione": (prezzo_target / prezzo_base - 1) * 100,
            }
            aggiornate += 1

    return storico, aggiornate


def calcola_affidabilita(storico):
    """{modello: {orizzonte: {n, corrette, hit_rate}}} sui casi gia' verificati."""
    risultati = {}
    for record in storico:
        for modello, oriz_dict in record["previsioni"].items():
            for orizzonte, stima in oriz_dict.items():
                esito = record["esito"].get(orizzonte)
                if esito is None or stima["p_su"] is None:
                    continue
                previsto_su = stima["p_su"] > 0.5
                corretto = previsto_su == esito["salita"]
                d = risultati.setdefault(modello, {}).setdefault(orizzonte, {"n": 0, "corrette": 0})
                d["n"] += 1
                d["corrette"] += int(corretto)

    for oriz_dict in risultati.values():
        for d in oriz_dict.values():
            d["hit_rate"] = d["corrette"] / d["n"] if d["n"] > 0 else None
    return risultati


def fattore_fiducia(hit_rate, n, soglia=SOGLIA_MINIMA_CALIBRAZIONE):
    """1.0 = nessuna correzione. Scala verso 0 (cioe' verso il 50/50) se il
    modello ha avuto ragione solo poco piu' della meta' delle volte o peggio."""
    if hit_rate is None or n < soglia:
        return 1.0, False
    return max(0.0, min(1.0, (hit_rate - 0.5) * 2)), True


def calibra(p_su, hit_rate, n):
    fattore, attivo = fattore_fiducia(hit_rate, n)
    if not attivo or p_su is None:
        return p_su, attivo, fattore
    return 0.5 + (p_su - 0.5) * fattore, attivo, fattore
