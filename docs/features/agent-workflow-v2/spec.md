# Agent workflow v2 corrections

This file is the behavioral contract for correcting the Gitgeist agent workflow after the session-efficiency audit. Agents implement from it. Do not put execution progress, file checklists, or architecture history here.

Path: `docs/features/agent-workflow-v2/spec.md`

## Goal

Skrócić drogę agenta do poprawnego rezultatu bez osłabienia kontroli użytkownika nad publikacją, integralności finalnej weryfikacji ani zgodności z intencją produktu. Workflow ma działać przewidywalnie na Windows, WSL i POSIX, ujawniać niespełnione inwarianty produktu oraz przenosić je przez task records i handoffy.

## Related requirements

- `docs/agent-workflow/session-efficiency-review.md`, z korektami faktów zapisanymi w `.agents/tasks/session-efficiency-audit-review/task.md`.
- `_inbox/gitgeist-workflow-improvement-agent-prompt.md`.
- `docs/product/emotional-repository-portrait-system.md#L336-L359`, `#L786-L806`, `#L1390-L1393` i `#L1419-L1468`.
- `docs/features/feature-extraction/spec.md` oraz `docs/features/emotional-state-model/spec.md`, których łączne znaczenie pozostaje w konflikcie z produktowym wymaganiem prawdziwego JEV.
- `.agents/safety.md`, `.agents/workflows/spec-driven-development.md`, `.agents/skills/preflight/SKILL.md`, `.agents/skills/task-close/SKILL.md`, `.agents/skills/handoff/SKILL.md` i `.agents/skills/ci/references/publication.md`.

## Actors

- Użytkownik: ustala cele produktu, zatwierdza spec i plan oraz zachowuje kontrolę nad operacjami zewnętrznymi i destrukcyjnymi.
- Main: klasyfikuje, koordynuje, rozstrzyga źródła prawdy z dowodów i raportuje stan inwariantów.
- Implementer i reviewer: realizują i niezależnie oceniają zatwierdzone etapy zgodnie z obecnym workflow Standard/Large.
- Skrypty harnessu: wykonują deterministyczne kontrole środowiska, konfiguracji, rekordu, subject weryfikacji i publikacji.

## Scope

Obowiązkowy zakres:

1. Przenośne rozwijanie tokenu `{python}` w poleceniach verification do dokładnego interpretera uruchamiającego skrypt harnessu.
2. Proporcjonalny, read-only preflight środowiska i konfiguracji przed edycją produktu, bez powielania `publication-status`.
3. Ochrona dosłownie nazwanego celu użytkownika przed samodzielną podmianą na podobny obiekt.
4. Jawne rozstrzyganie konfliktu źródeł prawdy oraz wersjonowany rejestr inwariantów produktu z dowodami akceptacji.
5. Raportowanie statusu dotkniętych inwariantów przy zamknięciu Standard/Large i milestone, bez przedstawiania raportu jako implementacji brakującej funkcji.
6. Handoff przenoszący otwarte inwarianty i nierozstrzygnięte założenia.
7. Affected checks dla etapów oraz dokładnie jeden finalny recorded gate dla przechwyconego verification subject. Wcześniejsze testy bez wiązania z subject nie są finalnym dowodem.
8. Automatyczne testy deterministycznych elementów workflow i jednoznaczne scenariusze ręczne dla reguł wymagających oceny znaczenia.
9. Dokumentacja zachowania na Windows i WSL bez utrwalania konfiguracji konkretnej maszyny lub użytkownika.

Decyzje polityczne pozostające poza obowiązkowym rdzeniem do czasu zatwierdzenia wariantu:

- miejsce kanonicznej implementacji harnessu i sposób synchronizacji do Gitgeist;
- mechanizm opcjonalnej standing publication authorization;
- ewentualna zmiana `.gitignore` w celu śledzenia harnessu;
- automatyczna remediacja dirty worktree przez zmianę `.gitignore`.

## Non-goals

