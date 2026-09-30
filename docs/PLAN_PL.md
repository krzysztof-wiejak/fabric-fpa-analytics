# Plan budowy projektu krok po kroku (PL)

Ten plik jest dla Ciebie – README.md (po angielsku) jest dla rekruterów.
Szacowany czas: **4–5 wieczorów**.

---

## Etap 0 · GitHub (ok. 30 min)

1. Wejdź na **github.com → Sign up**. Wybierz profesjonalną nazwę użytkownika, np. `kwiejak` lub `krzysztof-wiejak` – będzie częścią linku, który pokażesz rekruterom.
2. Włącz uwierzytelnianie dwuskładnikowe (GitHub i tak o to poprosi).
3. Uzupełnij profil: zdjęcie (to samo co na LinkedIn), imię i nazwisko, krótkie bio, np. *Controlling & FP&A | Power BI | Microsoft Fabric*, link do LinkedIn.
4. Zainstaluj **GitHub Desktop** (desktop.github.com) – najprostszy sposób, żeby wysyłać zmiany bez znajomości komend.
5. W GitHub Desktop: **File → New repository**
   * Name: `fabric-fpa-analytics`
   * Local path: np. `Dokumenty\GitHub`
   * Git ignore: None, License: None (pliki są już w paczce)
6. Skopiuj **zawartość** rozpakowanego folderu do utworzonego folderu repozytorium (README.md ma leżeć bezpośrednio w nim).
7. W GitHub Desktop wpisz opis zmian, np. *Initial project structure and synthetic data* → **Commit to main** → **Publish repository**.
   * Zaznacz **Keep this code private** – upublicznisz repozytorium, gdy dodasz zrzuty ekranu (Settings → Danger Zone → Change visibility).

Każdą kolejną zmianę wysyłasz tak samo: Commit → **Push origin**.

---

## Etap 1 · Środowisko Fabric (ok. 1 godz.)

Trial Fabric (60 dni) nie działa na prywatny e-mail typu @op.pl. Masz dwie możliwości:

* **Konto służbowe** – tylko jeśli firma na to pozwala. Do portfolio lepiej go nie używać.
* **Własny tenant przez darmowe konto Azure** (zalecane) – oficjalna instrukcja Microsoft:
  https://learn.microsoft.com/en-us/fabric/fundamentals/free-trial-account-personal-email
  W skrócie: zakładasz darmowe konto Azure (karta tylko do weryfikacji), w Microsoft Entra ID tworzysz użytkownika, logujesz się nim na app.fabric.microsoft.com i klikasz **Free trial → Activate**.

Następnie:
1. **Workspaces → New workspace** → nazwa `FPA Analytics` → w ustawieniach licencji wybierz **Trial**.
2. W workspace: **New item → Lakehouse** → nazwa `lh_fpa`.

---

## Etap 2 · Wgranie danych (15 min)

1. W lakehouse, w sekcji **Files**, kliknij `...` → **New subfolder** → `raw`.
2. Wejdź do `raw` → **Upload → Upload folder** i wgraj po kolei foldery `erp`, `budget` i `master_data` z `data/raw`.
3. Sprawdź, czy masz: `Files/raw/erp/sales_invoices.csv`, `Files/raw/budget/budget_2025_2026.xlsx` itd.

---

## Etap 3 · Notebooki – bronze, silver, gold (1 wieczór)

1. W workspace: **Import → Notebook → From this computer** → wybierz 3 pliki z folderu `notebooks`.
2. Otwórz każdy notebook → po lewej **Lakehouses → Add → Existing lakehouse** → `lh_fpa` (będzie domyślny).
3. Uruchom **01_ingest_nbp_fx_rates** (Run all). Powinna powstać tabela `bronze_nbp_fx_rates` z kursami EUR od grudnia 2024.
4. Uruchom **02_bronze_to_silver**. W wynikach zobaczysz m.in. „removed duplicates: 18” – to celowo wstawione błędy w danych.
5. Uruchom **03_silver_to_gold**. Na końcu jest tabela P&L Actual vs Budget oraz kontrola: *Bridge reconciliation difference ≈ 0,00 PLN*.
6. W pierwszej komórce notebooków 01 i 03 sprawdź, czy jest ustawiona jako **parameter cell** (`...` przy komórce → *Toggle parameter cell*).

**Ważne:** przejdź przez kod komórka po komórce i upewnij się, że rozumiesz każdy krok. Na rozmowie padną pytania w stylu „dlaczego kurs z poprzedniego dnia roboczego?” albo „jak liczysz efekt cenowy?”. To Twoja domena, więc łatwo to obronisz.

---

## Etap 4 · Pipeline (30 min)

1. **New item → Data pipeline** → `pl_fpa_refresh`.
2. Dodaj 3 aktywności **Notebook** (01 → 02 → 03) połączone strzałką **On success**.
3. Uruchom pipeline (**Run**) i zrób zrzut ekranu udanego przebiegu – przyda się do README.
4. Opcjonalnie: **Schedule** raz dziennie. Pozwoli to pokazać, że kursy NBP aktualizują się automatycznie.

