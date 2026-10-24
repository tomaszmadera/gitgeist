# Features v2 i normalizacja

Path: `docs/features/features-v2-normalization/spec.md`

Status: zaakceptowany 2026-10-22 (etap 2 planu `docs/features/visual-diversity/plan.md`). Tomasz przyjął wszystkie rekomendowane warianty O1-O11 z sekcji "Decisions"; spec opisuje te warianty.

## Goal

Dodać do Warstwy 1 (ekstrakcja cech) strukturalne cechy repozytorium z sekcji "Features v2" w `design.md` (oś czasu, koncentracja autorów, masy katalogów, udziały języków, skorygowana koncentracja hotspotów, proporcje testów i dokumentacji, gęstość TODO, rozmiar kodu) oraz nowy, czysto deterministyczny moduł normalizacji, który zamienia skalary na wartości w [0, 1] w trybie `absolute` (kotwice logarytmiczne i `smoothstep`) albo `corpus` (percentyl względem tabeli kwantyli dostarczanej z pakietem). Etap nie zmienia żadnego obrazu: renderery, sensory i mapper nie czytają nowych pól. Cechy i normalizacja są wejściem etapu 3 (cechy portretu, `VisualSpec`).

## Related requirements

- `docs/product/emotional-repository-portrait-system.md#L279-L334` (Sekcja 8.1 - Repository Feature Layer).
- `docs/features/visual-diversity/plan.md:40-52` (etap 2: zakres i kryteria akceptacji).
- `docs/features/visual-diversity/design.md:52-89` ("Features v2", "Normalization": źródła cech, tryby skali, kotwice `absolute`).
- `docs/features/visual-diversity/design.md:21-29` (decyzje etapu 0: domyślna skala `absolute`, strategia `counters` domyślna).
- `docs/features/visual-diversity/analysis.md:70-103` (nasycone wejścia, cechy pomijane lub niewyciągane).
- `docs/decisions/0002-optional-llm-evaluation-strategy.md` (punkt 4: spec ekstrakcji cech pozostaje wyłącznie deterministyczny).
- `docs/features/feature-extraction/spec.md` (kontrakt, który ten spec rozszerza; patrz "Effect on existing specs").
- Reguły przeglądu gitgeist poza repozytorium, `F:\projects\grok-bot\review\gitgeist\rules.md` (R5: testy offline).

## Scope

1. Rozszerzenie schematów `src/gitgeist/schemas/features.py` o pola cech v2 (addytywnie, z wartościami domyślnymi):
   - `StaticFeatures`: `code_bytes`, `code_file_count`, `test_file_count`, `test_ratio`, `doc_ratio`, `todo_density`, `top_level_directory_count`, `language_shares`.
   - `GitHistoryFeatures`: `timeline_start`, `timeline`, `active_months_ratio`, `top_author_share`, `top3_author_share`.
   - `Hotspot`: `change_share`, `mass`.
   - Nowe modele `LanguageShare`, `Mass`, `StructureFeatures` oraz pole `RepositoryFeatures.structure`.
2. Rozszerzenie ingestorów bez nowych wywołań `git`:
   - `ingest/repository.py`: lista zeskanowanych plików z rozmiarem i językiem, lista katalogów najwyższego poziomu, zbiory `CODE_LANGUAGES` i `DOC_LANGUAGES`, reguła pliku testowego `is_test_path`.
   - `ingest/git_history.py`: zachowanie dat wszystkich commitów (`RawGitHistory.commit_dates`) z istniejącego wywołania `git log --format=%H%x1f%an%x1f%at`.
3. Kalkulatory cech:
   - `features/static.py` i `features/history.py`: nowe pola; `days_since_last_commit` jako funkcja pochodna (O3).
   - Nowy `features/structure.py`: masy, `hotspot_concentration`, przypisanie hotspotów do mas.
   - `features/extractor.py`: składanie `RepositoryFeatures` z `structure`; sygnatura `extract_features` bez zmian.
4. Nowy pakiet `src/gitgeist/normalization/`: lista znormalizowanych wejść z kotwicami, tryby `absolute` i `corpus`, model wyniku `NormalizedInputs`, model i loader tabeli kwantyli, tabela `data/quantiles-v1.json` jako package data.
5. Skrypt deweloperski `tools/build_quantile_table.py` i plik korpusu `tools/quantile-corpus.toml` (lista repozytoriów z URL i przypiętym commitem); skrypt działa offline na lokalnych klonach (O4).
6. Rozszerzenie `tools/diversity_report.py`: warstwa `normalized` (oba tryby) z licznikami wartości 0/1 i przycięć (do kryterium 3) oraz polecenie `extract-time` (do kryterium 2).
7. Fiksury `tests/fixtures/builder.py`: `create_timeline_repo`, `create_wide_repo` (opis w "Required tests") i odpowiadające im fixture w `tests/conftest.py`.
8. `pyproject.toml`: `[tool.setuptools.package-data]` dla `gitgeist/normalization/data/*.json`; wersja 0.7.0 i wpis w `CHANGELOG.md` (O9).

## Non-goals

- Cechy portretu (9 traits), formuły cech, `VisualSpec`, ziarna układu, style: etap 3.
- Jakakolwiek zmiana `EmotionalState`, sensorów (`sensors/*.py`), mappera, rendererów live i prompt composera. Istniejące pola cech i ich wartości pozostają bez zmian (w tym `has_tests` z obecną regułą, `unique_authors_count` z `%an`, lista 10 hotspotów).
- Flaga `--scale` i plik konfiguracji: etap 7. W etapie 2 tryb skali jest tylko argumentem funkcji biblioteki.
- Tryb `portfolio` i magazyn `~/.config/gitgeist/portfolio.json`: etap 8.
- Zapis znormalizowanych wartości do `profile.json` (O10).
- Tabela kwantyli z około 200 repozytoriów (`design.md:87`): poza etapem 2 przy wariancie rekomendowanym O4.
- Wywołania LLM, sieci, klonowanie repozytoriów przez kod pakietu lub skrypt.
- Naprawa istniejących szerokich `except` w `ingest/git_history.py` (linie 59, 77, 92, 147); etap nie dodaje nowych.