- Integracja prawdziwego modelu JEV od TypeSafe z produktem Gitgeist lub z control plane agenta.
- Zmiana sensorów emocjonalnych, rendererów, CLI albo innego zachowania aplikacji Gitgeist.
- Automatyczne publikowanie, commitowanie, tagowanie, push, release lub deploy w ramach tego zadania. Zakaz commita przekazany przez użytkownika ma pierwszeństwo także po zakończeniu implementacji.
- Traktowanie preflightu jako naprawy konfiguracji SSH, interpretera, venv albo worktree.
- Ponowne wykorzystanie affected check jako finalnego verify bez nowego mechanizmu, który przechwytuje subject przed testem i zachowuje wynik dla tego samego subject.
- Automatyczna zmiana `.gitignore` tylko dlatego, że plik lub katalog blokuje publikację.
- Zastąpienie deterministycznych reguł przez probabilistyczny supervisor.

## Behaviour

### Rozwiązywanie interpretera

- `verification.changed_command` i `verification.full_command` mogą zawierać token `{python}` jako osobny argument.
- Wspólny parser poleceń zastępuje każdy taki argument wartością `sys.executable` po podziale zgodnym z bieżącym systemem. Ta sama reguła obowiązuje Windows, WSL i pozostałe środowiska POSIX.
- Token osadzony wewnątrz innego argumentu nie jest rozwijany. Nieznany wymagany placeholder kończy się jawnym błędem konfiguracji przed uruchomieniem polecenia.
- `verify-changed`, `verify-full` i publication full gate korzystają z jednego zachowania rozwijania, aby nie powstały rozbieżne implementacje.
- Profil Gitgeist używa `{python} -m pytest tests`, nie launchera `py` ani ścieżki specyficznej dla systemu.

### Preflight

- Preflight uruchamia się dla recorded development przed pierwszą edycją produktu i przy resume implementacji. Trivial read-only i bounded analysis mogą go pominąć.
- Kontrola jest read-only i bez sieci. Raportuje:
  - system jako `windows`, `wsl` albo `posix`;
  - bieżący `sys.executable`, jego wersję oraz zgodność z `tooling.python_minimum`;
  - stan zadeklarowanego środowiska lokalnego, w tym czy aktywny interpreter pochodzi z venv, bez zakładania wspólnej przenośności venv między Windows i WSL;
  - możliwość rozwiązania skonfigurowanych poleceń verification oraz dostępność ich pierwszego programu po rozwinięciu `{python}`;
  - repozytorium, branch, upstream i relację ahead/behind, gdy upstream istnieje;
  - tracked dirty, staged i untracked counts oraz nazwy wykrytych katalogów artefaktów projektu.
- Brak upstreamu, nieaktywny venv albo dirty worktree są informacją, dopóki zatwierdzony etap nie wymaga odpowiednio remote, venv albo czystego drzewa.
- Niezgodny Python, nierozwiązywalne wymagane polecenie lub brak repozytorium kończy preflight kodem różnym od zera.
- Preflight nie sprawdza SSH, zdalnych refów, tagów, wersji wydania ani możliwości push. Te dane pozostają własnością `publication-status` uruchamianego dopiero przed ofertą lub autoryzowaną publikacją.
- Wcześniejsze wykrycie blockera jest raportowane jako redukcja reworku. Nie wolno przedstawiać go jako usuniętego czasu konfiguracji albo gwarantowanej oszczędności wall-clock.

### Nazwane cele użytkownika

- Ścieżka, ref, identyfikator, nazwa repozytorium, środowisko albo inny dosłownie nazwany target jest sprawdzany w podanej postaci.
- Brak targetu nie upoważnia do użycia najbliższej nazwy. Podobne kandydaty można wyświetlić jako read-only evidence.
- Podmiana jest dozwolona wyłącznie po potwierdzeniu użytkownika albo na podstawie jednoznacznego, repozytoryjnego mapowania aliasu. Podobieństwo nazwy i istnienie tylko jednego kandydata nie są takim mapowaniem.
- Jeśli dalszy wynik może pozostać poprawnie sparametryzowany bez wyboru targetu, agent może go przygotować i jawnie pozostawić target nierozstrzygnięty. Nie może twierdzić, że wykonał test na celu użytkownika.

### Źródła prawdy i inwarianty produktu

