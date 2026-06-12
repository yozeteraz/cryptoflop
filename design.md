# CryptoFlop — design rules

> Estetyka iOS. Każda decyzja UI/CSS musi być zgodna z tym dokumentem. Jeśli nowa propozycja koliduje — najpierw pytanie do użytkownika.

## Naczelna zasada

**Trzymamy się estetyki iOS.** Ciężar wizualny niesie typografia i layout, nie ozdoby. Decyzje wzorujemy na natywnych apkach Apple (Settings, Health, Stocks, Weather, Wallet, App Store).

## Co to znaczy konkretnie

### Karty i powierzchnie
- **Zaokrąglone rogi**: 12–18px (iOS używa ~13px wewnętrznie, ~22px dla większych modali). U nas: 14px standardowo, 18px dla "feature cards".
- **Tła wielowarstwowe**: ciemny gradient base (`--bg`), na to półprzezroczyste panele (`--panel`, `--panel-2`). Karty nie są płaskie czarne kwadraty — mają delikatny "lift" przez subtelnie jaśniejsze tło niż canvas.
- **Hairline borders**: granice są cienkie (1px) i ciemne (`--border` = `#232b3a` — prawie niewidoczne). iOS nie używa grubych ramek.
- **Bez drop shadow**. iOS rzadko używa cieni — separację robi przez tło, nie cień. Jeśli kiedyś dodajemy, to bardzo subtelne (`0 1px 2px rgba(0,0,0,.3)`).

### Łączenie elementów ("grouping")
- Powiązane wizualnie elementy **dzielimy hairline'em**, nie gap'em. Wzorzec z iOS Settings: lista pozycji w jednym kontenerze, między nimi cienka linia.
- Niepowiązane elementy oddzielamy **wyraźnym odstępem** (16–24px) i osobnymi kartami.
- Reguła: jeśli dwa bloki tworzą jedną "jednostkę informacji" → jedna karta z divider'em w środku. Jeśli dwie różne jednostki → dwie karty z gap'em.

### Typografia
- **Helvetica Neue** (system fallback). To najbliższe SF Pro bez używania licencjonowanego SF.
- **Hierarchia przez weight i size**, nie przez kolor. Główne liczby duże (48–68px, 700), labels małe i muted (10–11px uppercase 0.1em letter-spacing), body 14px.
- **Letter-spacing ujemny dla dużych liczb** (-0.02em) — daje "tight" look iOS dla wartości.
- **Bez podkreśleń, kursyw, dekoracji.** Tylko regular i bold.

### Kolory
- Paleta minimalna (patrz `colors.md`). System colors iOS: red dla danger/negative, green dla success/positive, gray dla neutral.
- **Kolor niesie znaczenie**: czerwony = strach/spadek, zielony = chciwość/wzrost, szary = spokój/neutralny.
- Nie używamy koloru "ozdobnie". Każdy kolor coś znaczy.

### Interaktywność (mobile-first)
- **Tap-able elementy mają subtle press state**: `transform: scale(0.997)` lub `opacity: 0.7` przy `:active`. Nie skacze, nie podskakuje.
- **Brak hover effects sugerujących klikalność**, które nie istnieją na mobile. Hover może podświetlić tło, ale nie unosić.
- **Gesty natywne**: swipe, tap, pull. Nie wymyślamy własnych. Swipe = pager. Tap = navigate. Long-press unikamy (mało odkrywalne).
- **Routing przez hash lub history API**, browser back działa "out of the box".
- **Animacje krótkie i z natury fizycznej**: 200–300ms, easing `cubic-bezier(0.22, 0.61, 0.36, 1)` lub `ease-out`. Nigdy `linear`.

### Spacing
- **Generous whitespace**. Dwa razy więcej padding niż wydaje się "potrzebne".
- **Wewnątrz kart**: 18–24px padding.
- **Między kartami**: 16–24px gap.
- **Między sekcjami**: 28–36px margin.

### iOS NIE robi (i my też nie)
- Gradientów na tekście.
- 3D bevels, glossy buttons.
- Disco rainbow colors.
- Pulsujących animacji ("attention seekers").
- Modal dialogs na każdy klik.
- Tooltipów na hover (mobile-first znaczy że ich nie ma).
- Floating action buttons "tylko żeby coś było".
- Skeumorficznych ikonek.

## Praktyczne checki przed każdą zmianą UI

