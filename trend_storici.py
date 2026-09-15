"""
I grandi periodi di trend dell'oro negli ultimi 10 anni, con la causa
principale secondo l'assistente.

Sono una sintesi interpretativa (i movimenti dei mercati hanno sempre
piu' cause insieme), non una verita' matematica: servono a dare un
contesto generale, i prezzi e le variazioni percentuali invece sono
calcolati sui dati reali.
"""

import pandas as pd

TREND = [
    ("2016-09-15", "2018-12-31",
     "Consolidamento con i tassi Fed in salita",
     "La Federal Reserve alza gradualmente i tassi e il dollaro resta forte: "
     "senza un forte motivo per comprare oro, il prezzo si muove lateralmente."),

    ("2019-01-01", "2020-08-07",
     "Corsa al record storico: guerra commerciale e COVID-19",
     "Prima la guerra commerciale USA-Cina, poi la pandemia: i tassi reali "
     "crollano sotto zero e le banche centrali inondano i mercati di "
     "liquidita'. L'oro tocca un record storico ad agosto 2020."),

    ("2020-08-08", "2021-12-31",
     "Ritracciamento dopo il record",
     "Con i vaccini e la riapertura dell'economia, i mercati iniziano ad "
     "aspettarsi una stretta monetaria: l'oro perde parte dei guadagni."),

    ("2022-01-01", "2022-10-31",
     "L'oro fatica nonostante la guerra in Ucraina",
     "La Fed alza i tassi al ritmo piu' rapido in decenni per combattere "
     "l'inflazione: il dollaro fortissimo pesa sull'oro piu' di quanto "
     "pesi, in senso opposto, la guerra appena scoppiata."),

    ("2022-11-01", "2023-12-31",
     "Ripresa e acquisti record delle banche centrali",
     "La Fed rallenta la stretta monetaria; le banche centrali (Cina in "
     "testa) accumulano oro a ritmi record per diversificare le riserve; "
     "la crisi delle banche regionali USA (marzo 2023) rilancia la "
     "domanda di rifugio."),

    ("2024-01-01", "2024-12-31",
     "Raffica di record storici",
     "Attese di tagli dei tassi, guerre in corso in Medio Oriente ed Est "
     "Europa, e continui acquisti dei paesi BRICS spingono l'oro a "
     "superare piu' volte il proprio massimo storico."),

    ("2025-01-01", "2026-09-15",
     "Nuovi massimi oltre i 4000 dollari",
     "Guerra commerciale e dazi, timori sul debito pubblico USA, ulteriori "
     "tagli dei tassi e un contesto geopolitico ancora instabile "
     "mantengono l'oro su livelli record."),
]


def load_trend() -> pd.DataFrame:
    df = pd.DataFrame(TREND, columns=["inizio", "fine", "titolo", "causa"])
    df["inizio"] = pd.to_datetime(df["inizio"])
    df["fine"] = pd.to_datetime(df["fine"])
    return df
