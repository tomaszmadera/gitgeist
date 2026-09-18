# Model stanu emocjonalnego i bank sensorów JEV

Path: `docs/features/emotional-state-model/spec.md`

## Goal

Zbudować deterministyczny moduł przekształcający cechy repozytorium (`RepositoryFeatures`) w jawny profil emocjonalny i semantyczny (`EmotionalState`), stanowiący Warstwę 2 (Semantic Interpretation Layer) architektury Gitgeist.

## Related requirements

- `docs/product/emotional-repository-portrait-system.md#L336-L408` (Sekcja 8.2 i 9)
- `docs/product/emotional-repository-portrait-system.md#L690-L709` (Sekcja 14.3)
- `docs/product/emotional-repository-portrait-system.md#L954-L1011` (Sekcja 18)
- `docs/product/emotional-repository-portrait-system.md#L1390-L1393` (Faza 2 planu budowy)

## Scope

1. Modele Pydantic v2 dla stanu emocjonalnego:
   - `EmotionalScores`: ciągłe wskaźniki w przedziale [0.0, 1.0] (`coherence`, `maturity`, `volatility`, `fragility`, `novelty`, `discipline`, `tension`, `chaos`, `identity_strength`, `internal_conflict`).
   - `EmotionalNouls`: binarne kwalifikatory semantyczne (`appears_experimental`, `feels_stable`, `feels_overloaded`, `feels_under_control`, `feels_fragmented`, `feels_unfinished`, `feels_resilient`).
   - `EmotionalChoices`: kategoryczne profile rozkładów i dominujące cechy:
     - `temperament`: rozkład wag i wiodący temperament (`calm`, `restless`, `disciplined`, `playful`, `brooding`, `proud`, `anxious`, `mysterious`).
     - `visual_tone`: rozkład wag i wiodący ton wizualny (`luminous`, `austere`, `dense`, `delicate`, `monumental`, `fractured`, `flowing`).
     - `energy_profile`: rozkład wag i wiodący profil energii (`static`, `pulsing`, `coiled`, `diffused`, `turbulent`, `focused`).
   - `EmotionalState`: główny niemutowalny model agregujący scores, nouls, choices oraz metadane (czas oceny, hash wejściowy).
2. Deterministyczne sensory metryk emocjonalnych (`src/gitgeist/sensors/`):
   - Kalkulatory metryk mapujące cechy `RepositoryFeatures` (statyczne, historia Git, podsumowanie dokumentacji) na znormalizowane wskaźniki emocjonalne.
   - Deterministyczne wyznaczanie dominujących wyborów i rozkładów prawdopodobieństw.
3. Fasada analityczna:
   - `evaluate_emotional_state(features: RepositoryFeatures) -> EmotionalState`.
4. Poprawka asercji wersji semver pre-release w `tests/test_version.py`.
5. Zestaw testów jednostkowych i integracyjnych dla sensorów, modeli oraz determinizmu.

## Non-goals

- Generowanie obrazów ani promptów (Faza 4 i Faza 5).
- Mapowanie stanu emocjonalnego na wektory wizualne latentne (Faza 3: Visual Latent Mapper).
- Integracja z zewnętrznymi API LLM (MVP bazuje na regułowym banku sensorów JEV; podłączenie silniejszego modelu językowego jako opcjonalnego rozszerzenia nastąpi po ukończeniu MVP).

## Behaviour

- Funkcja `evaluate_emotional_state` przyjmuje zwalidowany obiekt `RepositoryFeatures` i zwraca niemutowalny obiekt `EmotionalState`.
- Identyczne dane wejściowe gwarantują identyczny stan emocjonalny (100% determinizmu, brak losowości bez podania jawnego seeda).
- Wszystkie wartości ciągłe `scores` są clampowane do przedziału [0.0, 1.0].
- Wagi w `choices` są znormalizowane i sumują się do 1.0 (z tolerancją numeryczną 1e-6).
- Pole `dominant` w każdym choice odpowiada kategorii o najwyższej wadze (z deterministycznym rozstrzyganiem remisów alfabetycznie).