## Behaviour

### Ekstrakcja

- `extract_features(repo_path)` zwraca `RepositoryFeatures` z wypełnionymi polami v2 i `structure`. Liczba wywołań `git` się nie zmienia (dwa wywołania `git rev-parse` i dwa `git log`).
- Wszystkie udziały i proporcje (`share`, `*_share`, `*_ratio`, `hotspot_concentration`) są zaokrąglane do 4 miejsc (`round(x, 4)`), `todo_density` do 2 miejsc. Zaokrąglenie dotyczy wartości zapisanej; obliczenia pośrednie używają pełnej precyzji.
- Ścieżki w cechach v2 mają separator `/` i są względne wobec korzenia repozytorium.

### Klasyfikacja plików

- Plik ma język wtedy, gdy jego rozszerzenie jest w `EXTENSION_LANGUAGE_MAP` (`ingest/repository.py:55-90`, bez zmian).
- `CODE_LANGUAGES` = Python, JavaScript, TypeScript, HTML, CSS, Shell, Go, Rust, C, C/C++ Header, C++, Java, Ruby, PHP, SQL. Języki danych i prozy (JSON, YAML, TOML, XML, Markdown, reStructuredText, Text) nie są kodem.
- `DOC_LANGUAGES` = Markdown, reStructuredText, Text.
- `is_test_path(path)`: prawda, gdy dowolny katalog w ścieżce (bez nazwy pliku), po zamianie na małe litery, zawiera podciąg `test` albo jest równy `spec`, lub gdy nazwa pliku spełnia obecną regułę nazw (`test_*`, `*_test.py`, `*.test.js`, `*.test.ts`, `*.spec.js`, `*.spec.ts`; `ingest/repository.py:186-193`). Podciąg `test` łapie `testes/` (Lua, `analysis.md:164`) i `testing/`, ale też `latest/`; ten fałszywy alarm jest świadomie przyjęty za `design.md:67`.
- Plik testowy w sensie `test_file_count`, `test_ratio` i `test_file_share` to plik kodu spełniający `is_test_path`.

### Cechy statyczne

| Pole | Definicja |
|---|---|
| `code_bytes` | suma `st_size` plików z językiem z `CODE_LANGUAGES` (także plików > 10 MB) |
| `code_file_count` | liczba plików kodu |
| `test_file_count` | liczba plików kodu spełniających `is_test_path` |
| `test_ratio` | `min(1, test_file_count / code_file_count)`; `0.0`, gdy brak plików kodu |
| `doc_ratio` | pliki z językiem z `DOC_LANGUAGES` / pliki ze znanym językiem; `0.0`, gdy brak plików ze znanym językiem |
| `todo_density` | `todo_count * 1000 / file_count`; `0.0`, gdy `file_count == 0` |
| `top_level_directory_count` | liczba nieignorowanych katalogów bezpośrednio w korzeniu (także bez plików) |
| `language_shares` | do 5 języków o największej liczbie plików; `share = file_count / pliki ze znanym językiem`; remis rozstrzyga nazwa rosnąco |

### Cechy historii

| Pole | Definicja |
|---|---|
| `timeline_start` | `"YYYY-MM"` miesiąca (UTC) najstarszego commitu |
| `timeline` | liczby commitów w kolejnych miesiącach kalendarzowych UTC od miesiąca pierwszego do miesiąca ostatniego commitu włącznie; miesiące bez commitów mają `0` |
| `active_months_ratio` | liczba niezerowych pozycji `timeline` / długość `timeline` |
| `top_author_share` | commity najaktywniejszego autora / `commit_count` |
| `top3_author_share` | commity trzech najaktywniejszych autorów / `commit_count` |
| `Hotspot.change_share` | `change_count` / suma wszystkich wpisów `RawGitHistory.file_changes` |

- Tożsamość autora to `%an`, jak w `unique_authors_count` (O5).
- `days_since_last_commit(history, reference_time)` zwraca `(reference_time - last_commit_date)` w dniach jako `float` zaokrąglony do 4 miejsc, przycięty od dołu do `0.0`; `None`, gdy `last_commit_date is None`. Wartość nie jest polem `RepositoryFeatures` (O3).

### Struktura: masy i koncentracja zmian

- Kandydaci na masy: każdy nieignorowany katalog najwyższego poziomu zawierający co najmniej jeden zeskanowany plik (rekurencyjnie) oraz `.` dla plików w korzeniu, jeśli takie istnieją.
- Kolejność kandydatów: `file_count` malejąco, potem nazwa rosnąco (porównanie łańcuchów, więc `.` przed literami).
- Ścieżka z historii należy do kandydata według pierwszego segmentu ścieżki (`.` dla ścieżek bez `/`). Ścieżki, których segment nie jest kandydatem (katalog usunięty, katalog ignorowany, np. zacommitowany `dist/`), trafiają do masy `other`.
- Limit: co najwyżej 8 mas łącznie, z `other` włącznie (O6). Jeśli kandydatów jest więcej niż 8 albo historia ma zmiany poza kandydatami, zostaje 7 pierwszych kandydatów, a reszta oraz zmiany spoza kandydatów tworzą masę `other` z `is_merged = True`. W przeciwnym razie wszyscy kandydaci są masami i `other` nie powstaje.
- Pola masy: `file_count`; `file_share = file_count / StaticFeatures.file_count`; `churn_share` = zmiany plików masy (liczba wpisów `file_changes`, czyli dotknięć pliku przez commit, nie linii; O8) / wszystkie zmiany, `0.0` bez historii; `dominant_language` = język z największą liczbą plików masy (remis: nazwa rosnąco), `None` bez plików ze znanym językiem; `test_file_share` = pliki testowe / pliki kodu masy, `0.0` bez plików kodu.
- `Hotspot.mass` = nazwa masy, do której należy ścieżka (`other` dla scalonych i spoza kandydatów, także gdy `masses` jest puste); `None` tylko bez historii.
- `hotspot_concentration = top10_share - min(1, 10 / file_count)`, gdzie `top10_share` = suma `change_count` 10 pierwszych hotspotów / wszystkie zmiany. Wartość surowa jest w [-1, 1] i nie jest przycinana w cechach; `0.0`, gdy `file_count == 0` lub brak zmian. Przycięcie do [0, 1] należy do normalizacji.

