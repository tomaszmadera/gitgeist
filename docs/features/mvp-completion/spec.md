# MVP completion: CLI i testy zachowania aplikacji

Path: `docs/features/mvp-completion/spec.md`

## Goal

Domknąć lukę MVP Definition of Done (sekcja 25 dokumentu produktowego): dać użytkownikowi punkt wejścia do aplikacji oraz udowodnić testami zachowania na poziomie całego pipeline, że MVP spełnia kryteria 1, 7 i 8. Po tej fazie użytkownik uruchamia `gitgeist analyze <repo>` i `gitgeist render <repo> ...` zamiast wywołań bibliotecznych, a plan testów produktowych z sekcji 29 (Testy 1, 2, 5, 6) ma pokrycie na pełnym pipeline.

## Related requirements

- `docs/product/emotional-repository-portrait-system.md#L1118-L1146` (Sekcja 22: CLI / UX: `analyze`, `render` z `--representation` i `--mode`; `compare` jest post-MVP)
- `docs/product/emotional-repository-portrait-system.md#L1203-L1219` (Sekcja 25: MVP Definition of Done, punkty 1, 6, 7, 8)
- `docs/product/emotional-repository-portrait-system.md#L1301-L1319` (Sekcja 29: Test plan, Testy 1, 2, 5, 6; Testy 3-4 są post-MVP)
- `docs/product/emotional-repository-portrait-system.md#L647-L667` (Sekcja 14.1: MVP scope: representation modes `character`/`abstract`, generation modes `live`/`prompt_to_image_gen_llm`, outputs)
- `docs/product/emotional-repository-portrait-system.md#L1149-L1167` (Sekcja 23: nazwy artefaktów: wymagane `profile.json`, `summary.md`; live: `live-preview.html`, `live-state.json`; prompt: `prompt.txt`, `portrait.png`)

## Scope

1. Moduł `src/gitgeist/cli.py` (argparse, bez nowych zależności) i konsolowy punkt wejścia `gitgeist` zarejestrowany w `pyproject.toml` (`[project.scripts]`).
2. Polecenie `gitgeist analyze <repo_path> [-o DIR]`: pełny pipeline `extract_features` -> `evaluate_emotional_state` -> `map_emotional_to_latent` -> `explain`; zapis wymaganej pary artefaktów `profile.json` i `summary.md` do `DIR`; domyślnie `DIR = ./gitgeist-output/<repository_name>` względem katalogu roboczego procesu; `source_commit` ustawiane na HEAD repo (gdy repo jest repozytorium git).
3. Polecenie `gitgeist render <repo_path> --representation {character,abstract} --mode {live,prompt-to-image} [-o DIR] [--backend {fake,openai-compatible}]`: pipeline jak w `analyze` plus artefakty trybu generacji:
   - `live`: `live-preview.html`, `live-state.json` (przez `render_live`);
   - `prompt-to-image`: `prompt.txt`, `portrait.png` (przez `render_prompt`);
   - oba tryby zapisują także wymaganą parę `profile.json` i `summary.md`.
4. Backend obrazu: `fake` (domyślny, deterministyczny `FakeImageBackend`) oraz `openai-compatible` (`OpenAICompatibleBackend`, klucz z `GITGEIST_IMAGE_API_KEY`).
5. Testy zachowania aplikacji: `tests/test_cli.py` (end-to-end CLI) i `tests/test_mvp_behavior.py` (Testy 1, 2, 5, 6 z sekcji 29 na pełnym pipeline).

## Non-goals

- `compare`, `timeline.json`, `comparison.json`, animacja ewolucji, tożsamość między snapshotami (Faza 7, post-MVP, sekcje 16 i 26).
- Critique loop, style packs, interactive explanation mode, routing modeli OpenRouter.
- Zmiana zachowania sensorów, mapowania, rendererów ani explainability; CLI je wyłącznie łączy.
- Interaktywny TUI, daemon, watch mode; brak nowych zależności runtime poza stdlib argparse.
- Realne wywołania sieciowe w testach; testy używają wyłącznie `FakeImageBackend`.

## Behaviour

