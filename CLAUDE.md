# CryptoFlop — kontekst projektu

> Ten plik czytany jest automatycznie przy starcie Claude Code w tym katalogu. Zawiera ustalenia i decyzje z rozmowy planistycznej, której nie ma już w pamięci konwersacji.

---

## Co to jest

**CryptoFlop** to osobiste narzędzie do codziennej obserwacji „mgły" rynku krypto — pomoc w budowaniu intuicji o nastroju rynku, **nie** silnik predykcyjny. Generuje statyczny HTML dashboard aktualizowany 3× dziennie (rano / południe / wieczór).

Filozofia: rynek jest w dużej mierze efektywny i krótkoterminowo emocjonalny, więc nie próbujemy go „przewidywać". Zamiast tego pokazujemy **sentyment w warstwach czasowych**, żeby użytkownik mógł sam wyrobić sobie wyczucie.

## Użytkownik

- Średnio zaawansowany w krypto, **nie trader**
- Strategia: **DCA ~$100/miesiąc** w BTC i BNB
- Operuje na Binance (Binance jako benchmark cenowy — w pełni akceptowalne dla jego trybu)
- Teza w BNB: to asset oparty na **realnej działającej firmie**, więc jego fundamenty (wolumeny Binance, burny, regulacje) realnie wpływają na cenę. Daje więcej fundamentalnego oparcia niż większość altów, ale ma skoncentrowane ryzyko regulacyjne.

## Stan obecny — etap 1 ukończony (2026-05-11)

- `index.html` — statyczny HTML, **fetchuje `data.json`** przy ładowaniu i renderuje wszystko dynamicznie
- `fetch.py` — Python skrypt (stdlib only) który ściąga dane z CoinGecko + alternative.me, liczy score'y rules-based, generuje narrative-template, zapisuje `data.json` + dorzuca do `history.json`
- `data.json` — aktualny snapshot rynku (przepisywany przy każdym refreshu)
- `history.json` — historia score'ów dla sparklinów (rolling last 7) + 30-dniowy strip DCA
- `.github/workflows/refresh.yml` — GitHub Actions cron 3× dziennie (06:00/12:00/19:00 UTC = 8:00/14:00/21:00 PT letni). Cron uruchamia fetch.py → commit data.json+history.json → Vercel auto-deploy
- `colors.md` — pełna paleta kolorów + uzasadnienie + CSS variables

**Co dalej**: etap 2 (Claude API zamiast prostych reguł scoringu + bogatsza narracja). Patrz "Plan etapów".

## Decyzje produktowe — zatwierdzone

### Co pokazujemy
- **Sentyment w warstwach czasowych**: Dziś (24h) · Tydzień · Miesiąc · Kwartał · Cykl (od halvingu)
- **Aktywa**: BTC i BNB osobno, każde z 3 surowymi metrykami (cena, wolumen 24h, dominacja/BNB-BTC ratio)
- **Hero**: agregowany sentyment dnia + 2-zdaniowa narracja „co się dzieje"
- **DCA na dziś**: werdykt **3-stopniowy** (od 2026-06-12): `okazja` (rynek w strachu: F&G ≤ 20 lub -15%/30d) / `tak` (normalny dzień) / `wstrzymaj` → NIE (rynek rozgrzany: F&G ≥ 75 lub +15%/30d). Stary binarny próg (NIE gdy score ≥ 80) był martwy — 0 wystąpień NIE w całej historii. Pasek 30 dni ma 3 kolory (zielony/złoty/czerwony).
- **Karta „Czy warto dziś kupić?"** na detalu (dla wzrokowca, nie krypto-speca): werdykt + pasek skali 0–100 z markerem + 4 sygnały prostym językiem (nastrój F&G, cena vs zakres 90d, trend 30d, prognoza 7d), każdy z kropką zielona/szara/czerwona. Treść generuje `fetch.py` (`verdict` w data.json) — JS tylko renderuje. Sekcje eksperckie (narracja, siatka czasu, metryki, forecast, on-chain, newsy) schowane pod zwijanym „Szczegóły i metryki".
- **Wydarzenia z 24h**: top newsy z tagami (Binance / Regulacje / Makro / On-chain)
- **Panel szczegółów**: po kliknięciu komórki — rozbicie wyniku na wymiary (cena, wolumen) + krótki komentarz „dlaczego"

