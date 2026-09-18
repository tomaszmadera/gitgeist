# Emotional Repository Portrait System
## System do przedstawiania repozytorium w formie emocjonalnego obrazu

**Status:** Proposal / implementation specification  
**Wersja:** 0.1  
**Cel:** projekt dla agenta implementującego  
**Output:** dokumentacja systemu generującego emocjonalny profil i obraz repozytorium  
**Tryby wyjścia:** `character`, `abstract`  
**Tryby generowania:** `live`, `prompt_to_image_gen_llm`  
**Podział:** MVP + Post-MVP

---

# 1. Cel projektu

Celem projektu jest zbudowanie systemu, który analizuje repozytorium i przedstawia jego stan, charakter, napięcia, rytm zmian oraz „osobowość” w formie **emocjonalnego portretu wizualnego**.

System nie ma tworzyć tradycyjnego dashboardu ani suchych metryk w rodzaju:

- liczba plików,
- liczba commitów,
- liczba testów,
- coverage,
- TODO count.

Te sygnały mogą być wykorzystane, ale tylko jako część głębszej interpretacji.

Docelowy output ma odpowiadać na pytanie:

> **„Jak to repozytorium się czuje i jaki ma charakter?”**

Nie w sensie żartu oderwanego od danych, ale w sensie:
- semantycznego profilu wyprowadzonego z analizy,
- stabilnego systemu cech,
- wizualnej reprezentacji wynikającej z obliczeń,
- obrazu, który można pokazać człowiekowi i który coś ujawnia o stanie projektu.

---

# 2. Główna idea

System składa się z 4 warstw:

```text
Repository
   ↓
Feature extraction
   ↓
Semantic interpretation
   ↓
Portrait generation
```

Czyli:

1. **Repository analysis**  
   Zbieramy sygnały z repo.

2. **Feature extraction**  
   Tworzymy profil liczbowy / symboliczy.

3. **Semantic interpretation**  
   JEV oraz opcjonalnie mocniejszy LLM mapują repo na **wielowymiarowy stan semantyczno-emocjonalny**.

4. **Portrait generation**  
   Stan ten jest przedstawiany jako:
   - **postać** (`character`)
   - **abstrakcja** (`abstract`)

i renderowany w trybie:
- **live**
- **prompt_to_image_gen_llm**

---

# 3. Kluczowa zasada projektowa

Najważniejsze ograniczenie tego projektu:

> **Nie chcemy ręcznie wpisywać banalnych reguł typu: „duże legacy = brzydki potwór”, „małe nowe repo = słodki robocik”.**

To jest bardzo ważne.

System nie ma polegać na prostych memicznych mapowaniach typu:

```text
old repo → monster
new repo → clean robot
many tests → glasses
many TODO → scars
```

To podejście jest zbyt płaskie i zbyt silnie projektowane przez człowieka.

Zamiast tego chcemy:

## emergent visual identity

Wygląd powinien wyłaniać się z:
- profilu semantycznego,
- geometrii cech,
- latentnych przestrzeni,
- deformacji i wag,
- oraz ewentualnego tłumaczenia tego profilu na prompt dla modelu generującego obraz.

Oznacza to, że system powinien działać tak:

```text
repo
  ↓
semantic state vector
  ↓
portrait latent / visual grammar
  ↓
character or abstract form
```

a nie tak:

```text
repo
  ↓
if old then monster
if clean then robot
```

---

# 4. Zakres projektu

System ma działać na jednym repozytorium i generować:

## 4.1. Profile

- surowy profil liczbowy,
- profil semantyczny,
- profil emocjonalny,
- profil wizualny.

## 4.2. Formy prezentacji

### A. `character`
Repo jest przedstawione jako postać / istota / byt.

Nie musi to być humanoid.  
Może to być:
- android,
- duch,
- zwierzęce bóstwo,
- biomorficzny organizm,
- geometryczna postać,
- maszyna,
- abstrakcyjna istota.

Ale forma powinna wynikać z systemu generacji, nie z ręcznie wpisanych stereotypów.