- `analyze` i `render` przyjmują ścieżkę istniejącego katalogu; nieistniejąca ścieżka kończy się komunikatem na stderr i kodem wyjścia 1, bez tracebacku.
- Pipeline jest wspólny dla obu poleceń: te same dane wejściowe dają te same `EmotionalState` i `VisualLatentProfile` niezależnie od polecenia, `--representation` i `--mode`; tryby zmieniają wyłącznie artefakty renderowania.
- `--representation` dotyczy obu trybów generacji: `character` i `abstract` dają inną symulację live oraz inny segment promptu; wspólny rdzeń (scores, axes, materiałowość, kwalifikatory) pozostaje identyczny.
- Stabilność snapshotu (DoD 8): dwa uruchomienia na tym samym stanie repo dają identyczne wartości scores, nouls, choices, axes, materiałowości oraz bajt w bajt identyczne `summary.md`, `live-state.json` i `prompt.txt`; `profile.json` może różnić się wyłącznie polami ulotnymi (`calculated_at`, `extracted_at`, `source_commit`, `engine_version`).
- `prompt-to-image` z backendem `fake` jest w pełni deterministyczny: identyczny prompt daje identyczne bajty `portrait.png`.
- Zapis artefaktów tworzy katalogi wraz z rodzicami i nadpisuje wcześniejsze pliki pełną treścią; kolejność zapisu: wymagana para (`profile.json`, `summary.md`), potem artefakty trybu; błąd zapisu propaguje `OSError` bez tłumienia.
- Domyślny katalog artefaktów leży poza analizowanym repozytorium: zapis nie mutuje analizowanego snapshotu (wymóg stabilności DoD 8); przekazanie `-o` wskazującego do wewnątrz repo jest jawnym wyborem użytkownika.
- Komunikat ukończenia zawiera ścieżki zapisanych artefaktów; nic nie jest drukowane na stdout w przypadku błędu.

## Business rules

- Nazwa konsolowa to `gitgeist`; odstępstwo od przykładu `repo-portrait` w sekcji 22 wynika z nazwy pakietu (`pyproject.toml` `name = "gitgeist"`, README); przykład produktowy jest wcześniejszy względem zmiany nazwy.
- Nazwy i zestaw plików artefaktów są zgodne z sekcją 23; CLI nie tworzy artefaktów opcjonalnych (`timeline.json`, `comparison.json`, `identity-seed.json`, `critique.json`).
- Różnicowanie (DoD 7, Test 1 z sekcji 29) jest mierzalne: dla par różnych repozytoriów testowych profil ma co najmniej 3 osie różniące się o `>= 0.1`, co najmniej 3 scores różniące się o `>= 0.1` oraz inną dominującą materiałowość. Dowód z fiksür `clean_modular_repo` i `legacy_chaotic_repo`: 13 z 14 osi i 9 z 10 scores różni się o `>= 0.1`, materiałowość `crystalline` vs `organic`.
- Wspólny rdzeń trybów (Testy 5 i 6): wartości osi, kwalifikatory i dominanta materiałowości w `prompt.txt` są równe wartościom w `live-state.json` wygenerowanym z tego samego snapshotu.
- Brak repozytorium git nie jest błędem: `source_commit` pozostaje `None`, pipeline używa domyślnych wartości non-git (jak w istniejących testach `non_git_dir`).

## Authorization

Brak. Funkcja działa lokalnie na ścieżce podanej przez użytkownika; jedyne wyjście sieciowe to opcjonalny backend `openai-compatible` inicjowany jawnie przez użytkownika i wymagający klucza z `GITGEIST_IMAGE_API_KEY`.

## Data / API

- Konsolowy punkt wejścia: `gitgeist` (`[project.scripts]` `gitgeist = "gitgeist.cli:main"`).
- `gitgeist analyze <repo_path> [-o DIR]`:
  - `<repo_path>`: istniejący katalog (wymagany);
  - `-o/--output DIR`: katalog artefaktów, domyślnie `./gitgeist-output/<repository_name>` względem katalogu roboczego procesu;
  - wyjście: pliki `profile.json`, `summary.md`.
- `gitgeist render <repo_path> --representation {character,abstract} --mode {live,prompt-to-image} [-o DIR] [--backend {fake,openai-compatible}]`:
  - `--representation` (wymagany): `character` albo `abstract`;
  - `--mode` (wymagany): `live` albo `prompt-to-image`;
  - `-o/--output DIR`: domyślnie `./gitgeist-output/<repository_name>` względem katalogu roboczego procesu;
  - `--backend`: domyślnie `fake`; `openai-compatible` używa `GITGEIST_IMAGE_API_KEY`, domyślnego `base_url` i modelu z `image_backend.py`;
  - wyjście: `profile.json`, `summary.md` plus `live-preview.html` i `live-state.json` (tryb `live`) albo `prompt.txt` i `portrait.png` (tryb `prompt-to-image`).
- Wejście pipeline (bez zmian): `extract_features(Path)`, `evaluate_emotional_state(features, source_commit=...)`, `map_emotional_to_latent(state)`, `explain(features, state, profile, repository_name=<nazwa repo>, output_dir=DIR)`, `render_live(profile, mode=..., repository_name=..., output_dir=DIR)`, `render_prompt(state, profile, mode=..., backend=..., output_dir=DIR)`.
- Kody wyjścia: `0` sukces; `1` błąd użycia lub wykonania (ścieżka, backend, zapis); `2` błąd argparse (domyślny).

## Edge cases

