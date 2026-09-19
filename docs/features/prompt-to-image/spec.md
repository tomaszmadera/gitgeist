# Prompt-to-Image: prompt composer, image backend i artefakty

Path: `docs/features/prompt-to-image/spec.md`

## Goal

Zbudować Fazę 5 architektury Gitgeist: tryb generowania `prompt_to_image_gen_llm`. System składa deterministyczny prompt tekstowy z emocjonalnego stanu repozytorium (`EmotionalState`) i profilu wizualnego (`VisualLatentProfile`), przekazuje go do konfigurowalnego backendu generowania obrazów i zapisuje artefakty (`prompt.txt`, `portrait.png`). Celem jest uzyskanie jednego końcowego obrazu portretu w trybie reprezentacji `character` lub `abstract`, wiernie wynikającego z profilu, bez ręcznych stereotypów.

## Related requirements

- `docs/product/emotional-repository-portrait-system.md#L1140-L1167` (Sekcja 14.6: MVP prompt-to-image mode: pipeline i wynik)
- `docs/product/emotional-repository-portrait-system.md#L1045-L1091` (Sekcja 20: Prompt composer: struktura promptu)
- `docs/product/emotional-repository-portrait-system.md#L1159-L1162` (Sekcja 23: artefakty trybu prompt: `prompt.txt`, `portrait.png`, opcjonalny `critique.json`)
- `docs/product/emotional-repository-portrait-system.md#L1198-L1200` (Sekcja 24: Image generation: backend konfigurowalny)
- `docs/product/emotional-repository-portrait-system.md#L1403-L1407` (Faza 5: Prompt mode: prompt composer, image backend, artifacts)
- `docs/product/emotional-repository-portrait-system.md#L1264-L1271` (Sekcja 28.1: Visual cliché trap: zakaz dosłownych stereotypów w prompt composer)

## Scope

1. Kompozytor promptu (`src/gitgeist/render/prompt_composer.py`):
   - Funkcja `compose_prompt(emotional_state: EmotionalState, profile: VisualLatentProfile, mode: Literal["abstract", "character"] = "abstract", repository_name: str | None = None) -> str`.
   - Prompt zawiera bloki zgodne z sekcją 20 dokumentu produktowego: blok tożsamości semantycznej, blok stanu emocjonalnego (nazwane osie z kwalifikatorami niski/średni/wysoki), blok profilu latentnego (osie + dominująca materiałowość), wybrany tryb reprezentacji, ograniczenia spójności oraz ograniczenia negatywne (zakaz dosłownych symboli programistycznych i memicznych personifikacji).
2. Backend generowania obrazu (`src/gitgeist/render/image_backend.py`):
   - Interfejs `ImageGenerationBackend` (ABC) z metodą `generate_image(prompt: str) -> bytes` zwracającą bajty obrazu PNG.
   - Implementacja `OpenRouterImageBackend`: wywołanie OpenRouter Image API (parametry `api_url`, `api_key`, `model`, `timeout`), zbudowane na `urllib.request` ze standardowej biblioteki, bez nowych zależności.
   - Implementacja `FakeImageBackend`: deterministyczny, offline generator PNG na potrzeby testów i pracy bez sieci.
3. Fasada trybu prompt (`src/gitgeist/render/facade.py`):
   - Funkcja `render_prompt(emotional_state: EmotionalState, profile: VisualLatentProfile, mode: Literal["abstract", "character"] = "abstract", repository_name: str | None = None, backend: ImageGenerationBackend | None = None, output_dir: Path | str | None = None) -> PromptRenderArtifacts`.
   - Klasa wynikowa `PromptRenderArtifacts`: `prompt_text: str`, `image_bytes: bytes | None`, `prompt_path: Path | None`, `image_path: Path | None`.
   - Domyślnie (`backend=None`) używa `FakeImageBackend`; wywołanie z `OpenRouterImageBackend` pozostaje jawną decyzją wywołującego.
   - Zapis artefaktów: `prompt.txt` oraz `portrait.png` w `output_dir` (nazwy wg sekcji 23 dokumentu produktowego, kanoniczne względem nazw z sekcji 14.7).