### Skala sentymentu
- **0–100**, jeden wynik per komórka (nie split na wymiary)
- Mood labele: Krew / Wyprzedaż / Słabość / Spokój / Wzmocnienie / Siła / Hossa / Mocna hossa / Mania
- **Skala % → score jest per-horyzont** (od 2026-06-12): 24h ±6%, 7d ±12%, 30d ±25%, 90d ±40% na pełną skalę. Jedna wspólna skala ±20% zamrażała komórkę 30d na 0 przy -20%/30d, a 24h trzymała wiecznie przy 50.
- **Delta** = vs poprzednie odświeżenie (realnie ~2–5h, GitHub Actions throttluje cron). NIE "vs wczoraj" — legenda w stopce mówi to wprost.
- Sparkline z ostatnich 24 odświeżeń (~2–4 dni) w każdej komórce
- Komórka "Dziś" używa **tego samego wzoru co score widgetu** (BTC: (F&G + 2·s24)//3, BNB: (F&G + 3·s24)//4 — mniejsza waga F&G, bo indeks jest BTC-centryczny)

### Czego świadomie nie pokazujemy
- Dominacji BTC jako głównego wymiaru (zrzucone do detali, drugorzędny sygnał dla DCA)
- Funding rates / MVRV / Pi Cycle na pierwszym widoku (advanced, w detalach po kliknięciu)
- **Predykcji cenowych — nigdy**. Nie liczymy, nie pokazujemy, nie sugerujemy konkretnych target-prices.
- Sygnałów typu „buy/sell" intraday

### Co pokazujemy z przyszłości (od 2026-05-13)
- **Forecast pasma sentymentu w 7d** — rules-based, transparentny, z explicit konwikcją (low/medium/high). To NIE predykcja ceny, tylko probabilistyczna ekstrapolacja widocznego setupu (volume confirmation, mean reversion, momentum streak, cykl).
- Zasady: zawsze pasmo (nie pojedynczy punkt), zawsze z konwikcją, zawsze z rozbiciem regła-po-regle na detalu, zawsze z disclaimerem.
- Szczegóły implementacji w `design.md` → sekcja "Rules-based forecast".

## Konwencje UI/UX — z uzasadnieniem

> **Naczelna zasada estetyki: iOS.** Pełna specyfikacja w `design.md` (cards, hairlines vs gap, typografia, animacje). Każda zmiana UI musi być z tym zgodna.
>
> **Why:** te zasady wynikają z konkretnych iteracji w rozmowie. Nie zmieniaj ich bez ponownego pytania.
> **How to apply:** każde nowe miejsce/element musi się tych zasad trzymać.

- **„Spokój" = szary, nie żółty/amber.** Konwencja Fear & Greed Index jest semantycznie błędna — żółty komunikuje „ostrzeżenie", nie „brak emocji". Środek skali (45–55) to neutralny slate gray.
- **Brak kolorowych pasków po lewej** w komórkach i blokach detali. Wynik liczbowy jest pofarbowany sam — to wystarczy.
- **Strzałka delty obok wielkiej liczby** (nie przy etykiecie). Wcześniej próbowaliśmy umieszczać ją przy labelu — testowo wróciliśmy, ale po stronie użytkownika lepiej się czyta gdy jest tuż obok wyniku. Strzałka w kolorze wyniku (`--cell-color`), nie w klasycznym czerwono-zielonym — kierunek niesie sam symbol ↑↓.
- **Hero w tym samym stylu co komórki**, tylko większy. Bez okrągłych dialów / wskazówek — to nie jest gauge. Spójność wizualna z resztą. Hero też ma własny sparkline (większy, ~44px wysokości).
- **Sparkline w każdej komórce** — ostatnie 7 odświeżeń, cienka linia w kolorze sentymentu, z kropką na ostatnim punkcie. Daje kontekst „trendu" bez konieczności klikania.
- **Nagłówek strony minimalistyczny**: brand „CRYPTOFLOP" po lewej, **tylko data** po prawej. Bez „ostatnia aktualizacja / kolejna", bez info o cyklu (cykl ma własną komórkę w siatce czasu).
- **Sekcje mają jednozdaniowy podtytuł** wyjaśniający kontekst. Użytkownik nie jest tradera, każdy techniczny termin (np. „Aktywa") wymaga krótkiego doprecyzowania.
- **Sekcja Aktywa to wiersz: kafelek wyniku + 3 stat blocki** (Cena, Wolumen, vs rynek). Nie szerokie 2 komórki obok siebie — to wyglądało niezbalansowane vs siatka czasu.
- **Pomost decyzyjny „DCA na dziś"** pod hero — 1-zdaniowa synteza danych → rekomendacja. Bez tego użytkownik czyta liczby, ale nie wie *co z tego*. Skrót DCA = Dollar-Cost Averaging (stała kwota w regularnych odstępach).
- **Hero narracja** ma nagłówek „Co się dzieje", **nie** powtórzony mood label — żeby uniknąć redundancji „Lekkie osłabienie" pojawiające się dwa razy.
- **Brak emoji** w UI (z wyjątkiem strzałek ↑ ↓ →). Jednoznaczne, profesjonalne.
- **Font: Helvetica Neue** (fallback: Helvetica, Arial, system fonts). Daje neutralny, klasyczny charakter zamiast „bardzo nowoczesnego" SF Pro.

## Architektura techniczna

**Stack:**
- Python 3.10+ (instalacja przez `uv` jeśli brakuje)
- SQLite (przechowywanie historii odświeżeń + cache surowych danych)
- Claude API (`claude-opus-4-7` lub `claude-sonnet-4-6` — sonnet wystarczy do tego zadania, taniej)
- Statyczny HTML generowany ze skryptu (jeden plik, otwierasz lokalnie z zakładki)
- `launchd` na Macu — odpalanie 3× dziennie

**Workflow każdego odświeżenia:**
1. Skrypt Python ściąga surowe dane z darmowych API (cena, wolumen, on-chain, RSS)
2. Liczy podstawowe metryki regułami (delty, średnie, ratio)
3. Wysyła do Claude API: surowe dane + ich kontekst historyczny → otrzymuje (a) score 0–100 per komórka, (b) mood label, (c) krótki komentarz, (d) syntezę „co się dzieje" dla hero, (e) DCA bridge
4. Renderuje HTML z szablonu (Jinja2 albo proste f-stringi)
5. Zapisuje aktualny stan + dodaje wpis do historii (sparkline = ostatnie 7 odświeżeń)

**Koszt:** ~$1–2/miesiąc API (3× dziennie × ~3k tokens/refresh).

## Źródła danych — zweryfikowane 2026-05-11

> Status każdego źródła sprawdzony bezpośrednim HTTP probe. Dostępność i pricing API się zmieniają — przy starcie etapu 1 zrobić quick re-check.

### Działa darmowo, bez klucza

| Źródło | Endpoint | Co | Notes |
|---|---|---|---|
| **Binance Spot** | `api.binance.com/api/v3/ticker/24hr` | Ceny BTC/BNB, wolumeny 24h | Public, bez rejestracji |
| **Binance Futures** | `fapi.binance.com/fapi/v1/premiumIndex` | Funding rates, premium index | Public, bez rejestracji |
| **CoinGecko global** | `api.coingecko.com/api/v3/global` | Dominacja BTC (`market_cap_percentage.btc`), total market cap | Bez klucza. Rate limit OK do naszego use case (3×/dzień) |
| **alternative.me** | `api.alternative.me/fng/?limit=1` | Fear & Greed Index | Bez klucza. **NIE z CoinGecko** (poprzedni plan się mylił) |
| **mempool.space** | `mempool.space/api/...` | BTC on-chain: bloki, mempool, address stats | Bez klucza. Dla "wpłat na Binance" potrzebujemy własnej listy adresów (patrz "Co zamiast Arkham") |
| **CoinDesk RSS** | `coindesk.com/arc/outboundfeeds/rss?outputType=xml` | Newsy, regulacje | Bez slash przed `?` (poprzedni URL → 308 redirect) |
| **CoinTelegraph RSS** | `cointelegraph.com/rss` | Newsy, listings | Standardowy RSS |
| **Binance Announcements** | `binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=10` | Listings, burns, regulacje | **Nie RSS** — JSON od wewnętrznego CMS Binance (nieoficjalne, stabilne; jeśli zmienią CMS, padnie) |

### Wymagało zmiany strategii (poprzedni plan był nierealny)

| Co chcieliśmy | Czemu nie działa | Co zamiast |
|---|---|---|
| **BscScan API** dla BNB on-chain | V1 deprecated; Etherscan V2 multichain dla BSC wymaga paid plan (`"Free API access is not supported for this chain"`) | **BSC RPC** bezpośrednio: `bsc-dataseed.binance.org` (darmowe, JSON-RPC, bez klucza). Wymaga pracy nad `eth_call`/`getLogs`. Albo MVP-cięcie: BNB on-chain ograniczony do tego co da się wyciągnąć z Binance API |
| **Whale Alert** dla dużych transakcji | Free tier wymaga klucza + 10 req/min + ostatnia 1h + min $500k. Twitter feed za paywallem od 2023 | Dla BTC: własna logika nad mempool.space — filtr transakcji na/z hardcoded listy adresów Binance, próg np. >100 BTC. Dla BNB: w MVP pomijamy |
| **Arkham Intelligence** dla etykiet portfeli | Web UI nie ma stabilnego endpointu; API wymaga paid plan | **Hardcoded lista** znanych Binance hot/cold wallets (~15–20 publicznie udokumentowanych adresów, np. `34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo`) |

### Świadomie pominięte

- **Glassnode / CryptoQuant** — płatne, niepotrzebne dla naszej skali
- **Płatne API sentymentu z Twittera** — szumne, mało wartościowe
- **Whale Alert paid (~$50/mc)** — sztywne limity, niewart kosztu vs własna logika na mempool.space
- **Arkham paid** — jw., własna lista wystarczy

## Plan etapów

> **Zasada projektu (decyzja 2026-05-14):** zero płatnych API. Trzymamy się darmowych źródeł i rules-based logiki. Etap 2 (LLM) został odrzucony.

1. ✅ **MVP** — ceny + wolumeny z CoinGecko → reguły scoring → dynamiczne dane w HTML. **Ukończone 2026-05-11.** Binance API porzucone (HTTP 451 z GitHub Actions); CoinGecko działa globalnie. GitHub Actions cron — od 2026-05-14 lecimy co 1h zamiast 3×/dzień.
2. ⚙️ **Etap 1.5 — wzmocnienie MVP** (ukończone 2026-05-14):
   - Restruktura UI: 2 widgety BTC/BNB hairline-połączone, detail pages jako iOS modal sheet (drag handle, blur Material, slide-up), forecast 7d rules-based z 4 regułami (volume/mean-reversion/momentum/cykl), DCA per-asset (Dziś / Za 7 dni), header z czasem ostatniej aktualizacji.
3. ❌ **Sentyment z Claude API** — **ODRZUCONE 2026-05-14**. Zostajemy na rules-based scoring + template narrative. Powód: użytkownik nie chce płacić za API. Patrz [[feedback_no_paid_apis]].
3. ❌ **Sentyment z Claude API** — **ODRZUCONE 2026-05-14** (jw.).
4. ✅ **On-chain BTC/BNB** (ukończone 2026-05-15) — net flows na/z portfeli Binance: BTC przez mempool.space (4 publiczne adresy, funded/spent txo delta), BNB przez BSC RPC eth_getBalance (3 adresy). Ring buffer snapshotów ~24h. Sekcja „On-chain · ostatnie Nh" na detalu z sygnałem inflow/outflow.
5. ✅ **Newsy i wydarzenia** (ukończone 2026-05-14) — RSS CoinDesk + CoinTelegraph + Binance announcements JSON. Rules-based tagging (Binance/Regulacje/Makro/On-chain), per-asset filtering. Sekcja „Wydarzenia · 24h" na detalu, top 6 nagłówków z linkami. Bez LLM.
6. ✅ **Alerty zdarzeniowe** (ukończone 2026-05-15, opcjonalne/opt-in) — Telegram bot. Triggery: DCA flip, F&G band do ekstremum, ruch ceny ±5% 24h, duży on-chain net flow (>500 BTC). Dedupe przez `alert_state` w history.json. **Aktywne tylko gdy ustawione GitHub Secrets `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`** — bez nich `fetch.py` cicho pomija.

## Audyt 2026-06-12 — poprawki logiki predykcji

Wieloagentowy audyt (16 potwierdzonych findingów) wykazał m.in.: martwy binarny próg DCA (0× NIE w historii), zamrożoną komórkę 30d (jedna skala ±20%), forecast zakotwiczony w szumie 24h z fikcyjną precyzją pasma, dwa różne wzory na "dziś" na jednym ekranie, tipy przewidujące CENĘ wbrew zasadom, on-chain BTC jako martwy czujnik + bug częściowego fetchu (fantomowe +248k BTC), BNB net flow alarmujący na szumie operacyjnym. Wdrożone poprawki:

- DCA: werdykt 3-stopniowy (okazja/tak/wstrzymaj), progi na F&G + trend 30d, backtest na 230 rewizjach git: maj = "tak", od 3 czerwca (krach) = "okazja"
- Skale per-horyzont; komórka "Dziś" = score widgetu (jeden wzór)
- Forecast: baza wygładzona (średnia ostatnich refreshy), min. szerokość pasma 12, konwikcja wymaga ≥2 aktywnych reguł, momentum tylko na pełnych zamknięciach (min. 2 dni), rampa F&G zamiast klifu; BNB: reguła BNB/BTC zamiast cyklu halvingu; `dca_in_7d` liczone w Pythonie (nie w JS)
- Detal forecastu przywrócony do spec z design.md: pasmo + konwikcja + rozbicie reguł + disclaimer; usunięte tipy "wkrótce taniej/droższe"
- On-chain: fetch wszystko-albo-nic + sanityzacja ring buffera (kumulatywne sumy nie mogą maleć), sygnał "coverage low" gdy śledzone adresy nieaktywne, progi znormalizowane per 24h (BNB: 0,5% śledzonego salda), etykieta "zmiana salda śledzonych portfeli" zamiast "net flow → Binance"
- cycle_score spójny z forecast_cycle (od mies. 24 opada z 50 o 4/mies. — poniżej pasma "Spokój" od ~25,4 mies.; wcześniej wisiał przy 51 mimo narracji "po szczycie, bearish")

## Redesign 2026-06-15 — narzędzie buy-centryczne (WAŻNE: nadpisuje część decyzji wyżej)

Cel od użytkownika: *„uprość do dwóch metryk per BTC/BNB na home, za dużo metryk i opisów; zielony = kolor największej szansy żeby kupić; w podglądzie coina max 4 metryki; zoptymalizuj reguły kiedy kupić. To narzędzie używane raz dziennie, żeby zorientować się jak kurs i czy warto dziś kupić."*

**Kluczowa zmiana koncepcyjna:** główna liczba 0–100 to już **WYNIK OKAZJI do kupna**, nie „sentyment". High = rynek w strachu + tanio + wyprzedany = **zielony = kupuj**. Używa tej samej palety kolorów (high=zielony), więc kolor niesie wprost jedno znaczenie. To eliminuje dawną sprzeczność (zielony=chciwość, choć dla DCA-kupującego najlepiej kupować w strachu). **Sentyment/mood (Krew…Mania) wycofany z UI.**

- **`opportunity_score(asset, fng, pos_90d, pct_30d)`** w `fetch.py`: ważona suma `100-F&G`, `100-pozycja_w_90d`, `opp_from_pct(trend_30d)`. Wagi per-asset (`OPP_WEIGHTS`): BTC 0.45/0.30/0.25 (F&G ciężki, bo indeks BTC-centryczny), BNB 0.35/0.35/0.30 (własna dynamika cenowa).
- **Werdykt 3-stopniowy z progów** (`opp_level`, jedno źródło prawdy): `OPP_OKAZJA=84` → **OKAZJA**, `OPP_TAK=42` → **KUP**, niżej → **CZEKAJ**. Skalibrowane backtestem na ~6 mies. realnych cen + F&G: BTC ~13/71/16%, BNB ~8/79/13% (okazja/tak/wstrzymaj). OKAZJA realnie WYJĄTKOWA (próg podniesiony 74→84 w re-audycie 2026-06-15, bo przy 74 padała w 31-40% dni i „78 OKAZJA / 70 KUP" wyglądało arbitralnie). KUP to codzienność, CZEKAJ zapala się na szczytach — dawny binarny próg dawał 0× NIE.
- **Spójność „taniości" (re-audyt 2026-06-15):** jeden próg `CHEAP_30D_PCT=-8%` rządzi naraz: kropką+tekstem „Cena" na home, sygnałem „Trend 30 dni" na detalu i wariantem nagłówka okazji. Wcześniej każde miało własny próg (pos≤0,5 / pos≤0,25 / -10%), co dało zieloną kropkę obok „śr. zakresu 90d" i nagłówek „stoi nisko" przy pozycji 27%. Home „Cena" mówi teraz wprost o trendzie 30d („taniej/drożej niż miesiąc temu") — kropka i tekst z tego samego źródła; pozycja w 90d (`pos_band`: nisko≤0,33 / wysoko≥0,66) została tylko na detalu. `opp_label` kluczone do `OPP_OKAZJA`/`OPP_TAK`, żeby etykieta nie przebijała słowa-werdyktu. Wagi `OPP_WEIGHTS` i `opportunity_score` **bez zmian** — backtest potwierdził, że są zdrowe (co-movement BTC/BNB to realna struktura rynku: corr 0,72, werdykty różne w 31% dni).
- **Forecast 7d przeramowany na OKAZJĘ** (nie sentyment, nie cenę): direction up=okno się poprawia, down=domyka. **Wszystkie znaki reguł odwrócone** względem wersji sentymentowej (wzrost ceny obniża okazję, odbicie ze strachu obniża okazję, faza po szczycie cyklu podnosi okazję). Reszta spec (pasmo+konwikcja+rozbicie+disclaimer) bez zmian — patrz `design.md`.
- **Home**: 1 kafelek/asset = cena (mute) + wielki wynik okazji + słowo OKAZJA/KUP/CZEKAJ + podtytuł + **2 sygnały** (Nastrój=F&G, Cena=trend30d „taniej/drożej niż miesiąc temu"; pozycja90d zeszła na detal) + **pasek „ostatnie 30 dni"** (przywrócony 2026-06-15 na życzenie: 30 kostek = okazja dzień po dniu na skali okazji, oś „30 dni temu→dziś"; dane `*_opp_daily` w history.json, 1/dzień, `push_daily_opp`, zbackfillowane realną historią). Usunięte: sparkline, mood, badge forecastu, panel DCA (Dziś/Za 7 dni), narracja.
- **Detal**: tylko karta werdyktu (wynik + skala „drogo/neutralnie/okazja" + 4 sygnały) + prognoza okazji 7d. Usunięte: siatka 5 horyzontów, siatka metryk, on-chain, newsy, narracja, zwijane „Szczegóły".
- **Kolor**: zielony/czerwony zarezerwowane dla sygnału zakupu. Zmiana ceny 24h w nagłówku jest **wyciszona szarym** (sam znak), żeby czerwony spadek nie konkurował z „zielony=kupuj".
- **`data.json` odchudzone**: usunięte `narrative`, `events`, per-asset `time`/`stats`/`onchain`/`mood`/`score`/`history`/`dca`. Nowe pola per-asset: `opp`, `opp_label`, `opp_30d` (pasek 30 dni), `verdict` (z `word`, `sublabel`, `opp`, `home_signals`), `forecast`.
- **Backend**: on-chain liczony tylko gdy ustawiony `TELEGRAM_BOT_TOKEN` (jedyny konsument — alerty); inaczej fetch pomijany. News (`fetch_all_events`) i on-chain nie trafiają do UI. `history.json` zmigrowano (serie score `btc`/`bnb` zresetowane — zmieniły sens z sentymentu na okazję). Martwe helpery sentymentu (`mood_label`, `score_from_pct`, `cycle_score`, `asset_time_block`, `PCT_FULL_SCALE`) pozostają zdefiniowane, ale nieużywane.

> Sekcje „Decyzje produktowe", „Skala sentymentu" i opisy struktury home/detalu **powyżej** opisują stan sprzed tego redesignu — czytaj je przez pryzmat tej sekcji.

## Status: plan wykonany

Wszystkie etapy poza odrzuconym etapem 2 (płatne API) są gotowe i zdeployowane. Projekt jest w pełni funkcjonalny i zero-cost. Aktualny kształt produktu definiuje **Redesign 2026-06-15** (wyżej).

**Aktywacja Telegram (opcjonalna, gdy użytkownik zechce):**
1. Telegram → @BotFather → `/newbot` → skopiuj token
2. Napisz coś do swojego bota, potem otwórz `https://api.telegram.org/bot<TOKEN>/getUpdates` → znajdź swój `chat.id`
3. GitHub repo → Settings → Secrets and variables → Actions → dodaj `TELEGRAM_BOT_TOKEN` i `TELEGRAM_CHAT_ID`
4. Od następnego cron-runa alerty działają. Zero zmian w kodzie.

## Nazwa, branding

- Nazwa: **CryptoFlop**
- Brand color: `#c4a878` (złoto-piaskowy, motyw latarni)
- Paleta: patrz `colors.md` (kompletna z uzasadnieniem)

---

**Kiedy ktokolwiek startuje Claude Code w tym katalogu:** przeczytaj ten plik + `colors.md` + `design.md` + `index.html`. Plan jest **wykonany** (etapy 1, 1.5, 3, 4, 5 gotowe; etap 2 odrzucony — zero płatnych API). Projekt działa i jest zdeployowany na cryptoflop.vercel.app. Dalsze prace to iteracje/polish na życzenie użytkownika, nie nowe etapy.