### B. `abstract`
Repo jest przedstawione jako obraz abstrakcyjny:
- kompozycja,
- krajobraz emocjonalny,
- aura,
- pole energii,
- rzeźba,
- geometria,
- tekstura,
- układ dynamicznych form.

---

## 4.3. Tryby generacji

### A. `live`
Obraz lub scena budowane są bezpośrednio przez lokalny renderer / silnik wizualny na podstawie stanu repo.

Przykłady:
- WebGL / Three.js,
- Canvas 2D,
- shader,
- proceduralny generator,
- particle system,
- rzeźba 3D.

### B. `prompt_to_image_gen_llm`
Repo jest analizowane, tworzony jest opis semantyczno-wizualny, a następnie program generuje prompt i przekazuje go do modelu image generation.

Możliwe backendy:
- OpenAI image generation,
- inne image-gen LLM,
- OpenRouter, jeśli umożliwia odpowiedni routing do modeli obrazowych lub pomocniczych LLM do promptingu.

---

# 5. Możliwe zastosowania

To nie musi być system „na 100% przydatny produkcyjnie”.  
Ma być:
- ciekawy,
- pokazowy,
- eksploracyjny,
- potencjalnie odkrywczy.

Przykłady użycia:
- portret bieżącego stanu projektu po każdym commicie,
- porównanie portretów branchy,
- galeria ewolucji repo w czasie,
- „moodboard” projektu dla ludzi wchodzących do zespołu,
- artystyczne podsumowanie sprintu,
- semantyczna wizualizacja stanu kodu,
- zabawny, ale ugruntowany w danych sposób oglądania repo.

---

# 6. Główna hipoteza

Repozytorium ma nie tylko właściwości techniczne, ale także:
- rytm,
- napięcie,
- spójność,
- dojrzałość,
- kruchość,
- agresywność zmian,
- ambiwalencję,
- stabilność,
- gęstość semantyczną,
- tożsamość.

Część z tych cech nie jest łatwa do uchwycenia pojedynczą metryką, ale może być widoczna po połączeniu:

- cech statycznych,
- historii zmian,
- sygnałów semantycznych z JEV,
- interpretacji mocniejszego LLM.

Jeśli zbudujemy dobry wektor stanu, można z niego tworzyć obraz, który:
- różni się istotnie między repozytoriami,
- zachowuje pewną spójność między kolejnymi snapshotami tego samego repo,
- daje się porównywać,
- potrafi ujawnić zmiany charakteru projektu.

---

# 7. Architektura systemu

```text
repo path / repo snapshot
        │
        ▼
┌───────────────────────────┐
│ Repository Feature Layer  │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ Semantic Interpretation   │
│ (JEV + optional strong    │
│  LLM + deterministic      │
│  mappers)                 │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ Emotional State Model     │
│ + Visual Latent Profile   │
└─────────────┬─────────────┘
              ▼
  ┌────────────────────┬────────────────────┐
  ▼                    ▼                    │
live renderer    prompt composer            │
  │                    │                    │
  ▼                    ▼                    │
live image/scene   image-gen model          │
                       │                    │
                       ▼                    │
                 final portrait             │
```

---

# 8. Warstwy systemu

## 8.1. Repository Feature Layer

Ta warstwa wyciąga sygnały z repo.

### Cechy statyczne
- liczba plików,
- liczba katalogów,
- rozkład języków,
- wielkość repo,
- średnia wielkość pliku,
- stopień modularności,
- import graph / dependency graph,
- coupling,
- test presence,
- config density,
- docs presence.

### Cechy jakościowe / strukturalne
- poziom spójności namingowej,
- regularność struktury katalogów,
- obecność wzorców architektonicznych,
- liczba entry points,
- poziom koncentracji logiki,
- rozproszenie odpowiedzialności,
- gęstość komentarzy,
- sygnały legacy,
- ślady eksperymentów / prototypowości.

### Cechy historyczne
- liczba commitów,
- tempo zmian,
- burstiness,
- liczba autorów,
- rytm zmian,
- zmienność obszarów repo,
- częstość refaktorów vs feature work,
- częstość rollbacków / hotfix-like zmian,
- stabilność branchy.

