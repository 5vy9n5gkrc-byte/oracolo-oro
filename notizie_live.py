"""
Scarica titoli di notizie recenti da Google News RSS, in italiano E in
inglese, per una manciata di query mirate (una per categoria di
evento), cosi' la ricerca e' piu' precisa di una singola parola chiave
generica e copre anche le notizie che escono prima sui media
anglosassoni.
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ogni categoria ha una query in italiano e una in inglese
QUERY_PER_CATEGORIA = {
    "escalation_militare": {
        "it": '"attacco missilistico" OR "raid aereo" OR offensiva OR bombardamento',
        "en": '"missile strike" OR airstrike OR offensive OR bombing',
    },
    "deescalation_militare": {
        "it": '"cessate il fuoco" OR tregua OR armistizio',
        "en": '"ceasefire" OR truce OR armistice',
    },
    "sanzioni": {
        "it": '"nuove sanzioni" OR embargo OR "export control"',
        "en": '"new sanctions" OR embargo OR "export controls"',
    },
    "shock_energetico": {
        "it": 'oleodotto OR gasdotto OR OPEC OR "stretto di Hormuz" OR raffineria',
        "en": 'pipeline OR OPEC OR "strait of hormuz" OR refinery OR oil',
    },
    "instabilita_politica": {
        "it": '"colpo di stato" OR golpe OR dimissioni OR "elezioni anticipate"',
        "en": '"coup d\'etat" OR "snap election" OR resignation',
    },
    "politica_monetaria": {
        "it": '"tassi di interesse" OR "banca centrale" OR Fed OR "taglio dei tassi"',
        "en": '"interest rate" OR "Federal Reserve" OR "rate cut" OR "rate hike"',
    },
    "crisi_finanziaria": {
        "it": '"crisi bancaria" OR "fallimento di una banca" OR "crollo dei mercati"',
        "en": '"bank failure" OR "banking crisis" OR "market crash" OR "market selloff"',
    },
}


def _fetch_rss(query: str, lingua: str, max_items: int = 4):
    parametri = {
        "it": {"hl": "it", "gl": "IT", "ceid": "IT:it"},
        "en": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
    }[lingua]
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": query, **parametri})
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()

    root = ET.fromstring(raw)
    items = []
    for item in root.findall(".//item")[:max_items]:
        title = item.findtext("title", default="").strip()
        pub = item.findtext("pubDate", default="")
        link = item.findtext("link", default="")
        try:
            dt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
        except ValueError:
            dt = None
        items.append({"titolo": title, "data": dt, "link": link})
    return items


def notizie_recenti_per_categoria(max_per_lingua: int = 3):
    """{categoria: [ {titolo, data, link}, ... ]}, unione IT+EN, piu' recenti prima."""
    out = {}
    for cat, query in QUERY_PER_CATEGORIA.items():
        risultati = []
        for lingua in ("it", "en"):
            try:
                risultati += _fetch_rss(query[lingua], lingua, max_per_lingua)
            except Exception:
                pass

        visti = set()
        deduplicati = []
        for r in risultati:
            chiave = r["titolo"].lower()[:60]
            if chiave in visti:
                continue
            visti.add(chiave)
            deduplicati.append(r)

        deduplicati.sort(key=lambda r: r["data"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        out[cat] = deduplicati
    return out
