"""
Event study: le notizie geopolitiche muovono l'oro?

Misura il rendimento ANOMALO dell'oro attorno a eventi geopolitici,
cioe' il rendimento ripulito dal movimento del dollaro, e lo confronta
con un gruppo di controllo di date casuali.

Dipendenze: numpy, pandas, scipy

Uso:
    python event_study.py                 # dati sintetici, per testare la pipeline
    python event_study.py --real          # usa prices.csv e events.csv
"""

import argparse
import numpy as np
import pandas as pd
from scipy import stats

# ----------------------------------------------------------------------
# PARAMETRI - cambiali qui, non sparsi nel codice
# ----------------------------------------------------------------------
ESTIM_WINDOW = 60      # giorni di stima del modello oro~dollaro (pre-evento)
ESTIM_GAP = 5          # giorni di stacco tra fine stima e evento
HORIZONS = [1, 3, 5]   # orizzonti in giorni su cui misurare il CAR
N_PLACEBO = 500        # date casuali per il gruppo di controllo
SEED = 42


# ----------------------------------------------------------------------
# 1. DATI
# ----------------------------------------------------------------------
def load_synthetic(n_days=750, n_events=30, true_effect=0.0, seed=SEED):
    """
    Serie fittizie per testare la pipeline.

    true_effect = rendimento anomalo VERO iniettato il giorno dell'evento.
    Mettilo a 0.0 per verificare che il test non trovi nulla dove non c'e'
    (controllo dei falsi positivi), e a 0.005 per verificare che lo trovi
    quando c'e' (controllo della potenza).
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=n_days)

    # il dollaro fa il suo, l'oro ci reagisce con beta negativo + rumore proprio
    dxy_ret = rng.normal(0, 0.004, n_days)
    gold_ret = -0.6 * dxy_ret + rng.normal(0, 0.010, n_days)

    # eventi distribuiti nella seconda meta' del campione
    ev_idx = rng.choice(np.arange(200, n_days - max(HORIZONS) - 1),
                        size=n_events, replace=False)
    gold_ret[ev_idx] += true_effect

    prices = pd.DataFrame(
        {"gold_ret": gold_ret, "dxy_ret": dxy_ret}, index=dates
    )
    events = pd.DataFrame({"date": dates[np.sort(ev_idx)]})
    return prices, events


def load_real(prices_path="prices.csv", events_path="events.csv"):
    """
    prices.csv : date,gold_close,dxy_close
    events.csv : date,headline,source,severity   (severity opzionale)

    L'oro spot lo prendi da Stooq (xauusd), il dollaro da FRED (DTWEXBGS).
    Gli eventi dalla query GDELT, MAI da una lista compilata a posteriori.
    """
    px = pd.read_csv(prices_path, parse_dates=["date"]).set_index("date").sort_index()
    prices = pd.DataFrame({
        "gold_ret": np.log(px["gold_close"]).diff(),
        "dxy_ret": np.log(px["dxy_close"]).diff(),
    }).dropna()

    events = pd.read_csv(events_path, parse_dates=["date"])
    return prices, events


# ----------------------------------------------------------------------
# 2. RENDIMENTI ANOMALI
# ----------------------------------------------------------------------
def abnormal_returns(prices, event_date, horizon):
    """
    Stima gold_ret = alpha + beta*dxy_ret su una finestra PRE-evento,
    poi restituisce la somma dei residui sui 'horizon' giorni successivi.

    Lo stacco (ESTIM_GAP) evita che la finestra di stima sia contaminata
    da movimenti gia' anticipatori dell'evento.
    """
    idx = prices.index
    pos = idx.searchsorted(event_date)
    if pos >= len(idx):
        return None

    est_end = pos - ESTIM_GAP
    est_start = est_end - ESTIM_WINDOW
    if est_start < 0 or pos + horizon >= len(idx):
        return None

    est = prices.iloc[est_start:est_end]
    X = np.column_stack([np.ones(len(est)), est["dxy_ret"].values])
    y = est["gold_ret"].values
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    alpha, beta = coef

    ev = prices.iloc[pos:pos + horizon]
    expected = alpha + beta * ev["dxy_ret"].values
    return float(np.sum(ev["gold_ret"].values - expected))


def run_event_study(prices, event_dates, horizon):
    cars = [abnormal_returns(prices, d, horizon) for d in event_dates]
    return np.array([c for c in cars if c is not None])


# ----------------------------------------------------------------------
# 3. CONTROLLO PLACEBO
# ----------------------------------------------------------------------
def placebo_distribution(prices, horizon, n=N_PLACEBO, seed=SEED):
    """Stesso calcolo su date casuali. E' il vero benchmark da battere."""
    rng = np.random.default_rng(seed + horizon)
    lo = ESTIM_WINDOW + ESTIM_GAP + 1
    hi = len(prices) - horizon - 1
    picks = rng.choice(prices.index[lo:hi], size=min(n, hi - lo), replace=False)
    return run_event_study(prices, picks, horizon)


# ----------------------------------------------------------------------
# 4. REPORT
# ----------------------------------------------------------------------
def min_detectable_effect(sigma, n, alpha=0.05, power=0.80):
    """Effetto minimo rilevabile: se il tuo CAR medio e' sotto, non puoi saperlo."""
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    return (z_a + z_b) * sigma / np.sqrt(n)


def report(prices, events):
    print("=" * 64)
    print(f"Osservazioni: {len(prices)}   Eventi: {len(events)}")
    print(f"Volatilita' giornaliera oro: {prices['gold_ret'].std():.2%}")
    print("=" * 64)

    for h in HORIZONS:
        car = run_event_study(prices, events["date"], h)
        plc = placebo_distribution(prices, h)
        if len(car) < 5:
            print(f"\n[h={h}g] eventi utilizzabili insufficienti")
            continue

        t, p = stats.ttest_ind(car, plc, equal_var=False)
        # quota di date casuali che batte il CAR medio degli eventi
        pct = float((plc >= car.mean()).mean())
        mde = min_detectable_effect(plc.std(), len(car))

        print(f"\n[orizzonte {h} giorni]  n={len(car)}")
        print(f"  CAR medio eventi   : {car.mean():+.3%}  (sd {car.std():.2%})")
        print(f"  CAR medio placebo  : {plc.mean():+.3%}  (sd {plc.std():.2%})")
        print(f"  t = {t:+.2f}   p = {p:.3f}")
        print(f"  quota di date casuali che fa meglio: {pct:.1%}")
        print(f"  effetto minimo rilevabile con n={len(car)}: {mde:.2%}")
        if p < 0.05 and abs(car.mean()) > mde:
            print("  --> segnale distinguibile dal rumore")
        else:
            print("  --> NON distinguibile dal rumore")

    print("\n" + "-" * 64)
    print("Nota: con 3 orizzonti testati, un p<0.05 isolato non basta.")
    print("Aspettati un falso positivo ogni ~7 test a caso.")
    print("-" * 64)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true", help="usa prices.csv / events.csv")
    ap.add_argument("--effect", type=float, default=0.0,
                    help="effetto vero da iniettare nei dati sintetici (es. 0.005)")
    args = ap.parse_args()

    if args.real:
        prices, events = load_real()
    else:
        prices, events = load_synthetic(true_effect=args.effect)
        print(f"[dati sintetici, effetto vero iniettato: {args.effect:+.2%}]\n")

    report(prices, events)
