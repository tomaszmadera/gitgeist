# Live Renderers: Abstract and Character Modes

Path: `docs/features/live-renderers/spec.md`

Zmiana z 2026-11-03 (etap 4 planu visual-diversity, GITGEIST-17, wersja 0.10.0): tryb `abstract` nie jest już opisany w tej specyfikacji. Rysuje go styl `orbits` z `VisualSpec`, a jego zasady, dane i kryteria są w `docs/features/live-renderer-v2/spec.md`. Reguły trybu `character` poniżej obowiązują bez zmian do etapu 5.

## Goal

Zbudować silnik renderowania wizualnego w czasie rzeczywistym dla Warstwy 4 (Live Renderers) architektury Gitgeist. Silnik generuje interaktywny, autonomiczny podgląd wizualny (`live-preview.html`) oraz powiązany ustrukturyzowany stan symulacji (`live-state.json`) na podstawie profilu cech wizualnych `VisualLatentProfile` w dwóch trybach reprezentacji: `abstract` (kompozycja dynamicznych pól, geometrii i przepływów) oraz `character` (proceduralny byt wyłaniający się z cech repozytorium).

## Related requirements

- `docs/product/emotional-repository-portrait-system.md#L474-L541` (Sekcja 11: Dwa tryby reprezentacji: 11.1 Character mode, 11.2 Abstract mode)
- `docs/product/emotional-repository-portrait-system.md#L1094-L1117` (Sekcja 21: Live renderer)
- `docs/product/emotional-repository-portrait-system.md#L1155-L1158` (Sekcja 23: Live mode artifacts)
- `docs/product/emotional-repository-portrait-system.md#L1184-L1188` (Sekcja 24: Live frontend)
- `docs/product/emotional-repository-portrait-system.md#L1398-L1402` (Faza 4: Live renderers: abstract first, then simplified character)

## Scope

1. Schematy danych Pydantic v2 dla stanu symulacji live (`src/gitgeist/schemas/live_state.py`):
   - `ColorPalette`: definicja spójnej gamy kolorystycznej (background, foreground, primary, secondary, accent, aura) w notacji hex/rgba.
   - `MotionDynamics`: parametry prędkości przepływu, częstotliwości pulsacji, amplitudy oddechu i turbulencji.
   - `GeometryParameters`: parametry zagęszczenia, segmentacji, symetrii, ostrości krawędzi i warstwowości.
   - `LiveSimulationState`: nadrzędny niemutowalny model zawierający tryb (`abstract` lub `character`), ziarno generatora (`seed`), paletę barw, parametry dynamiki, parametry geometryczne, dominujący materiał oraz metadane. Od 0.10.0 używa go tylko tryb `character`; scenę trybu `abstract` opisuje `OrbitsScene` (`docs/features/live-renderer-v2/spec.md`).
2. Generator palety barw (`src/gitgeist/render/palette.py`):
   - Deterministyczne mapowanie osi `luminosity`, `contrast`, `tension_curvature` oraz dominantu materiałowości na zharmonizowaną paletę HSL/Hex.
3. Generator dynamiki ruchu (`src/gitgeist/render/dynamics.py`):
   - Translacja parametrów rytmu (`visual_rhythm`), napięcia (`tension_curvature`) i równowagi (`compositional_balance`) na wartości fizyczne symulacji czasu rzeczywistego (prędkość, puls, drgania).
4. Renderer trybu Abstract: zastąpiony w 0.10.0. Moduł `src/gitgeist/render/abstract_renderer.py` i funkcja `generate_abstract_simulation` zostały usunięte. Scenę buduje `build_orbits_scene` (`src/gitgeist/render/orbits.py`), a stronę rysuje `generate_orbits_html` z `VisualSpec` w stylu `orbits` (`docs/features/live-renderer-v2/spec.md`).
5. Renderer trybu Character (`src/gitgeist/render/character_renderer.py`):
   - Obliczanie cech struktury bytu: proceduralny rdzeń/szkielet, liczba segmentów, zniekształcenia symetrii, aura peryferyjna oraz wskaźnik organiczności/mechaniczności z `biological_vs_mechanical`.
6. Szablon i kompozytor HTML (`src/gitgeist/render/html_template.py`):
   - Generowanie w pełni autonomicznego dokumentu HTML5 z osadzonym skryptem Canvas 2D/WebGL bez żadnych zewnętrznych zależności (npm, CDN, bundlery) – działającego bezpośrednio z dysku lokalnego (`file:///`).
   - Pętla animacji `requestAnimationFrame`, responsywne skalowanie do okna przeglądarki, wizualna informacja o profilu latentnym i trybie (tryb `character`; w trybie `abstract` HUD pokazuje trzy proste wnioski o repozytorium i można go wyłączyć flagą `--caption off`).
   - Od 0.10.0 szablon trybu `character` nie zawiera już kodu rysowania trybu `abstract` (obracane kopie), a `generate_orbits_html(scene)` rysuje tryb `abstract`.