- Katalog nie będący repozytorium git: pełny pipeline działa, `source_commit` jest `None`.
- `-o` wskazuje zagnieżdżoną, nieistniejącą ścieżkę: katalogi powstają wraz z rodzicami.
- Ponowne uruchomienie do tego samego `DIR`: nadpisanie artefaktów pełną treścią, bez duplikatów i resztek; przy domyślnym katalogu drugie przejście widzi ten sam snapshot repo (artefakty nie trafiają do analizowanego katalogu).
- `--backend openai-compatible` bez klucza w środowisku: błąd użycia z komunikatem o `GITGEIST_IMAGE_API_KEY`, kod wyjścia 1, brak częściowych artefaktów obrazu.
- `render` na repo non-git: działa jak `analyze`, z artefaktami trybu.
- `--backend` przekazany z `--mode live`: błąd użycia z komunikatem, kod wyjścia 1; `--backend` dotyczy wyłącznie `--mode prompt-to-image`.

## Errors

- Nieistniejąca ścieżka repo: komunikat na stderr, kod 1, brak tracebacku i brak artefaktów.
- Nieznany tryb, reprezentacja albo backend odcina argparse (`2`).
- Brak `GITGEIST_IMAGE_API_KEY` przy `openai-compatible`: jawny błąd, kod 1; nie ma cichego przełączenia na backend `fake`.
- `OSError` i kontraktowe `ValueError` warstw niższych (np. uszkodzona odpowiedź backendu obrazu, błąd zapisu) docierają do granicy CLI i zamieniają się w komunikat na stderr z kodem 1, bez tracebacku; żadna warstwa nie tłumi błędów.

## Acceptance criteria

1. Po instalacji pakietu konsolowe `gitgeist` istnieje; `gitgeist analyze <repo>` kończy się kodem 0 i tworzy `profile.json` oraz `summary.md` w domyślnym katalogu poza analizowanym repo; `profile.json` parsuje się z powrotem do modeli warstw 1-3.
2. `gitgeist render <repo> --representation character --mode live` i `--representation abstract --mode live` kończą się kodem 0 i tworzą `live-preview.html`, `live-state.json` oraz parę wymaganą; `--representation character --mode prompt-to-image` i `--representation abstract --mode prompt-to-image` tworzą `prompt.txt`, `portrait.png` oraz parę wymaganą.
3. Test 1 (sekcja 29): pełny pipeline na dwóch różnych fiksürach repo daje profile różniące się zgodnie z regułą różnicowania (osie, scores, materiałowość).
4. Test 2 (sekcja 29): dwa przejścia pipeline na tym samym snapshotcie dają identyczne scores/nouls/choices/axes/materiałowość, bajt w bajt identyczne `summary.md` i `prompt.txt`, a `profile.json` różni się co najwyżej polami ulotnymi.
5. Test 5 (sekcja 29): dla `character` i `abstract` obiekty `EmotionalState` i `VisualLatentProfile` są identyczne; różnią się wyłącznie artefakty renderowania.
6. Test 6 (sekcja 29): `prompt.txt` i `live-state.json` z tego samego snapshotu noszą wspólny rdzeń: równe wartości osi, kwalifikatory i dominanta materiałowości.
7. Błędy użycia (brak ścieżki, brak klucza API) dają kod 1, komunikat na stderr i brak tracebacku.
8. Wszystkie dotychczasowe testy przechodzą; nowa suma testów zawiera `tests/test_cli.py` i `tests/test_mvp_behavior.py`.

## Required tests

- `tests/test_cli.py`:
  - `analyze` na fiksutrze git i non-git: kod 0, zestaw plików, roundtrip `profile.json`, komunikat o ścieżkach;
  - `render` w pełnym przecięciu representation x mode: kod 0 i komplet artefaktów trybu plus para wymagana;
  - domyślny katalog `./gitgeist-output/<repository_name>` (poza analizowanym repo) oraz `-o` z zagnieżdżeniem i nadpisaniem;
  - `--backend openai-compatible` bez klucza: kod 1 i komunikat o `GITGEIST_IMAGE_API_KEY`;
  - nieistniejąca ścieżka: kod 1, stderr, brak tracebacku; zapis rzucający `OSError` wychodzi kodem 1.
- `tests/test_mvp_behavior.py`:
  - Test 1: clean modular vs legacy chaotic na pełnym pipeline według reguły różnicowania;
  - Test 2: stabilność podwójnego przejścia (wartości profili, `summary.md` bajt w bajt, `profile.json` po odfiltrowaniu pól ulotnych identyczny);
  - Test 5: identyczność `EmotionalState` i `VisualLatentProfile` między representation modes; różność artefaktów;
  - Test 6: zgodność rdzenia osi, kwalifikatorów i materiałowości między `prompt.txt` a `live-state.json`.

## Relevant SDD / ADR

- `docs/product/emotional-repository-portrait-system.md` (sekcje 14.1, 22, 23, 25, 29)
- `docs/features/explainability/spec.md`, `docs/features/prompt-to-image/spec.md`, `docs/features/live-renderers/spec.md` (wzorce fasad, artefaktów, backendów i kwalifikatorów)