- Dla wymagań produktowych obowiązuje kolejność: bieżąca jawna decyzja użytkownika, zaakceptowana decyzja produktowa lub ADR, kanoniczny dokument produktu, spec funkcji, plan, task record, handoff i dokument analityczny.
- Niższe źródło nie może po cichu zmienić znaczenia wyższego. Konflikt wymaga korekty niższego kontraktu albo jawnej decyzji zapisanej wraz z konsekwencjami.
- `docs/product/invariants.md` przechowuje dla każdego inwariantu: stabilne id, treść, źródło, zakres blokowania, status, kryterium akceptacji, dowód, powiązane specy i ostatnią potwierdzoną decyzję.
- Dozwolone statusy to `met`, `unmet` i `deferred-by-decision`. Status `met` wymaga aktualnego, wykonywalnego dowodu albo jednoznacznego ręcznego kryterium, gdy zachowania nie da się zautomatyzować. Status `deferred-by-decision` wymaga linku do jawnej decyzji użytkownika lub zaakceptowanego ADR.
- Początkowy inwariant JEV ma status `unmet`: dokument produktu wymaga JEV w Semantic Interpretation Layer i w Phase 2, a obecna implementacja dostarcza deterministyczne reguły nazwane bankiem sensorów JEV. Sam rejestr i raport nie zmieniają tego statusu.
- Inwariant JEV blokuje twierdzenie, że produkt realizuje pełną semantyczną rolę JEV albo że wszystkie kluczowe założenia MVP są spełnione. Nie blokuje ukończenia niezależnych zadań, które raportują tę lukę wprost.

### Zamknięcie i raport inwariantów

- Przed zamknięciem Standard/Large lub milestone task-close ustala inwarianty dotknięte przez spec, zmienione ścieżki i deklarowany rezultat.
- Raport `Done` rozróżnia ukończenie tasku od stanu produktu. Wymienia dotknięte `unmet` i `deferred-by-decision` oraz ich dowody.
- Zielone testy lokalnej specyfikacji nie zmieniają automatycznie statusu inwariantu produktu.
- Milestone nie może być opisany jako spełniający blokujący inwariant, jeśli status nie jest `met`.

### Handoff

- Nowy format handoffu zawiera `schema_version` oraz sekcje `Open product invariants` i `Unresolved assumptions`.
- Każdy otwarty inwariant podaje id, status, wpływ na bieżący rezultat i dowód potrzebny do zmiany statusu.
- Każde założenie podaje źródło, konsekwencję oraz dowód lub decyzję potrzebną do rozstrzygnięcia.
- Walidator wymaga nowych sekcji dla nowej wersji schematu i nadal akceptuje istniejące snapshoty legacy bez przepisywania historii.

### Verification i review

- Każdy etap uruchamia najtańsze affected checks pokrywające zmianę oraz pełny diff self-review.
- Review pozostaje zgodne z obecnym routingiem: niezależne dla każdego etapu Large i Standard, jeśli workflow tego wymaga.
- Po zakończeniu wszystkich zmian, korekt, dokumentacji, lekcji i review task-record przechwytuje immutable verification subject.
- Dla zadania Large wykonywany jest jeden finalny `full` gate dla tego subject. Affected checks wykonane wcześniej pozostają dowodem etapu, lecz nie zastępują gate.
- Jeśli finalny gate nie przejdzie, dowód pozostaje append-only. Każda korekta tworzy nowy subject i dopiero wtedy nową pojedynczą próbę finalnego gate.
- `verification_subject check` dowodzi niezmienności subject po przechwyceniu. Nie dowodzi, że wcześniejszy test został wykonany dla tego subject.

### Postęp i pytania

- Agent kontynuuje bez pytania, gdy następny krok jest read-only, lokalny albo jest zwykłym krokiem zatwierdzonego planu i nie przekracza granic bezpieczeństwa.
- Agent pyta tylko o wybór, którego repozytorium i polityka nie rozstrzygają, albo o działanie wymagające nowej autoryzacji.
- Powtórzenie tego samego nieskutecznego podejścia bez nowego dowodu jest zabronione. Po dwóch nieudanych próbach z tym samym blockerem agent zmienia hipotezę lub plan; pyta dopiero, gdy bez danych użytkownika albo zmiany stanu zewnętrznego nie istnieje bezpieczny następny krok.