> Opcjonalnie, żeby pokazać też **Dataflow Gen2**: zbuduj dataflow, który wczytuje pliki z `Files/raw/master_data` i zapisuje je do tabel `silver_*` (Destination: lh_fpa, Replace). Następnie dodaj go w pipeline przed notebookiem 03 i usuń sekcję „4. Master data” z notebooka 02.

---

## Etap 5 · Model semantyczny (1 wieczór)

1. W lakehouse: **New semantic model** → nazwa `sm_fpa` → zaznacz tabele `dim_*` i `fact_*` (wszystkie z gold).
2. Otwórz model (**Open data model**) i utwórz relacje zgodnie z `semantic-model/model_and_measures.md`.
3. `dim_date` → **Mark as date table**. Ustaw **Sort by column** (month_name → month_no, pl_line → pl_line_order, step → step_order).
4. Dodaj miary DAX z pliku (**New measure**) i pogrupuj je w display folders.
5. Ukryj kolumny kluczy w tabelach faktów.

---

## Etap 6 · Raport Power BI (1–2 wieczory)

1. W Power BI Desktop: **Get data → Power BI semantic models** → `sm_fpa` (połączenie live).
2. Zbuduj 4–5 stron opisanych na końcu `model_and_measures.md`. Najważniejszy jest **waterfall Budget → Volume → Price → FX → Actual**.
3. Zapisz raport jako **Power BI Project (.pbip)**: *File → Save as → typ: Power BI project files*, do folderu `report/` w repozytorium. Dzięki temu na GitHubie widać definicję raportu w formie tekstowej.
4. Opublikuj raport do workspace `FPA Analytics`.

Wskazówki:
* Jedna spójna paleta, np. granat plus zielony i czerwony dla odchyleń.
* Każda strona z tytułem-wnioskiem, np. *„EBITDA 2025 below budget mainly due to price and turnaround”*, a nie samym „P&L”.
* Tooltips z komentarzem, co się stało w danym miesiącu (turnaround, gaz, awaria).

---

## Etap 7 · Dokończenie GitHuba (1 godz.)

1. Zrób zrzuty ekranu (Win + Shift + S) każdej strony raportu, lineage view w workspace, udanego pipeline'u i fragmentu notebooka. Zapisz je w `docs/images/` jako `01_executive_summary.png`, `02_pnl.png`, `03_bridge.png` itd.
2. Nagraj krótki GIF (20–30 s) przeklikiwania raportu – darmowy program **ScreenToGif**.
3. W README podmień linię ze zrzutem na `![Report](docs/images/01_executive_summary.png)`, dodaj pozostałe obrazki i wpisz swój link do LinkedIn.
4. Commit → Push → zmień repozytorium na **Public**.
5. Na stronie repozytorium, w polu **About** (koło zębate), dodaj opis i tematy: `microsoft-fabric`, `power-bi`, `dax`, `pyspark`, `fpa`, `financial-analysis`.
6. Na profilu GitHub: **Customize your pins** → przypnij to repozytorium.

Opcjonalnie (plus na rozmowie): **Workspace settings → Git integration → GitHub** – podłączasz workspace Fabric bezpośrednio do repozytorium i notebooki, pipeline oraz model synchronizują się same.

---

## Etap 8 · LinkedIn

1. Profil → **Add section → Featured → Add a link** → link do repozytorium (z miniaturą ze zrzutu ekranu).
2. Post: 1–2-minutowe nagranie ekranu raportu i 3–4 zdania: problem biznesowy → co zbudowałeś → czego się nauczyłeś → link.
3. W sekcji **Projects** dodaj projekt z opisem i umiejętnościami.

---

## Co jest w paczce

| Plik | Opis |
|---|---|
| `data/raw/erp/sales_invoices.csv` | 7 351 wierszy faktur (01.2025–08.2026), PLN i EUR, 18 duplikatów i niespójne kody klientów |
| `data/raw/erp/gl_cost_postings.csv` | 1 740 księgowań kosztów w formacie polskiego ERP |
| `data/raw/budget/budget_2025_2026.xlsx` | budżet: założenia, wolumeny, ceny, koszty (miesiące w kolumnach) |
| `data/raw/master_data/*.csv` | produkty, klienci, MPK, plan kont |
| `notebooks/*.ipynb` | 3 notebooki PySpark (bronze → silver → gold) |
| `semantic-model/model_and_measures.md` | relacje, ustawienia modelu, miary DAX, projekt stron raportu |
| `scripts/generate_data.py` | generator danych syntetycznych |

Wbudowana historia biznesowa (do opowiadania na rozmowie):
* **H1 2025** – słaby rynek, ceny ok. 3–4% poniżej budżetu, suchy kwiecień i maj (niższy popyt na nawozy)
* **VIII 2025** – postój remontowy wytwórni amoniaku przedłużony o ok. 10 dni: niższy wolumen mocznika i amoniaku, remont droższy o ok. 38 mln PLN
* **XII 2025** – rezerwa na premie roczne
* **I–III 2026** – skok cen gazu (do 252 PLN/MWh przy budżecie 175) i silny popyt przedsezonowy
* **IV–VI 2026** – ceny eksportowe ok. 6% powyżej budżetu
* **VII 2026** – nieplanowana awaria wytwórni saletry
