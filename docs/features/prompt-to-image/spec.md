# Prompt-to-Image: prompt composer, image backend i artefakty

Aktualizacja etapu 6 (0.12.0): publiczne API poniżej przyjmuje `VisualSpec`, a fasada wymaga nazwanego argumentu `features`. Szczegółowe szablony kompozytora v2, paleta, seed i pasek podpisu są w [`docs/features/prompt-composer-v2/spec.md`](../prompt-composer-v2/spec.md). Ten plik opisuje zgodne z nimi sygnatury, backendy, wykrywanie typu mediów, błędy OpenRouter, `image_format` i nazwy artefaktów; nie zachowuje starego API pozycyjnego.

Path: `docs/features/prompt-to-image/spec.md`

## Goal

Zbudować Fazę 5 architektury Gitgeist: tryb generowania `prompt_to_image_gen_llm`. System składa deterministyczny prompt tekstowy z wizualnej specyfikacji repozytorium (`VisualSpec`), przekazuje go do konfigurowalnego backendu generowania obrazów i zapisuje artefakty (`prompt.txt`, portret o ekstensji zgodnej z rzeczywistym formatem bajtów: `portrait.png`, `portrait.jpg` lub `portrait.webp`). Celem jest uzyskanie jednego końcowego obrazu portretu w trybie reprezentacji `character` lub `abstract`, wiernie wynikającego z profilu, bez ręcznych stereotypów.

Uzupełnienie kontraktu (2026-09-19, zadanie `portrait-media-types`): backendy OpenRouter zwracają różne formaty; zmierzono 13 modeli: 8 PNG, 3 JPEG, 1 WebP, 2 błędy API. Artefakt portretu musi mieć ekstensję i zarejestrowany typ mediów zgodne z wykrytą zawartością (sniffing magii bajtów), nie z obietnicą API. Normalizacja do PNG jest dostępna jako opt-in przez Pillow.

## Related requirements

- `docs/product/emotional-repository-portrait-system.md#L1140-L1167` (Sekcja 14.6: MVP prompt-to-image mode: pipeline i wynik)
- `docs/product/emotional-repository-portrait-system.md#L1045-L1091` (Sekcja 20: Prompt composer: struktura promptu)
- `docs/product/emotional-repository-portrait-system.md#L1159-L1162` (Sekcja 23: artefakty trybu prompt: `prompt.txt`, `portrait.png`, opcjonalny `critique.json`)
- `docs/product/emotional-repository-portrait-system.md#L1198-L1200` (Sekcja 24: Image generation: backend konfigurowalny)
- `docs/product/emotional-repository-portrait-system.md#L1403-L1407` (Faza 5: Prompt mode: prompt composer, image backend, artifacts)
- `docs/product/emotional-repository-portrait-system.md#L1264-L1271` (Sekcja 28.1: Visual cliché trap: zakaz dosłownych stereotypów w prompt composer)

## Scope

1. Kompozytor promptu (`src/gitgeist/render/prompt_composer.py`):
   - Funkcja `compose_prompt(spec: VisualSpec, *, include_name: bool = False, repository_name: str | None = None) -> str`.
   - Prompt zawiera zdanie tematu, 5–7 wybranych dyrektyw opisujących fakty z `VisualSpec`, paletę hex, medium wybrane z seed oraz ograniczenia negatywne. Nazwa repozytorium jest domyślnie wyłączona; `include_name=True` wymaga niepustego `repository_name`. Układ i selekcję określa specyfikacja kompozytora v2.