## Business rules

- `coherence`: rośnie wraz z modularnością kodu i obecnością dokumentacji architektonicznej; maleje przy wysokiej fragmentacji katalogów i rozproszeniu plików.
- `maturity`: rośnie z wiekiem repozytorium, liczbą commitów, obecnością tagów semver, licencji i testów.
- `volatility`: rośnie przy wysokim churn kodu i częstych zmianach w krótkim okresie.
- `fragility`: rośnie przy obecności hotspotów w newralgicznych plikach o niskim pokryciu testowym i wielu autorach.
- `novelty`: rośnie, gdy repozytorium jest świeże i ma duży odsetek niedawno dodanych plików.
- `discipline`: rośnie przy obecności plików konfiguracyjnych narzędzi (CI, lintery, pyproject.toml), ustrukturyzowanych katalogów i konwencjonalnych commitów.
- `tension`: rośnie przy wysokim churn w plikach hotspotów oraz asymetrii wkładu.
- `chaos`: rośnie przy braku struktury (pliki w korzeniu), braku testów i wysokiej entropii rozszerzeń plików.
- `identity_strength`: rośnie przy obecności spójnego README, opisu i zdefiniowanych zależności.
- `internal_conflict`: rośnie przy mieszaniu przeciwstawnych sygnałów (np. wysoki churn w repozytorium bez testów, wielojęzykowość bez dominującej technologii).

## Authorization

none

## Data / API

- Wejście: `RepositoryFeatures` (`gitgeist.schemas.features`).
- Wyjście: `EmotionalState` (`gitgeist.schemas.emotional`).
- Główna fasada: `evaluate_emotional_state(features: RepositoryFeatures) -> EmotionalState` eksportowana w głównym pakiecie `gitgeist`.

## Edge cases

- Minimalne repozytorium (1 plik, 1 commit): sensory obliczają spójny stan bazowy bez błędów `ZeroDivisionError`.
- Brak historii Git (`commits_count == 0`): sensory opierają się wyłącznie na cechach statycznych, stosując bezpieczne wartości neutralne dla historii.
- Skrajny churn lub anomalne wartości metryk: automatyczny clamping do przedziału [0.0, 1.0].

## Errors

- Przekazanie niepoprawnego typu danych wejściowych generuje `TypeError` lub `pydantic.ValidationError`.
- Błędy nie są po cichu maskowane pustymi blokami `except`.

## Acceptance criteria

1. Modele `EmotionalScores`, `EmotionalNouls`, `EmotionalChoices` i `EmotionalState` są zaimplementowane w Pydantic v2 z `frozen=True`.
2. Wszystkie wskaźniki w `scores` należą do przedziału [0.0, 1.0].
3. Wszystkie rozkłady wag w `choices` sumują się do 1.0.
4. Funkcja `evaluate_emotional_state` jest czysta i w pełni deterministyczna.
5. Poprawiono asercję w `tests/test_version.py` dla wersji z oznaczeniem pre-release.
6. Nowe testy weryfikują determinizm, przypadki brzegowe i poprawność kalkulacji na fixtures syntetycznych.
7. Wszystkie testy w projekcie kończą się kodem wyjścia 0.

## Required tests

- `tests/test_emotional_schemas.py`: walidacja modeli Pydantic, serializacja i deserializacja JSON, niezmienniczość `frozen`.
- `tests/test_sensors.py`: testy jednostkowe poszczególnych sensorów metryk emocjonalnych.
- `tests/test_emotional_model.py`: testy integracyjne fasady `evaluate_emotional_state`, determinizm, zachowanie dla fixtures minimalnych i chaotycznych.
- `tests/test_version.py`: weryfikacja poprawności formatu wersji z uwzględnieniem tagów pre-release.

## Relevant SDD / ADR

- `docs/product/emotional-repository-portrait-system.md`