### Cechy dynamiczne / opcjonalne
- test health,
- build success,
- linter issues,
- CI flakiness,
- change churn,
- hotspoty.

### Cechy semantyczne z zawartości
- charakter README,
- ton dokumentacji,
- „język” kodu i komentarzy,
- nazewnictwo modułów,
- rodzaj domeny biznesowej,
- poziom formalności / improwizacji.

---

## 8.2. Semantic Interpretation Layer

To kluczowa warstwa.

Jej rolą jest zamiana repo na **profile semantyczne i emocjonalne**.

### Rola JEV
JEV jest używany jako zestaw sensorów, np.:

- `Score coherence`
- `Score tension`
- `Score maturity`
- `Score volatility`
- `Score elegance`
- `Score fragility`
- `Score internal conflict`
- `Noul appears_experimental`
- `Noul feels_overloaded`
- `Noul feels_under_control`
- `Choice temperament`
- `Choice visual_tone`
- `Choice energy_profile`
- `Choice behavioral_mode`

### Rola mocniejszego LLM
Silniejszy model może:
- podsumować charakter repo,
- wykryć bardziej złożone wzorce,
- syntetyzować opis wizualny,
- pomóc w wyborze ważniejszych cech,
- generować lepsze prompt specs dla image-gen.

### Rola deterministyczna
Nie wszystko powinno przechodzić przez model.

Część sygnałów jest mechaniczna:
- size,
- churn,
- graph stats,
- test presence,
- complexity proxies.

Te sygnały stają się „surowcem”, z którego dopiero budowana jest warstwa interpretacji.

---

# 9. Emotional State Model

System powinien zbudować **jawny model stanu emocjonalnego / semantycznego**, a nie tylko prompt końcowy.

Przykład:

```json
{
  "coherence": 0.81,
  "volatility": 0.43,
  "maturity": 0.72,
  "fragility": 0.37,
  "novelty": 0.64,
  "pressure": 0.22,
  "discipline": 0.77,
  "chaos": 0.28,
  "identity_strength": 0.69,
  "internal_conflict": 0.31,
  "temperament": {
    "calm": 0.41,
    "restless": 0.18,
    "proud": 0.16,
    "anxious": 0.07,
    "mysterious": 0.18
  }
}
```

Ten model powinien być trwałym artefaktem.

---

# 10. Visual Latent Profile

To najważniejsza warstwa dla uniknięcia naiwnych mapowań.

Nie chcemy:
- ręcznych stereotypów,
- twardych ifów z symbolicznymi maskami,
- arbitralnego przypisania jednej cechy do jednego rekwizytu.

Chcemy coś bliższego:

```text
semantic state vector
   ↓
latent visual parameters
   ↓
form, silhouette, texture, rhythm, palette, composition, density
```

## 10.1. Parametry latentne

Przykłady latentnych osi:
- form complexity,
- symmetry,
- fragmentation,
- tension curvature,
- texture density,
- luminosity,
- contrast,
- softness vs sharpness,
- visual rhythm,
- compositional balance,
- materiality,
- ornamental load,
- biological vs mechanical tendency,
- opacity,
- layering.

To NIE są jeszcze „robot” albo „potwór”.  
To są bardziej fundamentalne parametry wizualne.

### Przykład idei
Repo może mieć:
- wysoką spójność,
- średnią złożoność,
- dużą dojrzałość,
- niskie napięcie,
- średnią nowość.

To może prowadzić do:
- stabilnych proporcji,
- niskiej fragmentacji,
- uporządkowanego rytmu,
- wyważonej kompozycji,
- ograniczonej palety.

Ale czy z tego wyjdzie istota, maska, aura, krajobraz czy konstrukcja geometryczna — to zależy od trybu renderingu.

---

# 11. Dwa tryby reprezentacji

## 11.1. Character mode

Repo jest przedstawiane jako „byt”.

### Założenia
- wygląd powinien wynikać z cech latentnych,
- unikać bezpośrednich stereotypów,
- zachować tożsamość między snapshotami,
- móc delikatnie zmieniać się wraz z ewolucją repo.