2. Backend generowania obrazu (`src/gitgeist/render/image_backend.py`):
   - Interfejs `ImageGenerationBackend` (ABC) z metodą `generate_image(prompt: str, *, spec: VisualSpec | None = None, seed: int | None = None) -> GeneratedImage`, gdzie `GeneratedImage` jest zamrożonym modelem pydantic z polami `image_bytes: bytes` oraz `media_type: Literal["png", "jpeg", "webp"]` wykrytym z magii bajtów, nie z metadanych serwera.
   - Implementacja `OpenRouterImageBackend`: wywołanie OpenRouter Image API (parametry `api_url`, `api_key`, `model`, `timeout`), zbudowane na `urllib.request` ze standardowej biblioteki; bajty z `b64_json` lub URL są poddawane detekcji typu przed zwróceniem.
   - Implementacja `FakeImageBackend`: deterministyczny, offline raster 64×64 RGB rysowany z wymaganego `VisualSpec`; prompt i seed nie zmieniają pikseli. Brak poprawnego `spec` rzuca `ValueError`; wynik ma `media_type="png"`.
   - Detekcja formatu: PNG przy nagłówku `\x89PNG\r\n\x1a\n`; JPEG przy `\xff\xd8\xff`; WebP przy `RIFF` na pozycji 0 i `WEBP` na pozycji 8; każda inna zawartość rzuca `ValueError`.
3. Fasada trybu prompt (`src/gitgeist/render/facade.py`):
   - Funkcja `render_prompt(spec: VisualSpec, *, features: RepositoryFeatures, repository_name: str | None = None, include_name: bool = False, caption: bool = True, backend: ImageGenerationBackend | None = None, output_dir: Path | str | None = None, image_format: Literal["native", "png"] = "native") -> PromptRenderArtifacts`.
   - Klasa wynikowa `PromptRenderArtifacts`: `prompt_text: str`, `image_bytes: bytes | None`, `media_type: str | None`, `prompt_path: Path | None`, `image_path: Path | None`.
   - Domyślnie (`backend=None`) używa `FakeImageBackend`; wywołanie z `OpenRouterImageBackend` pozostaje jawną decyzją wywołującego.
   - Zapis artefaktów: `prompt.txt` oraz portret nazwany wg wykrytego typu (`portrait.png`, `portrait.jpg`, `portrait.webp`) w `output_dir`; render nie usuwa portretów o innych ekstensjach z wcześniejszych uruchomień.
   - Normalizacja: `image_format="png"` przy typie innym niż PNG przekodowuje bajty do PNG przez Pillow. `image_format="native"` zachowuje wykryty format, ale domyślne `caption=True` nadal dodaje pasek Pillow. Dopiero `caption=False` i brak normalizacji pozostawiają bajty backendu bez zmian.
4. Re-eksport publicznego API (`gitgeist.render.compose_prompt`, `gitgeist.render.render_prompt`, `gitgeist.render.ImageGenerationBackend`, modele wynikowe) w pakiecie `gitgeist`.
5. Zestaw testów jednostkowych i integracyjnych pokrywających kompozycję promptu, budowę żądania HTTP, obsługę błędów backendu, determinizm i zapis artefaktów.

## Non-goals

- Pętla krytyki (`critique.json`) i consistency prompting z obrazem referencyjnym (Post-MVP, sekcje 26.7 i 16.2).
- Style packs (Post-MVP, sekcja 16.7); MVP stosuje stały, neutralny styl opisowy.
- Interfejs CLI pozostaje poza Fazą 5; uzupełnienie z 2026-09-19 dodaje do istniejącego `render` wyłącznie flagę `--image-format` opisaną w Behaviour.
- Multiple fine-tuning, maski, edycja obrazu (inpainting) i generacja wielu wariantów.
- Wbudowywanie kluczy API w kod lub repozytorium.

## Behaviour

