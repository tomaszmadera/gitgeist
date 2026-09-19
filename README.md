# Gitgeist

System do przedstawiania repozytorium w formie emocjonalnego portretu wizualnego.

## Status

MVP ukończone (0.3.0): konsolowy punkt wejścia `gitgeist` (`analyze`, `render`) oraz pełny pipeline: sensory regułowe, model emocjonalny, profil wizualny, explainability i renderowanie `live` / `prompt-to-image`.

## Wymagania

- Python >= 3.11 (rekomendowany 3.14)
- Środowisko lokalne: `venv`

## Instalacja i uruchomienie lokalne

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Przykłady poniżej wywołują `.venv/bin/gitgeist` bezpośrednio; po `source .venv/bin/activate` wystarczy `gitgeist`.

## Użycie

### Analiza repozytorium

```bash
.venv/bin/gitgeist analyze /sciezka/do/repo
```

Tworzy `profile.json` i `summary.md` w `./gitgeist-output/<nazwa-repo>` (domyślnie poza analizowanym repozytorium). Własny katalog: `-o DIR`.

### Portret live (HTML, bez sieci)

```bash
.venv/bin/gitgeist render /sciezka/do/repo --representation character --mode live
.venv/bin/gitgeist render /sciezka/do/repo --representation abstract --mode live
```

Dodaje `live-preview.html` i `live-state.json` obok pary wymaganej.

### Portret z generatora obrazu

Tryb offline, deterministyczny (ten sam prompt daje identyczne bajty `portrait.png`):

```bash
.venv/bin/gitgeist render /sciezka/do/repo --representation character --mode prompt-to-image
```

Realna generacja przez API zgodne z OpenAI:

```bash
export GITGEIST_IMAGE_API_KEY="..."
.venv/bin/gitgeist render /sciezka/do/repo --representation character --mode prompt-to-image --backend openai-compatible
```

Bez klucza polecenie kończy się błędem z kodem 1 (nie ma cichego przełączenia na backend `fake`). Oba wywołania tworzą `prompt.txt` i `portrait.png`. Opcja `--backend` dotyczy wyłącznie `--mode prompt-to-image`.

### Test determinizmu na własnym repo

```bash
.venv/bin/gitgeist analyze /sciezka/do/repo -o /tmp/gg-a
.venv/bin/gitgeist analyze /sciezka/do/repo -o /tmp/gg-b
diff /tmp/gg-a/summary.md /tmp/gg-b/summary.md
```

Ten sam stan repo daje bajt w bajt identyczny `summary.md`; `profile.json` różni się wyłącznie polami ulotnymi (`calculated_at`, `extracted_at`, `source_commit`, `engine_version`).

## Testy i weryfikacja

```bash
.venv/bin/pytest tests
```

## Dokumentacja

- `docs/product/` - zatwierdzone wymagania produktu.
- `docs/features/` - kontrakty zachowania funkcji.
- `docs/architecture/` - decyzje i dokumentacja architektury.
- `docs/development/` - instrukcje dla osób rozwijających projekt.
- `docs/operations/` - runbooki wdrożenia i utrzymania.

## Praca z agentami

Zasady pracy znajdują się w [`AGENTS.md`](AGENTS.md), a aktualny stos i polecenia projektu w [`.agents/project-profile.yaml`](.agents/project-profile.yaml). Postęp większych zadań jest w `.agents/tasks/<id>/task.md`, plan w `.agents/tasks/<id>/plan.md`, a kontrakt zachowania w `docs/features/<nazwa>/spec.md`.

Używaj `implement` dla standardowej i większej implementacji, `systematic-debugging` dla nieoczywistych błędów oraz `code-review` do przeglądu bez modyfikowania zmian. W poleceniu dla agenta podaj nazwę skilla, kanoniczne źródło wymagań, zakres, wyłączenia i kryteria akceptacji.