### Elementy możliwe do modelowania
- sylwetka,
- proporcje,
- postura,
- liczba segmentów,
- poziom symetrii,
- gęstość detali,
- rodzaj powierzchni,
- dynamika „aury”,
- ornament,
- materiał,
- maska/twarz,
- stopień organiczności vs mechaniczności.

### Ważne
Character mode nie musi oznaczać:
- ludzkiej twarzy,
- słodkiego maskota,
- dosłownej personifikacji.

Może to być:
- biomechaniczny byt,
- architektoniczna postać,
- duch-konstrukcja,
- semantyczny avatar.

---

## 11.2. Abstract mode

Repo jest przedstawiane jako abstrakcyjna kompozycja.

### Możliwe formy
- pole energetyczne,
- krajobraz,
- chmura strukturalna,
- płótno emocjonalne,
- geometryczna kompozycja,
- rzeźba światła,
- topografia,
- mandala,
- noise-field.

### Elementy możliwe do modelowania
- układ mas,
- gradienty,
- ruch / puls,
- gęstość,
- przepływ,
- napięcia geometryczne,
- tekstura,
- dystrybucja światła,
- ostrość / mglistość,
- stabilność kompozycji.

---

# 12. Dwa tryby generowania

## 12.1. Live mode

### Cel
Bezpośrednio renderować wynik lokalnie lub w aplikacji webowej.

### Zalety
- natychmiastowość,
- możliwość animacji,
- możliwość porównania dwóch snapshotów,
- możliwość interakcji,
- łatwość aktualizacji po każdym commicie.

### Technologie
- Three.js,
- React + WebGL,
- p5.js / Canvas,
- shaders,
- procedural geometry,
- particle systems,
- SVG / 2D generative rendering.

### Uwaga
Live mode nie musi wyglądać „jak obraz AI”.
Może być bardziej:
- instrumentalny,
- proceduralny,
- rzeźbiarski,
- dynamiczny.

---

## 12.2. Prompt to image-gen LLM

### Cel
Generować pełny obraz końcowy przez model generujący obrazy.

### Pipeline
1. build emotional state,
2. build visual latent profile,
3. create visual spec,
4. synthesize prompt,
5. send to image model,
6. receive final image,
7. optional critique loop.

### Zalety
- bardziej „artystyczny” look,
- bogatsza tekstura,
- łatwiejsze tworzenie wysokiej jakości ilustracji,
- możliwość uzyskania gotowych obrazów do prezentacji.

### Ryzyka
- model może ignorować część subtelnych cech,
- prompt może zbyt silnie narzucać styl,
- trudniej zachować spójność między kolejnymi snapshotami.

---

# 13. Problem „emergent appearance”

To jest najważniejszy problem badawczy systemu.

Jak doprowadzić do tego, żeby wygląd:
- nie był ręcznie opisanym stereotypem,
- ale jednak był sterowalny i powtarzalny?

## Proponowane podejście

### Poziom 1 — jawne cechy semantyczne
Repo → emotional state vector.

### Poziom 2 — latent visual grammar
Emotional state → visual latent profile.

### Poziom 3 — renderer
Visual latent profile → final form.

To oznacza, że zamiast:

```text
fragility > 0.8 → broken glass body
```

stosujemy coś bliższego:
- `fragility` wpływa na kilka latentnych osi,
- one razem wpływają na poziom pękniętości, przejrzystości, segmentacji, delikatności i rytmu formy,
- finalny wygląd wyłania się z wielu czynników jednocześnie.

---

# 14. MVP

MVP ma udowodnić trzy rzeczy:

1. da się z repo zbudować stabilny **emotional state vector**,
2. da się wygenerować z niego **charakterystyczny profil wizualny**,
3. można pokazać to w dwóch niezależnych trybach:
   - live
   - prompt_to_image_gen_llm

---

## 14.1. MVP scope

### Inputs
- repo path
- opcjonalnie git history depth
- opcjonalnie current branch / commit

### Outputs
- profile JSON
- profile summary markdown
- live rendering
- one final image via image-gen LLM

### Representation modes
- `character`
- `abstract`

### Generation modes
- `live`
- `prompt_to_image_gen_llm`

W MVP nie trzeba robić pełnej animacji czasu ani porównania branchy.