### Normalizacja

- `normalize_features(features, scale="absolute", *, reference_time=None, table=None)` liczy 13 wejść z tabeli niżej i zwraca `NormalizedInputs`. `reference_time` domyślnie równa się `features.extracted_at`.
- Transformacja `log`: `u = log10(x + 1)`. Transformacja `linear`: `u = x`.
- Tryb `absolute`, wejścia `log`: `t = (u - log10(low + 1)) / (log10(high + 1) - log10(low + 1))`, `value = smoothstep(clamp(t, 0, 1))`, gdzie `smoothstep(t) = 3t^2 - 2t^3`. Wejścia `linear`: `value = clamp(x, 0, 1)` bez `smoothstep` ("Ratios stay linear", `design.md:78`).
- Tryb `corpus`: `value = percentile(u, table.inputs[name])`. Punkty tabeli to wartości `u` dla prawdopodobieństw `0.00, 0.05, ..., 1.00` (21 punktów, niemalejące). `u` poniżej pierwszego punktu daje `0.0`, powyżej ostatniego `1.0`. `u` równe jednemu lub kilku kolejnym punktom daje średnią ich prawdopodobieństw (plateau). W pozostałych przypadkach interpolacja liniowa między sąsiednimi punktami.
- Wejście `inverted` jest odwracane po skalowaniu: `value = 1 - value`.
- `clipped = True`, gdy w trybie `absolute` surowe `x` leży poza `[low, high]`, a w trybie `corpus` gdy `u` leży poza zakresem punktów tabeli. Dla wejść `linear` w trybie `absolute` `clipped = True`, gdy `x < 0` lub `x > 1`.
- `ci` jest flagą `0.0`/`1.0` z `has_ci`, przekazywaną bez skalowania w obu trybach, z `clipped = False`.
- Brak historii (`last_commit_date is None`): `recency` ma `raw = None`, `value = 0.0`, `clipped = False`; pozostałe wejścia historii liczą się z wartości domyślnych `0`.

| Wejście | Źródło | Transformacja | Kotwice `absolute` (0 / 1) |
|---|---|---|---|
| `code_size` | `static.code_bytes` | `log` | 1 000 B / 100 000 000 B (O2; `design.md:89` ma 10 kB) |
| `age` | `history.repository_age_days` | `log` | 7 / 7300 dni |
| `recency` | `days_since_last_commit` | `log`, `inverted` | 1 / 1825 dni |
| `authors` | `history.unique_authors_count` | `log` | 1 / 1000 |
| `top_author_share` | `history.top_author_share` | `linear` | 0 / 1 |
| `active_months` | `history.active_months_ratio` | `linear` | 0 / 1 |
| `focus` | `structure.hotspot_concentration` | `linear` | 0 / 1 |
| `test_ratio` | `static.test_ratio` | `linear` | 0 / 1 |
| `doc_ratio` | `static.doc_ratio` | `linear` | 0 / 1 |
| `debt` | `static.todo_density` | `log` | 0 / 200 na 1000 plików |
| `top_level_dirs` | `static.top_level_directory_count` | `log` | 1 / 100 (O7) |
| `depth` | `static.max_directory_depth` | `log` | 1 / 15 (O7) |
| `ci` | `static.has_ci` | flaga | brak |

- Normalizacja działa per wejście. Formuły cech z `design.md:95-105` (np. `alive`, `crowd`, `care`) łączą wejścia i należą do etapu 3; funkcje `smoothstep`, `anchor_position` i `percentile` są publiczne, żeby etap 3 mógł skalować także wartości złożone (O11).

### Tabela kwantyli i skrypt

- `load_quantile_table()` czyta `gitgeist/normalization/data/quantiles-v1.json` przez `importlib.resources` i waliduje go modelem `QuantileTable`. Tabela ma własną wersję `table_version` niezależną od `engine_version`.
- `tools/build_quantile_table.py build --corpus tools/quantile-corpus.toml --reference-time <ISO 8601 z UTC> --out <plik> NAME=PATH [NAME=PATH ...]`:
  - czyta korpus (`[[repository]]` z polami `name`, `url`, `commit` jako pełny SHA);
  - każdy wpis korpusu musi mieć podaną ścieżkę `NAME=PATH`; ścieżka musi być repozytorium z czystym drzewem roboczym i `HEAD` równym `commit`;
  - dla każdego repozytorium liczy `extract_features`, surowe wejścia (ta sama funkcja co normalizacja, z podanym `reference_time`) i `u`; kwantyle liczy interpolacją liniową po posortowanych wartościach (`q = p * (n - 1)`);
  - zapisuje JSON z `sort_keys=True`, `indent=2`, LF i końcowym znakiem nowej linii; ten sam korpus i `reference_time` dają plik identyczny bajt w bajt;
  - nie klonuje, nie pobiera i nie łączy się z siecią.
- Tabela v1 powstaje z korpusu `analysis.md:40` z przypiętymi commitami, bez syntetycznego `fresh` (nie ma URL), czyli z 11 repozytoriów (O4). `reference_time` tabeli v1 zostaje zapisany w pliku.

### Raport różnorodności

