"""
Predittore condizionale: dato un evento geopolitico, cosa fa l'oro?

Principi di progetto:
  1. NOVITA' > GRAVITA'. Conta la sorpresa, non la drammaticita' del titolo.
  2. WALK-FORWARD. La previsione al tempo t usa solo dati fino a t.
  3. ASTENSIONE. Se l'evidenza e' insufficiente, non risponde.
  4. NETTO COSTI. Un edge lordo che non copre lo spread non e' un edge.

Richiede event_study.py nella stessa cartella.

Uso:
    python gold_predictor.py                  # nessun segnale vero nei dati
    python gold_predictor.py --effect 0.008   # segnale vero iniettato
"""

from __future__ import annotations

import argparse
import numpy as np
import pandas as pd
from scipy import stats

from event_study import abnormal_returns, load_synthetic, ESTIM_WINDOW, ESTIM_GAP

# ----------------------------------------------------------------------
# PARAMETRI
# ----------------------------------------------------------------------
HORIZON = 3              # giorni su cui prevediamo
MIN_N = 15               # sotto questo numero di casi storici -> astensione
NOVELTY_WINDOW = 10      # giorni: un evento simile recente riduce la novita'
COST_ROUNDTRIP = 0.0012  # spread + overnight stimati, 0.12% andata/ritorno
CONF = 0.90

EVENT_CLASSES = [
    "escalation_militare",
    "deescalation_militare",
    "sanzioni",
    "shock_energetico",
    "instabilita_politica",
]

# Regole keyword minimali. In produzione qui va una chiamata a un LLM che
# restituisce {classe, novita', intensita'} in JSON: fa un lavoro molto
# migliore su titoli ambigui. Le regole servono come fallback verificabile.
KEYWORDS = {
    "escalation_militare": ["attacco", "raid", "invasione", "bombardamento",
                            "strike", "offensiva", "missili"],
    "deescalation_militare": ["tregua", "cessate il fuoco", "armistizio",
                              "ritiro", "ceasefire", "accordo di pace"],
    "sanzioni": ["sanzioni", "embargo", "dazi", "export control", "blacklist"],
    "shock_energetico": ["oleodotto", "gasdotto", "opec", "stretto di hormuz",
                         "raffineria", "greggio"],
    "instabilita_politica": ["colpo di stato", "golpe", "dimissioni",
                             "elezioni anticipate", "proteste"],
}


