#!/usr/bin/env python3
"""CryptoFlop — fetch market data, compute scores, write data.json.

Uruchamiane przez GitHub Actions (cron '0 * * * *'). Uwaga: Actions throttluje
scheduled runy — realna kadencja to ~1,5–5h, nie 1h. Żadne okno/bufor nie może
więc zakładać "N wpisów = N godzin". No external deps (stdlib only).

Note: Binance API jest zablokowane dla US data centerów (HTTP 451),
więc na GitHub Actions używamy CoinGecko (działa globalnie).
"""

import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data.json"
HISTORY_FILE = ROOT / "history.json"
SPARKLINE_LEN = 24      # last 24 entries — przy realnej kadencji ~1,5-5h to ~2-4 dni trendu
DAILY_OPP_LEN = 30      # pasek "ostatnie 30 dni" — jeden wpis okazji na dzień kalendarzowy
SCORE_VERSION = "opportunity_v1"  # sens serii score (sentyment -> okazja); zmiana => reset baz
HALVING_DATE = datetime(2024, 4, 19)  # Bitcoin 4th halving

DAY_NAMES_PL = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
MONTHS_PL = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
             "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]


def fetch_json(url, timeout=20, retries=3):
    """GET JSON z prostym retry na transient 429/5xx (exponential backoff)."""
    req = urllib.request.Request(url, headers={"User-Agent": "cryptoflop/0.1"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                wait = 5 * (2 ** attempt)  # 5s, 10s, 20s
                print(f"  HTTP {e.code} z {url[:50]}… — retry za {wait}s")
                time.sleep(wait)
                continue
            raise


# ---------- Wynik OKAZJI do kupna (0-100, 100 = najlepszy moment na zakup) ----------
# Narzędzie służy DO JEDNEGO: "czy warto dziś dokupić w ramach DCA". Wynik jest
# więc kontrariański — wysoki, gdy rynek jest w strachu (niski F&G), gdy cena
# stoi nisko w zakresie 90 dni i spadła przez ostatni miesiąc. Dzięki temu
# istniejąca skala kolorów (high = zielony) niesie wprost jedno znaczenie:
# ZIELONY = największa szansa na zakup. To zastępuje dawny "sentyment" jako
# główną, jedyną liczbę 0-100 w całej aplikacji (home, werdykt, prognoza).

# Wagi per-asset: F&G to indeks BTC-centryczny, więc dla BTC waży najwięcej;
# BNB ma własną dynamikę cenową, więc sygnały cenowe (pozycja, trend) ważą tam
# mocniej, a wspólny F&G mniej.
OPP_WEIGHTS = {
    "btc": {"fng": 0.45, "pos": 0.30, "trend30": 0.25},
    "bnb": {"fng": 0.35, "pos": 0.35, "trend30": 0.30},
}
OPP_TREND30_FULL = 25.0   # -25%/30d => maks. okazja z tej składowej (jak skala 30d)

# Próg "taniości" 30d — JEDNO źródło prawdy dla: kropki "Cena" na home, tekstu
# tej kropki, sygnału "Trend 30 dni" na detalu ORAZ nagłówka okazji. Wcześniej
# każde z nich miało własny próg (pos<=0,5 vs pos<=0,25 vs -10%), co dawało
# zieloną kropkę obok "śr. zakresu" i nagłówek "stoi nisko" przy pozycji 27%.
CHEAP_30D_PCT = -8.0

# Progi werdyktu — skalibrowane backtestem na 6 mies. realnych cen + F&G.
# OKAZJA podniesiona do 84, by była realnie WYJĄTKOWA (~8-13% dni: BTC 13/71/16,
# BNB 8/79/13 okazja/tak/wstrzymaj) — przy 74 padała w 31-40% dni i słowo traciło
# wagę (78 to OKAZJA, 70 to KUP wyglądało arbitralnie). KUP to codzienność,
# CZEKAJ zapala się na szczytach. OPP_TAK=42 sprawdzony (34 prawie zabija
# wstrzymaj, 50 odpala je za często).
OPP_OKAZJA = 84    # >= => "okazja" (głęboki strach + tanio — rzadki, wyjątkowy dzień)
OPP_TAK = 42       # >= => "tak" (zwykły dzień DCA); poniżej => "wstrzymaj"


def opp_from_pct(pct, full_scale=OPP_TREND30_FULL):
    """Spadek ceny = wyższa okazja. -full% => 100, 0% => 50, +full% => 0."""
    return int(max(0, min(100, round(50 - pct / full_scale * 50))))


def opportunity_score(asset_key, fng, pos_90d, pct_30d):
    """Złożony wynik okazji 0-100 z trzech kontrariańskich składowych."""
    w = OPP_WEIGHTS[asset_key]
    opp_fng = 100 - fng                       # strach => wysoka okazja
    opp_pos = 100 - round(pos_90d * 100)      # nisko w zakresie 90d => wysoka okazja
    opp_trend = opp_from_pct(pct_30d)         # spadek 30d => wysoka okazja
    raw = w["fng"] * opp_fng + w["pos"] * opp_pos + w["trend30"] * opp_trend
    return int(max(0, min(100, round(raw))))


def opp_level(opp):
    """3-stopniowy werdykt z wyniku okazji (jedno źródło prawdy)."""
    if opp >= OPP_OKAZJA:
        return "okazja"
    if opp >= OPP_TAK:
        return "tak"
    return "wstrzymaj"


def opp_word(level):
    return {"okazja": "OKAZJA", "tak": "KUP", "wstrzymaj": "CZEKAJ"}[level]


def opp_label(opp):
    # Górne pasma kluczone do OPP_OKAZJA/OPP_TAK, żeby etykieta nigdy nie
    # przebijała słowa-werdyktu (np. "Dobra okazja" w dniu, gdy słowo to KUP).
    if opp >= 90: return "Wyjątkowa okazja"
    if opp >= OPP_OKAZJA: return "Dobra okazja"
    if opp >= 60: return "Sprzyja zakupom"
    if opp >= OPP_TAK: return "Zwykły dzień"
    if opp >= 28: return "Raczej drogo"
    if opp >= 16: return "Drogo"
    return "Przegrzane"


def pos_band(pos):
    """Kanoniczne pasma pozycji ceny w zakresie 90d — jedno źródło prawdy
    (nisko / środek / wysoko), używane przez sygnał 'Cena vs 3 mies.' na detalu."""
    if pos <= 0.33:
        return "nisko"
    if pos >= 0.66:
        return "wysoko"
    return "srodek"


def pct_change_from_prices(prices, days):
    if len(prices) < days + 1:
        return 0.0
    return (prices[-1] - prices[-1 - days]) / prices[-1 - days] * 100


def fmt_price(p):
    if p >= 10000:
        return ("$" + f"{int(p):,}").replace(",", " ")
    if p >= 100:
        return f"${p:,.0f}".replace(",", " ")
    return f"${p:,.2f}".replace(",", " ").replace(".", ",")


def fmt_pct(p):
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.1f}%".replace(".", ",")


def load_history():
    h = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else {"scores": {}}
    h.setdefault("scores", {})
    # Serie score 'btc'/'bnb' zmieniły sens (sentyment -> okazja do kupna).
    # Gdy marker wersji nie pasuje, zresetuj je, by baza prognozy nie mieszała
    # niekompatybilnych skal — wymuszone kodem, nie ręczną migracją pliku.
    if h.get("score_version") != SCORE_VERSION:
        h["scores"]["btc"] = []
        h["scores"]["bnb"] = []
        h["score_version"] = SCORE_VERSION
    return h


def push_score(history, key, score):
    arr = history["scores"].setdefault(key, [])
    arr.append(score)
    if len(arr) > SPARKLINE_LEN:
        del arr[: len(arr) - SPARKLINE_LEN]
    return list(arr)


def push_daily_opp(history, key, opp):
    """Jedna wartość OKAZJI na dzień kalendarzowy (ostatnie 30 dni) — pasek
    "30 dni do tyłu". Re-run tego samego dnia aktualizuje ostatni wpis, więc
    pasek pokazuje 30 realnych dni, nie 30 ostatnich odświeżeń."""
    today = datetime.now().strftime("%Y-%m-%d")
    date_key = f"{key}_last_date"
    arr = history.setdefault(key, [])
    if history.get(date_key) == today and arr:
        arr[-1] = opp
    else:
        arr.append(opp)
        if len(arr) > DAILY_OPP_LEN:
            del arr[: len(arr) - DAILY_OPP_LEN]
    history[date_key] = today
    return list(arr)


def okazja_streak(daily, threshold=None):
    """Ile ostatnich DNI z rzędu (z dziennej serii okazji) wynik >= próg OKAZJA.
    Służy do ramki "okno otwarte od N dni — akumuluj wg planu" zamiast codziennego
    superlatywu "wyjątkowa okazja" w utrzymującej się bessie (audyt 2026-06-25)."""
    th = OPP_OKAZJA if threshold is None else threshold
    s = 0
    for v in reversed(daily):
        if v >= th:
            s += 1
        else:
            break
    return s


def forecast_volume(price_change_7d, vol_now, vol_30d_avg):
    """Wolumen POTWIERDZA ruch ceny. Cena w górę z wolumenem => okazja maleje
    (drożeje przekonująco); cena w dół z wolumenem => okazja rośnie. Delta
    dotyczy OKAZJI, więc jest przeciwna do kierunku ceny."""
    direction = 1 if price_change_7d > 0.5 else -1 if price_change_7d < -0.5 else 0
    if direction == 0 or vol_30d_avg == 0:
        return (0, "Ruch w cenie zbyt mały, by oceniać potwierdzenie wolumenem")
    ratio = vol_now / vol_30d_avg
    pct_str = f"{(ratio - 1) * 100:+.0f}%"
    kierunek_s = "w górę" if direction > 0 else "w dół"
    okno_s = "okno zakupowe się domyka" if direction > 0 else "okno zakupowe się otwiera"
    if ratio > 1.2:
        return (-5 * direction, f"Ruch {kierunek_s} z wolumenem {pct_str} vs 30d — {okno_s} przekonująco")
    elif ratio < 0.9:
        return (-2 * direction, f"Ruch {kierunek_s} bez wolumenu ({pct_str} vs 30d) — słabe potwierdzenie")
    else:
        return (-3 * direction, f"Ruch {kierunek_s} z umiarkowanym wolumenem ({pct_str} vs 30d)")


def forecast_mean_reversion(fng, prices, trend30=0.0):
    """Skrajności wracają do średniej. Strach/tanio (wysoka okazja DZIŚ) zwykle
    odbija => okazja MALEJE (okno się domyka). Chciwość/drogo => korekta może
    OTWORZYĆ lepsze okno => okazja rośnie. Delta dotyczy okazji.

    BRAMKA TRENDU (audyt 2026-06-25): w utrzymanym trendzie spadkowym
    (trend30 <= CHEAP_30D_PCT ORAZ cena wciąż przy dnie 90d) zakład o odbicie
    jest systematycznie błędny — to właśnie ujemny wkład tej reguły mylił
    kierunek prognozy 0/3 razy w realnym oknie 15-25.06 (strach pogłębiał się,
    a okazja rosła). W takim reżimie wyciszamy kontrariański (ujemny) wkład."""
    pos = None
    if len(prices) >= 90:
        window = prices[-90:]
        lo, hi = min(window), max(window)
        if hi > lo:
            pos = (prices[-1] - lo) / (hi - lo)
    strong_downtrend = trend30 <= CHEAP_30D_PCT and pos is not None and pos < 0.15

    delta_v = 0
    notes = []
    if fng <= 35:
        d = min(4, round((35 - fng) * 0.2))
        if d and not strong_downtrend:
            delta_v -= d
            notes.append(f"F&G {fng} (strach) — rynek wyprzedany, odbicie domyka okno")
    elif fng >= 65:
        d = min(4, round((fng - 65) * 0.2))
        if d:
            delta_v += d
            notes.append(f"F&G {fng} (chciwość) — korekta może otworzyć lepsze okno")

    if pos is not None:
        if pos > 0.9:
            delta_v += 3
            notes.append("Cena przy szczycie zakresu 90d — przestrzeń do spadku")
        elif pos < 0.1 and not strong_downtrend:
            delta_v -= 3
            notes.append("Cena przy dnie zakresu 90d — odbicie prawdopodobne")

    if strong_downtrend:
        notes.append("trwały trend spadkowy — reguła odbicia wyciszona (w trendzie myli kierunek)")
    if not notes:
        return (0, f"F&G {fng} i pozycja w 90d range neutralne")
    return (delta_v, "; ".join(notes))


def forecast_momentum(prices):
    """Streak na PEŁNYCH zamknięciach dziennych — ostatni punkt market_chart
    to dzień częściowy (cena "teraz"), więc go pomijamy; inaczej wynik reguły
    zależał od godziny runa. Wymagamy >= 2 pełnych dni, bo streak=1 to szum,
    który i tak ma już wagę w score (zmiana 24h)."""
    closes = prices[:-1]
    if len(closes) < 4:
        return (0, "Za mało historii do oceny streaku")
    threshold = 0.002  # 0.2%
    streak = 0
    direction = 0
    for i in range(len(closes) - 1, 0, -1):
        change = (closes[i] - closes[i - 1]) / closes[i - 1]
        if abs(change) < threshold:
            break
        sign = 1 if change > 0 else -1
        if direction == 0:
            direction = sign
            streak = 1
        elif sign == direction:
            streak += 1
        else:
            break

    if streak < 2 or direction == 0:
        return (0, "Brak wyraźnego streaku cenowego (min. 2 pełne dni)")

    # Delta dotyczy OKAZJI, więc przeciwna do kierunku ceny: cena rośnie =>
    # okazja maleje (drożeje). Przy wyczerpaniu długiego streaku spodziewamy się
    # odwrócenia ceny, więc znak się zmienia.
    kierunek_s = "w górę" if direction > 0 else "w dół"
    taniej_s = "drożeje" if direction > 0 else "tanieje"
    if streak <= 3:
        return (-direction * 3, f"{streak} dni z rzędu {kierunek_s} — kontynuacja, rynek {taniej_s}")
    elif streak <= 5:
        return (-direction * 1, f"{streak} dni z rzędu {kierunek_s} — momentum stygnie")
    else:
        return (direction * 3, f"{streak} dni z rzędu {kierunek_s} — wyczerpanie, odwrócenie prawdopodobne")


def forecast_cycle(months):
    """Faza cyklu vs okazja: wczesna hossa => okazje raczej znikają (okna
    drożeją); po szczycie => bearish bias => okna zakupowe raczej się poprawiają."""
    if months < 12:
        return (-3, f"{months} mies. po halvingu — wczesna hossa, okazje raczej znikają")
    elif months < 18:
        return (0, f"{months} mies. po halvingu — dojrzała faza wzrostu (neutralnie)")
    elif months < 24:
        return (2, f"{months} mies. po halvingu — bliski szczyt cyklu, ryzyko korekty rośnie")
    else:
        return (3, f"{months} mies. po halvingu — cykl po szczycie, okna zakupowe raczej się poprawiają")


def forecast_relative_strength(rel_7d):
    """Reguła tylko dla BNB: siła relatywna do BTC w 7d. Relatywna siła => BNB
    drożeje względem BTC => mniejszy rabat (okazja maleje); słabość => większy
    rabat względem BTC (okazja rośnie)."""
    if rel_7d > 3:
        return (-2, f"BNB względem Bitcoina {fmt_pct(rel_7d)} w 7d — relatywna siła, mniejszy rabat")
    if rel_7d < -3:
        return (2, f"BNB względem Bitcoina {fmt_pct(rel_7d)} w 7d — relatywna słabość, większy rabat")
    return (0, f"BNB względem Bitcoina {fmt_pct(rel_7d)} w 7d — porusza się z rynkiem")


def compose_forecast(score_base, deltas_with_notes):
    """deltas_with_notes: list of dicts {name, delta, note}. Returns forecast dict.

    score_base to WYGŁADZONA baza (średnia z ostatnich refreshy), nie chwilowy
    score zdominowany przez zmianę 24h — pasmo nie może być węższe niż szum
    samej bazy między odświeżeniami (min. 12 pkt)."""
    deltas = [r["delta"] for r in deltas_with_notes]
    total = max(-30, min(30, sum(deltas)))
    expected = max(0, min(100, score_base + total))

    # Reguły STRUKTURALNE (np. faza cyklu — stała przez miesiące) nie są
    # "głosem" świadczącym o zgodzie sygnałów dzień-do-dnia, więc nie podbijają
    # bramki konwikcji. Inaczej stałe +3 sztucznie robiło z prognozy "pewną".
    active = sum(1 for r in deltas_with_notes
                 if r["delta"] != 0 and not r.get("structural"))

    spread = max(deltas) - min(deltas)
    all_same_sign = all(d >= 0 for d in deltas) or all(d <= 0 for d in deltas)
    if all_same_sign and spread <= 5:
        width = 12
    elif spread <= 8:
        width = 16
    else:
        width = 22

    lo = max(0, expected - width // 2)
    hi = min(100, expected + width // 2)
    # Pasmo przycięte do krawędzi skali raportujemy jednostronnie ("≥85"),
    # bo "[85,100]" udaje przedział, którego górny koniec jest praktycznie
    # nieosiągalny (F&G=0 ∧ pos=0 ∧ trend≤-25% naraz) — to fikcyjna precyzja.
    clamped = "hi" if expected + width // 2 > 100 else \
              "lo" if expected - width // 2 < 0 else None

    # Konwikcja: gdy o kierunku decyduje dominujący (co do wielkości) głos
    # "Powrót do średniej" — czyli kontrariański zakład o odbicie — nie wolno
    # wystawiać "high". To właśnie ten zakład mylił kierunek 0/3 w trendzie.
    nonzero = [r for r in deltas_with_notes if r["delta"] != 0]
    dominant = max(nonzero, key=lambda r: abs(r["delta"]), default=None)
    reversion_drives = dominant is not None and dominant["name"] == "Powrót do średniej"

    # Konwikcja wymaga zgody między AKTYWNYMI regułami — milczące reguły
    # (delta 0) to brak głosu, nie zgoda. [0,0,0,-3] ma być "low", nie "high".
    if active <= 1 or width >= 22:
        confidence = "low"
    elif active >= 3 and width <= 12 and abs(total) >= 6 and not reversion_drives:
        confidence = "high"
    else:
        confidence = "medium"

    # direction "up" = OKAZJA rośnie (lepsze okno zakupowe), "down" = okno się domyka.
    if total > 1:
        direction_s = "up"
    elif total < -1:
        direction_s = "down"
    else:
        direction_s = "flat"

    return {
        "horizon_days": 7,
        "score_base": score_base,
        "score_range": [lo, hi],
        "clamped": clamped,
        "direction": direction_s,
        "confidence": confidence,
        "total_delta": total,
        # Strip kluczy wewnętrznych (structural) — do UI idzie tylko name/delta/note.
        "rules": [{"name": r["name"], "delta": r["delta"], "note": r["note"]}
                  for r in deltas_with_notes],
    }


def build_forecast(score_base, prices, vol_now, vol_30d_avg, fng,
                   months_since_halving=None, rel_strength_7d=None, trend30=0.0):
    """Prognoza OKAZJI (nie ceny, nie sentymentu) na 7 dni: czy okno zakupowe
    raczej się poprawi czy domknie. Cykl halvingu wchodzi tylko do BTC; BNB
    zamiast tego dostaje regułę siły relatywnej BNB/BTC."""
    pct_7d = pct_change_from_prices(prices, 7) if len(prices) >= 8 else 0.0
    d_vol, n_vol = forecast_volume(pct_7d, vol_now, vol_30d_avg)
    d_mr, n_mr = forecast_mean_reversion(fng, prices, trend30)
    d_mom, n_mom = forecast_momentum(prices)
    rules = [
        {"name": "Wolumen",            "delta": d_vol, "note": n_vol},
        {"name": "Powrót do średniej", "delta": d_mr,  "note": n_mr},
        {"name": "Momentum",           "delta": d_mom, "note": n_mom},
    ]
    if months_since_halving is not None:
        d_cyc, n_cyc = forecast_cycle(months_since_halving)
        # structural: stała przez miesiące — nie liczy się jako głos w konwikcji.
        rules.append({"name": "Cykl", "delta": d_cyc, "note": n_cyc, "structural": True})
    if rel_strength_7d is not None:
        d_rel, n_rel = forecast_relative_strength(rel_strength_7d)
        rules.append({"name": "Siła BNB vs BTC", "delta": d_rel, "note": n_rel})
    return compose_forecast(score_base, rules)


# ---------- Werdykt okazji (3 stany + proste sygnały dla nie-tradera) ----------


def position_in_range(prices, days=90):
    """Pozycja aktualnej ceny w zakresie min-max ostatnich `days` dni (0..1)."""
    if not prices:
        return 0.5
    window = prices[-days:]
    lo, hi = min(window), max(window)
    if hi <= lo:
        return 0.5
    return (prices[-1] - lo) / (hi - lo)


def build_verdict(asset_key, name, opp, level, decision, fng, pct_30d, pos_90d,
                  forecast, okazja_streak_days=0):
    """Karta "Czy warto dziś kupić?" — werdykt + 4 sygnały prostym językiem,
    plus 2 skrótowe sygnały na home (Nastrój + Cena). Tone: good = sprzyja
    zakupowi dziś, warn = przemawia przeciw, neutral. Wszystko generuje Python
    (jedno źródło prawdy), JS tylko renderuje."""
    signals = []

    # 1. Nastrój rynku (Fear & Greed)
    if fng <= 25:
        fng_word, t = "skrajny strach", "good"
        txt = f"skrajny strach ({fng}/100) — rynek wyprzedany, historycznie sprzyja dokupowaniu"
    elif fng <= 45:
        fng_word, t = "strach", "good"
        txt = f"strach ({fng}/100) — sprzyja regularnym zakupom"
    elif fng < 55:
        fng_word, t = "neutralnie", "neutral"
        txt = f"neutralnie ({fng}/100)"
    elif fng < 75:
        fng_word, t = "chciwość", "neutral"
        txt = f"chciwość ({fng}/100) — kupuj wg planu, bez zwiększania kwot"
    else:
        fng_word, t = "skrajna chciwość", "warn"
        txt = f"skrajna chciwość ({fng}/100) — rynek rozgrzany"
    signals.append({"label": "Nastrój rynku", "tone": t, "text": txt})
    nastroj_signal = {"label": "Nastrój", "tone": t, "text": f"{fng_word} · {fng}/100"}

    # 2. Cena vs 3 mies. (pozycja w zakresie 90d) — pasma z pos_band().
    # Opis SŁOWNY, bez surowego "(0%)" — laik czytał "0%" jako "zero zmiany",
    # co kłóciło się ze słowem "nisko" (audyt 2026-06-25).
    band = pos_band(pos_90d)
    if band == "nisko":
        t2, txt = "good", "przy dolnej granicy zakresu 3 mies. — kupujesz blisko lokalnego dołka"
    elif band == "wysoko":
        t2, txt = "warn", "przy górnej granicy zakresu 3 mies. — kupujesz wysoko"
    else:
        t2, txt = "neutral", "w środku zakresu 3 mies."
    signals.append({"label": "Cena vs 3 mies.", "tone": t2, "text": txt})

    # 3. Trend 30 dni — próg "good" = CHEAP_30D_PCT (ten sam co kropka "Cena" na home)
    if pct_30d <= CHEAP_30D_PCT:
        t3, txt = "good", f"{fmt_pct(pct_30d)} przez miesiąc — kupujesz taniej niż miesiąc temu"
    elif pct_30d >= 10:
        t3, txt = "warn", f"{fmt_pct(pct_30d)} przez miesiąc — kupujesz drożej niż miesiąc temu"
    else:
        t3, txt = "neutral", f"{fmt_pct(pct_30d)} przez miesiąc — bez dużych zmian"
    signals.append({"label": "Trend 30 dni", "tone": t3, "text": txt})

    # 4. Prognoza okazji na 7 dni (neutralna kropka — prognoza to nie fakt).
    # POMIJANA jako sygnał, gdy werdykt to OKAZJA: "okno może się domykać" tuż
    # pod "dobry moment na zakup" czyta się sprzecznie, a pełny blok prognozy
    # (z konwikcją + rozbiciem reguł) i tak jest niżej na detalu (audyt 2026-06-25).
    if level != "okazja":
        dir_txt = {"up": "okno zakupowe może się poprawić",
                   "down": "okno zakupowe może się domykać",
                   "flat": "okno raczej bez zmian"}[forecast["direction"]]
        conf_txt = {"low": "niska", "medium": "średnia", "high": "wysoka"}[forecast["confidence"]]
        signals.append({"label": "Prognoza 7 dni", "tone": "neutral",
                        "text": f"{dir_txt} (pewność: {conf_txt}) — prognoza okazji, nie ceny"})

    # Skrótowa "Cena" na home: kropka I tekst liczone z TEGO SAMEGO (trend 30d,
    # próg CHEAP_30D_PCT), więc kolor zawsze zgadza się z tekstem. "Taniej niż
    # miesiąc temu" to pojęcie, które nie-trader rozumie od ręki; pozycja w
    # zakresie 90d zostaje tylko na detalu (sygnał "Cena vs 3 mies.").
    if pct_30d <= CHEAP_30D_PCT:
        price_tone, price_txt = "good", f"{fmt_pct(pct_30d)}/30d · taniej niż miesiąc temu"
    elif pct_30d >= 10:
        price_tone, price_txt = "warn", f"{fmt_pct(pct_30d)}/30d · drożej niż miesiąc temu"
    else:
        price_tone, price_txt = "neutral", f"{fmt_pct(pct_30d)}/30d · bez dużych zmian"
    price_signal = {"label": "Cena", "tone": price_tone, "text": price_txt}

    if level == "okazja":
        # Gdy OKAZJA utrzymuje się od kilku dni (realny krach), codzienne
        # "wyjątkowa okazja, kup!" jest niewykonalne przy DCA ~$100/mc i wypala
        # słowo. Przeramowujemy na AKUMULACJĘ wg planu — bez pośpiechu, bez
        # zwiększania kwot. Bez zmiany score/progów (audyt 2026-06-25).
        if okazja_streak_days >= 3:
            sublabel = f"okno otwarte od {okazja_streak_days} dni — akumuluj wg planu"
            headline = (f"Rynek od kilku dni jest w strachu i {name} pozostaje tani — okno zakupowe "
                        f"jest otwarte już {okazja_streak_days} dni. Dla DCA to dobry okres na zakupy "
                        f"zgodnie z planem, bez pośpiechu i bez zwiększania kwot.")
        else:
            # Wariant "tańszy niż miesiąc temu" odpalany TYM SAMYM progiem co kropka
            # "Cena" na home (CHEAP_30D_PCT) — nagłówek i kropka nie mogą się kłócić.
            if pct_30d <= CHEAP_30D_PCT:
                headline = (f"Rynek jest w strachu, a {name} jest tańszy niż miesiąc temu — dla strategii "
                            f"stałych zakupów (DCA) to statystycznie lepszy dzień niż zwykle.")
            else:
                headline = ("Rynek jest w strachu — dla strategii stałych zakupów (DCA) "
                            "to statystycznie lepszy dzień niż zwykle.")
            sublabel = "dobry moment na zakup — rynek w strachu"
    elif level == "wstrzymaj":
        headline = (f"Rynek wygląda na rozgrzany — rozsądniej wstrzymać dziś dodatkowe zakupy {name} "
                    f"i poczekać na spokojniejszy moment.")
        sublabel = "drogo — rozważ przeczekanie"
    else:
        headline = (f"Zwykły dzień na rynku — ani okazja, ani przegrzanie. "
                    f"Regularna, stała kwota DCA w {name} to tu najlepsza strategia.")
        sublabel = "zwykły dzień DCA"

    return {"decision": decision, "level": level, "word": opp_word(level),
            "sublabel": sublabel, "opp": opp, "fng": fng,
            "headline": headline, "signals": signals,
            "home_signals": [nastroj_signal, price_signal]}


# ---------- Wspólny User-Agent (BSC RPC w sekcji on-chain wymaga "przeglądarkowego") ----------
# News/events (etap 4) usunięte z UI w redesignie 2026-06-15 — nie pobieramy ich już wcale.

NEWS_USER_AGENT = "Mozilla/5.0 (cryptoflop/0.2; +https://cryptoflop.vercel.app)"


# ---------- On-chain net flows (etap 3) ----------

# Publicznie udokumentowane adresy Binance (cold + hot). Net flow = zmiana
# zagregowanego salda. Inflow (dodatni) = krypto trafia na giełdę = możliwa
# presja sprzedażowa. Outflow (ujemny) = odpływ = akumulacja.
BINANCE_BTC_ADDRESSES = [
    "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",                                  # Binance cold (largest)
    "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97",      # Binance hot
    "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s",                                  # Binance
    "3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6",                                  # Binance
]
BINANCE_BSC_ADDRESSES = [
    "0xF977814e90dA44bFA03b6295A0616a897441aceC",                          # Binance 8 (duży holder BNB)
    "0x8894E0a0c962CB723c1976a4421c95949bE2D4E3",                          # Binance hot
    "0x28C6c06298d514Db089934071355E5743bf21d60",                          # Binance 14
]
ONCHAIN_HISTORY_LEN = 25  # ~2-4 dni przy realnej kadencji ~1,5-5h (okno raportowane w window_h)


def fetch_btc_onchain():
    """Zsumuj funded/spent across Binance BTC addresses (mempool.space).

    Wszystko-albo-nic: częściowa suma (np. bez cold walleta) zapisana do ring
    buffera wygląda potem jak fantomowy przepływ setek tysięcy BTC."""
    funded = 0
    spent = 0
    for addr in BINANCE_BTC_ADDRESSES:
        try:
            d = fetch_json(f"https://mempool.space/api/address/{addr}", timeout=15)
        except Exception as e:
            print(f"  mempool.space {addr[:12]}… failed: {e} — pomijam cały snapshot")
            return None
        cs = d.get("chain_stats")
        if not cs or not cs.get("funded_txo_sum"):
            # Odpowiedź bez chain_stats / z zerem to zdegradowany fetch, nie
            # "adres bez historii" — te adresy mają lata aktywności.
            print(f"  mempool.space {addr[:12]}… puste chain_stats — pomijam cały snapshot")
            return None
        funded += cs["funded_txo_sum"]
        spent += cs.get("spent_txo_sum", 0)
    return {"funded": funded, "spent": spent, "n": len(BINANCE_BTC_ADDRESSES)}


def fetch_bnb_onchain():
    """Zsumuj balansy Binance BSC addresses (BSC RPC eth_getBalance).
    Wszystko-albo-nic — jak w fetch_btc_onchain."""
    total_wei = 0
    for addr in BINANCE_BSC_ADDRESSES:
        try:
            req = urllib.request.Request(
                "https://bsc-dataseed.binance.org",
                data=json.dumps({
                    "jsonrpc": "2.0", "method": "eth_getBalance",
                    "params": [addr, "latest"], "id": 1,
                }).encode(),
                headers={"Content-Type": "application/json", "User-Agent": NEWS_USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                res = json.loads(r.read())
            total_wei += int(res["result"], 16)
        except Exception as e:
            print(f"  BSC RPC {addr[:12]}… failed: {e} — pomijam cały snapshot")
            return None
    return {"balance_wei": total_wei}


def push_onchain_snapshot(history, key, snapshot):
    arr = history.setdefault(key, [])
    arr.append({"ts": datetime.now(timezone.utc).isoformat(), **snapshot})
    if len(arr) > ONCHAIN_HISTORY_LEN:
        del arr[: len(arr) - ONCHAIN_HISTORY_LEN]
    return list(arr)


def btc_netflow_block(history, snap):
    """Build on-chain block for BTC. snap = {funded, spent} lub None."""
    if snap is None:
        return {"available": False, "note": "Brak danych on-chain (mempool.space niedostępny)"}
    arr = push_onchain_snapshot(history, "onchain_btc", snap)
    # chain_stats są kumulatywne (nigdy nie maleją) — wpis z niższą sumą niż
    # poprzedni to skutek częściowego faila fetchu (suma podzbioru adresów).
    # Wyrzucamy takie wpisy, zanim staną się bazą porównania (arr[0]).
    clean = []
    for e in arr:
        if "n" in e and e["n"] != len(BINANCE_BTC_ADDRESSES):
            print(f"  on-chain BTC: odrzucam snapshot z niepełną listą adresów {e['ts']}")
            continue
        if clean and (e["funded"] < clean[-1]["funded"] or e["spent"] < clean[-1]["spent"]):
            print(f"  on-chain BTC: odrzucam skorumpowany snapshot {e['ts']}")
            continue
        clean.append(e)
    # Filtr parowy nie weryfikuje bazy (arr[0]). Realny przyrost kumulatywnych
    # sum w oknie 2-4 dni jest mikroskopijny — baza odstająca o >1% od
    # bieżącego snapa to na pewno częściowa suma (legacy), nie ruch rynkowy.
    while clean and (snap["funded"] - clean[0]["funded"]) > snap["funded"] * 0.01:
        print(f"  on-chain BTC: odrzucam podejrzaną bazę {clean[0]['ts']}")
        clean.pop(0)
    history["onchain_btc"] = clean
    arr = clean
    if len(arr) < 2:
        return {"available": False, "note": "Zbieram dane on-chain — pierwszy snapshot"}
    oldest = arr[0]
    d_funded = snap["funded"] - oldest["funded"]
    d_spent = snap["spent"] - oldest["spent"]
    inflow_btc = d_funded / 1e8
    outflow_btc = d_spent / 1e8
    net_btc = inflow_btc - outflow_btc  # dodatni = napływ na Binance
    hours = max(1, round((datetime.now(timezone.utc) -
                          datetime.fromisoformat(oldest["ts"])).total_seconds() / 3600))
    # Progi per 24h (okno przy realnej kadencji cron ma ~2-4 dni, nie 24h).
    # Z okna <12h NIE ekstrapolujemy ×24 — jednorazowy ruch 30 BTC w 1h
    # wyglądałby jak 720 BTC/24h i odpalał fałszywy alert.
    short_window = hours < 12
    net_per24 = 0.0 if short_window else net_btc * 24 / hours
    activity_btc = inflow_btc + outflow_btc
    coverage = "low" if (activity_btc < 5 or short_window) else "ok"
    if short_window:
        signal = f"okno pomiaru dopiero {hours}h — za wcześnie na ocenę"
    elif activity_btc < 5:
        signal = ("śledzone adresy prawie nieaktywne w tym oknie — znikome pokrycie "
                  "realnych przepływów Binance, traktuj jako brak danych")
    elif net_per24 > 50:
        signal = "napływ na śledzone portfele — możliwa presja sprzedażowa"
    elif net_per24 < -50:
        signal = "odpływ ze śledzonych portfeli — akumulacja / mniejsza podaż"
    else:
        signal = "ruch netto bliski zera — bez wyraźnego sygnału"
    return {
        "available": True,
        "net_btc": round(net_btc),
        "net_per24": round(net_per24),
        "threshold_24h": 50,
        "coverage": coverage,
        "short_window": short_window,
        "inflow_btc": round(inflow_btc),
        "outflow_btc": round(outflow_btc),
        "window_h": hours,
        "signal": signal,
    }


def bnb_netflow_block(history, snap):
    if snap is None:
        return {"available": False, "note": "Brak danych on-chain (BSC RPC niedostępny)"}
    # Najpierw walidujemy SNAP względem mediany istniejącego bufora — odstający
    # odczyt (zdegradowane RPC) nie może ani wejść do historii, ani jej czyścić.
    prev = history.get("onchain_bnb", [])
    if prev:
        med = sorted(e["balance_wei"] for e in prev)[len(prev) // 2]
        if abs(snap["balance_wei"] - med) > med * 0.15:
            print("  on-chain BNB: odczyt salda odstaje >15% od mediany — pomijam snapshot")
            return {"available": False, "note": "Odczyt salda odstaje od historii — pomijam ten snapshot"}
    arr = push_onchain_snapshot(history, "onchain_bnb", snap)
    # Sanity parami (jak w BTC): saldo skarbca nie skacze o >10% między
    # KOLEJNYMI snapshotami — kumulatywny dryf w całym oknie to sygnał,
    # nie korupcja, więc nie wolno go przycinać do bieżącego snapa.
    clean = []
    for e in arr:
        if clean and abs(e["balance_wei"] - clean[-1]["balance_wei"]) > clean[-1]["balance_wei"] * 0.10:
            print(f"  on-chain BNB: odrzucam skorumpowany snapshot {e['ts']}")
            continue
        clean.append(e)
    history["onchain_bnb"] = clean
    arr = clean
    if len(arr) < 2:
        return {"available": False, "note": "Zbieram dane on-chain — pierwszy snapshot"}
    oldest = arr[0]
    net_bnb = (snap["balance_wei"] - oldest["balance_wei"]) / 1e18  # dodatni = wzrost salda
    hours = max(1, round((datetime.now(timezone.utc) -
                          datetime.fromisoformat(oldest["ts"])).total_seconds() / 3600))
    # To delta SALDA 3 portfeli (w tym rezerwa korporacyjna), nie przepływ
    # klientów — dolewki między portfelami Binance wyglądają jak "flow".
    # Próg względny: 0,5% śledzonego salda na 24h; poniżej = szum operacyjny.
    # Z okna <12h nie ekstrapolujemy ×24 (fałszywe alarmy z 1-2h okien).
    short_window = hours < 12
    net_per24 = 0.0 if short_window else net_bnb * 24 / hours
    tracked_bnb = snap["balance_wei"] / 1e18
    threshold_24h = round(tracked_bnb * 0.005)
    if short_window:
        signal = f"okno pomiaru dopiero {hours}h — za wcześnie na ocenę"
    elif net_per24 > threshold_24h:
        signal = "saldo śledzonych portfeli rośnie wyraźnie — możliwy podwyższony napływ na giełdę"
    elif net_per24 < -threshold_24h:
        signal = "saldo śledzonych portfeli maleje wyraźnie — możliwy odpływ z giełdy"
    else:
        signal = "zmiana w granicach normalnego ruchu operacyjnego skarbca"
    return {
        "available": True,
        "net_bnb": round(net_bnb),
        "net_per24": round(net_per24),
        "threshold_24h": threshold_24h,
        "short_window": short_window,
        "window_h": hours,
        "signal": signal,
    }


# ---------- Telegram alerty (etap 5, opt-in) ----------

def send_telegram(text):
    """Wyślij wiadomość na Telegram. No-op jeśli brak env TELEGRAM_BOT_TOKEN/CHAT_ID."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    try:
        data = urllib.parse.urlencode({
            "chat_id": chat_id, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": "true",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data, headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception as e:
        print(f"  Telegram send failed: {e}")
        return False


def fng_band(fng):
    if fng < 20: return "extreme-fear"
    if fng < 40: return "fear"
    if fng < 60: return "neutral"
    if fng < 80: return "greed"
    return "extreme-greed"


def build_and_send_alerts(history, btc_24h, bnb_24h, fng, btc_dca, bnb_dca,
                          btc_onchain, bnb_onchain):
    """Porównaj stan vs last_alert_state, wyślij tylko zmiany progowe."""
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        print("  Telegram: pominięte (brak TELEGRAM_BOT_TOKEN)")
        return

    prev = history.get("alert_state", {})
    cur = {
        "btc_dca": btc_dca, "bnb_dca": bnb_dca,
        "fng_band": fng_band(fng),
        "btc_big": abs(btc_24h) >= 5, "bnb_big": abs(bnb_24h) >= 5,
    }
    msgs = []

    if prev.get("btc_dca") and prev["btc_dca"] != btc_dca:
        msgs.append(f"🟠 <b>BTC DCA: {prev['btc_dca']} → {btc_dca}</b>")
    if prev.get("bnb_dca") and prev["bnb_dca"] != bnb_dca:
        msgs.append(f"🟡 <b>BNB DCA: {prev['bnb_dca']} → {bnb_dca}</b>")

    if prev.get("fng_band") and prev["fng_band"] != cur["fng_band"]:
        if cur["fng_band"] in ("extreme-fear", "extreme-greed"):
            label = "ekstremalny strach" if cur["fng_band"] == "extreme-fear" else "ekstremalna chciwość"
            msgs.append(f"📊 <b>Fear &amp; Greed: {fng} ({label})</b>")

    if cur["btc_big"] and not prev.get("btc_big"):
        msgs.append(f"⚡ <b>BTC {btc_24h:+.1f}% w 24h</b>")
    if cur["bnb_big"] and not prev.get("bnb_big"):
        msgs.append(f"⚡ <b>BNB {bnb_24h:+.1f}% w 24h</b>")

    if (btc_onchain.get("available") and btc_onchain.get("coverage") != "low"
            and abs(btc_onchain.get("net_per24", 0)) >= 500):
        net = btc_onchain["net_per24"]
        kier = "napływ na Binance" if net > 0 else "odpływ z Binance"
        msgs.append(f"🔗 <b>BTC on-chain: {net:+} BTC/24h ({kier})</b>")

    if msgs:
        body = "<b>CryptoFlop — alert</b>\n\n" + "\n".join(msgs) + \
               "\n\nhttps://cryptoflop.vercel.app/"
        if send_telegram(body):
            print(f"  Telegram: wysłano {len(msgs)} alert(ów)")
        else:
            print("  Telegram: send nieudany")
    else:
        print("  Telegram: brak progowych zmian")

    history["alert_state"] = cur


# ---------- main ----------


def main():
    print("Fetching data...")

    prices_resp = fetch_json(
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin,binancecoin&vs_currencies=usd"
        "&include_24hr_change=true&include_24hr_vol=true"
    )
    btc_p = prices_resp["bitcoin"]
    bnb_p = prices_resp["binancecoin"]

    btc_price = btc_p["usd"]
    bnb_price = bnb_p["usd"]
    btc_24h = btc_p["usd_24h_change"]
    bnb_24h = bnb_p["usd_24h_change"]
    btc_vol = btc_p["usd_24h_vol"]
    bnb_vol = bnb_p["usd_24h_vol"]

    btc_chart = fetch_json(
        "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        "?vs_currency=usd&days=95&interval=daily"
    )
    bnb_chart = fetch_json(
        "https://api.coingecko.com/api/v3/coins/binancecoin/market_chart"
        "?vs_currency=usd&days=95&interval=daily"
    )
    btc_prices = [p[1] for p in btc_chart["prices"]]
    bnb_prices = [p[1] for p in bnb_chart["prices"]]
    btc_vols = [v[1] for v in btc_chart["total_volumes"]]
    bnb_vols = [v[1] for v in bnb_chart["total_volumes"]]

    btc_7d = pct_change_from_prices(btc_prices, 7)
    btc_30d = pct_change_from_prices(btc_prices, 30)
    btc_90d = pct_change_from_prices(btc_prices, 90)
    bnb_7d = pct_change_from_prices(bnb_prices, 7)
    bnb_30d = pct_change_from_prices(bnb_prices, 30)
    bnb_90d = pct_change_from_prices(bnb_prices, 90)

    btc_vol_7d_avg = sum(btc_vols[-8:-1]) / 7 if len(btc_vols) >= 8 else btc_vol
    bnb_vol_7d_avg = sum(bnb_vols[-8:-1]) / 7 if len(bnb_vols) >= 8 else bnb_vol
    btc_vol_vs_7d = (btc_vol / btc_vol_7d_avg - 1) * 100 if btc_vol_7d_avg else 0.0
    bnb_vol_vs_7d = (bnb_vol / bnb_vol_7d_avg - 1) * 100 if bnb_vol_7d_avg else 0.0

    if len(btc_prices) > 7 and len(bnb_prices) > 7:
        bnb_btc_now = bnb_prices[-1] / btc_prices[-1]
        bnb_btc_then = bnb_prices[-8] / btc_prices[-8]
        bnb_vs_btc_7d = (bnb_btc_now / bnb_btc_then - 1) * 100
    else:
        bnb_vs_btc_7d = 0.0

    fng_resp = fetch_json("https://api.alternative.me/fng/?limit=1")
    fng = int(fng_resp["data"][0]["value"])

    print(f"  BTC: ${btc_price:.0f} ({btc_24h:+.1f}% 24h)")
    print(f"  BNB: ${bnb_price:.0f} ({bnb_24h:+.1f}% 24h)")
    print(f"  F&G: {fng}")

    pos90_btc = position_in_range(btc_prices)
    pos90_bnb = position_in_range(bnb_prices)

    # Główna liczba 0-100 to WYNIK OKAZJI do kupna (high = strach/tanio =
    # zielony = kupuj), nie sentyment. Werdykt 3-stopniowy wynika wprost z niego.
    opp_btc = opportunity_score("btc", fng, pos90_btc, btc_30d)
    opp_bnb = opportunity_score("bnb", fng, pos90_bnb, bnb_30d)
    btc_level = opp_level(opp_btc)
    bnb_level = opp_level(opp_bnb)
    btc_dca = "NIE" if btc_level == "wstrzymaj" else "TAK"
    bnb_dca = "NIE" if bnb_level == "wstrzymaj" else "TAK"

    months_since_halving = int((datetime.now() - HALVING_DATE).days / 30.4)

    btc_vol_30d_avg = sum(btc_vols[-31:-1]) / 30 if len(btc_vols) >= 31 else btc_vol_7d_avg
    bnb_vol_30d_avg = sum(bnb_vols[-31:-1]) / 30 if len(bnb_vols) >= 31 else bnb_vol_7d_avg

    history = load_history()
    btc_hist = push_score(history, "btc", opp_btc)
    bnb_hist = push_score(history, "bnb", opp_bnb)
    btc_opp_daily = push_daily_opp(history, "btc_opp_daily", opp_btc)
    bnb_opp_daily = push_daily_opp(history, "bnb_opp_daily", opp_bnb)
    btc_okazja_streak = okazja_streak(btc_opp_daily)
    bnb_okazja_streak = okazja_streak(bnb_opp_daily)

    # Baza prognozy = średnia wyniku okazji z ostatnich refreshy (odporna na
    # szum 24h), nie chwilowa wartość zdominowana przez ruch 24h.
    btc_base = round(sum(btc_hist[-7:]) / len(btc_hist[-7:]))
    bnb_base = round(sum(bnb_hist[-7:]) / len(bnb_hist[-7:]))
    btc_forecast = build_forecast(btc_base, btc_prices, btc_vol, btc_vol_30d_avg, fng,
                                  months_since_halving=months_since_halving, trend30=btc_30d)
    bnb_forecast = build_forecast(bnb_base, bnb_prices, bnb_vol, bnb_vol_30d_avg, fng,
                                  rel_strength_7d=bnb_vs_btc_7d, trend30=bnb_30d)

    btc_verdict = build_verdict("btc", "BTC", opp_btc, btc_level, btc_dca, fng,
                                btc_30d, pos90_btc, btc_forecast, btc_okazja_streak)
    bnb_verdict = build_verdict("bnb", "BNB", opp_bnb, bnb_level, bnb_dca, fng,
                                bnb_30d, pos90_bnb, bnb_forecast, bnb_okazja_streak)

    # On-chain liczymy tylko gdy aktywne są alerty Telegram (jedyny konsument).
    # Audyt uznał on-chain za "martwy czujnik", więc znikł z UI; bez Telegramu
    # pomijamy też fetch — mniej połączeń sieciowych i powierzchni błędu.
    btc_onchain = bnb_onchain = {}
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        print("Fetching on-chain (dla alertów)...")
        btc_onchain = btc_netflow_block(history, fetch_btc_onchain())
        bnb_onchain = bnb_netflow_block(history, fetch_bnb_onchain())

    print("Telegram alerts (etap 5)...")
    build_and_send_alerts(history, btc_24h, bnb_24h, fng, btc_dca, bnb_dca,
                          btc_onchain, bnb_onchain)

    now_local = datetime.now()
    header_label = f"{DAY_NAMES_PL[now_local.weekday()]}, {now_local.day} {MONTHS_PL[now_local.month - 1]}"

    data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "header_label": header_label,
        "assets": [
            {
                "key": "btc",
                "name": "BTC",
                "sub": "Bitcoin",
                "price": fmt_price(btc_price),
                "price_change_24h": round(btc_24h, 1),
                "opp": opp_btc,
                "opp_30d": btc_opp_daily,
                "verdict": btc_verdict,
                "forecast": btc_forecast,
            },
            {
                "key": "bnb",
                "name": "BNB",
                "sub": "Binance Coin",
                "price": fmt_price(bnb_price),
                "price_change_24h": round(bnb_24h, 1),
                "opp": opp_bnb,
                "opp_30d": bnb_opp_daily,
                "verdict": bnb_verdict,
                "forecast": bnb_forecast,
            },
        ],
    }

    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2))

    print(f"BTC okazja: {opp_btc}/100 ({opp_label(opp_btc)}) — {opp_word(btc_level)} [{btc_level}]")
    print(f"BNB okazja: {opp_bnb}/100 ({opp_label(opp_bnb)}) — {opp_word(bnb_level)} [{bnb_level}]")
    print(f"Wrote {DATA_FILE.name} and {HISTORY_FILE.name}")


if __name__ == "__main__":
    main()