- `compose_prompt` zwraca końcowy tekst wyłącznie z `VisualSpec` i argumentów nazwanych; identyczne wejścia dają identyczny tekst. Reprezentację wybiera `spec.style` (`orbits` lub `creature`), nie argument `mode`.
- Treść promptu nie zawiera znaczników czasu (`calculated_at`), nazw plików ani ścieżek lokalnych.
- Dobór 5–7 dyrektyw, progi 0.33/0.66, fakty o anatomii i aktywności, paleta oraz medium wynikają z kontraktu kompozytora v2, a nie z dawnych bloków osi `EmotionalState` i `VisualLatentProfile`.
- `render_prompt` komponuje prompt, wywołuje `backend.generate_image(prompt, spec=spec, seed=spec.seeds.effective_seed & (2**53 - 1))`, wykrywa typ mediów z magii bajtów i przy `output_dir` zapisuje `prompt.txt` oraz portret o ekstensji wynikającej z typu: `png` -> `portrait.png`, `jpeg` -> `portrait.jpg`, `webp` -> `portrait.webp` (UTF-8 i bajty odpowiednio), tworząc katalog wraz z rodzicami w razie potrzeby.
- `media_type` w `PromptRenderArtifacts` jest równy typowi zapisanego portretu; ekstensja pliku jest trwałym zapisem typu na dysku. `profile.json` nie zawiera pól zależnych od renderowania (kontrakt determinizmu `analyze`, README.md:71-73).
- Przy `image_format="png"` portret o typie innym niż `png` jest przekodowywany do PNG przez Pillow przed zapisem; wynikowa ekstensja to zawsze `portrait.png`. Przy `image_format="native"` nie ma konwersji formatu; `caption=True` po sniffingu i normalizacji dodaje pasek z `conclusions(features, spec)` i może zmienić bajty obrazu. `caption=False` wyłącza ten pasek.
- Styl `creature` opisuje byt, a `orbits` kompozycję abstrakcyjną; CLI mapuje na nie odpowiednio `character` i `abstract`. Oba style zachowują ograniczenia negatywne z kontraktu v2.
- Żądanie HTTP do backendu używa nagłówka `Authorization: Bearer <api_key>`, treści JSON i endpointu `api_url` (domyślnie `https://openrouter.ai/api/v1/images`); odpowiedź musi zawierać dane obrazu (pole `b64_json` lub URL pobierany dodatkowym żądaniem GET).
- CLI: `gitgeist render --mode prompt-to-image` przyjmuje `--image-format {native,png}` (domyślnie `native`); flaga jest dozwolona wyłącznie w trybie `prompt-to-image`, jak `--backend`. Komunikat CLI wymienia faktyczną ścieżkę zapisanego portretu.

## Business rules

- Opisuje się fakty i wybrane cechy `VisualSpec`, bez symbolicznych stereotypów, nazw ścieżek ani sztucznego wymuszania unikalnych zdań. Medium i zgodne z prawdą wspólne cechy mogą się powtarzać. Stare bloki osi i dominant profilu nie są wejściem publicznego API kompozytora.
- `FakeImageBackend` zwraca poprawny PNG zależny wyłącznie od wizualnych danych `spec`; ten sam `spec` z innym promptem lub seed daje te same bajty, zawsze `media_type="png"`.
- `OpenRouterImageBackend` nie loguje klucza API i nie zapisuje go w artefaktach.
- Typ mediów wynika wyłącznie z magii bajtów odpowiedzi; pola typu MIME od serwera nie mają wpływu na detekcję ani ekstensję.
- Zależność Pillow jest opcjonalna: extra `[project.optional-dependencies] image = ["pillow>=10.0"]`. Jest wymagana przy `caption=True` oraz przy normalizacji nie-PNG do PNG. Brak Pillow przy żądanym podpisie kończy się błędem przed wywołaniem backendu i zapisem; nie ma cichego pominięcia podpisu.

## Authorization

Dostęp do backendu obrazowego kontroluje posiadacz klucza API przekazanego do `OpenRouterImageBackend` (domyślne źródło: zmienna środowiskowa `OPENROUTER_IMAGE_API_KEY`). Brak klucza przy próbie wywołania jest błędem konfiguracji, nie fallbackiem.

## Data / API

- Wejście:
  - `spec`: `VisualSpec` (wymagane; jedyny argument pozycyjny obu funkcji)
  - `features`: `RepositoryFeatures` (wymagany argument nazwany fasady; źródło wniosków podpisu)
  - `include_name`: `bool = False`
  - `caption`: `bool = True` (fasada)
  - `repository_name`: `str | None = None`
  - `backend`: `ImageGenerationBackend | None = None` (domyślnie `FakeImageBackend`)
  - `output_dir`: `Path | str | None = None`
  - `image_format`: `Literal["native", "png"] = "native"`