---

## 14.2. MVP feature extraction

Minimum:
- file count
- language distribution
- directory structure metrics
- test presence
- docs presence
- code churn from recent commits
- hotspot modules
- change velocity
- basic complexity proxies
- simple dependency graph stats
- README / top docs summary
- semantic codebase summary from LLM

---

## 14.3. MVP emotional sensors

Minimalny zestaw:
- coherence
- maturity
- volatility
- fragility
- novelty
- discipline
- tension
- chaos
- identity_strength
- internal_conflict

Plus 2–3 `Choice`:
- temperament
- energy_profile
- visual_tone

---

## 14.4. MVP visual latent profile

Minimalne latentne osie:
- complexity
- symmetry
- fragmentation
- luminosity
- softness
- contrast
- ornament
- materiality
- balance
- rhythm

---

## 14.5. MVP live mode

### Character
Prosta generatywna postać 2D lub uproszczona 3D:
- sylwetka,
- proporcje,
- aura,
- ornament,
- kolorystyka,
- struktura powierzchni.

### Abstract
Abstrakcyjna kompozycja:
- warstwy,
- pole cząstek,
- gradient,
- rytm linii,
- plamy / formy / światło.

### Ważne
To nie musi być wizualnie perfekcyjne.
MVP ma pokazać, że profil wpływa na wygląd w sposób:
- wyraźny,
- stabilny,
- różnicujący różne repo.

---

## 14.6. MVP prompt-to-image mode

Pipeline:
1. profile JSON,
2. short explanation,
3. visual latent description,
4. mode = character/abstract,
5. prompt composer,
6. image generation call.

Wynik:
- 1 obraz końcowy,
- plus prompt zapisany jako artefakt.

---

## 14.7. MVP artifacts

```text
profile.json
summary.md
live-preview.html
portrait-character.png
portrait-abstract.png
portrait-prompt.txt
```

Nie wszystko musi być generowane w jednym runie; użytkownik może wybrać.

---

# 15. MVP architecture

```text
repo/
  ↓
feature extraction
  ↓
repository summary
  ↓
JEV sensor bank
  ↓
emotional state model
  ↓
visual latent mapper
  ↓
┌──────────────────────────┬─────────────────────────┐
│ live renderer            │ prompt composer         │
└───────────────┬──────────┴──────────────┬──────────┘
                ▼                         ▼
      html/webgl/canvas scene     image-gen LLM
```

---

# 16. Post-MVP

Post-MVP powinno pójść w czterech kierunkach:
1. jakość interpretacji,
2. jakość i spójność wizualna,
3. wymiar czasowy,
4. eksploracja i porównania.

---

## 16.1. Time dimension

Najważniejszy rozwój.

System nie patrzy tylko na jeden snapshot repo, ale na serię snapshotów:

```text
commit_1 → commit_2 → commit_3 → ... → commit_n
```

Dzięki temu można generować:
- ewolucję portretu,
- animację emocjonalną,
- galerię epok projektu,
- porównanie branchy,
- wykrywanie nagłych zmian charakteru repo.

---

## 16.2. Identity persistence

Repo powinno zachowywać pewną tożsamość między snapshotami.

To bardzo ważne w character mode.

Jeśli repo ma już „istotę”, to kolejne commity powinny:
- nie resetować całkowicie jej wyglądu,
- ale modyfikować ją subtelnie lub znacząco zależnie od zmian.

To wymaga:
- seed identity,
- stable latent anchors,
- consistency prompting,
- optional stored reference portrait.

---

## 16.3. Multi-portrait system

Post-MVP może generować różne portrety:
- **current portrait**
- **historical portrait**
- **branch portrait**
- **conflict portrait**
- **release portrait**
- **drift portrait**

---

## 16.4. Comparative mode

Porównanie dwóch repo lub dwóch branchy.

Output:
- delta of emotional state,
- delta of visual latent profile,
- split-view portraits,
- merged contrast portrait.

---

## 16.5. Narrative mode

System może tworzyć krótkie opisy typu:

> „Repo retains a disciplined core, but recent bursts of change increased its volatility and gave it a more restless surface structure.”