# ----------------------------------------------------------------------
# 1. CLASSIFICAZIONE E NOVITA'
# ----------------------------------------------------------------------
def classify(headline: str) -> str | None:
    h = headline.lower()
    scores = {c: sum(k in h for k in kws) for c, kws in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def novelty(event_date, event_class, history: pd.DataFrame) -> float:
    """
    1.0 = evento isolato, informazione nuova.
    ->0 = storyline gia' in corso, il mercato ha gia' prezzato.
    """
    prior = history[(history["class"] == event_class) &
                    (history["date"] < event_date) &
                    (history["date"] >= event_date - pd.Timedelta(days=NOVELTY_WINDOW))]
    if len(prior) == 0:
        return 1.0
    return 1.0 / (1.0 + len(prior))


# ----------------------------------------------------------------------
# 2. MODELLO CONDIZIONALE (addestrato solo sul passato)
# ----------------------------------------------------------------------
class ConditionalModel:
    """Distribuzione empirica del rendimento anomalo, per classe di evento."""

    def __init__(self, prices, horizon=HORIZON):
        self.prices = prices
        self.horizon = horizon
        self.dist = {}

    def fit(self, events: pd.DataFrame, as_of):
        """Usa SOLO gli eventi la cui finestra si e' gia' chiusa prima di as_of."""
        cutoff = as_of - pd.Timedelta(days=self.horizon + 1)
        past = events[events["date"] <= cutoff]
        self.dist = {}
        for cls, grp in past.groupby("class"):
            ars = [abnormal_returns(self.prices, d, self.horizon) for d in grp["date"]]
            ars = np.array([a for a in ars if a is not None])
            if len(ars) >= 3:
                self.dist[cls] = ars
        return self

    def predict(self, event_class, nov=1.0):
        ars = self.dist.get(event_class)
        if ars is None or len(ars) < MIN_N:
            n = 0 if ars is None else len(ars)
            return {"astenuto": True, "motivo": f"casi storici insufficienti (n={n})",
                    "n": n, "classe": event_class}

        n = len(ars)
        mu, sd = ars.mean(), ars.std(ddof=1)
        se = sd / np.sqrt(n)
        tcrit = stats.t.ppf(0.5 + CONF / 2, n - 1)
        lo, hi = mu - tcrit * se, mu + tcrit * se
        p_up = float((ars > 0).mean())

        # la novita' attenua l'ampiezza attesa: storyline vecchia, meno reazione
        mu_adj, lo_adj, hi_adj = mu * nov, lo * nov, hi * nov

        # l'intervallo contiene lo zero -> nessuna direzione affidabile
        if lo_adj <= 0 <= hi_adj:
            return {"astenuto": True,
                    "motivo": f"IC{int(CONF*100)}% attraversa lo zero "
                              f"[{lo_adj:+.2%}, {hi_adj:+.2%}]",
                    "n": n, "classe": event_class, "media": mu_adj}

        netto = abs(mu_adj) - COST_ROUNDTRIP
        return {
            "astenuto": netto <= 0,
            "motivo": None if netto > 0 else "edge lordo inferiore ai costi",
            "classe": event_class,
            "n": n,
            "direzione": "LONG" if mu_adj > 0 else "SHORT",
            "atteso_lordo": mu_adj,
            "atteso_netto": np.sign(mu_adj) * netto,
            "ic": (lo_adj, hi_adj),
            "prob_positivo": p_up,
            "novita": nov,
        }


# ----------------------------------------------------------------------
# 3. BACKTEST WALK-FORWARD
# ----------------------------------------------------------------------
def walk_forward(prices, events, horizon=HORIZON):
    """Per ogni evento: riaddestra sul solo passato, prevede, registra l'esito."""
    events = events.sort_values("date").reset_index(drop=True)
    model = ConditionalModel(prices, horizon)
    rows = []

    for i, ev in events.iterrows():
        model.fit(events, as_of=ev["date"])
        nov = novelty(ev["date"], ev["class"], events.iloc[:i])
        pred = model.predict(ev["class"], nov)
        actual = abnormal_returns(prices, ev["date"], horizon)
        if actual is None:
            continue
        rows.append({
            "date": ev["date"], "class": ev["class"],
            "astenuto": pred["astenuto"],
            "direzione": pred.get("direzione"),
            "atteso": pred.get("atteso_netto", np.nan),
            "reale": actual,
        })
    return pd.DataFrame(rows)


def evaluate(wf: pd.DataFrame):
    tot = len(wf)
    act = wf[~wf["astenuto"]]
    print("=" * 62)
    print(f"Eventi valutati      : {tot}")
    print(f"Astensioni           : {tot - len(act)}  ({(tot-len(act))/max(tot,1):.0%})")
    print(f"Previsioni emesse    : {len(act)}")

    if len(act) < 5:
        print("\nTroppe poche previsioni per una valutazione sensata.")
        print("E' l'esito corretto quando il segnale non c'e'.")
        print("=" * 62)
        return

    signed = np.where(act["direzione"] == "LONG", 1, -1)
    pnl = signed * act["reale"].values - COST_ROUNDTRIP
    hit = float((signed * act["reale"].values > 0).mean())
    t, p = stats.ttest_1samp(pnl, 0)

    print(f"\nHit rate direzionale : {hit:.1%}  (nulla = 50%)")
    print(f"P&L medio netto/trade: {pnl.mean():+.3%}")
    print(f"P&L cumulato         : {pnl.sum():+.2%}")
    print(f"t = {t:+.2f}   p = {p:.3f}")
    print("  --> " + ("edge distinguibile dal rumore"
                      if p < 0.05 and pnl.mean() > 0
                      else "NON distinguibile dal rumore"))
    print("=" * 62)


# ----------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--effect", type=float, default=0.0)
    ap.add_argument("--events", type=int, default=120)
    args = ap.parse_args()

    rng = np.random.default_rng(7)
    prices, events = load_synthetic(n_days=1500, n_events=args.events,
                                    true_effect=0.0)
    # assegna classi e inietta l'effetto SOLO su una classe, come sarebbe
    # se la realta' avesse un segnale concentrato in un tipo di evento
    events["class"] = rng.choice(EVENT_CLASSES, size=len(events))
    if args.effect != 0.0:
        target = "escalation_militare"
        for d in events.loc[events["class"] == target, "date"]:
            pos = prices.index.searchsorted(d)
            prices.iloc[pos:pos + HORIZON, prices.columns.get_loc("gold_ret")] += \
                args.effect / HORIZON
        print(f"[segnale vero iniettato su '{target}': {args.effect:+.2%} a {HORIZON}g]\n")
    else:
        print("[nessun segnale vero nei dati]\n")

    wf = walk_forward(prices, events)
    evaluate(wf)
