# Instrukcja odtworzenia lokalnego harnessu Gitgeist

Pakiet `gitgeist-local-harness.zip` zawiera lokalny harness agentów, reguły pracy, adaptery asystentów, rejestry zadań, snapshoty handoff oraz lekcje dla projektu Gitgeist.

Wszystkie pliki w archiwum są lokalne i ignorowane przez Git (`.gitignore`), dlatego nie są obecne w zdalnym repozytorium.

## 1. Zawartość archiwum
- `AGENTS.md`: Główny podręcznik i konstytucja agentów w projekcie.
- `opencode.json`: Uprawnienia i konfiguracja OpenCode.
- `.agents/`:
  - `engineering.md`, `safety.md`, `project-profile.md`, `project-profile.yaml`: Zasady inżynieryjne, polityka bezpieczeństwa i profil projektu.
  - `environments/`: Wytyczne środowiskowe (Windows, WSL).
  - `rules/`: Nakładki dla agentów (AGY itp.).
  - `templates/`: Szablony specyfikacji, planów i handoffów.
  - `workflows/`: Procedury spec-driven development, small development, investigation itp.
  - `skills/`: Rejestr 19 skilli harnessu (ci, code-review, implement, specification, task-record itp.).
  - `scripts/`: Narzędzia pomocnicze (`validate-config`, `task-status`, `handoff-status`, `taskctl` itp.).
  - `hooks/`: Skrypty hooków i dispatch (`dispatch.py`, `policy.json`, moduł `session_log`).
  - `lessons/`: Baza wyciągniętych lekcji operacyjnych (`index.json` i pozycje w `items/`).
  - `tasks/`: Rejestry zadań (`gitgeist-19-prompt-composer-v2` oraz archiwum).
  - `handoffs/`: Bieżące i archiwalne snapshoty handoff.
  - `.env.example`: Wzór konfiguracji zmiennych środowiskowych harnessu.
- `.claude/`: Konfiguracja hooków i definicje skilli dla Claude Code.
- `.codex/`: Konfiguracja Codex (`config.toml`, `hooks.json`, `README.md`).
- `.grok/`: Konfiguracja Grok (`hooks/quota.json`, skille, `README.md`).
- `.opencode/`: Wtyczki i konfiguracja OpenCode (`plugins/quota.js`, `plugins/safety.js`, `package.json`, `package-lock.json`).

## 2. Pominięte kategorie
- **Sekrety i poświadczenia**: Pliki `.env` oraz `.agents/.env` (klucze API, tokeny Sanctum Hub, hasła, tokeny dostępowe) zostały pominięte ze względów bezpieczeństwa.
- **Środowiska wirtualne i zależności**: `.venv/`, `.opencode/node_modules/`, `src/gitgeist.egg-info/`.
- **Pamięć podręczna (cache)**: `__pycache__/`, pliki `.pyc`, `.pytest_cache/`.
- **Wyniki buildów i artefakty wykonania**: `gitgeist-output/`, `tmp/`.
- **Logi sesji i tymczasowe**: Pliki `.log`.
- **Eksploracyjny inbox**: Katalog `_inbox/`.
- **Śledzony kod i repozytorium**: Katalog `.git/` oraz pliki śledzone w repozytorium gita.

## 3. Zależności zewnętrzne (wymagane na drugim komputerze)
Harness NIE jest w 100% samodzielnym binarium i wymaga zainstalowania następujących komponentów w systemie:
1. **Python 3.11+** (zgodnie z `project-profile.yaml` zalecany Python 3.12-3.14).
2. **Git** (narzędzia `git` lub `git.exe` w PATH).
3. **Pakiety Pythona**: `pytest` oraz instalacja samego projektu w trybie deweloperskim (`pip install -e .`).
4. **Node.js i npm** (opcjonalnie, ale wymagane dla wtyczek OpenCode oraz Codex Context7 MCP):
   - Wtyczki OpenCode wymagają instalacji pakietów npm w `.opencode/`.
   - Context7 MCP wymaga `npx`.
5. **Klucze i poświadczenia**:
   - Jeśli używane są usługi zewnętrzne (np. OpenRouter do generowania obrazów, Personal Data Hub do limitów, Plane API do kanbana), konieczne jest ręczne utworzenie `.env` i `.agents/.env`.

## 4. Procedura instalacji i odtworzenia

### Krok 1: Klonowanie repozytorium
```bash
git clone git@github.com:tomaszmadera/gitgeist.git
cd gitgeist
git checkout docs/stage-6-spec  # lub main / właściwa gałąź
```

### Krok 2: Rozpakowanie archiwum
Rozpakuj zawartość `gitgeist-local-harness.zip` bezpośrednio do głównego katalogu repozytorium:
```powershell
# PowerShell:
Expand-Archive -Path ..\gitgeist-local-harness.zip -DestinationPath . -Force
```
lub w Bashu:
```bash
unzip -o ../gitgeist-local-harness.zip -d .
```

### Krok 3: Konfiguracja venv Pythona
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/WSL:
source .venv/bin/activate

pip install -e .
pip install pytest pytest-mock
```

### Krok 4: Konfiguracja sekretów i środowiska
1. Utwórz `.env` na podstawie `.env.example`:
   ```bash
   cp .env.example .env
   # Uzupełnij ewentualny OPENROUTER_IMAGE_API_KEY
   ```
2. Utwórz `.agents/.env` na podstawie `.agents/.env.example`:
   ```bash
   cp .agents/.env.example .agents/.env
   # Uzupełnij tokeny HUB/Plane/Z.ai jeśli są używane
   ```

### Krok 5: Zależności asystentów (jeśli dotyczy)
Jeśli używasz OpenCode:
```bash
cd .opencode
npm install
cd ..
```

### Krok 6: Weryfikacja działania harnessu
Uruchom walidację harnessu:
```bash
python .agents/scripts/validate-config
```
Oczekiwany rezultat:
`configuration valid: 19 skills, minimal orchestration, Claude Code/Codex/Grok Build/OpenCode adapters`

Sprawdź stan aktywnego zadania:
```bash
python .agents/scripts/task-status
```
Oczekiwany rezultat:
`gitgeist-19-prompt-composer-v2  active  Phase 3.1  5/6 ...`

Sprawdź stan handoffu:
```bash
python .agents/scripts/handoff-status
```

## 5. Bezwzględne ścieżki w notatkach
Archiwalne wpisy w `.agents/handoffs/archive/*.md` oraz w logu zadania `gitgeist-19-prompt-composer-v2/task.md` zawierają odwołania do ścieżek `F:\projects\gitgeist` oraz `/home/tomek/Workspace/gitgeist`.
Wszystkie skrypty harnessu operują dynamicznie na `git rev-parse --show-toplevel` lub ścieżkach względnych, więc zmiana lokalizacji repozytorium nie wpływa na działanie narzędzi. Jednak przy klikaniu linków w archiwalnych notatkach Markdown należy uwzględnić nową ścieżkę projektu.