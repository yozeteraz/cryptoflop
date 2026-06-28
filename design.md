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
- **Kolor niesie znaczenie (od 2026-06-15): ZIELONY = okazja do kupna, CZERWONY = drogo/przegrzane, SZARY = neutralnie.** Główna liczba 0–100 to wynik OKAZJI (high = strach/tanio = zielony = kupuj), nie sentyment.
- **Zielony/czerwony niosą dwa znaczenia — rozdzielone kontekstem.** (1) Wynik okazji + kropki sygnałów: zielony = sprzyja zakupowi, czerwony = przeciw (logika kontrariańska). (2) **Zmiana ceny 24h w nagłówku: kolorowanie giełdowe — wzrost = zielony, spadek = czerwony** (na życzenie użytkownika 2026-06-28; wcześniej była wyciszona szarym). Używa **stonowanego rejestru** (`--chg-up #5fa87d` / `--chg-down #d07b72`), niżej saturowanego niż vivid zieleń/czerwień wyniku okazji — kierunek czyta się, ale nie konkuruje z wielką liczbą „kupuj". Świadomie akceptujemy wynikającą z tego pozorną sprzeczność: w dniu spadku ceny czerwone „−1,3% 24h" stoi obok zielonego wyniku okazji (bo dla DCA-kupującego tańsza cena = lepsza okazja). Kropki sygnałów: zielona = sprzyja zakupowi, czerwona = przeciw, szara = neutralna.
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

## Redesign „okazja do kupna" (2026-06-15)

Narzędzie służy do JEDNEGO: raz dziennie zerknąć, jak wygląda kurs i **czy warto dziś dokupić**. Cała aplikacja jest teraz buy-centryczna, nie „sentyment-centryczna".

### Home — minimalizm (2 metryki per asset)