4. Re-eksport publicznego API (`gitgeist.render.compose_prompt`, `gitgeist.render.render_prompt`, `gitgeist.render.ImageGenerationBackend`, modele wynikowe) w pakiecie `gitgeist`.
5. Zestaw testów jednostkowych i integracyjnych pokrywających kompozycję promptu, budowę żądania HTTP, obsługę błędów backendu, determinizm i zapis artefaktów.

## Non-goals

- Pętla krytyki (`critique.json`) i consistency prompting z obrazem referencyjnym (Post-MVP, sekcje 26.7 i 16.2).
- Style packs (Post-MVP, sekcja 16.7); MVP stosuje stały, neutralny styl opisowy.
- Interfejs CLI (sekcja 22 dokumentu produktowego pozostaje poza Fazą 5).
- Multiple fine-tuning, maski, edycja obrazu (inpainting) i generacja wielu wariantów.
- Wbudowywanie kluczy API w kod lub repozytorium.

## Behaviour

- `compose_prompt` zwraca końcowy tekst promptu wyłącznie z danych wejściowych; identyczne `EmotionalState`, `VisualLatentProfile`, tryb i nazwa repo dają identyczny tekst promptu.
- Treść promptu nie zawiera znaczników czasu (`calculated_at`), nazw plików ani ścieżek lokalnych.
- Oś ciągła otrzymuje kwalifikator tekstowy: `<= 0.33` niski, `<= 0.66` średni, powyżej wysoki; progi są włączne dla dolnych granic przedziałów.
- `render_prompt` komponuje prompt, wywołuje `backend.generate_image(prompt)` i zwraca `PromptRenderArtifacts`; przy `output_dir` zapisuje `prompt.txt` oraz `portrait.png` (UTF-8 i bajty PNG odpowiednio), tworząc katalog wraz z rodzicami w razie potrzeby.
- Prompt wprost wymusza tryb reprezentacji: `character` opisuje emergentny byt, `abstract` opisuje kompozycję abstrakcyjną; oba blokują dosłowne stereotypy („robot”, „maskotka”, symbole programisty).
- Żądanie HTTP do backendu używa nagłówka `Authorization: Bearer <api_key>`, treści JSON i endpointu `api_url` (domyślnie `https://openrouter.ai/api/v1/images`); odpowiedź musi zawierać dane obrazu (pole `b64_json` lub URL pobierany dodatkowym żądaniem GET).

## Business rules

- Kwalifikatory osi (niski/średni/wysoki) wynikają wyłącznie z wartości liczbowych pól `EmotionalScores` i `VisualLatentAxes`, bez twardych mapowań typu „wysoka kruchość = pęknięte szkło”.
- Dominująca materiałowość (`materiality.dominant`) jest opisywana słownie w bloku profilu latentnego; wagi pozostałych materiałów nie trafiają do promptu.
- Wybory dominant (`temperament`, `visual_tone`, `energy_profile` z `EmotionalChoices`) są opisywane słownie jako charakterystyka nastroju i tonu wizualnego.
- `FakeImageBackend` zwraca poprawny plik PNG deterministycznie zależny wyłącznie od treści promptu (ten sam prompt: te same bajty).
- `OpenRouterImageBackend` nie loguje klucza API i nie zapisuje go w artefaktach.

## Authorization

Dostęp do backendu obrazowego kontroluje posiadacz klucza API przekazanego do `OpenRouterImageBackend` (domyślne źródło: zmienna środowiskowa `OPENROUTER_IMAGE_API_KEY`). Brak klucza przy próbie wywołania jest błędem konfiguracji, nie fallbackiem.

## Data / API

- Wejście:
  - `emotional_state`: `EmotionalState` (wymagane)
  - `profile`: `VisualLatentProfile` (wymagane)
  - `mode`: `Literal["abstract", "character"] = "abstract"`
  - `repository_name`: `str | None = None`
  - `backend`: `ImageGenerationBackend | None = None` (domyślnie `FakeImageBackend`)
  - `output_dir`: `Path | str | None = None`
- Wyjście:
  - `PromptRenderArtifacts`:
    - `prompt_text`: `str`
    - `image_bytes`: `bytes | None`
    - `prompt_path`: `Path | None` (jeśli zapisano)
    - `image_path`: `Path | None` (jeśli zapisano)
