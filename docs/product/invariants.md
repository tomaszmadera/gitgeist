# Rejestr inwariantów produktu

Ten rejestr jest kanonicznym wykazem inwariantów produktu Gitgeist. Status `met` oznacza inwariant spełniony z aktualnym dowodem, `unmet` oznacza status niespełniony, a `deferred-by-decision` oznacza odroczenie na mocy jawnej decyzji użytkownika lub ADR. Sam rejestr i raportowanie nie zmieniają statusu żadnego wpisu.

## Wpisy

### jev-real-integration

statement: Dokument produktu docs/product/emotional-repository-portrait-system.md wymaga JEV w warstwie Semantic Interpretation Layer i w Phase 2, podczas gdy obecna implementacja dostarcza wyłącznie deterministyczne reguły nazwane bankiem sensorów JEV. Znaczenie docs/features/feature-extraction/spec.md i docs/features/emotional-state-model/spec.md pozostaje w konflikcie z tym wymaganiem produktowym.
source: docs/product/emotional-repository-portrait-system.md
blocking_scope: Nie wolno twierdzić, że produkt realizuje pełną semantyczną rolę JEV, ani że wszystkie kluczowe założenia MVP są spełnione. Zakres nie blokuje ukończenia niezależnych zadań, które raportują tę lukę wprost.
status: unmet
acceptance: Prawdziwa integracja JEV w ścieżkach produktowych wymaganych przez dokument produktu.
evidence:
related_specs: docs/features/feature-extraction/spec.md, docs/features/emotional-state-model/spec.md
decision:
