# Explainability: summary, why-this-look i profile.json (Faza 6)

Path: `docs/features/explainability/spec.md`

## Goal

Zbudować Fazę 6 architektury Gitgeist: warstwę explainability. Dla przeanalizowanego repozytorium system produkuje deterministyczne, czytelne dla człowieka wyjaśnienie portretu: podsumowanie analizy (`summary.md`, artefakt wymagany sekcji 23) oraz uzasadnienie wyglądu (why-this-look) wywodzone z emotional state i visual latent profile, wraz z `profile.json` (drugi artefakt wymagany sekcji 23, serializacja profili warstw 1-3). Celem jest pokazanie, dlaczego portret wygląda tak, a nie inaczej, zanim system stanie się „generatorem ładnych obrazków" (sekcja 27).

## Related requirements

- `docs/product/emotional-repository-portrait-system.md#L1238-L1259` (Sekcja 27: Explainability: emotional state, visual latent profile, top contributing repository signals, top JEV sensors, textual explanation; przykład „Why does this portrait look stable and layered?")
- `docs/product/emotional-repository-portrait-system.md#L1149-L1167` (Sekcja 23: artefakty wymagane `profile.json`, `summary.md`)
- `docs/product/emotional-repository-portrait-system.md#L1409-L1411` (Faza 6: Explainability: summary + why-this-look)
- `docs/product/emotional-repository-portrait-system.md#L1282-L1289` (Sekcja 28.3: Random pretty pictures: mitigacja przez explainability)
- `docs/features/prompt-to-image/spec.md` (wzorzec fasady, zapisu artefaktów i kwalifikatorów osi)

## Scope

1. Moduł explainability (`src/gitgeist/explain/explainer.py`, pakiet `src/gitgeist/explain/`):
   - Funkcja `explain(features: RepositoryFeatures, emotional_state: EmotionalState, profile: VisualLatentProfile, repository_name: str | None = None, output_dir: Path | str | None = None) -> ExplanationArtifacts`.
   - Klasa wynikowa `ExplanationArtifacts` (pydantic, frozen): `summary_md: str`, `why_this_look: tuple[str, ...]`, `profile_json: str`, `summary_path: Path | None`, `profile_path: Path | None`.
   - `summary_md` to pełna treść artefaktu `summary.md` w języku angielskim ze stałymi sekcjami: nagłówek z nazwą repo, repository overview (sygnały warstwy 1), emotional state (nazwane scores z kwalifikatorami, nouls, dominanty choices), visual latent profile (osie z kwalifikatorami, dominująca materiałowość, dominant features), why-this-look.
   - `profile_json` to deterministyczna serializacja JSON pakietu `{"repository": ..., "emotional_state": ..., "visual_latent": ...}` przez `model_dump(mode="json")` każdego profilu.
2. Why-this-look (deterministyczne uzasadnienie wyglądu):
   - Nagłówek pytania wskazuje cechy wyglądu wynikające z osi o największej odległości od neutralnej wartości 0.5, opisane stałym, dosłownym słownictwem osi (np. `layering` → „layered", `symmetry` → „symmetrical"); bez metafor i stereotypów.
   - Dla każdej wyróżnionej osi lista 1-3 najsilniej przyczyniających się emotional scores z kierunkiem wpływu i kwalifikatorem (niski/średni/wysoki), na podstawie jawnego, utrzymywanego obok wag mapowania `src/gitgeist/mapping/axes.py`.
   - Sekcja top JEV sensors: do 5 pól `EmotionalScores` o największej odległości od 0.5, z kwalifikatorami.
   - Sekcja top contributing repository signals: bounded, deterministyczne reguły atrybucji cech warstwy 1 (obecność testów/CI/readme/licencji, velocity, hotspots, todo_count, dominujący język) do scores, zgodne z regułami `src/gitgeist/sensors/scores.py`.
3. Zapis artefaktów: przy `output_dir` zapis `summary.md` i `profile.json` (UTF-8), z tworzeniem katalogu wraz z rodzicami; nazwy kanoniczne wg sekcji 23.
4. Re-eksport publicznego API (`gitgeist.explain`, `gitgeist.ExplanationArtifacts`) w pakiecie `gitgeist`.
5. Testy jednostkowe i integracyjne pokrywające treść, determinizm, atrybucję, zapis artefaktów i obsługę błędów.

## Non-goals

- Interaktywny tryb wyjaśnień (interactive explanation mode) i eksploracja (Post-MVP, sekcje 31-32).
- Wyjaśnienia generowane przez LLM lub OpenRouter; explainability pozostaje w pełni deterministyczne.
- Artefakty `timeline.json`, `comparison.json`, `identity-seed.json`, `critique.json` (Post-MVP / inne fazy).
- Interfejs CLI (sekcja 22) i pipeline łączący fazy end-to-end.
- Zmiana zachowania istniejących sensorów, mapowania i rendererów.

## Behaviour

- `explain` zwraca kompletne `ExplanationArtifacts` wyłącznie z danych wejściowych; identyczne obiekty wejściowe dają identyczne `summary_md`, `why_this_look` i `profile_json` (bajt w bajt).
- Treść `summary_md` i `why_this_look` nie zawiera `calculated_at`, `source_commit`, `engine_version`, ścieżek lokalnych ani innych pól ulotnych; zmiana tych pól nie zmienia tekstów.
- Kwalifikatory osi są spójne z prompt composer: wartość `<= 0.33` niska, `<= 0.66` średnia, powyżej wysoka; progi włączne dla dolnych granic przedziałów.
- Kierunek wpływu score na oś jest zgodny ze znakiem wagi w `axes.py` (np. `chaos` obniża `symmetry`); dla osi `biological_vs_mechanical` wyjaśnienie opisuje oba kierunki dosłownie (0.0 organic, 1.0 mechanical).
- `profile_json` zawiera pełne profile (w tym `calculated_at`, `source_commit`, `engine_version`), sortowanie kluczy stabilne (`json.dumps` z `sort_keys=True`, `indent=2`), kodowanie UTF-8 bez znaków nienależących do ASCII w danych strukturalnych.
- Przy `output_dir` funkcja zapisuje dokładnie `summary.md` i `profile.json` i zwraca ustawione `summary_path` oraz `profile_path`; bez `output_dir` ścieżki pozostają `None` i nic nie jest zapisywane.

## Business rules

- Wyróżnione osie wyglądu: do 3 osi o największej wartości `abs(value - 0.5)` spośród 14 osi `VisualLatentAxes`, w kolejności malejącej; przy remisie kolejność alfabetyczna nazw pól.
- Wyróżnione score w atrybucji osi: wyłącznie score z niezerowym współczynnikiem w tabeli wag dla danej osi, sortowane malejąco po `|waga * (score_value - 0.5)|` z progiem odcinka; maksymalnie 3 pozycje.
- Top JEV sensors: maksymalnie 5 pól `EmotionalScores` sortowanych malejąco po `abs(value - 0.5)`; przy remisie kolejność alfabetyczna.
- Reguły atrybucji sygnałów repozytorium są statyczne i jawne w kodzie modułu (tabela signal→score), mirrorują reguły `scores.py` tylko opisowo; modyfikacja `scores.py` poza tym modułem jest zakazana.
- Materiałowość: w `summary_md` i why-this-look pojawia się wyłącznie `materiality.dominant`; wagi pozostałych materiałów nie są ujawniane.
- Pusta lista `dominant_features` i brak `repository_name`: sekcje opcjonalne są pomijane, treść pozostaje kompletna.

## Authorization

Brak (funkcja czysto lokalna, bez dostępu sieciowego i bez kontroli dostępu).

## Data / API

- Wejście:
  - `features`: `RepositoryFeatures` (wymagane)
  - `emotional_state`: `EmotionalState` (wymagane)
  - `profile`: `VisualLatentProfile` (wymagane)
  - `repository_name`: `str | None = None`
  - `output_dir`: `Path | str | None = None`
- Wyjście:
  - `ExplanationArtifacts`:
    - `summary_md`: `str`
    - `why_this_look`: `tuple[str, ...]`
    - `profile_json`: `str`
    - `summary_path`: `Path | None` (jeśli zapisano)
    - `profile_path`: `Path | None` (jeśli zapisano)
- Publiczne nazwy:
  - `gitgeist.explain.explain`
  - `gitgeist.explain.ExplanationArtifacts`
  - oba re-eksportowane na poziomie pakietu `gitgeist`

## Edge cases

- Ekstremalne profile (wszystkie osie 0.0 lub 1.0): treść powstaje bez błędów, bez wartości NaN, kwalifikatory poprawne.
- Wszystkie osie równe 0.5: tryb remisu wyboru osi daje ustaloną, alfabetyczną trójkę; tekst pozostaje sensowny.
- `features.history.is_git_repo = False` i zerowe liczniki: sekcja repository overview opisuje brak historii bez dzielenia przez zero.
- Wielokrotne wywołania z tymi samymi danymi i tym samym `output_dir`: nadpisują artefakty identyczną treścią.

## Errors

- Przekazanie obiektu innego niż `RepositoryFeatures`, `EmotionalState` lub `VisualLatentProfile` rzuca `TypeError`.
- Błąd zapisu pliku propaguje standardowy `OSError` bez tłumienia i bez częściowego milczącego fallbacku (najpierw `summary.md`, potem `profile.json`).
- Brak cichej podmiany danych: brakujące pola opcjonalne są pomijane w treści, nie podszywane pod wartości zastępcze.

## Acceptance criteria

1. `explain` zwraca `ExplanationArtifacts`, którego `summary_md` zawiera wszystkie wymagane sekcje: nagłówek, repository overview, emotional state, visual latent profile, why-this-look.
2. Identyczne dane wejściowe dają bajt w bajt identyczne `summary_md` i `profile_json`; zmiana wyłącznie `calculated_at`, `source_commit` lub `engine_version` nie zmienia `summary_md` ani `why_this_look`.
3. `why_this_look` zaczyna się od pytania „Why does this portrait look ...?" zawierającego dosłowne nazwy wyróżnionych cech i zawiera punkty odnoszące się do realnych wartości scores z kwalifikatorami zgodnymi z progami.
4. `profile_json` parsuje się z powrotem do trzech modeli (RepositoryFeatures, EmotionalState, VisualLatentProfile) z zachowaniem wartości.
5. Przy `output_dir` powstają pliki `summary.md` i `profile.json` o treści tożsamej z polami wyniku; katalogi są tworzone wraz z rodzicami.
6. Kwalifikatory, wybór top osi i top sensors są zgodne z regułami biznesowymi dla profili granicznych (0.0/0.5/1.0) w testach.
7. Wszystkie testy z Faz 0-5 nadal przechodzą pomyślnie.

## Required tests

- `tests/test_explain.py`:
  - treść i kompletność sekcji `summary_md`; pomijanie sekcji opcjonalnych przy braku `repository_name`/`dominant_features`;
  - determinizm tekstów i stabilność wobec pól ulotnych;
  - poprawność wyboru top osi, atrybucji scores i top JEV sensors na profilach granicznych;
  - roundtrip `profile_json` do trzech modeli;
  - zapis `summary.md` i `profile.json` (tworzenie katalogów, treść plików, ścieżki w wyniku);
  - `TypeError` dla złych typów i propagacja `OSError` zapisu.

## Relevant SDD / ADR

- `docs/product/emotional-repository-portrait-system.md`
- `docs/features/prompt-to-image/spec.md` (wzorzec fasady, artefaktów i kwalifikatorów)
- `docs/features/live-renderers/spec.md` (wzorzec zapisu artefaktów)