- Wyjście:
  - `PromptRenderArtifacts`:
    - `prompt_text`: `str`
    - `image_bytes`: `bytes | None`
    - `media_type`: `str | None` (`"png"`, `"jpeg"` lub `"webp"` po detekcji; po normalizacji zawsze `"png"`)
    - `prompt_path`: `Path | None` (jeśli zapisano)
    - `image_path`: `Path | None` (jeśli zapisano; ekstensja zgodna z `media_type`)
  - `GeneratedImage` (wynik backendu):
    - `image_bytes`: `bytes`
    - `media_type`: `Literal["png", "jpeg", "webp"]`
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
  - `gitgeist.render.GeneratedImage`

## Kompatybilność

- Zmiana typu zwracanego przez `ImageGenerationBackend.generate_image` z `bytes` na `GeneratedImage` jest łamiąca dla zewnętrznych implementacji ABC; projekt jest przed 1.0, zmiana wchodzi jako minor i jest odnotowana w komunikacie wydania.
- Etap 6 (0.12.0) łamie stare API: `render_prompt` przyjmuje teraz `VisualSpec` oraz wymagane nazwane `features`; `compose_prompt` przyjmuje `VisualSpec`. Dawne wywołania z parą stan/profil lub argumentem `mode` nie są zgodne i rzucają `TypeError`. Nowe wywołanie fasady: `render_prompt(spec, features=features, caption=False, backend=backend, output_dir=directory)`.
- Własne backendy muszą przyjmować nazwane `spec` i `seed`, ponieważ fasada przekazuje oba. `OpenRouterImageBackend.generate_image(prompt)` nadal działa z domyślnym `seed=None` i pomija wtedy seed w JSON; przy podanym seed przekazuje go do API. `FakeImageBackend.generate_image(prompt)` bez `spec` rzuca `ValueError`.
- `PromptRenderArtifacts.image_path` zmienia ekstensję dla backendów zwracających JPEG lub WebP; konsumenci polegający na stałej nazwie `portrait.png` powinni używać `image_format="png"` lub czytać `media_type`.

## Edge cases

- Skrajne wartości cech poprawnego `VisualSpec`: prompt pozostaje poprawny; dobór dyrektyw określa kontrakt v2.
- Pusta lista `masses`: temat opisuje brak ciał; brak nazwy przy `include_name=False` nie dodaje wiersza repozytorium. Przy `include_name=True` brak niepustej nazwy jest błędem.
- Backend zwraca odpowiedź bez danych obrazu lub o nierozpoznanym formacie: rzuca wyjątek, nie zapisuje portretu, ale `prompt.txt` pozostaje zapisywalny przy kolejnej próbie.
- Odpowiedź w formacie innym niż wybrany `image_format`: portret jest przekodowywany lub zapisany pod ekstensją typu, nigdy pod błędną ekstensją.
- Portret z poprzedniego uruchomienia w innym formacie pozostaje na dysku; render go nie usuwa i nie nadpisuje.
- Prompt zawiera 5–7 wybranych dyrektyw; dopuszczalne wspólne cechy i medium nie są automatycznym błędem różnorodności. Ocena T1/T2 pozostaje po scaleniu według decyzji właściciela z 2026-11-07 21:33 Europe/Warsaw.

## Errors

