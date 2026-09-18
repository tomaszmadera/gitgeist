# Feature extraction

This file is the behavioral contract for the deterministic feature extraction layer of Gitgeist. Agents implement from it. Do not put execution progress, file checklists, or architecture history here.

Path: `docs/features/feature-extraction/spec.md`

## Goal

Zbudować moduł deterministycznej ekstrakcji cech repozytorium (Warstwa 1 w architekturze Gitgeist) oraz zestaw syntetycznych repozytoriów testowych (fixtures). Moduł analizuje repozytorium i tworzy ustrukturyzowany profil danych (`RepositoryFeatures`) zawierający cechy statyczne struktury plików, metryki historii Git oraz podsumowanie dokumentacji.

## Related requirements

- Specyfikacja produktu: [docs/product/emotional-repository-portrait-system.md](file:///F:/projects/gitgeist/docs/product/emotional-repository-portrait-system.md#L279-L334) (Sekcja 8.1 - Repository Feature Layer, Sekcja 14.2 - MVP feature extraction, Sekcja 31 - Phase 0 i Phase 1).

## Scope

1. **Syntetyczne fixtures testowe (`tests/fixtures/`)**:
   - `minimal-repo`: proste repozytorium (2-3 pliki, brak testów, 1-2 commity).
   - `clean-modular-repo`: repozytorium o ustrukturyzowanej architekturze (`src/`, `tests/`, `docs/`, `README.md`, testy jednostkowe, czysta historia).
   - `legacy-chaotic-repo`: repozytorium o dużej głębokości katalogów, wymieszanych rozszerzeniach, obecności TODO/FIXME, intensywnej historii zmian i hotspotach.
   - Skrypt/narzędzie pomocnicze lub fixture generator w testach do odtworzenia historii Git w fixtures.
2. **Modele schematów danych Pydantic (`src/gitgeist/schemas/features.py`)**:
   - `StaticFeatures`: liczba plików, liczba katalogów, maksymalna głębokość, rozkład języków/rozszerzeń, łączny rozmiar, średni rozmiar pliku, metryki obecności testów/dokumentacji/konfiguracji, liczba TODO/FIXME.
   - `GitHistoryFeatures`: liczba commitów, unikalni autorzy, data pierwszego i ostatniego commitu, wiek repozytorium (dni), tempo zmian (velocity), sumaryczny churn (dodane/usunięte linie), lista hotspotów (najczęściej modyfikowane pliki).
   - `DocsSummaryFeatures`: obecność README, długość README, fragment początkowy, typ licencji (jeśli występuje).
   - `RepositoryFeatures`: zbiorczy model łączący powyższe, ze znacznikiem czasu ekstrakcji i ścieżką repozytorium.
3. **Ingestory repozytorium (`src/gitgeist/ingest/`)**:
   - `repository.py`: skanowanie drzewa plików z pomijaniem katalogów ignorowanych (`.git`, `.venv`, `node_modules`, itp.).
   - `git_history.py`: analiza logu commitów Git przez komendy `git log` w sposób deterministyczny.
   - `docs_summary.py`: wyszukiwanie i odczyt README oraz licencji.
4. **Moduły kalkulacji cech (`src/gitgeist/features/`)**:
   - `static.py`: agregacja cech statycznych z drzewa plików.
   - `history.py`: agregacja cech historycznych z historii Git.
   - `extractor.py`: fasada integrująca proces ekstrakcji do `RepositoryFeatures`.

## Non-goals

- Interpretacja semantyczna / JEV / wyznaczanie wektora emocjonalnego (Warstwa 2 - odłożona do Fazy 2).
- Mapowanie na parametry wizualne (Warstwa 3 - odłożona do Fazy 3).
- Generowanie obrazów lub renderowanie live (Warstwa 4 - odłożona do Fazy 4 i 5).
- Wywoływanie zewnętrznych modeli językowych (LLM) podczas ekstrakcji deterministycznej.

## Behaviour

- Funkcja `extract_features(repo_path: Path) -> RepositoryFeatures` przyjmuje ścieżkę do katalogu i zwraca w pełni zwalidowany model `RepositoryFeatures`.
- Jeśli ścieżka nie istnieje lub nie jest katalogiem, funkcja podnosi `FileNotFoundError` lub `NotADirectoryError`.
- Jeśli ścieżka jest katalogiem, ale nie jest repozytorium Git (brak `.git` lub błąd `git rev-parse`), moduł generuje cechy statyczne i dokumentacji, a dla cech historii Git zwraca pusty/domyślny profil `GitHistoryFeatures(is_git_repo=False, commit_count=0, ...)`.
- Skanowanie plików ściśle ignoruje katalogi `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.eggs`, `dist`, `build`.

## Business rules

1. **Determinizm**: Wielokrotne uruchomienie ekstrakcji na niezmienionym repozytorium musi zwrócić identyczne wartości metryk (z wyjątkiem znacznika czasu wykonania ekstrakcji).
2. **Bezpieczeństwo**: Operacje odczytu nie mogą modyfikować ani tworzyć plików w badanym repozytorium (read-only analysis).
3. **Odporność na błędy kodowania**: Pliki binarne oraz pliki o niestandardowym kodowaniu znaków nie mogą powodować przerwania analizy statycznej; odczyt tekstu (np. do zliczania TODO) używa obsługi błędów `errors='replace'`.

## Authorization

`none` - biblioteka lokalna bez mechanizmu autoryzacji.

## Data / API

```python
from pathlib import Path
from gitgeist.schemas.features import RepositoryFeatures
from gitgeist.features.extractor import extract_features

features: RepositoryFeatures = extract_features(Path("/path/to/repo"))
```

Model `RepositoryFeatures` musi być serializowalny do formatu JSON za pomocą standardowej metody Pydantic `.model_dump_json()`.

## Edge cases

- Puste repozytorium (0 commitów, brak plików poza `.git`).
- Repozytorium bez commitów (świeżo po `git init`).
- Repozytorium z commitami, ale bez gałęzi (detached HEAD).
- Pliki o bardzo dużych rozmiarach (powyżej 10 MB) - pomijanie analizy tekstu TODO z zachowaniem rozmiaru w metrykach statycznych.
- Katalog bez inicjalizacji Git.

## Errors

- Brak ścieżki lub ścieżka niebędąca katalogiem: jawny wyjątek `ValueError` lub standardowy `FileNotFoundError` / `NotADirectoryError`.
- Błąd wykonania polecenia Git: brak cichego pomijania błędów krytycznych; jeśli katalog jest w Git, błędy polecenia są rejestrowane lub raportowane jako niekompletna historia.

## Acceptance criteria

1. Zestaw syntetycznych fixtures w `tests/fixtures/` posiada co najmniej 3 odmienne konfiguracje repozytoriów.
2. Modele `StaticFeatures`, `GitHistoryFeatures`, `DocsSummaryFeatures`, `RepositoryFeatures` są w pełni zdefiniowane w Pydantic v2.
3. Ekstrakcja na każdym z repozytoriów testowych fixtures działa poprawnie i zwraca poprawnie obliczone metryki.
4. Serializacja do JSON i deserializacja z JSON zachowuje pełną spójność danych.
5. Wszystkie testy jednostkowe i integracyjne przechodzą pomyślnie.

## Required tests

- `tests/test_schemas.py`: testy walidacji i serializacji modeli Pydantic.
- `tests/test_static_features.py`: testy zliczania plików, głębokości katalogów, wykrywania języków i TODO.
- `tests/test_history_features.py`: testy parsowania logów Git, wykrywania commitów, autorów, churnu i hotspotów.
- `tests/test_extractor.py`: testy integracyjne funkcji `extract_features` na repozytoriach testowych (w tym katalog nie-git).

## Relevant SDD / ADR

- [docs/product/emotional-repository-portrait-system.md](file:///F:/projects/gitgeist/docs/product/emotional-repository-portrait-system.md)