1. Czy element wyglądałby naturalnie w iOS Settings / iOS Health?
2. Czy oddzielenie elementów wynika z relacji (powiązane = hairline, niepowiązane = gap)?
3. Czy color niesie informację, czy jest dekoracyjny? (Jeśli dekoracyjny — wyrzuć.)
4. Czy interakcja używa natywnego gestu, czy wymyśla coś nowego? (Nowe = zła droga.)
5. Czy w stanie pustym/błędu element nadal wygląda spokojnie? (Pełne danych ≠ jedyny stan.)

## Karta „Czy warto dziś kupić?" (dodane 2026-06-12)

Pierwsza sekcja pod widgetem na detalu — jedyne, co nie-trader musi przeczytać. Reszta (narracja, siatka czasu, metryki, forecast, on-chain, newsy) żyje pod zwijanym wierszem „Szczegóły i metryki" (wzorzec iOS Settings, chevron).

1. **Werdykt słowem**: TAK (zielony) / NIE (czerwony) + podtytuł poziomu: „dobry moment — rynek w strachu" (okazja, złoty akcent) / „normalny dzień DCA" / „rynek rozgrzany — przeczekaj".
2. **Pasek skali 0–100** (gradient palety, marker w kolorze score) z podpisami strach/spokój/mania — wizualna kotwica zamiast gołej liczby. To pasek, nie gauge/dial.
3. **4 sygnały prostym językiem**, każdy z kropką: zielona = sprzyja zakupowi, szara = neutralna, czerwona = przemawia przeciw. Stały zestaw: Nastrój rynku (F&G) · Cena vs 3 mies. (pozycja w zakresie 90d) · Trend 30 dni · Prognoza 7 dni (zawsze szara — prognoza to nie fakt).
4. **Stopka**: legenda kropek + „nie porada inwestycyjna i nie prognoza ceny". Nie znika.
5. Cała treść (werdykt, headline, sygnały) generowana w `fetch.py` → `verdict` w data.json. JS niczego nie interpretuje.

## Rules-based forecast (dodane 2026-05-13)

Predykcja kierunku **sentymentu** (nie ceny) w horyzoncie 7 dni. To nie szklana kula — to probabilistyczna ekstrapolacja czterech składowych: wolumen, mean reversion, momentum oraz cykl halvingu (BTC) / siła relatywna BNB/BTC (BNB). Baza prognozy to średnia score z ostatnich odświeżeń (odporna na szum 24h). Frame'ujemy ostro żeby user nie traktował tego jak sygnał handlowy.

### Co MUSI być na ekranie kiedy pokazujemy forecast

1. **Pasmo, nie pojedynczy punkt**. Nigdy „score będzie 48". Zawsze „pasmo 42–56".
2. **Konwikcja jawna**. Zawsze obok pasma: `low / medium / high`. Konwikcja wynika z agreement między regułami — im bardziej zgodne, tym węższe pasmo i wyższa konwikcja.
3. **Rozbicie regła-po-regle na detalu**. Cztery wiersze: nazwa reguły · delta · krótka note wyjaśniająca. Suma. To jest "show your work" — user widzi *dlaczego* forecast jest taki.
4. **Disclaimer**. 11px, italic, muted. Tekst: „Forecast to rule-based ekstrapolacja z widocznego setupu — nie sygnał handlowy i nie prognoza ceny. Spodziewaj się odchyleń przy szybkich zmianach rynku." Disclaimer nie znika nigdy.

### Czego NIE robimy

- **Nie pokazujemy** mocnych słów „BUY / SELL / KUPUJ TERAZ". Forecast jest stwierdzeniem o setupu, nie nakazem.
- **Nie używamy** klasycznych czerwono-zielonych „signal" kolorów dla strzałki direction. Strzałka jest w kolorze sentymentu mid-range, neutralna emocjonalnie.
- **Nie pokazujemy** prognozy CENY w $$. Nigdy. Inny produkt, inne zasady, nie ten projekt.
- **Nie pokazujemy** historical accuracy ("75% poprzednich forecastów się sprawdziło") — to wydawałoby gwarancję, której nie ma.

### Estetyka

- Badge na widget home: jeden wiersz, 11px muted. Format: `↗ za 7d: 42–56 · medium`. Strzałka w kolorze sentymentu pasma środkowego, nie systemowo zielony/czerwony.
- Sekcja na detalu: ten sam wzorzec co Metryki (panel + hairlines), nie wyróżnia się wizualnie — forecast to JEDNA Z metryk, nie centralny element.
- Reguły jako lista: nazwa (muted) · delta (pos/neg/neutral kolor numeryczny) · note (muted mniejszy font).

---

**Kiedy w wątpliwości:** otwórz Settings na iPhonie, zobacz jak Apple to robi.