- `tools/diversity_report.py run` zapisuje dla każdego repozytorium warstwę `normalized` z wynikami obu trybów (`absolute` i `corpus` z tabelą pakietu) i dodaje do `report.md` sekcję "Normalized inputs": dla każdego wejścia poza `ci` liczba repozytoriów z `value` równym 0 lub 1 oraz liczba z `clipped = True`, osobno dla obu trybów. `reference_time` raportu jest argumentem `--reference-time` (domyślnie czas uruchomienia), zapisanym w `report.json`.
- `tools/diversity_report.py extract-time --runs N PATH` uruchamia `extract_features(PATH)` N razy (domyślnie 5) po jednym przebiegu rozgrzewającym i wypisuje medianę czasu w sekundach.

## Business rules

1. Determinizm: dwie ekstrakcje niezmienionego repozytorium dają identyczne `RepositoryFeatures` z wyjątkiem `extracted_at`; `normalize_features` z tym samym `reference_time` i tą samą tabelą daje identyczny wynik.
2. Nienaruszalność istniejących cech: wartości pól istniejących przed etapem 2 nie zmieniają się dla żadnego wejścia; `evaluate_emotional_state` i `map_emotional_to_latent` dają te same wyniki co na `main` w punkcie odgałęzienia.
3. Read-only: ekstrakcja, normalizacja i skrypt nie zapisują niczego w badanym repozytorium.
4. Brak cichych fallbacków: brak lub uszkodzenie tabeli w trybie `corpus` jest błędem, nie przełączeniem na `absolute`; nowe ścieżki kodu nie dodają `except` tłumiących błędy.
5. Wartości `value` w `NormalizedInputs` zawsze leżą w [0, 1] i są skończone.
6. Normalizacja nie wywołuje `git`, systemu plików (poza odczytem tabeli pakietu) ani sieci.

## Authorization

`none` - biblioteka lokalna i skrypty deweloperskie bez mechanizmu autoryzacji i bez sieci.

## Data / API

```python
# src/gitgeist/schemas/features.py (pola dodane; wszystkie modele frozen)
class LanguageShare(BaseModel):
    name: str
    file_count: int
    share: float

class Mass(BaseModel):
    name: str                       # nazwa katalogu, "." albo "other"
    is_merged: bool = False
    file_count: int = 0
    file_share: float = 0.0
    churn_share: float = 0.0
    dominant_language: str | None = None
    test_file_share: float = 0.0

class Hotspot(BaseModel):           # istniejące: path, change_count
    change_share: float = 0.0
    mass: str | None = None

class StaticFeatures(BaseModel):    # istniejące pola bez zmian
    code_bytes: int = 0
    code_file_count: int = 0
    test_file_count: int = 0
    test_ratio: float = 0.0
    doc_ratio: float = 0.0
    todo_density: float = 0.0
    top_level_directory_count: int = 0
    language_shares: list[LanguageShare] = Field(default_factory=list)

class GitHistoryFeatures(BaseModel):  # istniejące pola bez zmian
    timeline_start: str | None = None   # "YYYY-MM"
    timeline: list[int] = Field(default_factory=list)
    active_months_ratio: float = 0.0
    top_author_share: float = 0.0
    top3_author_share: float = 0.0

class StructureFeatures(BaseModel):
    masses: list[Mass] = Field(default_factory=list)
    hotspot_concentration: float = 0.0

class RepositoryFeatures(BaseModel):  # istniejące pola bez zmian
    structure: StructureFeatures = Field(default_factory=StructureFeatures)
```

```python
# src/gitgeist/ingest/repository.py
CODE_LANGUAGES: frozenset[str]
DOC_LANGUAGES: frozenset[str]
def is_test_path(relative_path: str) -> bool: ...

@dataclass(frozen=True)
class ScannedFile:
    path: str               # względna, separator "/"
    size_bytes: int
    language: str | None

# FileScanResult zyskuje pola:
#   files: list[ScannedFile]              (kolejność skanowania)
#   top_level_directories: list[str]      (posortowane)

# src/gitgeist/ingest/git_history.py
# RawGitHistory zyskuje pole:
#   commit_dates: list[datetime]          (aware UTC, kolejność git log)

# src/gitgeist/features/history.py
def compute_history_features(raw: RawGitHistory) -> GitHistoryFeatures: ...     # sygnatura bez zmian
def days_since_last_commit(history: GitHistoryFeatures, reference_time: datetime) -> float | None: ...

# src/gitgeist/features/structure.py
def compute_structure_features(scan: FileScanResult, raw: RawGitHistory) -> StructureFeatures: ...
def assign_hotspot_masses(hotspots: list[Hotspot], masses: list[Mass]) -> list[Hotspot]: ...

# src/gitgeist/features/extractor.py
def extract_features(repo_path: Path | str) -> RepositoryFeatures: ...           # sygnatura bez zmian
```

```python
# src/gitgeist/normalization/__init__.py eksportuje poniższe nazwy
ScaleMode = Literal["absolute", "corpus"]
INPUT_NAMES: tuple[str, ...]    # 13 nazw w kolejności tabeli z "Behaviour"

class NormalizedValue(BaseModel):     # frozen
    value: float                      # [0, 1]
    raw: float | None                 # x przed transformacją
    clipped: bool

class NormalizedInputs(BaseModel):    # frozen
    scale: ScaleMode
    table_version: str | None         # None w trybie absolute
    reference_time: datetime
    inputs: dict[str, NormalizedValue]   # klucze dokładnie INPUT_NAMES

class QuantileTable(BaseModel):       # frozen
    table_version: str
    probabilities: list[float]        # 21 wartości 0.00..1.00 co 0.05
    reference_time: datetime
    corpus: list[CorpusEntry]         # name, url, commit
    inputs: dict[str, list[float]]    # INPUT_NAMES bez "ci"; 21 niemalejących skończonych wartości u

def raw_inputs(features: RepositoryFeatures, reference_time: datetime) -> dict[str, float | None]: ...
def normalize_features(
    features: RepositoryFeatures,
    scale: ScaleMode = "absolute",
    *,
    reference_time: datetime | None = None,
    table: QuantileTable | None = None,   # None w trybie corpus = load_quantile_table()
) -> NormalizedInputs: ...
def load_quantile_table() -> QuantileTable: ...
def smoothstep(t: float) -> float: ...
def anchor_position(value: float, low: float, high: float) -> float: ...   # t przed clamp
def percentile(u: float, points: Sequence[float], probabilities: Sequence[float]) -> float: ...
```

