"""
Elenco di eventi geopolitici storici reali, con data e categoria.

Compilato manualmente dall'assistente sulla base di conoscenza generale
(non da un database strutturato) -> le date possono contenere piccole
imprecisioni (uno o due giorni). Anche ampliato restano pochi eventi per
categoria rispetto a uno studio statistico rigoroso: le statistiche che
se ne ricavano vanno lette come "casi simili nel passato", non come
prova statistica solida.
"""

import pandas as pd

EVENTI = [
    # --- escalation_militare ---
    ("2018-04-14", "escalation_militare", "Raid aereo di USA, Regno Unito e Francia in Siria dopo l'attacco chimico di Douma"),
    ("2019-06-20", "escalation_militare", "L'Iran abbatte un drone da sorveglianza USA nello Stretto di Hormuz"),
    ("2020-01-03", "escalation_militare", "Uccisione del generale iraniano Soleimani in un raid USA"),
    ("2021-05-10", "escalation_militare", "Nuova escalation militare tra Israele e Hamas a Gaza"),
    ("2022-02-24", "escalation_militare", "Invasione russa dell'Ucraina"),
    ("2023-10-07", "escalation_militare", "Attacco di Hamas a Israele, inizio della guerra a Gaza"),
    ("2024-04-13", "escalation_militare", "Attacco con droni e missili dell'Iran su Israele"),
    ("2024-10-01", "escalation_militare", "Nuovo attacco missilistico iraniano su Israele"),
    ("2025-03-15", "escalation_militare", "Gli Stati Uniti intensificano i raid aerei contro gli Houthi in Yemen"),
    ("2025-06-13", "escalation_militare", "Israele colpisce siti nucleari e militari iraniani"),

    # --- deescalation_militare ---
    ("2018-06-12", "deescalation_militare", "Vertice Trump-Kim a Singapore sulla denuclearizzazione nordcoreana"),
    ("2019-02-28", "deescalation_militare", "Secondo vertice Trump-Kim ad Hanoi sulla denuclearizzazione"),
    ("2020-02-29", "deescalation_militare", "Accordo di Doha USA-Talebani per il ritiro delle truppe"),
    ("2022-11-09", "deescalation_militare", "La Russia si ritira dalla citta' ucraina di Kherson"),
    ("2023-11-24", "deescalation_militare", "Tregua temporanea Israele-Hamas con scambio di ostaggi"),
    ("2025-01-19", "deescalation_militare", "Accordo di cessate il fuoco Israele-Hamas a Gaza"),
    ("2025-06-24", "deescalation_militare", "Cessate il fuoco tra Israele e Iran"),

    # --- sanzioni ---
    ("2018-04-06", "sanzioni", "USA sanzionano oligarchi russi (Deripaska/Rusal)"),
    ("2018-08-07", "sanzioni", "USA ripristinano le sanzioni contro l'Iran"),
    ("2018-11-05", "sanzioni", "Gli USA ripristinano tutte le sanzioni sul petrolio iraniano (snapback)"),
    ("2019-09-20", "sanzioni", "Gli USA sanzionano la banca centrale iraniana"),
    ("2020-01-10", "sanzioni", "Nuove sanzioni USA contro l'Iran dopo la crisi Soleimani"),
    ("2022-02-26", "sanzioni", "Russia esclusa dal sistema bancario SWIFT"),
    ("2022-06-03", "sanzioni", "UE approva l'embargo sul petrolio russo (6° pacchetto)"),
    ("2023-02-24", "sanzioni", "Nuovo pacchetto di sanzioni G7/UE contro la Russia"),
    ("2024-06-12", "sanzioni", "L'UE approva il 14° pacchetto di sanzioni contro la Russia"),

    # --- shock_energetico ---
    ("2018-05-08", "shock_energetico", "Trump ritira gli USA dall'accordo nucleare con l'Iran, timori sull'offerta di petrolio"),
    ("2019-09-14", "shock_energetico", "Attacco con droni agli impianti Aramco in Arabia Saudita"),
    ("2020-03-08", "shock_energetico", "Rottura dell'accordo OPEC+ tra Arabia Saudita e Russia"),
    ("2021-03-23", "shock_energetico", "La nave Ever Given blocca il Canale di Suez"),
    ("2022-09-26", "shock_energetico", "Sabotaggio dei gasdotti Nord Stream"),
    ("2023-04-02", "shock_energetico", "Taglio a sorpresa della produzione OPEC+"),
    ("2024-01-12", "shock_energetico", "Attacchi Houthi nel Mar Rosso mettono a rischio le rotte energetiche"),
    ("2025-06-22", "shock_energetico", "L'Iran minaccia la chiusura dello Stretto di Hormuz"),

    # --- instabilita_politica ---
    ("2016-07-15", "instabilita_politica", "Tentato colpo di stato in Turchia"),
    ("2019-06-09", "instabilita_politica", "Inizio delle grandi proteste a Hong Kong"),
    ("2020-08-04", "instabilita_politica", "Esplosione al porto di Beirut, crisi politica in Libano"),
    ("2021-08-15", "instabilita_politica", "Caduta di Kabul e ritorno dei talebani"),
    ("2022-09-23", "instabilita_politica", "Crisi di governo nel Regno Unito (mini-budget Truss)"),
    ("2023-06-24", "instabilita_politica", "Ammutinamento del gruppo Wagner in Russia"),
    ("2024-07-13", "instabilita_politica", "Attentato a Donald Trump durante un comizio elettorale"),
    ("2024-12-03", "instabilita_politica", "Dichiarazione di legge marziale in Corea del Sud"),
    ("2024-12-08", "instabilita_politica", "Caduta del regime di Assad in Siria"),

    # --- politica_monetaria ---
    ("2018-12-19", "politica_monetaria", "La Fed alza i tassi per l'ultima volta del ciclo 2015-2018"),
    ("2019-07-31", "politica_monetaria", "La Fed taglia i tassi per la prima volta dal 2008"),
    ("2020-03-15", "politica_monetaria", "La Fed porta i tassi a zero e lancia un QE illimitato per il COVID"),
    ("2021-11-03", "politica_monetaria", "La Fed annuncia il tapering (riduzione graduale degli stimoli)"),
    ("2022-03-16", "politica_monetaria", "La Fed avvia il ciclo di rialzi piu' aggressivo in decenni"),
    ("2023-07-26", "politica_monetaria", "Ultimo rialzo del ciclo Fed 2022-2023, tassi al picco"),
    ("2024-09-18", "politica_monetaria", "La Fed avvia il ciclo di tagli dei tassi con un taglio da 50 punti base"),

    # --- crisi_finanziaria ---
    ("2018-02-05", "crisi_finanziaria", "\"Volmageddon\": crollo lampo di Wall Street sulla volatilita'"),
    ("2020-03-12", "crisi_finanziaria", "Crollo dei mercati globali per il COVID (\"Black Thursday\")"),
    ("2022-11-08", "crisi_finanziaria", "Crollo dell'exchange di criptovalute FTX"),
    ("2023-03-10", "crisi_finanziaria", "Fallimento della Silicon Valley Bank"),
    ("2023-03-19", "crisi_finanziaria", "Credit Suisse salvata d'urgenza da UBS"),
    ("2024-08-05", "crisi_finanziaria", "Crollo globale dei mercati legato al carry trade sullo yen"),
]


def load_eventi_storici() -> pd.DataFrame:
    df = pd.DataFrame(EVENTI, columns=["date", "class", "descrizione"])
    df["date"] = pd.to_datetime(df["date"])
    return df
