# CryptoFlop — paleta kolorów

Pełna paleta używana w mockupie dashboardu. Podzielona na warstwy: brand, UI/tło, skala sentymentu, wskaźniki zmian.

---

## Brand & akcent

| Rola | Hex | Opis |
|---|---|---|
| **Accent / Brand** | `#c4a878` | Złoto-piaskowy — tytuł "CRYPTOFLOP", etykieta DCA, tag Binance. Charakter: latarnia, ciepło, dyskretny luksus |

## Tło i karty (dark mode)

| Rola | Hex | Opis |
|---|---|---|
| Background page | `#0d1117` | Tło strony |
| Background soft | `#11161f` | Lekkie wyróżnienie (panel detali) |
| Panel | `#161c27` | Tło kart i komórek |
| Panel deeper | `#1c2330` | Wewnętrzne karty (np. dla `dim`) |
| Border | `#232b3a` | Obramowania, linie podziału |

## Typografia

| Rola | Hex | Opis |
|---|---|---|
| Tekst główny | `#e6e9ef` | Domyślny kolor tekstu |
| Tekst osłabiony | `#8a93a6` | Etykiety sekcji, drugi plan |
| Tekst najsłabszy | `#6b7385` | Referencje, najmniej ważne metadane |

---

## Skala OKAZJI do kupna (0–100)

> **Zmiana 2026-06-15:** ta sama paleta, ale znaczenie odwrócone. Główna liczba 0–100 to teraz **wynik okazji do kupna**, nie „sentyment". **Zielony = największa szansa na zakup** (rynek w strachu i tanio). Czerwony = drogo / przegrzane (słaby moment na dokup). Hexy bez zmian — zmienił się sens, który niosą.

Od „drogo / przegrzane" (czerwień) przez „neutralnie" (szary) do „okazja" (zieleń). Szary w środku to **świadoma decyzja** — neutralność nie jest żółta/oliwkowa, bo to sugerowałoby ostrzeżenie. Pomarańcz i limonka jako „przedmuchy" wokół neutrum.

| OPP | Hex | Znaczenie | Label okazji |
|---|---|---|---|
| 0   | `#dc2626` | Najgorszy moment — przegrzane | Przegrzane |
| 15  | `#ef4444` | Drogo | Drogo |
| 30  | `#f97316` | Raczej drogo | Raczej drogo |
| 45  | `#9ca3af` | **Neutrum** — zwykły dzień | Zwykły dzień |
| 55  | `#84cc16` | Lekko sprzyja zakupom | Sprzyja zakupom |
| 65  | `#4ade80` | Sprzyja zakupom | Sprzyja zakupom |
| 75  | `#22c55e` | Dobra okazja (rynek w strachu) | Dobra okazja |
| 85  | `#16a34a` | Bardzo dobra okazja | Wyjątkowa okazja |
| 100 | `#15803d` | Najlepszy moment — głęboki strach + tanio | Wyjątkowa okazja |

## Wskaźniki zmian — DWA rejestry koloru (2026-06-28)

Zielony/czerwony niosą dwa różne znaczenia, więc mają dwie różne intensywności —
żeby się nie zlewały na jednej karcie:

| Rejestr | Rola | Hex | Uwaga |
|---|---|---|---|
| **Wynik (głośny)** | wynik okazji + kropki sygnałów | `--pos #22c55e` / `--neg #ef4444` | pełna saturacja — to bohater karty |
| **Status (cichy)** | zmiana ceny 24h w nagłówku | `--chg-up #5fa87d` / `--chg-down #d07b72` | **stonowane**: szałwiowa zieleń + glinkowa czerwień; kierunek czyta się, ale nie kradnie uwagi wielkiej liczbie |
| Bez zmian (0%) | — | `#7d8597` (szary) | |

Powód rozdziału: `--pos` to dokładnie ten sam hex co `--c-75` (zielony „Dobra okazja"
na skali wyniku). Gdyby zmiana 24h używała tej samej vivid zieleni, czytałaby się jak
drugi „sygnał kupna" obok wielkiej liczby. Stonowany rejestr `--chg-*` to rozwiązuje.

---

## Charakter / mood-board

- **Dominacja**: ciemne, przygaszone tła (`#0d1117` → `#161c27`)
- **Akcent**: ciepły, dyskretny złoto-piaskowy (`#c4a878`) — pojawia się rzadko, podkreśla istotne elementy
- **Skala**: pełny gradient czerwień → szary → zieleń, bez „kwaśnych" oliwek w środku
- **Niska saturacja** w warstwie UI/tła; **wysoka i bezpośrednia** w wskaźnikach i wynikach
- **Inspiracja**: latarnia morska, mgła, terminale finansowe (Bloomberg, Linear, Vercel)

---

## CSS variables (do skopiowania)

```css
:root {
  /* Brand */
  --accent: #c4a878;

  /* Surfaces */
  --bg: #0d1117;
  --bg-soft: #11161f;
  --panel: #161c27;
  --panel-2: #1c2330;
  --border: #232b3a;

  /* Text */
  --text: #e6e9ef;
  --muted: #8a93a6;
  --muted-2: #7d8597;   /* podbite do WCAG AA (2026-06-25) */

  /* Sentiment scale 0–100 */
  --c-0:   #dc2626;
  --c-15:  #ef4444;
  --c-30:  #f97316;
  --c-45:  #9ca3af;
  --c-55:  #84cc16;
  --c-65:  #4ade80;
  --c-75:  #22c55e;
  --c-85:  #16a34a;
  --c-100: #15803d;

  /* Change indicators — wynik (głośny) */
  --pos: #22c55e;
  --neg: #ef4444;
  /* Zmiana ceny 24h — status (cichy, stonowany rejestr) */
  --chg-up:   #5fa87d;
  --chg-down: #d07b72;
}
```