To nie ma być tylko poetycki tekst — ma być explanation layer między danymi a obrazem.

---

## 16.6. Interactive exploration

Użytkownik może:
- kliknąć cechę i zobaczyć, które sygnały na nią wpłynęły,
- zobaczyć, dlaczego obraz ma taki charakter,
- przełączyć representation mode,
- przełączyć generation mode,
- porównać kilka commitów,
- zablokować pewne latentne osie i obserwować różnice.

---

## 16.7. Style packs

Post-MVP może wspierać style:
- sumi-e,
- brutalist,
- cybernetic,
- biomorphic,
- minimalist geometric,
- dreamlike painterly,
- technical illustration.

Ważne:
styl nie zmienia semantycznej tożsamości, tylko sposób przedstawienia.

---

# 17. Repository feature extraction — szczegóły

## 17.1. Deterministic extractors
- LOC
- files
- directory depth
- graph density
- fan-in/fan-out
- entropy of file sizes
- churn entropy
- language diversity
- test ratio
- docs ratio
- commit frequency

## 17.2. Code intelligence extractors
- symbol inventory
- architectural zones
- repeated patterns
- anti-pattern hints
- dependency bottlenecks
- hotspot maps

## 17.3. LLM summaries
LLM może tworzyć:
- repo summary,
- module summary,
- architectural summary,
- change summary,
- historical summary.

Te podsumowania stają się inputem dla JEV.

---

# 18. JEV sensor bank

Sondy JEV powinny być wersjonowane.

Przykłady:

## Score
- coherence
- maturity
- volatility
- fragility
- elegance
- tension
- discipline
- internal_conflict
- identity_strength
- weirdness
- pressure
- maintainability_feeling

## Noul
- appears_experimental
- feels_stable
- feels_overloaded
- feels_under_control
- feels_fragmented
- feels_unfinished
- feels_resilient

## Choice
### temperament
- calm
- restless
- disciplined
- playful
- brooding
- proud
- anxious
- mysterious

### visual_tone
- luminous
- austere
- dense
- delicate
- monumental
- fractured
- flowing

### energy_profile
- static
- pulsing
- coiled
- diffused
- turbulent
- focused

---

# 19. Visual latent mapper

Ta warstwa tłumaczy emotional state na latentne parametry wizualne.

Nie powinna być zbiorem ifów, tylko funkcją / systemem wag.

Możliwe implementacje:

## A. Hand-designed weighted mapper (MVP)
Najprostsza wersja:
- macierz wag,
- kilka nieliniowości,
- normalizacja,
- noise seeds.

To nie jest to samo co „old repo = monster”.
To tylko matematyczne mapowanie cech na parametry wizualne.

## B. Learned mapper (Post-MVP)
Możliwa późniejsza ścieżka:
- dataset wielu repo,
- clustering,
- latent alignment,
- possibly human preference tuning.

## C. Hybrid mapper
- deterministyczne jądro
- plus LLM-assisted refinement
- plus style-pack transformations

---

# 20. Prompt composer

W trybie image-gen system nie powinien po prostu wysyłać:

```text
draw a repository character
```

Prompt composer powinien tworzyć:

1. semantic identity block,
2. emotional state block,
3. visual latent profile block,
4. selected representation mode,
5. selected style pack,
6. consistency constraints,
7. negative constraints.

### Example structure

```text
Create a visual portrait of a software repository as an emergent character.
Do not use clichéd stereotypes or literal programmer symbols.
The character should emerge from the following latent traits:

coherence: high
volatility: medium-low
identity_strength: high
fragility: low
novelty: medium
tension: medium-low
discipline: high

visual latent profile:
- complexity: moderate
- symmetry: medium-high
- fragmentation: low
- luminosity: medium
- softness: low-medium
- ornament: restrained
- materiality: precise, layered, slightly mechanical
- rhythm: stable with subtle pulse

The result should feel calm, self-contained, durable, deliberate and quietly intelligent.
...
```

---

# 21. Live renderer

## 21.1. Character live renderer
Możliwe podejście:
- procedural skeleton,
- body segmentation,
- symmetry distortion,
- layered materials,
- aura particles,
- posture inference,
- animated breathing/pulse.