## Business rules

1. Wymagania obowiązkowe nie mogą zależeć od włączenia opcjonalnej standing publication authorization.
2. Żadna polityka publikacji nie może autoryzować `--allow-dirty`, force-push, rewrite historii, deploy, nowego remote ani zmienionego zakresu bez osobnej jawnej zgody.
3. Dirty worktree jest stanem do rozdzielenia na task-owned i unrelated. Nie wolno automatycznie ignorować, usuwać ani commitować cudzych artefaktów.
4. Harness tests należą do kanonicznego źródła harnessu. Downstream nie może udawać ich pokrycia, jeśli aktualizator usuwa `.agents/tests/`.
5. Dokumentacja Windows/WSL opisuje zachowanie przenośne. Nie zawiera ścieżek do prywatnych kluczy, założeń o konkretnym dysku ani danych uwierzytelniających.
6. Replay historycznej sesji może wykazać, które postoje stałyby się zbędne, ale nie jest dowodem gwarantowanej oszczędności czasu.

## Policy variants requiring approval

### Canonical harness location

- `source-first` (zatwierdzony): implementować kanoniczne kontrakty, skrypty i testy na `main` w `project-template`, a do Gitgeist synchronizować wydaną wersję przez `harness-config-update`. Repo Gitgeist przechowuje własną specyfikację i rejestr inwariantów. Implementacja chroni istniejące zmiany użytkownika w obu repozytoriach i pozostaje niecommitowana do przeglądu.
- `in-repository adoption`: przestać ignorować wybrany, jawny zestaw plików harnessu w Gitgeist i uczynić go lokalnym źródłem prawdy. Wymaga reguł synchronizacji, aby przyszły update nie nadpisał lokalnych zmian.
- `ignored local overlay`: niedopuszczalny jako zakończona implementacja, ponieważ branch, review i historia nie pokażą zmian kontraktów.

### Publication authorization

- `explicit-each-time` (obecne, rekomendowane bez dodatkowej decyzji): zachować pytanie przed commit, bump i push.
- `opt-in-standing`: dodać domyślnie wyłączony, kontrolowany przez użytkownika mechanizm dla dokładnej sekwencji scoped commit + semver bump + push do istniejącego `origin`, z `publication-status` przed każdą akcją. Samo wdrożenie mechanizmu nie włącza go i nie zmienia zakazu commita w tym zadaniu.
- Automatyczna zmiana `.gitignore` pozostaje poza obiema opcjami. Może być osobno zatwierdzoną zmianą produktu lub repozytorium.

## Authorization

- Odczyt, preflight, testy i lokalne edycje zatwierdzonej implementacji nie wymagają dodatkowej zgody.
- Modyfikacja kanonicznych kontraktów `AGENTS.md`, `.agents/safety.md`, `.agents/engineering.md`, workflow i skills wymaga zatwierdzenia tej specyfikacji i planu z dokładnie nazwanym zakresem.
- Commit, bump, tag, push, release, deploy, zmiana remote, historia Git i destrukcyjne operacje nie są autoryzowane przez tę specyfikację.

## Data / API

### Verification command

- Input: string z `verification.changed_command` albo `verification.full_command`.
- Output: lista argumentów gotowa do `subprocess.run`.
- `{python}` jako osobny argument mapuje się na `sys.executable`.
- Błąd konfiguracji jest raportowany przed wykonaniem procesu.

### Preflight output

- Stabilny tekstowy format: jedna linia `[ok]`, `[info]`, `[skip]` albo `[fail]` na kontrolę.
- Kod wyjścia `0`: wszystkie wymagane prerequisites są spełnione; informacje i skipy pozostają jawne.
- Kod wyjścia różny od zera: co najmniej jeden wymagany prerequisite nie jest spełniony.

### Product invariant record

Każdy wpis zawiera co najmniej:

```text
id
statement
source
blocking_scope
status
acceptance
evidence
related_specs
decision
```