- Kompozytor i fasada wymagają `VisualSpec`; fasada dodatkowo `RepositoryFeatures` w `features`. Błędny typ rzuca `TypeError`.
- Nieznany `spec.style` lub `include_name=True` bez niepustej nazwy rzuca `ValueError`. Nie ma starego argumentu `mode`.
- `FakeImageBackend` bez poprawnego `VisualSpec` rzuca `ValueError`.
- Wywołanie `OpenRouterImageBackend.generate_image` bez klucza API rzuca `ValueError` (brak cichego fallbacku).
- Zawartość obrazu o nierozpoznanym formacie rzuca `ValueError` z jawnym komunikatem; nic nie jest zapisywane jako portret.
- Żądanie podpisu (`caption=True`) lub normalizacji nie-PNG do PNG bez Pillow rzuca `ValueError` z podpowiedzią `pip install gitgeist[image]`; brak cichego fallbacku na obraz bez podpisu lub format natywny.
- Błędy HTTP (`HTTPError`, `URLError`, `TimeoutError`) propagują się z `urllib` bez tłumienia; treść błędu nie zawiera klucza API.
- Błąd zapisu pliku rzuca standardowy `OSError`.

## Acceptance criteria

1. `compose_prompt` opisuje `VisualSpec`: temat, 5–7 wybranych dyrektyw, paletę hex, seeded medium i ograniczenia negatywne; style `creature` i `orbits` mają właściwe dla nich tematy.
2. Identyczne `VisualSpec` i argumenty nazwane dają bajt w bajt identyczny prompt; selekcja dyrektyw, paleta, medium i opt-in nazwy są sprawdzane zgodnie z kontraktem v2. Nie wymaga się zmiany tekstu po każdej dowolnej małej zmianie liczbowej.
3. `FakeImageBackend` zwraca deterministyczny poprawny PNG 64×64 z `media_type="png"`; ten sam `spec` z różnym promptem lub seed zachowuje bajty. Test obejmuje brak wymaganego `spec`.
4. `OpenRouterImageBackend` buduje poprawne żądanie (URL, metoda, nagłówki z `Bearer`, treść JSON) bez wykonywania prawdziwego połączenia sieciowego w testach; bajty odpowiedzi otrzymują wykryty typ mediów.
5. `render_prompt` zapisuje `prompt.txt` i portret o ekstensji zgodnej z wykrytym typem (`portrait.png`, `portrait.jpg`, `portrait.webp`) w podanym `output_dir`, tworząc katalogi, i zwraca kompletne `PromptRenderArtifacts` z ustawionymi ścieżkami oraz `media_type`.
6. Detekcja formatu rozpoznaje PNG, JPEG i WebP z magii bajtów; nierozpoznana zawartość kończy się `ValueError` bez zapisu portretu.
7. `image_format="png"` przekodowuje JPEG i WebP do PNG (wynik: `portrait.png`, `media_type="png"`); bez Pillow rzuca `ValueError` z podpowiedzią instalacji.
8. `--image-format` w trybie innym niż `prompt-to-image` kończy się błędem z kodem 1.
9. Wszystkie testy z Faz 1-4 nadal przechodzą pomyślnie.
10. Nowe testy pokrywają kompozycję promptu, determinizm, budowę żądania HTTP, detekcję formatu, obsługę błędów backendu, normalizację i zapis artefaktów.

## Required tests

- `tests/test_prompt_composer.py`: układ i wzorzec v2, determinizm, selekcja dyrektyw, tematy obu stylów, anatomia/aktywność postaci, paleta, medium, opt-in nazwy i błędne wejścia.
- `tests/test_image_backend.py`: kontrakt `FakeImageBackend`, budowa żądania `OpenRouterImageBackend` (URL, nagłówki, JSON) na fasadzie `urllib`, brak klucza rzuca `ValueError`, obsługa odpowiedzi `b64_json` i błędów HTTP bez połączenia sieciowego, detekcja typu dla PNG/JPEG/WebP i `ValueError` dla nierozpoznanych bajtów.
- `tests/test_prompt_render.py`: fasada `render_prompt`, zapis i treść artefaktów z ekstensją wg typu, tworzenie katalogów, przepływ błędów typów i trybów, normalizacja `image_format="png"` dla bajtów JPEG i WebP, błąd przy braku Pillow.

## Relevant SDD / ADR

- `docs/product/emotional-repository-portrait-system.md`
- `docs/features/live-renderers/spec.md` (wzorzec fasady i zapisu artefaktów)