Pliki zapisywane:

- Pakiet: brak nowych artefaktów CLI. `profile.json` zyskuje nowe pola w bloku `repository` (patrz "Compatibility and migration").
- Package data: `src/gitgeist/normalization/data/quantiles-v1.json` (w repozytorium, budowany skryptem).
- Skrypty: `tools/build_quantile_table.py` zapisuje tylko plik `--out`; `tools/diversity_report.py` zapisuje tylko w `--out` (git-ignored `tmp/`).

## Compatibility and migration

- `profile.json`: blok `repository` zyskuje pola z "Data / API" (addytywnie). Starszy `profile.json` nadal się waliduje (nowe pola mają wartości domyślne). Nowe pola nie są ulotne: dwa przejścia na tym samym snapshotcie dają te same wartości, więc reguła stabilności z `docs/features/mvp-completion/spec.md:41` obowiązuje bez zmian (przy O3 rekomendowanym).
- `summary.md`, `why_this_look`, `live-state.json`, `live-preview.html`, `prompt.txt`, `identity-seed.json`: bez zmian bajt w bajt.
- Wersja: 0.7.0 (zmiana kształtu `profile.json`), wpis w `CHANGELOG.md` (O9). Nowe zależności runtime: brak.

## Effect on existing specs

- `docs/features/feature-extraction/spec.md` (zmiana w PR implementacji, po polsku): w "Scope" punkt 2 wymienia nowe pola i `StructureFeatures` z odnośnikiem do tego specu; w "Data / API" pojawia się `RepositoryFeatures.structure`; w "Required tests" nowe pliki testów; w "Relevant SDD / ADR" odnośnik do tego specu. Reguły biznesowe i obsługa błędów bez zmian.
- `docs/features/explainability/spec.md`: bez zmian; kryterium 4 (roundtrip `profile_json`) obejmuje nowe pola automatycznie.
- `docs/features/mvp-completion/spec.md`: bez zmian przy O3 rekomendowanym; przy wariancie "pole w cechach" lista pól ulotnych w linii 41 i kryterium 4 zyskują `days_since_last_commit`.
- `emotional-state-model`, `visual-latent-mapper`, `live-renderers`, `prompt-to-image`: bez zmian (nie czytają nowych pól).
- `README.md`, sekcja "Measuring visual diversity": warstwa `normalized`, polecenie `extract-time` i skrypt tabeli kwantyli.
- `docs/features/visual-diversity/plan.md`: status etapu 2 aktualizowany dopiero po merge'u.

## Edge cases