Puste `evidence` jest dozwolone tylko przy `unmet`. `deferred-by-decision` bez `decision` i `met` bez `evidence` są nieważne.

### Handoff schema

- Nowy snapshot deklaruje wersję schematu.
- Legacy snapshot bez wersji zachowuje dotychczasowe wymagane sekcje.
- Nowa wersja wymaga dwóch dodatkowych sekcji bez zmiany nazw istniejących pól.

## Compatibility and migration

- Windows: argumenty są dzielone zgodnie z bieżącą regułą Windows, a ścieżka `sys.executable` jest przekazywana jako jeden argument niezależnie od spacji.
- WSL: używany jest interpreter WSL uruchamiający harness. Windowsowy launcher `py` i Windowsowy venv nie są prerequisites.
- POSIX: zachowanie pozostaje zgodne z `shlex` i bieżącym interpreterem.
- Istniejące profile bez `{python}` nadal działają, jeśli ich pierwszy program istnieje.
- Istniejące handoffy przechodzą walidację jako legacy. Migracja następuje przy utworzeniu nowego snapshotu, nie przez masową edycję archiwum.
- Rejestr inwariantów jest nowym kanonicznym dokumentem produktu. Początkowa migracja zapisuje tylko statusy poparte obecnym repozytorium i nie przypisuje `met` na podstawie nazwy testu lub historycznego raportu.
- Przy wariancie `source-first` Gitgeist nie przechowuje downstreamowej kopii testów harnessu; dowód testów pochodzi z kanonicznego repo, a synchronizacja ma własną walidację.

## Edge cases

- `sys.executable` zawiera spacje.
- Polecenie zawiera cytowane argumenty na Windows.
- Profil nadal używa `py`, ale `py` nie istnieje w WSL: preflight zgłasza fail przed verify.
- Repo nie ma upstreamu albo jest w detached HEAD: preflight raportuje stan, lecz nie udaje relacji ahead/behind.
- Worktree zawiera unrelated staged, unstaged albo untracked files: raport rozdziela kategorie i niczego nie modyfikuje.
- Nazwany target nie istnieje, a istnieje wiele lub jeden podobny kandydat: brak automatycznej podmiany.
- Feature spec jest zielona, ale produktowy inwariant jest `unmet`: task może się zamknąć, lecz raport nie może ogłosić inwariantu ani milestone jako spełnionego.
- Inwariant ma status `deferred-by-decision`, ale linkowana decyzja nie istnieje: walidacja lub review traktuje wpis jako błędny.
- Finalny gate przeszedł, po czym zmienił się plik subject: subject check blokuje close i wymaga nowego subject oraz gate.
- Dirty artifact blokuje publikację: workflow pokazuje blocker i nie zmienia `.gitignore` bez zakresowej zgody.
- Handoff legacy i handoff nowej wersji istnieją jednocześnie: walidator stosuje wymagania odpowiadające każdemu plikowi.

## Errors

- Nierozpoznany placeholder albo brak programu w wymaganym verification command: jawny fail z nazwą pola profilu i argumentu; brak próby uruchomienia.
- Brak kompatybilnego Pythona lub repozytorium: preflight kończy się niezerowym kodem i podaje wykryty stan.
- Brak nazwanego targetu: agent pokazuje dokładny target i evidence, nie wykonuje pracy na substytucie.
- Konflikt źródeł bez rozstrzygnięcia: spec, plan albo raport nazywa oba źródła i pozostawia decyzję otwartą; nie wybiera wygodniejszego dokumentu.
- Nieważny wpis inwariantu: walidacja wskazuje id oraz brakujące lub sprzeczne pole.
- Brak sekcji wymaganej przez wersję handoffu: `handoff-status --check` kończy się błędem z nazwą sekcji.
- Finalny subject nie pasuje: close pozostaje aktywny i zachowuje wcześniejsze dowody.

## Acceptance criteria

