# Visual Latent Profile i Mapper

Path: `docs/features/visual-latent-mapper/spec.md`

## Goal

Zbudować deterministyczny moduł tłumaczący wielowymiarowy profil stanu emocjonalnego (`EmotionalState`) na uniwersalne parametry profilu wizualnego (`VisualLatentProfile`). Moduł stanowi Warstwę 3 (Visual Latent Mapper) architektury Gitgeist, pośredniczącą między interpretacją semantyczną a silnikami renderującymi portret (tryb character i abstract).

## Related requirements

- `docs/product/emotional-repository-portrait-system.md#L414-L472` (Sekcja 10: Visual Latent Profile)
- `docs/product/emotional-repository-portrait-system.md#L474-L541` (Sekcja 11: Dwa tryby reprezentacji)
- `docs/product/emotional-repository-portrait-system.md#L1013-L1043` (Sekcja 19: Visual Latent Mapper)
- `docs/product/emotional-repository-portrait-system.md#L1063-L1090` (Sekcja 20: Struktura profilu latentnego w prompt composerze)
- `docs/product/emotional-repository-portrait-system.md#L1394-L1397` (Faza 3 planu budowy)

## Scope

1. Schematy danych Pydantic v2 dla parametrów latentnych (`src/gitgeist/schemas/visual_latent.py`):
   - `VisualLatentAxes`: ciągłe znormalizowane osie wizualne w przedziale [0.0, 1.0]:
     - `form_complexity`: złożoność formy (prosta/minimalistyczna vs złożona/wieloczłonowa).
     - `symmetry`: stopień symetrii (asymetryczna/dynamiczna vs osiowo/promieniście symetryczna).
     - `fragmentation`: stopień fragmentacji (zwarta/monolityczna vs rozproszona/cząstkowa).
     - `tension_curvature`: dynamika krzywizn i linii (miękka/spokojna vs ostra/napięta/łamana).
     - `texture_density`: gęstość faktury/tekstury (gładka/jednolita vs ziarnista/chropowata/gęsta).
     - `luminosity`: jasność i emisyjność (ciemna/mroczna vs jasna/świetlista).
     - `contrast`: kontrast tonalny (stonowany/zamglony vs wysoki/dramatyczny).
     - `sharpness`: ostrość krawędzi (rozmyta/mglista vs ostra/wyrazista).
     - `visual_rhythm`: regularność rytmu (nieregularny/turbulentny vs miarowy/uporządkowany).
     - `compositional_balance`: równowaga kompozycji (chwiejna/niestabilna vs stabilna/wyważona).
     - `biological_vs_mechanical`: tendencja materiałowa (organiczna/biologiczna vs mechaniczna/architektoniczna).
     - `ornamental_load`: nasycenie ornamentem (surowa/funkcjonalna vs bogato zdobiona).
     - `opacity`: krycie i transparentność (eteryczna/prześwitująca vs solidna/nieprzenikniona).
     - `layering`: głębia i warstwowość (płaska/jednowarstwowa vs wieloplanowa/głęboka).
   - `MaterialityDistribution`: rozkład wag podstawowych typów materiału (`organic`, `mechanical`, `crystalline`, `ethereal`) wraz z dominantem.
   - `VisualLatentProfile`: nadrzędny niemutowalny model zawierający:
     - `axes`: `VisualLatentAxes`
     - `materiality`: `MaterialityDistribution`
     - `dominant_features`: lista kluczowych dominantów wizualnych (np. top 3 najbardziej wyraziste odchylenia od średniej 0.5)
     - `calculated_at`: znacznik czasu kalkulacji (domyślnie dziedziczony z `EmotionalState.calculated_at`)
     - `source_commit`: opcjonalny identyfikator commita
     - `engine_version`: wersja silnika
2. Deterministyczny ważony mapper latentny (Hand-designed weighted mapper MVP w `src/gitgeist/mapping/`):
   - Macierz wag łącząca wskaźniki emocjonalne (`scores`), flagi kwalifikujące (`nouls`) oraz rozkłady temperamentu/tonu/energii (`choices`) z osiami wizualnymi.
   - Deterministyczne nieliniowości i clampowanie do [0.0, 1.0].
   - Wpływ dominujących wyborów `visual_tone`, `energy_profile` oraz `temperament` jako modyfikatorów profilu.
3. Fasada mapowania:
   - `map_emotional_to_latent(state: EmotionalState) -> VisualLatentProfile` eksportowana w `gitgeist`.
4. Testy automatyczne:
   - Testy walidacji schematów Pydantic (granice [0.0, 1.0], frozen, niezmienniki rozkładu).
   - Testy determinizmu mapowania i monotoniczności kluczowych relacji (np. wzrost `chaos` zwiększa `fragmentation`).
   - Testy integracyjne z modelami z Fazy 1 i Fazy 2.

## Non-goals

- Renderowanie portretu w SVG/Canvas ani shadery (Faza 4: Live renderers).
- Kompozytor promptów dla generatorów obrazów AI (Faza 5: Prompt composer).
- Uczenie maszynowe / trenowanie modeli sieci neuronowych (Learned mapper - zakres post-MVP).
- Dowolna niedeterministyczna losowość bez jawnego parametru seed.

## Behaviour

- Funkcja `map_emotional_to_latent` przyjmuje obiekt `EmotionalState` i zwraca zwalidowany, niemutowalny obiekt `VisualLatentProfile`.
- Czysty determinizm: identyczny `EmotionalState` generuje bitowo identyczny `VisualLatentProfile`.
- Brak stereotypowych uproszczeń regułowych (np. brak reguł typu "jeśli legacy to potwór"). Mapowanie operuje na fundamentalnych parametrach wizualnych (forma, światło, rytm, kontrast, materiał).
- Wszystkie osie `VisualLatentAxes` są ściśle ograniczone do zakresu [0.0, 1.0].
- Rozkład materiałowości sumuje się do 1.0 w tolerancji 1e-4 z deterministycznym wyznaczaniem dominantu.