- Katalog bez Git oraz repozytorium bez commitów: pola historii v2 mają wartości domyślne (`timeline = []`, `timeline_start = None`, udziały `0.0`); masy powstają z drzewa z `churn_share = 0.0`; `hotspot_concentration = 0.0`; `Hotspot` lista pusta; `recency` ma `raw = None`.
- Brak skanowanych plików (pusty katalog albo repozytorium, w którym wszystkie pliki z historii są usunięte lub ignorowane): `masses = []`, `language_shares = []`, wszystkie proporcje `0.0`, `todo_density = 0.0`. Jeśli historia ma zmiany, hotspoty z niej zostają i każdy ma `mass = "other"`, choć na liście mas nie ma masy `other`. To zamierzone (decyzja Q1 z przeglądu PR #6): `other` oznacza ścieżkę spoza nazwanych mas, więc konsumenci nie mogą zakładać, że `Hotspot.mass` zawsze wskazuje element `masses`.
- Tylko pliki w korzeniu: jedna masa `.` z `file_share = 1.0`.
- Katalog najwyższego poziomu bez plików (lub tylko z ignorowanymi): liczony w `top_level_directory_count`, nie jest masą.
- Prawdziwy katalog o nazwie `other`: pozostaje zwykłą masą (`is_merged = False`); scalona masa ma `is_merged = True`, więc nazwa może się powtórzyć, a konsumenci rozróżniają je po `is_merged`.
- Ścieżki w historii spoza drzewa (usunięte, ignorowane, submoduły): trafiają do `other` i zwiększają tylko `churn_share`.
- Commity w jednym miesiącu: `timeline` ma jedną pozycję, `active_months_ratio = 1.0`. Historia przez przełom roku: miesiące liczone ciągle (`2025-12`, `2026-01`).
- Daty commitów niemonotoniczne (rebase, cherry-pick): oś czasu liczy się z min i max dat, kolejność logu nie ma znaczenia.
- Ostatni commit późniejszy niż `reference_time` (przesunięty zegar): `days_since_last_commit = 0.0`, `recency` z `clipped = True`.
- Pojedynczy autor: `top_author_share = top3_author_share = 1.0`; mniej niż trzech autorów: `top3_author_share = 1.0`.
- Mniej niż 10 plików: `min(1, 10 / file_count) = 1`, więc `hotspot_concentration <= 0`.
- Wszystkie wartości wejścia w tabeli równe (plateau na całej długości): wartość równa daje `0.5`, mniejsza `0.0`, większa `1.0`.

## Errors

- `normalize_features` z `scale` spoza `absolute`, `corpus` (w tym `portfolio`): `ValueError` z nazwą trybu i listą obsługiwanych.
- `reference_time` bez strefy czasowej: `ValueError`.
- Tryb `corpus` bez pliku tabeli w pakiecie: `FileNotFoundError` z nazwą zasobu; plik niezgodny ze schematem (brak wejścia, zła liczba punktów, wartości malejące lub nieskończone, inne `probabilities`): `ValueError` z `table_version` i nazwą pola. Brak przełączenia na `absolute`.
- `tools/build_quantile_table.py`: wpis korpusu bez `NAME=PATH`, `NAME` spoza korpusu, ścieżka nie jest repozytorium, brudne drzewo robocze, `HEAD` różny od przypiętego commitu, `--reference-time` bez strefy: komunikat na stderr z nazwą repozytorium i przyczyną, kod wyjścia 1, brak pliku wyjściowego. Błąd zapisu: `OSError` zamieniony na komunikat i kod 1.
- Ekstrakcja: obsługa błędów `git` i ścieżek bez zmian względem `docs/features/feature-extraction/spec.md` "Errors".

## Acceptance criteria

1. Każda cecha v2 ma test na fiksurze z dokładną oczekiwaną wartością (lista w "Required tests"); każde wejście normalizacji ma test z dokładną wartością w obu trybach.
2. Czas ekstrakcji na `lua` (korpus `analysis.md`, przypięty commit `8cb93bad`): mediana z 5 przebiegów `tools/diversity_report.py extract-time` na gałęzi jest co najwyżej 1.5 x mediana na `main` z punktu odgałęzienia, na tej samej maszynie, w tej samej sesji. Log obu pomiarów z komendą trafia do PR.
3. Na korpusie 12 repozytoriów z `analysis.md` żadne wejście poza `ci` nie ma `clipped = True` dla więcej niż 3 repozytoriów, w trybie `absolute` i w trybie `corpus` (reguła liczenia: O2). Raport podaje też liczbę wartości dokładnie 0 lub 1. Prototyp poza repozytorium (nie kod produktu) na tym korpusie z kotwicami z tego specu daje maksymalnie 3 przycięcia na wejście (`age`, `recency`, `top_level_dirs`, `depth`); z kotwicą 10 kB `code_size` ma 4. W trybie `absolute` czas odniesienia (`--reference-time`) jest co najmniej 24 h po najnowszym commicie każdego repozytorium korpusu, bo `recency` ma dolną kotwicę 1 dnia: repozytorium z commitem młodszym niż 1 dzień zawsze ma `clipped = True` dla `recency`, niezależnie od rozkładu korpusu.
4. Brak zmiany obrazu: `tools/diversity_report.py run` na tym samym korpusie daje na gałęzi i na `main` z punktu odgałęzienia identyczne warstwy `scores`, `nouls`, `choices`, `axes`, `materiality`, `live-state.json`, prompty oraz identyczne wartości `D` v1 (mediana najbliższego sąsiada i najbliższa para, oba tryby). Jedyną dozwoloną różnicą jest ciąg wersji silnika: `engine_version` w `live-state.json` i etykieta wersji ("Engine: Gitgeist v…") w HTML, wraz z wynikającym z niej przesunięciem pikseli na zrzutach; po ustawieniu tej samej wersji pliki live i zrzuty są identyczne bajtowo. Etap 2 nie ma celu dla `D`; cele 0.40 i 0.25 dotyczą etapów 4 i 5.
5. `RepositoryFeatures` z polami v2 przechodzi roundtrip przez `profile.json` (`model_validate` po `model_dump(mode="json")`) z równością modeli.
6. Determinizm: dwie ekstrakcje dają równe cechy poza `extracted_at`; dwa przebiegi `build_quantile_table.py` na tym samym korpusie dają identyczny plik.
7. `quantiles-v1.json` jest w wheelu: `pip wheel . --no-deps -w tmp/wheel` i lista plików wheela zawiera `gitgeist/normalization/data/quantiles-v1.json` (log w PR).
8. Wszystkie testy przechodzą offline (R5) na Pythonie 3.11, 3.12 i 3.13 w CI `verify`; liczba testów rośnie względem 251.

## Required tests

Wartości oczekiwane poniżej policzył skrypt referencyjny poza repozytorium według reguł tego specu. Test implementacji jest źródłem prawdy; rozbieżność to pytanie do specu, nie powód do cichej zmiany oczekiwanej wartości.

Nowe fiksury w `tests/fixtures/builder.py` (daty commitów przez `GIT_AUTHOR_DATE` i `GIT_COMMITTER_DATE`, autor przez `GIT_AUTHOR_NAME`):

- `create_timeline_repo`: 5 commitów, każdy dodaje plik `f<i>.py` z treścią `x = <i>\n`: `2025-11-15` Ada, `2025-11-20` Ada, `2026-01-10` Bob, `2026-03-05` Cy, `2026-03-06` Dee (godzina `10:00:00Z`).
- `create_wide_repo`: `README.md` (`# wide\n`), katalogi `a` do `j`, gdzie k-ty katalog (od 0) ma `10 - k` plików `m<i>.py` z treścią `v = <i>\n`, oraz `old/x.py`; commit `2026-04-01`; potem commit usuwający `old/` i zmieniający `a/m0.py` (`2026-04-02`) i 4 commity zmieniające `a/m0.py` (`2026-04-03` do `2026-04-06`).

`tests/test_static_features.py`:

- `minimal-repo`: `code_bytes == 65`, `code_file_count == 2`, `test_ratio == 0.0`, `doc_ratio == 0.0`, `top_level_directory_count == 0`, `language_shares == [("Python", 2, 1.0)]`.
- `clean-modular-repo`: `code_file_count == 4`, `test_file_count == 2` (`tests/__init__.py`, `tests/test_core.py`), `test_ratio == 0.5`, `doc_ratio == 0.2857`, `top_level_directory_count == 4`, `language_shares` = Python 4 / 0.5714, Markdown 2 / 0.2857, YAML 1 / 0.1429.
- `legacy-chaotic-repo`: `todo_density == 1000.0` (5 TODO/FIXME w 5 plikach), `test_ratio == 0.0`, `language_shares` = Python 0.4, JSON 0.2, JavaScript 0.2, Shell 0.2 (remis po nazwie).
- `wide_repo`: `code_file_count == 55`, `doc_ratio == 0.0179`, `top_level_directory_count == 10`.
- `is_test_path` na ścieżkach: `testes/a.c` prawda, `spec/a_spec.rb` prawda, `src/foo_test.py` prawda, `latest/x.py` prawda (udokumentowany fałszywy alarm), `src/contest.py` fałsz (podciąg w nazwie pliku się nie liczy), `README.md` fałsz.
- Plik > 10 MB z kodem: wliczony do `code_bytes`, TODO nieliczone (zachowanie istniejące).

`tests/test_history_features.py`:

- `timeline_repo`: `timeline_start == "2025-11"`, `timeline == [2, 0, 1, 0, 2]`, `active_months_ratio == 0.6`, `top_author_share == 0.4`, `top3_author_share == 0.8`.
- `clean-modular-repo`: `top_author_share == 0.6667`, `top3_author_share == 1.0`, `timeline == [3]`.
- `legacy-chaotic-repo`: pierwszy hotspot `hotspot.py` z `change_share == 0.5556`.
- `days_since_last_commit`: dla `last_commit_date = 2026-03-06T10:00:00Z` i `reference_time = 2026-03-16T10:00:00Z` wynik `10.0`; `reference_time` wcześniejszy daje `0.0`; brak historii daje `None`; naiwny `reference_time` daje `ValueError`.
- Katalog bez Git i puste repozytorium: wartości domyślne pól v2.

`tests/test_structure_features.py` (nowy):

- `minimal-repo`: jedna masa `.` z `file_share == 1.0`, `churn_share == 1.0`, `dominant_language == "Python"`.
- `clean-modular-repo`: masy w kolejności `.`, `src`, `tests`, `.github`, `docs`; `tests` ma `test_file_share == 1.0`; `.` ma `dominant_language == "Markdown"`; `hotspot_concentration == 0.0`.
- `legacy-chaotic-repo`: masy `.` (`file_share == 0.8`, `churn_share == 0.8889`) i `legacy` (`0.2`, `0.1111`).
- `wide_repo`: 8 mas: `a` do `g` i `other` (`is_merged`, `file_count == 7` z `h`, `i`, `j` i `.`, `churn_share == 0.1429` z udziałem usuniętego `old/`); `a` ma `file_share == 0.1786` i `churn_share == 0.2381`; `hotspot_concentration == 0.0754`; hotspoty: `a/m0.py` (6, 0.0952, `a`), `old/x.py` (2, 0.0317, `other`).
- Prawdziwy katalog `other` wśród 7 pierwszych przy więcej niż 8 kandydatach: dwie masy `other`, rozróżnione `is_merged`.
- Katalog najwyższego poziomu bez plików: brak masy, `top_level_directory_count` go liczy.
- Suma `file_share` i suma `churn_share` po masach równa 1 z tolerancją 0.001 (gdy są pliki i historia).

`tests/test_normalization.py` (nowy):

- `smoothstep(0) == 0`, `smoothstep(0.5) == 0.5`, `smoothstep(1) == 1`; wartości poza [0, 1] są przycinane.
- Tryb `absolute`, dokładne wartości (6 miejsc): `authors` 31 -> 0.419417; `age` 365 -> 0.590880; `recency` 30 dni -> 0.645009; `debt` 20 -> 0.610307; `code_size` 1 000 000 B -> 0.647950; `top_level_dirs` 10 -> 0.402557; `depth` 5 -> 0.542436.
- Granice: `authors` 1 -> 0.0 z `clipped = False`; `authors` 5000 -> 1.0 z `clipped = True`; `focus` -0.2 -> 0.0 z `clipped = True`; `ci` przekazane jako 0.0 i 1.0.
- `percentile`: punkty `[0, 10, 20]` z prawdopodobieństwami `[0, 0.5, 1]`: 15 -> 0.75, -1 -> 0.0 (`clipped`), 25 -> 1.0 (`clipped`); plateau `[0, 0, 0, 10, 20]` z `[0, 0.25, 0.5, 0.75, 1]`: 0 -> 0.25.
- Tryb `corpus` na tabeli testowej zbudowanej w teście (nie z pakietu): oczekiwane wartości dla dwóch fiksur.
- Monotoniczność: każde wejście rośnie (`recency` maleje) z wartością surową na siatce 20 punktów.
- Katalog bez Git: `recency` ma `raw is None` i `value == 0.0`.
- Błędy: `scale="portfolio"` -> `ValueError`; naiwny `reference_time` -> `ValueError`; tabela bez wejścia, z 20 punktami lub z malejącymi wartościami -> `ValueError`.
- `load_quantile_table()` czyta tabelę pakietu, `table_version == "1"`, wszystkie wejścia poza `ci` obecne.

`tests/test_quantile_table.py` (nowy, skrypt importowany jak w `tests/test_diversity_report.py`):

- Budowa na dwóch fiksurach z korpusem TOML w `tmp_path` (commity z `git rev-parse HEAD` fiksur): dwa przebiegi dają identyczny plik, plik waliduje się jako `QuantileTable`.
- Brakujący `NAME=PATH`, `HEAD` różny od przypiętego, brudne drzewo: kod 1, komunikat z nazwą repozytorium, brak pliku wyjściowego.

`tests/test_diversity_report.py`:

- `run --no-images` na dwóch fiksurach zapisuje warstwę `normalized` dla obu trybów, a `report.md` ma sekcję "Normalized inputs".
- `extract-time --runs 2` na fiksurze wypisuje liczbę dodatnią.

Regresja i kontrakty:

- `tests/test_extractor.py`: dla każdej fiksury `evaluate_emotional_state(features)` równa się `evaluate_emotional_state(features_bez_v2)`, gdzie `features_bez_v2` ma pola v2 zresetowane do wartości domyślnych (sensory nie czytają nowych pól); to samo dla `map_emotional_to_latent` i `explain(...).summary_md`.
- `tests/test_schemas.py`: walidacja i roundtrip JSON nowych modeli; starszy JSON bez pól v2 się waliduje.
- `tests/test_cli.py`: `profile.json` z `analyze` zawiera `repository.structure.masses`.

Żaden test nie używa sieci, LLM ani korpusu z zewnętrznymi repozytoriami; kryteria 2, 3 i 4 sprawdzają skrypty deweloperskie z logiem w PR.

## Decisions

Wszystkie pytania rozstrzygnięte 2026-10-22: przyjęty wariant (a) w O1-O11. Opcje zostają poniżej jako zapis uzasadnienia.

O1. Forma specu. (a) Nowy spec `docs/features/features-v2-normalization/spec.md`, a `feature-extraction/spec.md` dostaje krótkie poprawki z odnośnikiem w PR implementacji. (b) Wszystko wpisane bezpośrednio do `feature-extraction/spec.md`. Rekomendacja: (a), bo normalizacja jest nowym modułem poza ekstrakcją, a plan dla etapu 9 też tworzy nowy spec.

O2. Reguła liczenia w kryterium 3 i dolna kotwica rozmiaru. (a) Liczyć tylko wartości przycięte (`clipped`), a prawdziwe granice (0 testów, 1 autor, brak TODO) raportować osobno; dolna kotwica `code_size` 1 kB zamiast 10 kB. (b) Liczyć dosłownie wartości 0 lub 1 w trybie `absolute`: prototyp daje 4 dla `code_size`, 4 dla `test_ratio` i 8 dla `debt` (6 repozytoriów bez TODO), więc kryterium nie przejdzie bez zmiany znaczenia cech. (c) Mierzyć kryterium tylko w trybie `corpus`: przy tabeli z tego samego korpusu wynik jest cyrkularny. Rekomendacja: (a).

O3. `days_since_last_commit`. (a) Funkcja pochodna liczona przy normalizacji z `last_commit_date` i `reference_time` (domyślnie `extracted_at`), bez pola w cechach; `profile.json` pozostaje stabilny. (b) Pole w `GitHistoryFeatures` liczone przy ekstrakcji; wtedy `profile.json` zmienia się z dnia na dzień i trzeba dopisać pole do listy pól ulotnych w `mvp-completion/spec.md:41`. Rekomendacja: (a).

O4. Źródło tabeli kwantyli v1. (a) 11 repozytoriów z korpusu `analysis.md` z przypiętymi commitami (bez syntetycznego `fresh`); tabela z około 200 repozytoriów później jako `table_version` 2. (b) Około 200 publicznych repozytoriów już w etapie 2: klonowanie, sieć, czas i miejsce na dysku, wymaga Twojej zgody. (c) Bez tabeli w etapie 2, tryb `corpus` później: niezgodne z planem. Rekomendacja: (a). Uwaga: korpus `analysis.md` jest dziś tylko na boksie agenta (`is-odd`, `click`, `flask`, `requests` w osobnym katalogu), nie na Twoim PC; `tools/quantile-corpus.toml` zapisze URL i commity, żeby dało się go odtworzyć.

O5. Tożsamość autora. (a) `%an`, jak istniejące `unique_authors_count`; bez zmiany istniejących wartości. (b) `%ae` jak w `design.md:61`: wymaga zmiany formatu `git log` i daje drugą liczbę autorów różną od `unique_authors_count` (albo zmienia ją i przesuwa sensory). Rekomendacja: (a).

O6. Limit mas. (a) Co najwyżej 8 mas łącznie, z `other`. (b) 8 nazwanych plus `other` (do 9). Rekomendacja: (a), bo daje stały górny limit dla układu w etapie 3; `design.md:62` dopuszcza oba odczyty.

O7. Kotwice bez wartości w `design.md:89`: `top_level_dirs` i `depth`. (a) Przyjąć 1 / 100 i 1 / 15 (log) teraz. (b) Zostawić je dla etapu 3 razem z formułą `sprawl`. Rekomendacja: (a), bo kryterium 3 obejmuje wszystkie wejścia, a prototyp daje dla nich po 3 przycięcia.

O8. Jednostka `churn_share`. (a) Liczba dotknięć pliku przez commity (`file_changes`), ta sama jednostka co hotspoty i `hotspot_concentration`, bez zmian w ingestorze. (b) Linie dodane i usunięte per plik: wymaga zbierania linii per ścieżka i przeważają w niej pliki generowane. Rekomendacja: (a).

O9. Wersja. (a) 0.7.0, bo zmienia się kształt `profile.json`. (b) 0.6.1, bo zmiana jest addytywna i obraz się nie zmienia. Rekomendacja: (a).

O10. Gdzie trafiają znormalizowane wartości. (a) Tylko biblioteka i `tools/diversity_report.py`; `profile.json` dostaje `traits` w etapie 3 (`plan.md:61`). (b) Blok `normalized` w `profile.json` już teraz: kolejna zmiana kształtu i wybór trybu bez flagi `--scale` (etap 7). Rekomendacja: (a).

O11. Kolejność normalizacji i formuł cech. Plan (kryterium 3) normalizuje każde wejście osobno, a tabela "Traits" w `design.md:95-105` podaje formuły "before scaling", czyli skalowanie wartości złożonej. (a) Etap 2 normalizuje per wejście i udostępnia funkcje skalujące; o kolejności dla każdej cechy decyduje spec etapu 3. (b) Etap 2 implementuje też skalowanie wartości złożonych według `design.md`. Rekomendacja: (a), bo (b) wchodzi w zakres etapu 3.

## Relevant SDD / ADR

- `docs/features/visual-diversity/plan.md`, `docs/features/visual-diversity/design.md`, `docs/features/visual-diversity/analysis.md`
- `docs/decisions/0001-trait-per-abstract-channel.md` (kanały, które etap 3 przypisze cechom; etap 2 ich nie dotyka)
- `docs/decisions/0002-optional-llm-evaluation-strategy.md`
- `docs/features/feature-extraction/spec.md`, `docs/features/mvp-completion/spec.md`, `docs/features/explainability/spec.md`
- `docs/product/emotional-repository-portrait-system.md` (sekcja 8.1)