1. `configured_command()` i publication full gate korzystają ze wspólnego resolvera, a testy dowodzą poprawnego `{python}` na Windows i POSIX, w tym ścieżki ze spacją.
2. `verification.changed_command` i `verification.full_command` Gitgeist używają `{python}`; `verify-changed` i `verify-full` nie wymagają launchera `py` w WSL.
3. Preflight w jednym uruchomieniu raportuje platformę, interpreter, minimum Python, venv, resolution verification commands, repo, branch/upstream, dirty categories i znane artefakty bez sieci i bez mutacji.
4. Preflight nie wywołuje ani nie duplikuje `publication-status`, SSH auth, tag checks, version checks ani remote-ref checks.
5. Kanoniczna reguła nazwanego targetu zabrania substitute bez repozytoryjnego aliasu lub potwierdzenia użytkownika. Ręczny replay `../projects-template` kontra `../project-template` kończy się bez testu na `../agents-template`.
6. `docs/product/invariants.md` zawiera poprawny wpis JEV `unmet`, wskazuje konflikt między dokumentem produktu a Phase 2 spec i nie twierdzi, że raportowanie dostarcza JEV.
7. Task-close dla Standard/Large i milestone raportuje dotknięte inwarianty. Ręczny replay zielonych testów z JEV `unmet` nie pozwala ogłosić pełnej zgodności MVP z kluczową rolą JEV.
8. Nowy handoff przenosi otwarte inwarianty i założenia, a walidator akceptuje zarówno nowy format, jak i istniejące snapshoty legacy.
9. Workflow i task-close wymagają affected checks per stage, subject capture po ostatniej zmianie oraz jednego finalnego recorded gate. Żaden tekst nie dopuszcza reuse wcześniejszego, niepowiązanego testu.
10. Dirty worktree replay nie zmienia `.gitignore`, nie usuwa artefaktów i nie rozszerza scope; raportuje blocker lub wykonuje tylko wcześniej zatwierdzoną remediację.
11. Approval replay zatrzymuje commit/push/deploy bez zakresowej autoryzacji. Continue-without-question replay przechodzi przez read-only inspekcję, test lub zatwierdzony lokalny krok bez pytania.
12. Wszystkie nowe automatyczne testy przechodzą w kanonicznym źródle harnessu, walidatory konfiguracji i handoffu przechodzą, a finalny full gate Gitgeist kończy się exit 0.
13. Implementacja powstaje na gałęzi `main` w objętych repozytoriach i pozostaje bez commita zgodnie z instrukcją użytkownika.

## Required tests

Automatyczne:

- resolver `{python}`: POSIX, Windows quoting, ścieżka interpretera ze spacją, brak placeholdera, nieznany placeholder;
- `verify-changed`, `verify-full` i publication full gate używają tego samego resolvera;
- preflight: Windows, WSL i POSIX; zgodny i za stary interpreter; aktywny i nieaktywny venv; brak `py` przy profilu `{python}`; brak upstreamu; dirty staged/unstaged/untracked; brak mutacji i brak wywołania sieci;
- handoff schema: legacy pass, nowa wersja pass, brak każdej nowej sekcji fail;
- rejestr inwariantów: `met` bez evidence fail, `deferred-by-decision` bez decision fail, poprawny `unmet` pass;
- verification subject: zmiana po capture blokuje close, a stage check bez subject nie jest przedstawiany jako finalny gate.

Ręczne, o jednoznacznym wyniku:

- replay błędnej ścieżki: brak substitute;
- replay green tests + unmet invariant: task Done z jawną luką, bez fałszywego claimu milestone;
- replay dirty worktree: zero automatycznej zmiany `.gitignore` i zero unrelated commit;
- replay approval: brak external mutation bez autoryzacji;
- replay kontynuacji: brak pytania dla read-only lub zatwierdzonego lokalnego kroku;
- replay historycznej sesji: raportuje tylko postoje, którym nowa reguła rzeczywiście zapobiega, bez przeliczania ich na gwarantowaną oszczędność.

## Relevant SDD / ADR

- Brak istniejącego ADR.
- Zatwierdzony wariant lokalizacji harnessu i praca na `main` muszą być zapisane w planie. Jeśli wybór zmieni własność źródła prawdy lub strategię synchronizacji, implementacja dodaje ADR w repozytorium będącym kanonicznym właścicielem harnessu.
