# Live Renderers: Abstract and Character Modes

Path: `docs/features/live-renderers/spec.md`

Zmiana z 2026-11-03 (etap 5 planu visual-diversity, GITGEIST-18, wersja 0.11.0): tryb `character` nie jest już opisany w tej specyfikacji. Rysuje go styl `creature` z `VisualSpec`, a jego zasady, dane i kryteria są w `docs/features/live-renderer-v2/character-spec.md`. Tryb `abstract` opisuje od 0.10.0 `docs/features/live-renderer-v2/spec.md`. Ta specyfikacja zachowuje tylko to, co dotyczy obu trybów: fasadę `render_live`, pliki wyjściowe, determinizm i ziarno tożsamości.

## Goal

Silnik renderowania wizualnego w czasie rzeczywistym dla Warstwy 4 (Live Renderers) architektury Gitgeist. Generuje interaktywny, autonomiczny podgląd wizualny (`live-preview.html`) oraz powiązany ustrukturyzowany stan sceny (`live-state.json`) w dwóch trybach reprezentacji: `abstract` (styl `orbits`) oraz `character` (styl `creature`: byt złożony z tułowia i kończyn, jedna część na katalog).

## Related requirements

- `docs/product/emotional-repository-portrait-system.md#L474-L541` (Sekcja 11: Dwa tryby reprezentacji: 11.1 Character mode, 11.2 Abstract mode)
- `docs/product/emotional-repository-portrait-system.md#L1094-L1117` (Sekcja 21: Live renderer)
- `docs/product/emotional-repository-portrait-system.md#L1155-L1158` (Sekcja 23: Live mode artifacts)
- `docs/product/emotional-repository-portrait-system.md#L1184-L1188` (Sekcja 24: Live frontend)
- `docs/product/emotional-repository-portrait-system.md#L1398-L1402` (Faza 4: Live renderers: abstract first, then simplified character)

## Scope

1. Schematy danych Pydantic v2 sceny live (`src/gitgeist/schemas/live_state.py`): `OrbitsScene` (tryb `abstract`, 0.10.0), `CreatureScene` z `CreatureBody`, `CreatureTorso`, `CreatureLimb` i `CreatureSegment` (tryb `character`, 0.11.0) oraz wspólny `HoverDetail`. Modele `ColorPalette`, `MotionDynamics`, `GeometryParameters` i `LiveSimulationState` zostały usunięte w 0.11.0 (zmiana łamiąca, wpis w `CHANGELOG.md`).
2. Generatory trybów: `build_orbits_scene` (`src/gitgeist/render/orbits.py`) i `build_creature_scene` (`src/gitgeist/render/creature.py`). Moduły `abstract_renderer.py` (usunięty w 0.10.0) oraz `character_renderer.py`, `dynamics.py` i `palette.py` (usunięte w 0.11.0), a także funkcje `generate_abstract_simulation`, `generate_character_simulation`, `generate_palette` i `generate_dynamics` nie istnieją. Wspólne części (teksty wniosków HUD, szczegóły hover, CSS i kod strony HUD) są w `src/gitgeist/render/captions.py` i `page_common.py`.
3. Szablon i kompozytor HTML (`src/gitgeist/render/html_template.py`): `generate_orbits_html(scene)` i `generate_creature_html(scene)` generują w pełni autonomiczny dokument HTML5 z osadzonym skryptem Canvas 2D bez żadnych zewnętrznych zależności (npm, CDN, bundlery), działający bezpośrednio z dysku lokalnego (`file:///`), z pętlą `requestAnimationFrame` i responsywnym skalowaniem do okna. HUD pokazuje nazwę repozytorium i trzy proste wnioski, a można go wyłączyć flagą `--caption off`. Funkcja `generate_live_html` została usunięta w 0.11.0.
4. Fasada i API renderera (`src/gitgeist/render/facade.py` oraz `src/gitgeist/__init__.py`):
   - Klasa wynikowa `LiveRenderArtifacts` zawierająca treść HTML, JSON stanu oraz opcjonalne zapisane ścieżki.
   - Funkcja `render_live(scene: OrbitsScene | CreatureScene, output_dir: Path | str | None = None, *, identity: IdentitySeed) -> LiveRenderArtifacts` (0.11.0). Tryb wynika z typu sceny; parametry `profile`, `mode` i `repository_name` zostały usunięte (nazwę repozytorium niesie scena).
5. Zestaw testów jednostkowych i integracyjnych pokrywających schematy, generowanie plików wyjściowych, determinizm i obsługę obu trybów.

## Non-goals

- Wymaganie instalacji `node`, `npm` czy lokalnego serwera deweloperskiego (artefakt HTML jest w 100% samodzielny).
- Kompozytor promptów tekstowych dla generatorów obrazów AI (Faza 5: Prompt composer).
- Backend generowania plików PNG na podstawie promptów (Faza 5).
- Analiza ewolucji w czasie / porównywanie wielu commitów (Faza 7).

## Behaviour