## 21.2. Abstract live renderer
Możliwe podejście:
- flow field,
- particle cloud,
- layered noise,
- spline field,
- geometric masses,
- light field,
- topology deformation.

---

# 22. CLI / UX

Przykładowe użycie:

```bash
repo-portrait analyze /path/to/repo
```

```bash
repo-portrait render \
  /path/to/repo \
  --representation character \
  --mode live
```

```bash
repo-portrait render \
  /path/to/repo \
  --representation abstract \
  --mode prompt-to-image
```

```bash
repo-portrait compare \
  /path/to/repo \
  --commit abc123 \
  --commit def456
```

---

# 23. Output artifacts

## Required
- `profile.json`
- `summary.md`

## Live mode
- `live-preview.html`
- `live-state.json`

## Prompt mode
- `prompt.txt`
- `portrait.png`
- optional `critique.json`

## Optional
- `timeline.json`
- `comparison.json`
- `identity-seed.json`

---

# 24. MVP technology recommendation

## Core
Python 3.12+

## Extraction
- GitPython or subprocess git
- tree-sitter optional
- ripgrep optional
- networkx
- pydantic
- polars/pandas

## Live frontend
- minimal HTML/JS
- Three.js or p5.js
- Plotly optional only for debug visuals

## LLMs
- JEV for structured semantic sensors
- stronger LLM for synthesis
- OpenRouter optional for:
  - repo summarization
  - prompt enhancement
  - critique/reflection
  - model routing

## Image generation
- image-gen API backend configurable

---

# 25. MVP — Definition of Done

MVP jest gotowy, jeśli:

1. użytkownik wskazuje repo,
2. system wyciąga podstawowe cechy,
3. system buduje emotional state vector,
4. system buduje visual latent profile,
5. system potrafi wygenerować:
   - `character` live
   - `abstract` live
   - `character` prompt-to-image
   - `abstract` prompt-to-image
6. system zapisuje artefakty,
7. dwa różne repozytoria dają wyraźnie różne portrety,
8. ten sam snapshot repo generuje stabilnie podobny profil,
9. użytkownik może prześledzić z grubsza, skąd wzięły się cechy końcowe.

---

# 26. Post-MVP — Definition of Done

Post-MVP core jest gotowy, jeśli:

1. system obsługuje serię commitów,
2. zachowuje tożsamość wizualną między snapshotami,
3. potrafi porównać branch A i branch B,
4. potrafi wygenerować animację ewolucji,
5. wspiera style packs,
6. ma interactive explanation mode,
7. wspiera critique loop dla prompt-to-image,
8. daje się używać jako „visual observatory” repo.

---

# 27. Explainability

To ważne, bo system łatwo mógłby stać się tylko generatorem ładnych obrazków.

Dlatego przy każdym porciecie powinno dać się zobaczyć:

- emotional state,
- visual latent profile,
- top contributing repository signals,
- top JEV sensors,
- optional textual explanation.

Przykład:

```text
Why does this portrait look stable and layered?
- high coherence
- high discipline
- low fragmentation
- strong identity_strength
- moderate but not chaotic change velocity
```

---

# 28. Ryzyka

## 28.1. Visual cliché trap
System zacznie generować memiczne, zbyt dosłowne personifikacje.

Mitigacja:
- zakaz literalnych stereotypów w prompt composer,
- latent mapping instead of symbolic mapping,
- critique layer.

## 28.2. Weak differentiation
Różne repo będą wyglądały podobnie.

Mitigacja:
- większy zestaw cech,
- history features,
- stronger latent mapper,
- consistency + diversity tests.

## 28.3. Random pretty pictures
Obraz będzie ładny, ale niepowiązany z repo.

Mitigacja:
- profile JSON jako obowiązkowy artefakt,
- explainability,
- contrast tests between repos,
- invariance tests for same snapshot.

## 28.4. Overfitting to one style
Całość zacznie wyglądać zbyt podobnie stylistycznie.

Mitigacja:
- oddzielenie stylu od semantycznej tożsamości,
- style packs,
- testy A/B.

---

# 29. Test plan