7. Fasada i API renderera (`src/gitgeist/render/facade.py` oraz `src/gitgeist/__init__.py`):
   - Klasa wynikowa `LiveRenderArtifacts` zawierająca treść HTML, słownik/JSON stanu oraz opcjonalne zapisane ścieżki.
   - Funkcja `render_live(profile: VisualLatentProfile, mode: Literal["abstract", "character"] = "abstract", repository_name: str | None = None, output_dir: Path | str | None = None, *, identity: IdentitySeed, scene: OrbitsScene | None = None) -> LiveRenderArtifacts`. Tryb `abstract` wymaga `scene`, tryb `character` wymaga `scene=None` (0.10.0).
8. Zestaw testów jednostkowych i integracyjnych pokrywających schematy, wyliczanie parametrów renderera, generowanie plików wyjściowych, determinizm i obsługę obu trybów.

## Non-goals

- Wymaganie instalacji `node`, `npm` czy lokalnego serwera deweloperskiego (artefakt HTML jest w 100% samodzielny).
- Kompozytor promptów tekstowych dla generatorów obrazów AI (Faza 5: Prompt composer).
- Backend generowania plików PNG na podstawie promptów (Faza 5).
- Analiza ewolucji w czasie / porównywanie wielu commitów (Faza 7).

## Behaviour

- Funkcja `render_live` przyjmuje obiekt `VisualLatentProfile`, opcjonalny tryb (`abstract` lub `character`, domyślnie `abstract`), wymagany argument nazwany `identity` (`IdentitySeed`) oraz argument nazwany `scene` (`OrbitsScene`, wymagany dla `abstract`, `None` dla `character`).
- Zwraca obiekt `LiveRenderArtifacts` zawierający wyrenderowany dokument HTML (`live-preview.html`) oraz zwalidowany stan (`live-state.json`): `LiveSimulationState` dla `character`, `OrbitsScene` dla `abstract`.
- Jeśli podano `output_dir`, funkcja deterministycznie zapisuje do wskazanego katalogu `live-preview.html`, `live-state.json` i `identity-seed.json`.
- Identyczny `VisualLatentProfile`, tryb i ziarno tożsamości dają identyczny stan symulacji `LiveSimulationState` oraz identyczny dokument HTML. Ziarno generatora trybu `character` (`seed`) zależy wyłącznie od ziarna tożsamości i trybu, nigdy od wartości profilu ani od HEAD. W trybie `abstract` ziarno to `seeds.effective_seed` z `VisualSpec` (ziarno tożsamości, ziarno użytkownika i styl). Ziarno tożsamości to SHA-256 posortowanych hashy commitów korzeniowych (gdy ścieżka nie jest korzeniem repozytorium Git z commitami: SHA-256 nazwy katalogu); `render_live` zapisuje je do `identity-seed.json`, gdy podano `output_dir` (poprawka z 2026-10-22, etap 1 planu visual-diversity).
- Dokument HTML osadza w sobie stan JSON oraz kod silnika Canvas, umożliwiając natychmiastowe uruchomienie bez połączenia internetowego i bez błędu CORS.

## Business rules

- Paleta barw:
  - Tło ciemnieje przy niskim `luminosity` i rozjaśnia się przy wysokim.
  - Kontrast między tłem a elementami pierwszoplanowymi jest wprost proporcjonalny do osi `contrast`.
  - Akcent barwny przyjmuje chłodniejsze odcienie (niebieski/cyan/srebrny) przy dominacji materiału `crystalline` lub `mechanical`, a cieplejsze/ziemiste (bursztyn/złoto/czerwień) przy `organic` lub wysokim `tension_curvature`. Eteryczność (`ethereal`) zwiększa rozmycie i przezroczystość barw aury.
- Dynamika symulacji:
  - `pulse_frequency` rośnie wraz z `visual_rhythm`.
  - `turbulence` i niestabilność przepływu rosną wraz z `tension_curvature` oraz maleją wraz z `compositional_balance`.
- Tryb Abstract: zasady zastąpione w 0.10.0. Dawne reguły (`fragmentation`, `symmetry`, `texture_density` oraz symetria obrotowa z kopiami) nie obowiązują. Obraz powstaje z kanałów `VisualSpec`, jedna cecha na kanał, bez obróconych kopii; patrz `docs/features/live-renderer-v2/spec.md`, sekcje "Channels in `orbits`", "Motion" i "Business rules".
- Tryb Character:
  - Liczba segmentów szkieletu i złożoność sylwetki rośnie z `form_complexity`.
  - `biological_vs_mechanical` bliskie 1.0 generuje ostre, geometryczne, wielokątne segmenty; bliskie 0.0 generuje obłe, płynne, organiczne krzywe.
  - `ornamental_load` generuje liczbę detali peryferyjnych i pierścieni wokół rdzenia.
  - `symmetry` kontroluje symetrię osiową sylwetki postaci (przy niskiej wartości generowane są asymetryczne wypustki i przesunięcia).

## Authorization

none