## Business rules

- `form_complexity`: dodatnio skorelowana z `scores.novelty`, `scores.internal_conflict`, `nouls.appears_experimental`; ujemnie z `nouls.feels_under_control`.
- `symmetry`: dodatnio skorelowana z `scores.discipline`, `scores.coherence`, `nouls.feels_under_control`; silnie ujemnie z `scores.chaos`.
- `fragmentation`: rośnie wraz ze `scores.chaos`, `scores.fragility`, `nouls.feels_fragmented`, `nouls.feels_overloaded`; maleje przy wysokim `scores.coherence`.
- `tension_curvature`: rośnie wraz ze `scores.tension`, `scores.internal_conflict`, `scores.volatility`.
- `texture_density`: rośnie przy wysokim `scores.tension`, `choices.visual_tone` (dense) oraz `choices.energy_profile` (turbulent).
- `luminosity`: rośnie przy tonie `visual_tone` (luminous), `scores.novelty`, `nouls.feels_resilient`; maleje przy `visual_tone` (austere).
- `contrast`: rośnie przy wysokim `scores.identity_strength`, `scores.tension`, `choices.energy_profile` (coiled, turbulent).
- `sharpness`: rośnie przy `scores.discipline`, `scores.maturity`, `visual_tone` (austere); maleje przy `energy_profile` (diffused).
- `visual_rhythm`: rośnie wraz ze `scores.discipline`, `scores.coherence`, `energy_profile` (focused); drastycznie maleje przy `scores.chaos`.
- `compositional_balance`: rośnie przy `scores.coherence`, `scores.maturity`, `nouls.feels_stable`; maleje przy `scores.volatility`.
- `biological_vs_mechanical`: mechaniczna tendencja (zbliżona do 1.0) przy wysokiej dyscyplinie, dojrzałości i architekturze; biologiczna (zbliżona do 0.0) przy wysokiej eksperymentalności, nowości i zabawie.
- `ornamental_load`: rośnie przy `temperament` (playful), wysokim `scores.novelty`; maleje przy surowej dyscyplinie (`scores.discipline`).
- `opacity`: rośnie wraz z `scores.maturity`, `scores.identity_strength`; maleje przy wysokim `scores.fragility`, `visual_tone` (delicate).
- `layering`: rośnie wraz ze `scores.maturity`, `scores.coherence`, `visual_tone` (dense, monumental).

## Authorization

none

## Data / API

- Wejście: `EmotionalState` z pakietu `gitgeist.schemas.emotional`.
- Wyjście: `VisualLatentProfile` z pakietu `gitgeist.schemas.visual_latent`.
- Publiczne API:
  - `gitgeist.schemas.visual_latent.VisualLatentAxes`
  - `gitgeist.schemas.visual_latent.MaterialityDistribution`
  - `gitgeist.schemas.visual_latent.VisualLatentProfile`
  - `gitgeist.map_emotional_to_latent(state: EmotionalState) -> VisualLatentProfile`

## Edge cases

- Minimalne repozytorium (puste lub niemal puste z zerowymi/minimalnymi wskaźnikami): mapper musi wygenerować stabilny profil bez dzielenia przez zero i wartości NaN.
- Wartości skrajne (wszystkie metryki 0.0 lub wszystkie 1.0): zachowanie stabilności numerycznej, brak przekroczeń przedziału [0.0, 1.0].
- Wyrównane wagi w rozkładzie materiału: deterministyczny wybór dominantu z alfabetycznym rozstrzyganiem remisów.

## Errors

- Przekazanie obiektu innego niż `EmotionalState` rzuca `TypeError`.
- Naruszenie przedziału [0.0, 1.0] lub niepoprawna suma wag w modelach Pydantic rzuca `ValidationError`.
- Brak cichych fallbacków ukrywających niepoprawne dane.

## Acceptance criteria

1. Modele `VisualLatentAxes`, `MaterialityDistribution` i `VisualLatentProfile` są zdefiniowane w Pydantic v2 z `frozen=True`.
2. Każda oś w `VisualLatentAxes` jest walidowana pod kątem przynależności do przedziału [0.0, 1.0].
3. `MaterialityDistribution` waliduje sumowanie wag do 1.0 w tolerancji 1e-4 oraz zgodność dominantu z maksymalną wagą.
4. `map_emotional_to_latent` przyjmuje `EmotionalState` i zwraca poprawny `VisualLatentProfile`.
5. Obliczenia są w 100% deterministyczne: identyczne wejście daje identyczne wyjście.
6. Zmiana parametrów wejściowych wywołuje przewidywalne zmiany w parametrach wizualnych (zgodnie z business rules).
7. Istniejące 42 testy z Fazy 1 i 2 nadal przechodzą bez regresji.
8. Nowy zestaw testów pokrywa schematy, mechanizm wag, normalizację, przypadki brzegowe i integralność fasady.

## Required tests

- `tests/test_visual_latent_schemas.py`: testy walidacji parametrów osi, niezmienników rozkładu wag, niemutowalności i serializacji.
- `tests/test_latent_mapper.py`: testy funkcji `map_emotional_to_latent`, determinizmu, wpływu dominujących tonów/energii/temperamentów oraz odporności na przypadki skrajne.

## Relevant SDD / ADR

- `docs/product/emotional-repository-portrait-system.md`