## Test 1 — Different repos
Dwa bardzo różne repo powinny dać wyraźnie różne profile.

## Test 2 — Same repo, same snapshot
Powinno dawać podobny profil.

## Test 3 — Same repo, nearby commits
Powinno dawać podobną tożsamość z umiarkowanym dryfem.

## Test 4 — Same repo, major architectural change
Powinno dawać istotnie odmieniony profil.

## Test 5 — Character vs abstract
Dwa tryby powinny zachowywać wspólną tożsamość semantyczną, ale inne medium.

## Test 6 — Live vs prompt
Dwa tryby generacji powinny reprezentować podobny rdzeń charakteru.

---

# 30. Suggested repo structure

```text
repo-portrait/
├── pyproject.toml
├── README.md
├── docs/
│   ├── architecture.md
│   ├── sensors.md
│   ├── feature-extraction.md
│   ├── visual-latent-profile.md
│   └── prompting.md
├── src/
│   └── repo_portrait/
│       ├── cli.py
│       ├── config.py
│       ├── schemas/
│       │   ├── profile.py
│       │   ├── features.py
│       │   ├── latent.py
│       │   └── render.py
│       ├── ingest/
│       │   ├── repository.py
│       │   ├── git_history.py
│       │   └── docs_summary.py
│       ├── features/
│       │   ├── static.py
│       │   ├── graph.py
│       │   ├── history.py
│       │   └── semantics.py
│       ├── jev/
│       │   ├── client.py
│       │   ├── sensors.py
│       │   └── runner.py
│       ├── interpretation/
│       │   ├── emotional_model.py
│       │   ├── latent_mapper.py
│       │   └── explanations.py
│       ├── rendering/
│       │   ├── live_character.py
│       │   ├── live_abstract.py
│       │   ├── prompt_composer.py
│       │   ├── image_backend.py
│       │   └── critique.py
│       ├── compare/
│       │   ├── snapshots.py
│       │   └── branches.py
│       └── reporting/
│           ├── markdown.py
│           ├── html.py
│           └── artifacts.py
└── tests/
```

---

# 31. Recommended build order

## Phase 0
Fixtures:
- 3–5 repozytoriów testowych,
- snapshoty dla co najmniej dwóch z nich.

## Phase 1
Feature extraction:
- static + history + summary.

## Phase 2
JEV sensor bank:
- emotional state model.

## Phase 3
Visual latent mapper:
- MVP weighted mapper.

## Phase 4
Live renderers:
- abstract first,
- then simplified character.

## Phase 5
Prompt mode:
- prompt composer,
- image backend,
- artifacts.

## Phase 6
Explainability:
- summary + why-this-look.

## Phase 7
Comparisons / time:
- post-MVP.

---

# 32. Najważniejsza zasada końcowa

Nie budujemy:
> „AI, które zmyśla śmieszne maskotki dla repo”.

Budujemy:
> **system, który odkrywa semantyczno-emocjonalny stan repo i przedstawia go wizualnie w sposób emergentny, spójny i porównywalny.**

JEV jest tutaj:
- sensorem znaczenia,
- dostawcą interpretowalnych sygnałów,
- częścią warstwy semantycznej.

Silniejsze LLM-y i image models są:
- warstwą syntezy,
- warstwą wyrazu,
- warstwą estetycznej realizacji.

Tożsamość systemu leży w:
- modelu cech,
- emotional state vector,
- visual latent profile,
- emergent mapping.

---

# 33. TL;DR

## MVP
- analiza pojedynczego repo,
- emotional state vector,
- visual latent profile,
- dwa representation modes: `character`, `abstract`,
- dwa generation modes: `live`, `prompt_to_image_gen_llm`,
- artefakty i explainability.

## Post-MVP
- ewolucja w czasie,
- identity persistence,
- compare mode,
- branch portraits,
- critique loop,
- style packs,
- interactive exploration.

## Core philosophy
- zero naiwnych stereotypów,
- wygląd ma się wyłaniać z analizy,
- JEV dostarcza warstwę semantycznych sensorów,
- obraz jest końcowym ucieleśnieniem profilu, nie ręcznym żartem.