## Data / API

- Wejście:
  - `profile`: `VisualLatentProfile` (wymagane)
  - `mode`: `Literal["abstract", "character"] = "abstract"`
  - `repository_name`: `str | None = None`
  - `output_dir`: `Path | str | None = None`
  - `identity`: `IdentitySeed` (wymagane, tylko jako argument nazwany; `gitgeist.compute_identity_seed(repo_path)`)
- Generator trybu `character`: `generate_character_simulation(profile, repository_name=None, *, identity_seed: str)`, gdzie `identity_seed` to `IdentitySeed.identity_seed`. Funkcja `generate_abstract_simulation` została usunięta w 0.10.0 (zmiana łamiąca, wpis w `CHANGELOG.md`); scenę abstrakcyjną buduje `gitgeist.render.orbits.build_orbits_scene(features, spec, *, repository_name=None, caption=True)`.
  - `scene`: `OrbitsScene | None = None` (tylko jako argument nazwany)
- Wyjście:
  - `LiveRenderArtifacts`:
    - `state`: `LiveSimulationState | OrbitsScene`
    - `html_content`: `str`
    - `state_json`: `str`
    - `html_path`: `Path | None` (jeśli zapisano do pliku)
    - `json_path`: `Path | None` (jeśli zapisano do pliku)
    - `identity_seed_path`: `Path | None` (jeśli zapisano do pliku)
- Publiczne modele:
  - `gitgeist.schemas.live_state.ColorPalette`
  - `gitgeist.schemas.live_state.MotionDynamics`
  - `gitgeist.schemas.live_state.GeometryParameters`
  - `gitgeist.schemas.live_state.LiveSimulationState`
  - `gitgeist.schemas.live_state.OrbitsScene` i `HoverDetail` (0.10.0)
  - `gitgeist.schemas.identity.IdentitySeed`
  - `gitgeist.render.LiveRenderArtifacts`
  - `gitgeist.render_live`

## Edge cases

- Ekstremalne wartości profilu (wszystkie osie 0.0 lub 1.0): brak wartości NaN, dzielenia przez zero i zawieszenia animacji Canvas.
- Identyczne wagi materiałów: deterministyczny wybór barw bez błędów losowości.
- Podanie nieistniejącego katalogu wyjściowego: automatyczne utworzenie katalogu (`mkdir(parents=True, exist_ok=True)`).

## Errors

- Przekazanie obiektu innego niż `VisualLatentProfile` albo `identity` innego typu niż `IdentitySeed` rzuca `TypeError`. Tryb `abstract` bez `scene` albo ze `scene` innego typu niż `OrbitsScene` rzuca `TypeError`.
- Przekazanie nieznanego trybu reprezentacji (np. `"surreal"`) rzuca `ValueError`. Tryb `character` ze `scene` rzuca `ValueError`.
- Błąd zapisu do pliku rzuca standardowy wyjątek `OSError`.
- Brak cichych fallbacków ukrywających niepoprawne dane.

## Acceptance criteria

1. Modele `ColorPalette`, `MotionDynamics`, `GeometryParameters` oraz `LiveSimulationState` są zdefiniowane w Pydantic v2 z `frozen=True`.
2. Generatory palety i dynamiki deterministycznie przekładają parametry osi na wartości liczbowe i formaty kolorów.
3. Tryb Abstract: kryterium zastąpione w 0.10.0 kryteriami z `docs/features/live-renderer-v2/spec.md` (strona rysuje `OrbitsScene`, rozstęp obrazów D v1 co najmniej 0.40 na korpusie 12 repozytoriów).
4. Generator trybu Character poprawnie tworzy parametry sylwetki, segmentacji i aury.
5. Wygenerowany plik `live-preview.html` jest poprawnym, autonomicznym dokumentem HTML5 osadzającym Canvas 2D/WebGL oraz stan JSON, działającym bez połączenia z siecią.
6. Funkcja `render_live` eksportowana jest na poziomie `gitgeist` i zwraca kompletny obiekt `LiveRenderArtifacts`.
7. Wszystkie 60 testów z Faz 1-3 nadal przechodzą pomyślnie.
8. Nowe testy automatyczne weryfikują poprawność generowania w obu trybach, determinizm, walidację schematów oraz zapis plików na dysku.

## Required tests

- `tests/test_live_state_schemas.py`: walidacja modeli Pydantic stanu live, niezmienniki, serializacja JSON.
- `tests/test_live_renderers.py`: testy generowania palety, dynamiki, trybu character, generowania dokumentu HTML oraz fasady `render_live` (tryb abstract przez `OrbitsScene`; testy dawnego generatora abstrakcyjnego usunięto w 0.10.0).
- Testy trybu abstract: `tests/test_orbits_scene.py`, `tests/test_orbits_html.py` (`docs/features/live-renderer-v2/spec.md`). Snapshot trybu character z 0.9.0: `tests/golden/live/`.

## Relevant SDD / ADR

- `docs/product/emotional-repository-portrait-system.md`