- Funkcja `render_live` przyjmuje scenę (`OrbitsScene` dla `abstract`, `CreatureScene` dla `character`), opcjonalny `output_dir` oraz wymagany argument nazwany `identity` (`IdentitySeed`).
- Zwraca obiekt `LiveRenderArtifacts` zawierający wyrenderowany dokument HTML (`live-preview.html`) oraz zwalidowany stan (`live-state.json`): `OrbitsScene` albo `CreatureScene`.
- Jeśli podano `output_dir`, funkcja deterministycznie zapisuje do wskazanego katalogu `live-preview.html`, `live-state.json` i `identity-seed.json`.
- Ta sama scena i to samo ziarno tożsamości dają identyczny stan JSON oraz identyczny dokument HTML. Ziarno generatora obu trybów to `seeds.effective_seed` z `VisualSpec` (ziarno tożsamości, ziarno użytkownika i styl). Ziarno tożsamości to SHA-256 posortowanych hashy commitów korzeniowych (gdy ścieżka nie jest korzeniem repozytorium Git z commitami: SHA-256 nazwy katalogu); `render_live` zapisuje je do `identity-seed.json`, gdy podano `output_dir` (poprawka z 2026-10-22, etap 1 planu visual-diversity).
- Dokument HTML osadza w sobie stan JSON oraz kod silnika Canvas, umożliwiając natychmiastowe uruchomienie bez połączenia internetowego i bez błędu CORS.

## Business rules

- Tryb Abstract: obraz powstaje z kanałów `VisualSpec`, jedna cecha na kanał, bez obróconych kopii; patrz `docs/features/live-renderer-v2/spec.md`, sekcje "Channels in `orbits`", "Motion" i "Business rules". Dawne reguły (`fragmentation`, `symmetry`, `texture_density`) zastąpiono w 0.10.0.
- Tryb Character: obraz powstaje z kanałów `VisualSpec` i planu ciała obliczonego z masy (tułów z największego katalogu, kończyny w parach po obu stronach, segmenty z `nesting_levels`, postawa z `alive`); patrz `docs/features/live-renderer-v2/character-spec.md`, sekcje "Body plan", "Channels in `creature`", "Motion" i "Business rules". Dawne reguły (`form_complexity`, `biological_vs_mechanical`, `ornamental_load`, `symmetry`, stały kręgosłup z żebrami i obrotowa korona) zastąpiono w 0.11.0.

## Authorization

none

## Data / API

- Wejście `render_live`:
  - `scene`: `OrbitsScene | CreatureScene` (wymagane)
  - `output_dir`: `Path | str | None = None`
  - `identity`: `IdentitySeed` (wymagane, tylko jako argument nazwany; `gitgeist.compute_identity_seed(repo_path)`)
- Wyjście:
  - `LiveRenderArtifacts`:
    - `state`: `OrbitsScene | CreatureScene`
    - `html_content`: `str`
    - `state_json`: `str`
    - `html_path`: `Path | None` (jeśli zapisano do pliku)
    - `json_path`: `Path | None` (jeśli zapisano do pliku)
    - `identity_seed_path`: `Path | None` (jeśli zapisano do pliku)
- Publiczne modele i funkcje:
  - `gitgeist.schemas.live_state.OrbitsScene`, `CreatureScene`, `CreatureBody`, `CreatureTorso`, `CreatureLimb`, `CreatureSegment` i `HoverDetail`
  - `gitgeist.render.orbits.build_orbits_scene(features, spec, *, repository_name=None, caption=True)` i `gitgeist.render.creature.build_creature_scene(features, spec, *, repository_name=None, caption=True)`
  - `gitgeist.schemas.identity.IdentitySeed`
  - `gitgeist.render.LiveRenderArtifacts`
  - `gitgeist.render_live`

## Edge cases

- Ekstremalne wartości cech (wszystkie osie 0.0 lub 1.0): brak wartości NaN, dzielenia przez zero i zawieszenia animacji Canvas.
- Podanie nieistniejącego katalogu wyjściowego: automatyczne utworzenie katalogu (`mkdir(parents=True, exist_ok=True)`).
- Repozytorium bez katalogów albo bez plików: opisane w specyfikacjach trybów.

## Errors

- Przekazanie `scene` innego typu niż `OrbitsScene` albo `CreatureScene` rzuca `TypeError`; `identity` innego typu niż `IdentitySeed` rzuca `TypeError`.
- Błąd zapisu do pliku rzuca standardowy wyjątek `OSError`.
- Brak cichych fallbacków ukrywających niepoprawne dane.

## Acceptance criteria

1. Modele scen są zdefiniowane w Pydantic v2 z `frozen=True` i `extra="forbid"`.
2. Tryb Abstract: kryteria z `docs/features/live-renderer-v2/spec.md` (rozstęp obrazów D v1 co najmniej 0.40 na korpusie 12 repozytoriów).
3. Tryb Character: kryteria z `docs/features/live-renderer-v2/character-spec.md` (rozstęp obrazów D v1 co najmniej 0.25 na tym korpusie, para `gitgeist` i `NeKode` nie jest najbliższą parą).
4. Wygenerowany plik `live-preview.html` jest poprawnym, autonomicznym dokumentem HTML5 osadzającym Canvas 2D oraz stan JSON, działającym bez połączenia z siecią.
5. Funkcja `render_live` eksportowana jest na poziomie `gitgeist` i zwraca kompletny obiekt `LiveRenderArtifacts`.
6. Testy automatyczne weryfikują generowanie w obu trybach, determinizm, walidację schematów oraz zapis plików na dysku.

## Required tests

- `tests/test_live_state_schemas.py`: walidacja modeli scen, niezmienniki, serializacja JSON.
- `tests/test_live_renderers.py`: fasada `render_live` dla obu scen (zapis plików, determinizm, błędy typów) oraz brak usuniętego kodu.
- Testy trybu abstract: `tests/test_orbits_scene.py`, `tests/test_orbits_html.py`, `tests/test_orbits_snapshot.py` (`docs/features/live-renderer-v2/spec.md`). Testy trybu character: `tests/test_creature_body.py`, `tests/test_creature_scene.py`, `tests/test_creature_html.py` (`docs/features/live-renderer-v2/character-spec.md`). Migawki w `tests/golden/live/`.

## Relevant SDD / ADR

- `docs/product/emotional-repository-portrait-system.md`