- Konfiguracja `OpenRouterImageBackend`:
  - `api_url: str | None = None` (domyślnie ze zmiennej `OPENROUTER_IMAGE_API_URL`, potem `https://openrouter.ai/api/v1/images`)
  - `api_key: str | None = None` (domyślnie ze zmiennej `OPENROUTER_IMAGE_API_KEY`)
  - `model: str | None = None` (domyślnie pierwszy wpis rozdzielanej przecinkami zmiennej `OPENROUTER_IMAGE_MODELS`, potem `google/gemini-3.1-flash-lite-image`)
  - `timeout: float = 120.0`
- Publiczne modele i funkcje:
  - `gitgeist.render.compose_prompt`
  - `gitgeist.render.render_prompt`
  - `gitgeist.render.ImageGenerationBackend`
  - `gitgeist.render.OpenRouterImageBackend`
  - `gitgeist.render.FakeImageBackend`
  - `gitgeist.render.PromptRenderArtifacts`

## Edge cases

- Ekstremalne wartości osi (wszystkie 0.0 lub 1.0): prompt powstaje bez błędów i bez wartości NaN.
- Pusta lista `dominant_features` i brak `repository_name`: bloki opcjonalne są pomijane, prompt pozostaje kompletny.
- Backend zwraca odpowiedź bez danych obrazu lub z nieobsługiwanym formatem: rzuca wyjątek, nie zapisuje `portrait.png`, ale `prompt.txt` pozostaje zapisywalny przy kolejnej próbie.
- Długi prompt (wiele cech): treść pozostaje w granicach rozsądnej długości (kompozycja blokowa, bez duplikacji).

## Errors

- Przekazanie obiektu innego niż `EmotionalState` lub `VisualLatentProfile` rzuca `TypeError`.
- Nieznany tryb reprezentacji rzuca `ValueError`.
- Wywołanie `OpenRouterImageBackend.generate_image` bez klucza API rzuca `ValueError` (brak cichego fallbacku).
- Błędy HTTP (`HTTPError`, `URLError`, `TimeoutError`) propagują się z `urllib` bez tłumienia; treść błędu nie zawiera klucza API.
- Błąd zapisu pliku rzuca standardowy `OSError`.

## Acceptance criteria

1. `compose_prompt` zwraca prompt zawierający bloki: tożsamość semantyczna, stan emocjonalny, profil latentny, tryb reprezentacji, ograniczenia spójności i negatywne; dla `mode="character"` i `mode="abstract"` treść opisu formy jest różna.
2. Identyczne dane wejściowe dają bajt w bajt identyczny prompt; zmiana dowolnej osi zmienia treść promptu.
3. `FakeImageBackend` zwraca deterministyczne, poprawne bajty PNG (ten sam prompt: te same bajty; różne prompty: różne bajty).
4. `OpenRouterImageBackend` buduje poprawne żądanie (URL, metoda, nagłówki z `Bearer`, treść JSON) bez wykonywania prawdziwego połączenia sieciowego w testach.
5. `render_prompt` zapisuje `prompt.txt` i `portrait.png` w podanym `output_dir`, tworząc katalogi, i zwraca kompletne `PromptRenderArtifacts` z ustawionymi ścieżkami.
6. Wszystkie testy z Faz 1-4 nadal przechodzą pomyślnie.
7. Nowe testy pokrywają kompozycję promptu, determinizm, budowę żądania HTTP, obsługę błędów backendu i zapis artefaktów.

## Required tests

- `tests/test_prompt_composer.py`: kompozycja bloków promptu, determinizm, kwalifikatory osi, różnice między trybami, brak znaczników czasu, zakaz stereotypów w treści.
- `tests/test_image_backend.py`: kontrakt `FakeImageBackend`, budowa żądania `OpenRouterImageBackend` (URL, nagłówki, JSON) na fasadzie `urllib`, brak klucza rzuca `ValueError`, obsługa odpowiedzi `b64_json` i błędów HTTP bez połączenia sieciowego.
- `tests/test_prompt_render.py`: fasada `render_prompt`, zapis i treść artefaktów, tworzenie katalogów, przepływ błędów typów i trybów.

## Relevant SDD / ADR

- `docs/product/emotional-repository-portrait-system.md`
- `docs/features/live-renderers/spec.md` (wzorzec fasady i zapisu artefaktów)