Jeden kafelek na asset (BTC, BNB), full-width, stackowane. Zawartość:
1. **Nagłówek**: `BTC · Bitcoin` (lewo) + cena + zmiana 24h **kolorowana giełdowo: wzrost zielony / spadek czerwony** (prawo; od 2026-06-28, wcześniej szara).
2. **Hero**: wielka liczba okazji 0–100 w kolorze skali (zielony = kupuj) + słowo-werdykt **OKAZJA / KUP / CZEKAJ** w tym samym kolorze + `/100`.
3. **Podtytuł 1-zdaniowy**: „dobry moment na zakup — rynek w strachu" (okazja, złoty akcent) / „zwykły dzień DCA" / „drogo — rozważ przeczekanie".
4. **Dokładnie 2 sygnały** (hairline): **Nastrój** (F&G) i **Cena** (trend 30d — „−14,7%/30d · taniej niż miesiąc temu"), każdy z kropką zielona/szara/czerwona. Kropka i tekst „Cena" liczone z jednego progu `CHEAP_30D_PCT=−8%`, więc kolor zawsze pasuje do słów. Pozycja w zakresie 90d zeszła na detal (sygnał „Cena vs 3 mies.").
5. **Pasek „ostatnie 30 dni"** (przywrócony 2026-06-15 na życzenie): 30 kostek = okazja dzień po dniu, kolor na skali okazji (zielona seria = okres dobrych okazji, czerwona = drogo), oś „30 dni temu → dziś". Daje kontekst pod dzisiejszą liczbę. Dane: dzienna seria `*_opp_daily` w history.json (1 wpis/dzień), zbackfillowana realną historią cen+F&G.

Usunięte z home (było „za dużo"): sparkline, mood label, badge forecastu, panel DCA (werdykt Dziś / Za 7 dni), narracja „Co się dzieje".

### Detal coina — max 4 metryki

Po tapnięciu kafelka (iOS sheet, swipe BTC↔BNB). Tylko dwa bloki:
1. **Karta „Czy warto dziś kupić?"** = hero detalu: cena (mute), wielka liczba okazji + słowo-werdykt, podtytuł, headline, **pasek skali 0–100** (gradient palety, marker w kolorze okazji) z podpisami **drogo / neutralnie / okazja**, oraz **sygnały** (max 4): Nastrój rynku · Cena vs 3 mies. · Trend 30 dni · Prognoza 7 dni (szara kropka). **Od audytu 2026-06-25: sygnał „Prognoza 7 dni" znika z karty, gdy werdykt to OKAZJA** — „okno się domyka" tuż pod „dobry moment na zakup" czytało się sprzecznie, a pełny blok prognozy (z konwikcją + rozbiciem) i tak jest niżej. Przy KUP/CZEKAJ prognoza zostaje (4 sygnały). Stopka: legenda kropek + „nie porada inwestycyjna i nie prognoza ceny".
2. **Prognoza okazji 7d** (patrz niżej).

Usunięte z detalu: siatka 5 horyzontów, osobna siatka metryk, on-chain (martwy czujnik wg audytu), newsy, narracja, zwijany „Szczegóły".

Cała treść (werdykt, headline, sygnały, home_signals) generowana w `fetch.py` → `verdict` w data.json. JS niczego nie interpretuje.

## Rules-based forecast — OKAZJI (dodane 2026-05-13, przeramowane 2026-06-15)

Predykcja kierunku **okazji do kupna** (nie ceny, nie „sentymentu") w horyzoncie 7 dni: czy okno zakupowe raczej się **poprawi** (up) czy **domknie** (down). To nie szklana kula — to probabilistyczna ekstrapolacja czterech składowych: wolumen, mean reversion, momentum oraz cykl halvingu (BTC) / siła relatywna BNB/BTC (BNB). **Uwaga przy edycji reguł:** delty dotyczą OKAZJI, nie ceny — wzrost ceny OBNIŻA okazję, odbicie ze strachu OBNIŻA okazję, faza po szczycie cyklu PODNOSI okazję. Baza prognozy to średnia wyniku okazji z ostatnich odświeżeń (odporna na szum 24h).

### Co MUSI być na ekranie kiedy pokazujemy forecast

1. **Pasmo, nie pojedynczy punkt**. Nigdy „okazja będzie 48". Zawsze „pasmo 42–56".
2. **Konwikcja jawna**. Zawsze obok pasma: `low / medium / high`. Konwikcja wynika z agreement między regułami — im bardziej zgodne, tym węższe pasmo i wyższa konwikcja.
3. **Rozbicie regła-po-regle na detalu**. Wiersze: nazwa reguły · delta · krótka note wyjaśniająca. Suma. To "show your work" — user widzi *dlaczego* forecast jest taki.
4. **Disclaimer**. 11px, italic, muted: „Prognoza okazji to rule-based ekstrapolacja z widocznego setupu — nie sygnał handlowy i nie prognoza ceny. Spodziewaj się odchyleń przy szybkich zmianach rynku." Nie znika nigdy.

### Czego NIE robimy

- **Nie pokazujemy** mocnych słów „BUY / SELL / KUPUJ TERAZ". Werdykt OKAZJA/KUP/CZEKAJ to ocena stanu, nie nakaz intraday.
- **Nie używamy** żadnych kolorów niosących ocenę dla strzałki direction. Strzałka jest w **wyciszonym szarym** (`--muted-2`) — zielona strzałka „okno się domyka" (↘) byłaby sprzeczna, skoro zielony = kupuj. Strzałka tylko wskazuje kierunek, nie ocenia.
- **Nie pokazujemy** prognozy CENY w $$. Nigdy.
- **Nie pokazujemy** historical accuracy — to udawałoby gwarancję, której nie ma.

### Estetyka

- Sekcja na detalu: ten sam wzorzec co karta werdyktu (panel + hairlines). Reguły jako lista: nazwa (muted) · delta (pos/neg/neutral kolor numeryczny) · note (muted mniejszy font).

## Audyt 2026-06-25 — poprawki UX/craft (po 10 dniach realnych danych)

Wdrożone po dwóch audytach UX + audycie reguł predykcyjnych. Wszystkie findingi
po adwersarialnej weryfikacji wyszły minor/nit (żadnego blockera) — to polish.

- **Kolor = werdykt (synchronizacja progów):** `scoreColor()` ma teraz punkty
  łamania zsynchronizowane z progami werdyktu (`OPP_TAK=42`, `OPP_OKAZJA=84`,
  „wyjątkowa"=90): 16/28/42/54/66/76/84/90. Pomarańcz „drogo" kończy się dokładnie
  na progu KUP (42), więc kolor nigdy nie maluje KUP na „drogo"; OKAZJA dostaje
  własną głębszą zieleń (c-85), „wyjątkowa" najgłębszą (c-100). Przystanki
  `.scale-bar` wyrównane do tych samych punktów (marker siedzi na pasku w swoim kolorze).
- **Karta werdyktu:** sygnał „Prognoza 7 dni" znika, gdy werdykt = OKAZJA (patrz wyżej).
- **Prognoza — pasmo jednostronne:** gdy pasmo przyklei się do krawędzi skali,
  pokazujemy je jednostronnie („≥ 85") zamiast `[85,100]` (fikcyjna precyzja). Pole
  `forecast.clamped` w data.json: `"hi" | "lo" | null`.
- **„Trwała OKAZJA":** gdy okno OKAZJI jest otwarte ≥3 dni (streak z `*_opp_daily`),
  podtytuł i headline zmieniają się na akumulacyjne („okno otwarte od N dni — akumuluj
  wg planu"), bo codzienne „wyjątkowa okazja, kup!" jest niewykonalne przy DCA ~$100/mc.
  Bez zmiany score/progów.
- **Dostępność:** `--muted-2` podbite `#6b7385 → #7d8597` (WCAG AA, ~4,6:1 na panelu).
- **Gest natywny:** swipe-down-to-dismiss na nagłówku arkusza (grabber to teraz
  prawdziwa afordancja, zamknięcie kciukiem od dołu). Tylko na `.sheet-header`, nie
  koliduje z poziomym pagerem.
- **Stan błędu:** wystylizowana karta + placeholder daty + „Spróbuj ponownie" zamiast
  surowego tekstu (check „błąd nadal wygląda spokojnie").
- **Treść:** nazwy reguł po polsku („Powrót do średniej", „Siła BNB vs BTC");
  pozycja w 90d opisana słownie zamiast surowego „(0%)".

### Zaakceptowane wyjątki od reguł powyżej (kod ≠ litera dokumentu, świadomie)

- **Modal sheet MA unoszący cień** (`0 -16px 40px rgba(0,0,0,.45)`) mimo reguły
  „bez drop shadow" — to standard iOS dla arkusza wysuwanego znad treści. Karty
  na home nadal bez cienia.
- **Radius kart = 16px** (w paśmie 12–18px; trzecia, teraz udokumentowana wartość obok 14/18).

---

**Kiedy w wątpliwości:** otwórz Settings na iPhonie, zobacz jak Apple to robi.
