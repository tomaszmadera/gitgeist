# Audyt flow pracy agenta: wydajność sesji i projekt flow v2

Zakres: rekonstrukcja obecnego workflow z `.agents/` i `AGENTS.md`, analiza zapisu sesji `tmp/longest-session-export.txt` (sesja `happy-garden`, 2026-09-19 11:52:51 do 13:17:31) oraz projekt docelowego flow. Ten dokument nie implementuje zmian; każda rekomendacja ma dowód w zapisie sesji (znacznik czasu lub linia) albo w aktualnym repo (`plik:linia`).

## 1. Executive summary

Sesja trwała 84 min 40 s i zawierała 108 wywołań narzędzi (80 `bash`, 12 `edit`, 11 `read`, 3 `skill`, 2 `write`; policzone z `tmp/longest-session-export.txt`). Samo wykonywanie pracy było sprawne: poprawka `engine_version` od zgłoszenia do formalnej weryfikacji zajęła 6 min 19 s, zadanie README 90 s, odpowiedzi na pytania produktowe 27-45 s.

Stratę czasu tworzą trzy zjawiska:

1. Bramki decyzyjne: 5 postojów na decyzję użytkownika, łącznie 33 min 17 s (39.3% zakresu sesji). Wszystkie 3 oferty publikacji zostały przyjęte w pełnej sekwencji (12:13:44 "2", 13:13:09 "1", plus oferta z 12:57:24 nadpisana zgłoszeniem defektu). Zero odmów i zero zawężeń zakresu.
2. Środowisko Windows/WSL: pusty `.venv/bin/python` (12:15:27), brak launchera `py` w WSL (13:10:18), zły wpis `IdentityFile` w `~/.ssh/config` (12:24:56 do 12:25:32). Dwa z tych problemów mają przyczynę w konfiguracji repo: profil twardo wpisuje launcher `py` w komendach weryfikacji (`.agents/project-profile.yaml:28-29`), choć harness wspiera placeholder `{python}` (`.agents/scripts/common.py:432`), a skrypt preflight sprawdza tylko git i wersję Pythona (`.agents/scripts/preflight`, funkcja `main`).
3. Luka intencji produktowej: MVP formalnie ukończone (task 6/6, 167 testów, review approve, wydane 0.3.0), a 18 minut później użytkownik ustalił, że sedno produktu, prawdziwy model JEV od typesafe.ai, nie jest podłączony (12:45:51). Wszystkie bramki były zielone, bo odroczenie JEV jest zapisane w specyfikacjach (`docs/features/feature-extraction/spec.md`, Non-goals; `docs/features/emotional-repository-portrait-system.md` sekcja 25 nie wymaga modelu JEV). To jest local correctness / global wrongness.

Rekomendacja: Wariant B (sekcja 13). Największy pojedynczy zysk czasu daje stała autoryzacja publikacji po pomyślnej weryfikacji (usuwa postoje z 11:53, 13:10 i większość z 12:57); największy zysk jakości daje rejestr inwariantów produktowych z obowiązkiem raportowania niespełnionych na zamknięciu milestone'a; najtańszą poprawką techniczną jest placeholder `{python}` w komendach weryfikacji.

## 2. Current workflow

Rekonstrukcja z `AGENTS.md` (router), `.agents/workflows/*`, `.agents/skills/*`, `.agents/safety.md`, `.agents/templates/task-record.md` i `.agents/skills/ci/references/publication.md`.

```text
intake (wiadomość użytkownika)
  -> classify (intent / complexity / risk / durability; bounded probe)
  -> [recorded] task-record create (.agents/tasks/<id>/task.md)
  -> route:
       Trivial feature/refactor/docs ..... wykonanie bezpośrednie
       Small development ................. plan w sesji -> implement -> affected checks
                                           -> self-review diffu -> verify(targeted) -> Done
       Standard/Large development ........ specification -> task-plan -> APPROVAL GATE
                                           -> preflight -> stage loop:
                                                implement(stage) -> affected checks
                                                -> diff self-review -> independent review (subagent)
                                                -> correction/re-review (max 2) -> kolejny etap
                                           -> task-close (verify changed/full) -> Done
       debug ............................. systematic-debugging
       review / analysis ................. praca własna, bez pętli implementera/reviewer-a
  -> completion report (Done / Unfinished / Stopped)
  -> ci publication-status --json -> OFERTA PUBLIKACJI (pytanie + opcje) -> GATE
       sekwencja: commit -> bump -> push -> (release/deploy wg strategy)
       reguła 7 publication.md: po blockerze wymagana nowa odpowiedź użytkownika
  -> handoff (pauza / granica kontekstu / przekazanie)
```

Stany i bramki:

| Stan | Wejście | Wyjście | Warunek przejścia | Kto decyduje | Artefakty | Walidacje |
|---|---|---|---|---|---|---|
| classify | wiadomość | intent, complexity, risk, durability | bounded probe rozstrzyga; niejasność konsekwencji = 1 pytanie | agent; użytkownik przy niejasności | brak | brak formalnych |
| task-record | klasyfikacja | rekord z Phase 0 | schemat v2, walidator | agent | `.agents/tasks/<id>/task.md` | `task-status --check` |
| specification (Std/Large) | rekord | `docs/features/<slug>/spec.md` | kontrakt zachowania kompletny | agent | spec | przegląd własny |
| task-plan + approval | spec | plan + zgoda | brama: brak zgody = brak preflight i edycji | użytkownik | plan w rekordzie | brak automatycznych |
| preflight | plan | dowód środowiska | wymogi przechodzą lub pre-existing udowodnione | agent | wpisy Verification | `commands.preflight` |
| implement stage | plan | diff + dowody | affected checks + self-review | agent | kod, testy | testy obszarowe |
| independent review (Std/Large) | diff | findings | brak blokujących lub korekta | subagent-reviewer | findings w rekordzie | review własne reviewer-a |
| verify | finalny diff | dowód exit status | dokładnie jedna próba na subject | agent | Verification table + subject | `verify-changed`/`-full`/`-targeted` |
| task-close | dowody | rekord completed | subject match, retro, lessons | agent | rekord completed | `task-status --check`, `verification_subject check` |
| publication offer | Done + status | wykonana sekwencja lub brak | każda mutacja: pytanie i odpowiedź | użytkownik | commity, tag | `publication-status` przed/po |
| handoff | pauza/kontekst | snapshot + checkpoint commit | walidacja, zakres task-owned | agent (autoryzacja stała z safety.md:19) | `.agents/handoffs/<id>.md` | `handoff-status --check` |

Obserwacja o ciężarze: spec-driven z niezależnym review dotyczy wyłącznie Standard/Large; Small i prace bezpośrednie są lekkie. Router sam w sobie nie jest overly heavy; problemem są nie bramki proceduralne, lecz bramki polityki publikacji (każdorazowe pytanie) i brak mechanizmów środowiskowych i produktowych opisanych niżej.

## 3. Evidence from `tmp/longest-session-export.txt`

Weryfikacja hipotez z wcześniejszej analizy:

| Hipoteza | Werdykt | Dowód |
|---|---|---|
| Sesja ok. 84 min 40 s | Potwierdzone | nagłówek eksportu: `11:52:51 -> 13:17:31 (84.7 min)` |
| Duża część wall-clock to oczekiwanie na użytkownika | Potwierdzone z niuansem | postoje na decyzje: 33:17 (39.3%); dodatkowo 13:06 przerwy po odpowiedzi z błędną ścieżką (użytkownik testował i korygował) |
| Ponad 100 tool calli | Potwierdzone | 108 wywołań (policzone) |
| Sekwencje produktywne | Potwierdzone | README 12:55:54-12:57:24 (6 narzędzi, smoke test wliczony); fix 13:04:23-13:10:42 z 174 testami i dowodem end-to-end |
| Kolejne approval gates: publikacja, naprawa, bump, dirty worktree | Potwierdzone | bramki o 11:53:04, 13:03:52, 13:10:42, 13:13:35; plus blocker SSH 12:17:42 |
| Windows/WSL: Python i SSH | Potwierdzone | pusty `.venv/bin/python` (12:15:27), brak `py` i shim w `/tmp/opencode` (13:10:18), ssh-agent nie przeżywa powłoki (12:25:32), zły klucz w configu (12:24:56) |
| Agent podmienił ścieżkę zamiast rozstrzygnąć intencję | Potwierdzone | 12:32:45: "`../projects-template` nie istnieje; jest `../agents-template` - na nim przetestowałem"; korekta użytkownika 12:45:51: "chodziło mi o ../project-template" |
| MVP ukończone formalnie, sedno (prawdziwy JEV) nieosiągnięte | Potwierdzone z przyczyną | 12:27:22 "MVP skończone: tak" wg kryteriów spec; 12:46:38 przyznanie: "prawdziwy JEV nie jest jeszcze podłączony"; przyczyna w specach, sekcja 9 niżej |
| Live test ujawnił stary `engine_version` | Potwierdzone | 13:03:29 pytanie użytkownika o `Engine: Gitgeist v0.1.0-beta.3`; root cause: zaszyte defaulty w 3 schematach |
| `gitgeist-output/` późno ujawnił brak `.gitignore` | Potwierdzone częściowo | wpis `.gitignore` powstał dopiero po blockerze bump (13:16:33, opcja 1), choć domyślny katalog wyjścia produktu był znany od tasku mvp-completion (11:52:51, wzmianka o przeniesieniu katalogu) |
| Weryfikacja powielała suite i natrafiła na różnice WSL | Potwierdzone | 13:09:37 pełna suite 174 passed jako affected checks; 13:10:09 `verify_changed` = `py -m pytest tests`, czyli ta sama suite; fail na launcherze; shim; rerun |

Fakty liczbowe:

- Bramki decyzyjne i czasy oczekiwania: 11:53:04 -> 12:13:44 = 20:40 (publikacja poprzedniego etapu, pytanie przeniesione z poprzedniej sesji); 12:17:42 -> 12:24:23 = 6:41 (SSH, decyzja o kluczu); 13:03:52 -> 13:04:23 = 0:31 (zgoda na fix); 13:10:42 -> 13:13:09 = 2:27 (publikacja fix + README); 13:13:35 -> 13:16:33 = 2:58 (bump zablokowany przez niescommitowany `gitgeist-output/` użytkownika). Suma: 33:17.
- Przerwa 12:32:45 -> 12:45:51 = 13:06: użytkownik poza sesją, wrócił z korektą ścieżki i pytaniem o JEV. To nie jest czas obliczeń agenta ani klasyczne oczekiwanie na decyzję.
- Oferty publikacji: 3 (11:53:04, 12:57:24, 13:10:42), wszystkie z pełną sekwencją commit+bump+push; przyjęte w całości 2, trzecia nadpisana zgłoszeniem defektu i scalona z następną. Odmów i zawężeń: 0.
- Narzędzia a wiadomości: 109 wiadomości asystenta, 108 wywołań narzędzi; przewaga pojedynczych wywołań na wiadomość, w tym seria 10 kolejnych pojedynczych `bash` w publikacji (12:14:09 do 12:15:27).
- Czasów trwania pojedynczych wywołań nie ma w eksporcie; wszelkie wnioski o wall-clock opierają się wyłącznie na znacznikach między wiadomościami.

Czego zapis nie pozwala ocenić: czasu trwania i kosztu pojedynczych narzędzi, treści wyników narzędzi (tylko nazwy), rzeczywistego czasu refleksji użytkownika między wiadomościami, pracy równoległej użytkownika.

## 4. Root causes

RC1. Launcher Windows zaszyty w komendach weryfikacji. `verification.changed_command` i `full_command` to `py -m pytest tests` (`.agents/project-profile.yaml:28-29`), podczas gdy wszystkie pozostałe komendy profilu używają placeholdera `{python}`, który harness rozwiązuje do bieżącego interpretera (`.agents/scripts/common.py:432`). Skutek w sesji: formalna weryfikacja nie mogła się uruchomić w WSL (13:10:18); obejście shimem zadziałało, ale było improwizacją poza workspace. Zasięg: systemowy, powtórzy się przy każdej weryfikacji w WSL. Najprostszy fix: `{python} -m pytest tests` w profilu. Lekcja `venv-python-shim-is-empty-use-python3` opisuje objaw po sąsiedzku, ale nie usuwa przyczyny w profilu.

RC2. Preflight nie pokrywa środowiska wykonania. Skrypt `.agents/scripts/preflight` sprawdza: dostępność gita, bycie w worktree, wersję Pythona, wpis `local_environment.provider`. Nie sprawdza: zdrowia venv (pusty plik), dostępności launchera dla bieżącego OS, tożsamości SSH i auth do remote, stanu upstream, brudnego worktree, niewaitowanych artefaktów produktu. Wszystkie trzy problemy środowiskowe sesji wyszły dopiero w momencie użycia (12:15:27, 12:17:42, 13:10:18), zamiast raz na starcie lub przed publikacją. Zasięg: systemowy.

RC3. Brak stałej autoryzacji publikacji mimo istniejącego mechanizmu. `safety.md:7` wprost przewiduje "explicit user-controlled standing authorization defined in this policy for the named operations and data scope", ale żadna taka autoryzacja dla commit+bump+push po weryfikacji nie jest wpisana. Skutek: 3 pytania o to samo w jednej sesji, 3/3 przyjęć pełnej sekwencji, 33:17 postojów w tym 23:07 (20:40 + 2:27) czysto na pytania publikacyjne, plus reguła 7 z `publication.md` wymuszająca nową odpowiedź po blockerze (postój 2:58 przy blockerze, którego bezpieczna poprawka, wpis `.gitignore` na zignorowanie własnego domyślnego katalogu wyjścia produktu, był znana i powtarzalna). Zasięg: systemowy i najkosztowniejszy mierzalnie.

RC4. Inwarianty produktowe nie są obiektem śledzenia. Łańcuch spec-ów legalnie odroczył JEV: `docs/features/feature-extraction/spec.md` (Non-goals: "Interpretacja semantyczna / JEV ... odłożona do Fazy 2"), `docs/features/emotional-state-model/spec.md` (Non-goals: "MVP bazuje na regułowym banku sensorów JEV"), a `docs/features/mvp-completion/spec.md` celuje w punkty 1, 6, 7, 8 DoD z sekcji 25 dokumentu produktowego. Punkt 3 tego DoD ("system buduje emotional state vector") jest spełnialny regułami. Dokument produktowy deklaruje JEV jako "kluczową warstwę" (sekcja 8.2) i rdzeń tożsamości systemu (sekcja 32), ale ten status nie istnieje poza prozą produktu. Zajęcie z poprzedniej sesji, `.agents/lessons/items/verify-product-dod-before-next-phase.md`, diagnozuje tę samą klasę: "Task handoffs carried per-phase completion faithfully; nothing carried scope-level DoD status". Zasięg: systemowy, najwyższa waga jakościowa; dwa milestone'y z rzędu ujawniły lukę dopiero po pytaniu użytkownika.

RC5. Brak reguły obsługi celu podanego przez użytkownika, który nie istnieje. Agent zamienił `../projects-template` na `../agents-template` i przetestował (12:32:45); prawdziwy cel to `../project-template` (12:45:51). Koszt: jeden przebieg na złym repo i runda korygująca (13:06 przerwy, w większości czas użytkownika). Delivered command był sparametryzowany, więc szkoda była ograniczona. Zasięg: jednostkowy wzorzec, powtarzalny w każdej sesji z mobile lub z literówek; wymaga ogólnej reguły, nie lekcji o jednej ścieżce.

RC6. Harness poza gitem. `.gitignore` ignoruje `AGENTS.md`, `.agents/`, `.claude/`, `.codex/`, `.grok/`, `.opencode/`, `opencode.json` (sekcja "Agent harness & assistant configs"); śledzonych jest 76 plików, wyłącznie produkt i dokumentacja. Skutek: ewolucja workflow bez historii, bez diffów, bez możliwości audytu zmian reguł; checkpointy handoff fizycznie nie mogą zawrzeć rekordu zadania bez łamania ignorów. To decyzja użytkownika (może być celowa), ale ma cenę audytową.

RC7. Słabe batchowanie inspekcji. 108 narzędzi na 109 wiadomości; w fazie publikacji 10 kolejnych pojedynczych `bash` na niezależne inspekcje read-only. Czasów brak, więc tego nie przeliczę na minuty; to efekt na latencję i tokeny, nie udowodniona strata wall-clock.

## 5. What is working well and should remain

- Uczciwość dowodowa w odpowiedziach: status JEV podany wprost z cytacjami (12:46:38, 12:53:14), "fake deterministyczny" wyjaśniony ze wskazaniem `src/gitgeist/render/image_backend.py:108-124`. Zaufanie do odpowiedzi agenta było zasadne.
- Trwałe poprawki u źródła: SSH config naprawiony permanentnie, nie objetówek na sesję (12:25:53); `engine_version` naprawiony na poziomie schematów z fabryką wersji z metadanych pakietu plus 7 testów regresyjnych, a przy okazji usunięte dwa identyczne ukryte defekty w `emotional.py` i `visual_latent.py` (13:10:42).
- Dyscyplina publikacji działała: `publication-status` przewidział fail push przed pierwszą mutacją (12:15:27), sekwencja zatrzymała się na blockerze, refe weryfikowane lokalnie i zdalnie po push (12:26:18, 13:17:22). Nie należy tego osłabiać.
- Fast path zadziałał tam, gdzie jest zaprojektowany: README 90 s end-to-end ze smoke testem; odpowiedzi na pytania 27-45 s z `plik:linia`.
- Resume po sesji kontynuacji: stan potwierdzony w 13 s (11:52:51 -> 11:53:04), bez powtórki pracy i bez faszarskich założeń.
- Integralność dowodów weryfikacji: przy problemie z launcherem agent uruchomił tę samą zarejestrowaną komendę przez shim, zamiast podmieniać ją na niezarejestrowaną; mechanizm `verification_subject` chronił spójność dowodu. Zachować.
- systematic-debugging przy `engine_version`: root cause odtworzony i potwierdzony przed edycją (13:05:21), łańcuch przyczynowy potwierdzony (13:08:02).

## 6. What should change

W wielkim skrócie, szczegóły w sekcjach 7-12:

1. Publikacja po pomyślnym zamknięciu zadania staje się `auto-with-report` na stałej autoryzacji wpisanej w `safety.md`; pytanie pozostaje dla pierwszej publikacji do nowego remote, deployów, `--allow-dirty` i każdego odstępstwa od nazwanej sekwencji.
2. Preflight dostaje dwa poziomy: odcisk środowiska na starcie zadania (tani, read-only) i readiness publikacji przed ofertą (venv, launcher, ssh auth, upstream, niewaitowane artefakty).
3. Profil przestaje hardcodować `py` w weryfikacji; dochodzi referencja środowiska WSL.
4. Inwarianty produktowe dostają plik-rejestr z statusami, a zamknięcie Standard/Large i milestone'y musi raportować niespełnione inwarianty wprost w `Done`.
5. Reguła celu użytkownika: nigdy nie podmieniać nazwanego celu ciszem; dosłowna weryfikacja, dowód z filesystemu, jedno pytanie lub wynik sparametryzowany.
6. Handoff dostaje sekcje o otwartych inwariantach i nierozstrzygniętych założeniach.
7. Batchowanie read-only inspekcji jako reguła wykonawcza.

## 7. Target Flow v2

Zasada zachowawcza: router, task-record, verify-subject, safety i publication-status pozostają. Zmiany są w polityce autonomii, preflight, treści handoff i ochronie intencji produktowej. To nie jest przebudowa faz; to dołożenie bramek tam, gdzie sesja wykazała luki, i zdjęcie ich tam, gdzie dowody pokazują czysty powtarzalny wzorzec.

```text
intake -> classify -> [recorded] task-record
  -> PREFLIGHT-0 (odcisk środowiska; pomiń dla trivial read-only)
  -> route:
       Trivial .................................. execute -> Done
       Small .................................... plan -> implement -> checks -> self-review
                                                  -> verify(targeted) -> task-close -> Done
       Standard/Large ........................... spec -> plan -> APPROVAL (raz, łącznie spec+plan)
                                                  -> preflight -> stage loop (bez zmian)
                                                  -> task-close -> INVARIANT REPORT -> Done
       debug / review / analysis ................ bez zmian
  -> PUBLICATION (po task-close):
       jeśli obowiązuje stała autoryzacja i sekwencja nazwana i subject/kontrole zielone
         -> wykonaj commit+bump+push auto-with-report (publication-status przed i po)
       odstępstwo, nowy remote, deploy, --allow-dirty -> APPROVAL
       blocker (np. dirty unrelated) -> napraw przyczynę jeśli safe-auto (np. .gitignore)
         i kontynuuj; pokaż raport
  -> handoff na pauzie/granicy kontekstu (z sekcjami invariants + assumptions)
```

Elementy i ich uzasadnienie (problem -> koszt -> kiedy pominąć):

1. PREFLIGHT-0. Problem: RC2, trzy odkrycia środowiskowe w środku pracy. Rozwiązanie: jedna wsadowa komenda read-only: OS i WSL, launcher (`py`/`python3`), zdrowie `.venv/bin/python3` (niepusty, wykonywalny), branch/upstream, krótki status worktree, obecność katalogów artefaktów produktu. Koszt: 1-2 tool calle, kilka sekund. Pominąć: trivial read-only pytania i analizy bez wykonania; uruchamiać przy pierwszym zadaniu z wykonaniem lub przy recorded.
2. APPROVAL łączne (spec+plan jednym pytaniem). Problem: Standard/Large i tak jest rzadkie; dwa pytania z rzędu o spójne artefakty to procedura bez informacji. Koszt: zero nowego ryzyka, bo subject i tak jest plan/spec. Pominąć: nigdy nie pomijać samej zgody przed edycją produktu.
3. PUBLICATION auto-with-report. Problem: RC3. Rozwiązanie: stała autoryzacja o nazwanym zakresie (sekcja 8); wykonanie przez `commands.ci` bez pytania, z pełnym raportem i weryfikacjami z `safety.md` (publication-status przed mutacją i po, weryfikacja refów). Koszt: utrata jednej okazji do kontroli ludzkiej przy rutynowych wydaniach; kompensowana ostrym katalogiem wyjątków i stopem przy każdym odstępstwie. Pominąć: przy braku stałej autoryzacji obecne zachowanie pozostaje.
4. INVARIANT REPORT przy Done. Problem: RC4. Rozwiązanie: rejestr (sekcja 9); task-close dla Standard/Large i milestone'y dołącza listę niespełnionych inwariantów do raportu; wypowiedzenie "MVP skończone" bez tej listy jest nieważne. Koszt: jedno spojrzenie w rejestr, jeden akapit w raporcie. Pominąć: prace, które nie dotykają ścieżek inwariantów (wg mapowania w rejestrze).
5. Blocker-first zamiast blocker-question, gdy istnieje safe-auto fix. Problem: postój 2:58 przy `gitgeist-output/`. Rozwiązanie: przy blockerze publikacji agent najpierw wykonuje dostępne safe-auto remediacje (tu: `.gitignore` na produktowy katalog wyjścia, commit `chore`), raportuje i kontynuuje sekwencję; pyta tylko, gdy remediacja nie istnieje lub jest poza safe-auto. Koszt: commit, który i tak zostałby wykonany po zgodzie. Pominąć: gdy remediacja dotyka plików użytkownika (usuwanie, przenoszenie) lub historii.
6. Handoff rozszerzony. Problem: RC4 poprzedniej sesji i tej; snapshot nie niósł statusu DoD zakresu. Rozwiązanie: dwie nowe obowiązkowe sekcje szablonu (sekcja 11). Koszt: kilka linii. Nigdy nie pomijać przy recorded.
7. STOP/REPLAN. Problem: brak formalnego kryteria koła się w miejscu; w sesji jedynie drobiazg (`rg -rn` powtórzony 13:05:41 -> 13:05:53). Rozwiązanie: reguła miękka: dwie kolejne próby tej samej komendy lub trzech rund bez zmiany stanu = STOP i replan w sesji lub jedno pytanie. Koszt: zerowy przy zdrowym postępie. Pominąć: nigdy nie stosować do loopów oczekujących (watch, serwery).

## 8. Approval/autonomy policy

Cztery poziomy, z przypisaniem na podstawie dowodów z sesji:

| Poziom | Zasada | Przykłady z tej sesji |
|---|---|---|
| `safe-auto` (bez pytania, bez specjalnego raportu) | read-only, lokalne, odwracalne | git inspect, testy, budowa venv w WSL (12:31:54), smoke testy, shim `py` w `/tmp/opencode` (13:10:18) |
| `auto-with-report` (wykonaj, raportuj w Done) | lokalne mutacje w zakresie zadania o niskim ryzyku, po zielonych kontrolach | commit task-owned po task-close; `.gitignore` na produktowe artefakty (13:16:33); fix z testem regresyjny dla zroot-cause'd defektu (13:04:23); naprawa własnego narzędzia środowiskowego |
| `approval-required` (pytanie, opcje numerowane) | external side effects bez stałej autoryzacji, scope creep, ryzyka | pierwsza publikacja do nowego remote; deploy; `--allow-dirty`; rebase/merge; przekroczenie scope zadania |
| `forbidden-without-explicit-approval` | destrukcja i kontrakty | force-push, rewrite historii, sekrety, edycja `AGENTS.md`/`engineering.md`/`safety.md`/workflow contracts (już w `safety.md:40`) |

Stała autoryzacja publikacji, do zaakceptowania przez użytkownika (wpis do `safety.md`, sekcja 12, pozycja 4): "Po zamknięciu zadania z pomyślną weryfikacją końcową, przy `publication.strategy: linear` i `versioning: semver`, autoryzowana jest automatyczna sekwencja: scoped commit plików task-owned, `bump` wg semver, `push` bieżącej gałęzi i nowego tagu do `origin`, wykonywana wyłącznie przez `commands.ci`, z weryfikacjami z sekcji Git publication checks przed i po każdej mutacji." Wyjątki zatrzymujące: pierwszy push do nowego remote, zmiana nazwy gałęzi/taga względem zapowiedzi, jakiekolwiek `--allow-dirty`, deploy, konflikt z obcym stanem refa. Każde odstępstwo = `approval-required`.

To nie obniża bezpieczeństwa tam, gdzie sesja pokazała wartość kontroli: dyscyplina weryfikacji refów (safety) pozostaje w pełni; znika tylko pytanie o zgodę na powtarzalną, nazwaną, w pełni weryfikowalną sekwencję.

## 9. Product-intent protection

Jak doszło do zielonego MVP bez sedna: intencja "JEV jako sensor semantyczny" żyje wyłącznie w prozie dokumentu produktowego (sekcje 8.2, 32), a spec-y funkcji legalnie ją odroczyły (RC4). Żaden artefakt procesu nie był zobowiązany odpowiedzieć na pytanie "które inwarianty produktowe są dziś niespełnione". Testy mierzyły zgodność ze spec, review ze spec, verify ze spec; lokalnie wszystko poprawne, globalnie odroczone sedno.

Proponowany mechanizm, najlżejszy, jaki spełnia wymóg:

1. Rejestr: `docs/product/invariants.md`. Każdy wpis: id, treść inwariantu, źródło w dokumencie produktowym (`sekcja:linia`), kryterium weryfikowalne, obecny status (`met` / `unmet` / `deferred by decision`), powiązane spec-y i testy. Startowy zestaw wywiedziony z dokumentu: I1 prawdziwy JEV jako warstwa sensorów (sekcja 8.2 i 32; status: unmet, odroczone w specach), I2 emergent mapping bez symbolicznych stereotypów (sekcja 3 i 13), I3 determinizm i stabilność snapshotu (sekcja 25 pkt 8; met, testy 1/2), I4 różnicowanie repo (sekcja 25 pkt 7; met, Test 1), I5 explainability (sekcja 27; met).
2. Obowiązek raportu: przy task-close dla Standard/Large oraz przy ogłaszaniu milestone'a, raport `Done` zawiera sekcję "Inwarianty": które dotknięte, które niespełnione. Wypowiedzenie o ukończeniu milestone'a bez tej sekcji jest naruszeniem kontraktu raportu (dopisek do `AGENTS.md` Project rules, decyzja użytkownika bo canonical).
3. Ślad traceability lekki: rejestr linkuje `goal -> sekcja produktu -> spec -> test`; nie buduje się osobnego narzędzia. Rozwiązania cięższe (semantic DoD, automatyczna matryca traceability) odradzam przy obecnym rozmiarze projektu: koszt przewyższa wartość, bo rejestr plus dyscyplina raportu usuwa zaobserwowaną klasę błędu.
4. Product-level smoke przed milestone: w praktyce już istnieje jako plan testów sekcji 29 pokryty przez `tests/test_mvp_behavior.py`; brakującym elementem nie był smoke, tylko raportowanie luk. Dlatego nie dodaję nowego obowiązku uruchamiania produktu; wymagam raportu inwariantów.

## 10. Preflight strategy

Dwa poziomy, oba wykonywalne w istniejącym `.agents/scripts/preflight`:

1. PREFLIGHT-0 (intake): OS i detect WSL, launcher Pythona dostępny dla bieżącego OS, `.venv/bin/python3` zdrowy (istnieje, niepusty, wykonywalny), branch i relacja do upstream, licznik brudnych plików, obecność `gitgeist-output/` i innych katalogów artefaktów. Wyjście: jedną linijką per check, status ok/skip/fail; fail nie blokuje startu, unless planowane wykonanie zależy od niego (wtedy pytanie lub naprawa safe-auto).
2. PREFLIGHT-P (publication readiness): przed ofertą lub automatyczną sekwencją: auth do remote (istnienie pliku klucza z `~/.ssh/config` dla hosta remote; opcjonalnie `ssh -T` tylko przy push), brak zablokowanych tagów, lista niewaitowanych artefaktów, zgodność wersji w `pyproject.toml` z ostatnim tagiem.

Kiedy uruchamiać, żeby nie generował narzutu: PREFLIGHT-0 raz na sesję przy pierwszym zadaniu z wykonaniem lub przy recorded; wynik cache'owany w rekordzie; pominięcie legalne dla trivial read-only. PREFLIGHT-P tylko bezpośrednio przed publikacją (i tak jest wymagany przez `publication-status`).

Koszt: rozszerzenie skryptu o kilka checków; żadnych wywołań sieciowych w PREFLIGHT-0. Test: zwykły pytest na funkcje skryptu.

## 11. Verify/review/handoff strategy

Verify: zachować "dokładnie jedna próba końcowa na subject" jako formalny dowód. Duplikacja suite z 13:09:37 -> 13:10:09 jest ceną formalności i przy 174 szybkich testach jest akceptowalna; realnym problemem był launcher (RC1), nie powtórka. Zasady: `changed` pozostaje domyślny dla Standard, `targeted` dla Small i docs-only, `full` dla Large i powierzchni publicznych; po fixie RC1 obie komendy działają wszędzie. Nowa zasada dowodowa: jeżeli między affected checks a verify subject się nie zmienił (mechanizm `verification_subject check` już to potrafi) i ten sam zarejestrowany command był ostatnio uruchomiony na tym subject z exit 0, verify może przyjąć ten dowód zamiast ponownego uruchomienia; wpisywać go z adnotacją "reused, subject match". To usuwa rytuał, nie osłabia dowodu.

Review: niezależny review pozostaje obowiązkowy dla Standard/Large (sesja go nie testowała; kontrakt jest rozsądny). Dla Small pozostaje self-review pełnego diffu. Podnieś wymagane do niezależnego review, niezależnie od complexity, gdy diff dotyka: auth/sekrety, kontrakty publiczne, migracje, wersjonowanie schematów. Zejdź do checklisty przy docs-only. To formalizacja, nie zmiana praktyki.

Handoff: mechanizm dobry (walidacja snapshotu przeciw dowodom, zakaz rozszerzania autorytetu). Braki treści: snapshot nie niesie statusu inwariantów i założeń. Do szablonu `.agents/templates/handoff.md` dochodzą dwie sekcje: "Open product invariants" (id, status, co wstrzymuje) i "Unresolved assumptions" (założenie, skąd, co je rozstrzygnie). Handoff przechowuje więc nie tylko stan wykonania, ale i nierozstrzygnięte intencje; to bezpośrednia odpowiedź na dwie kolejne sesje z luką ujawnioną po fakcie.

## 12. Concrete repository changes

Uwaga ogólna: `AGENTS.md`, `.agents/safety.md`, `.agents/engineering.md`, workflow i skill contracts są kanoniczne (`safety.md:40`): każda z tych zmian wymaga jawnej zgody użytkownika; pozostałe to konfiguracja lub szablon. Wszystkie pliki harnessu są obecnie poza gitem (RC6), więc "breaking" dotyczy zachowania agentów, nie API repo.

1. `.agents/project-profile.yaml`: `changed_command` i `full_command` -> `{python} -m pytest tests`. Dlaczego: RC1; harness wspiera placeholder (`common.py:432`), inne komendy już go używają. Breaking: nie (zachowanie w Windows identyczne przy uruchamianiu przez interpreter spełniający minimum). Ryzyko: minimalne; `{python}` rozwiązuje się do interpretera uruchamiającego skrypt, więc verify trzeba wołać przez poprawny python (zgodne z kontraktem preflight). Test: uruchomić `verify-changed` w WSL i w Windows; oba exit 0 na czystym drzewie. Akceptacja: brak shims w `/tmp` przy następnej weryfikacji.
2. `.agents/scripts/preflight`: dodać checki z sekcji 10 (funkcje: `check_venv_health`, `check_launcher`, `check_upstream`, `check_artifacts`; tryb `--publication` dla PREFLIGHT-P). Dlaczego: RC2. Breaking: nie; nadzbiór bieżących checków. Ryzyko: fałszywe faile na egzotycznych setupach; mitigacja: status `skip` zamiast `fail` dla checków informacyjnych. Test: pytest z tymczasowym drzewem; przypadek pustego `.venv/bin/python` jak w tej sesji. Akceptacja: PREFLIGHT-0 na tej maszynie wykrywa pusty venv i brak `py` bez uruchamiania czegokolwiek mutowalnego.
3. Nowy `.agents/environments/wsl.md`: odpowiednik `windows.md` dla WSL nad `/mnt/*`: venv tworzony po stronie Windows ma puste shimy; używaj `.venv/bin/python3`; `py` nie istnieje; ssh-agent nie przeżywa powłoki, użyj `IdentityFile` w `~/.ssh/config`; ścieżki Windows przez `/mnt/c/...` z uwagą o uprawnieniach 777 dla kluczy. Dlaczego: RC2/RC7 wiedzy środowiskowej, dziś żyjącej w lekcjach i w pamięci sesji. Breaking: nie. Ryzyko: brak. Akceptacja: nowa sesja w WSL dostaje te fakty z jednego pliku.
4. `.agents/safety.md`: nowa sekcja "Standing publication authorization" z treścią z sekcji 8 tego dokumentu. Dlaczego: RC3, największy mierzalny zysk czasu przy zachowaniu wszystkich weryfikacji. Breaking: zmiana polityki, wymagana zgoda użytkownika; po wpisaniu zmienia zachowanie wszystkich agentów w repo. Ryzyko: automatyczny push niechcianych zmian przy błędnym uznaniu zakresu za task-owned; mitigacja: definicja task-owned z publication.md (rule 1) pozostaje ostrożna: "If ownership cannot be established, report the uncertainty and do not offer to commit those paths". Test: scena replay z sekcji 15. Akceptacja: trzy oferty z sesji przechodzą automatycznie z identycznym zakresem i wersją.
5. Nowy `docs/product/invariants.md`: rejestr z sekcji 9. Dlaczego: RC4. Breaking: nie (nowy artefakt dokumentacyjny). Ryzyko: rejestr zdezaktualizuje się bez dyscypliny; mitigacja: obowiązek raportu w task-close. Test: przegląd przy każdym milestone. Akceptacja: wpis I1 (JEV) ma status `unmet` z linkami do speców, które go odroczyły.
6. `.agents/skills/task-close/SKILL.md` (kanoniczny; wymaga zgody): krok retro rozszerzony o obowiązek: jeżeli `docs/product/invariants.md` istnieje, raport zamknięcia dla Standard/Large i milestoneów zawiera statusy dotkniętych inwariantów. Dlaczego: RC4, egzekwowanie sekcji 9. Breaking: lekko; wydłuża raport. Ryzyko: ceremonialność przy małych taskach; mitigacja: obowiązek tylko dla Standard/Large i milestoneów. Akceptacja: replay sceny "green tests, unmet invariant" raportuje I1.
7. `.agents/templates/handoff.md`: sekcje "Open product invariants" i "Unresolved assumptions". Dlaczego: sekcja 11. Breaking: nie; szablon wymaga uzupełnienia nowymi sekcjami, walidator `handoff-status` może wymagać aktualizacji. Ryzyko: walidator odrzuci stare snapshoty; mitigacja: checki opcjonalne. Akceptacja: `handoff-status --check` przechodzi na nowym i zarchiwizowanym snapshocie.
8. `AGENTS.md` (kanoniczny; wymaga zgody): dopisek w Core rules: "Nigdy nie podmieniaj celu nazwanego przez użytkownika (ścieżka, nazwa, identyfikator) na najbliższy istniejący odpowiednik. Zweryfikuj cel dosłownie; gdy nie istnieje, pokaż dowód z filesystemu i kandydatów albo oddaj wynik sparametryzowany i zapytaj; samodzielny wybór substitute jest zabroniony." Dlaczego: RC5. Breaking: nie; zaostrzenie precyzji. Ryzyko: jedno dodatkowe pytanie przy naprawdę oczywistych literówkach; akceptowalne, bo koszt błędu (runda korekty) był 13:06 przerwy plus błędny przebieg. Akceptacja: scena replay z sekcji 15.
9. `.agents/engineering.md` (kanoniczny; wymaga zgody): dopisek w Execution evidence: "Grupuj niezależne inspekcje read-only w jedno wywołanie; izoluj mutacje osobno." Dlaczego: RC7. Breaking: nie. Ryzyko: długi output jednej komendy; mitigacja: limit do rozsądnej liczby checków. Akceptacja: serie pojedynczych `bash` w fazach inspekcji znikają z kolejnych eksportów.
10. Do rozważenia przez użytkownika (nie propozycja wlania): usunięcie sekcji "Agent harness & assistant configs" z `.gitignore` albo prowadzenie osobnego brancha/repo na harness, dla historii zmian reguł (RC6). Bez decyzji nie ruszać.

Usunięcia i uproszczenia, wprost: nic nie usuwam z bramek jakościowych; jedyna realna redukcja to zniesienie powtarzanego pytania publikacyjnego (pozycja 4) i łączne pytanie spec+plan (sekcja 7, pkt 2). Skrypt `verify-targeted` pozostaje, bo Small z niego korzysta.

## 13. Variant A / B / C

Wariant A: minimal patch (RC1 + RC2 rdzeń + RC5).

- Pozycje 1, 2, 3, 8 z sekcji 12. Bez zmian polityki, bez plików kanonicznych poza jednym zdaniem w `AGENTS.md`.
- Efekt: koniec shims i faili weryfikacji; wykrywanie środowiska przed pracą; koniec podmiany celów.
- Koszt: kilka godzin; ryzyko minimalne; nie usuwa postojów publikacyjnych ani luki inwariantów.

Wariant B: recommended redesign = A + polityka i ochrona intencji (pozycje 4, 5, 6, 7, 9).

- Efekt czasowy: usuwa 3 z 6 postojów z sesji (20:40 + 2:27 + 2:58 wprost; 6:41 SSH przewidywalny przez PREFLIGHT-P po pierwszej konfiguracji). Efekt jakościowy: raport inwariantów zapobiega trzeciemu z rzędu odkryciu luki produktowej po fakcie.
- Koszt: dwa pliki kanoniczne do zaakceptowania; jeden nowy plik produktowy; jeden skrypt rozszerzony.

Wariant C: aggressive simplification = B plus redukcje proceduralne:

- Jedna komenda weryfikacji: `verify_targeted` i rozróżnienie targeted/changed znikają z routingu; `changed_command` jest jedyną końcową komendą dla Small i Standard (suite jest szybka; upraszcza wybór scope). Koszt: wolniejsze Small na dużych suite; przy 174 testach niezauważalne, więc dopuszczalne, ale to decyzja zależna od wzrostu suite.
- Niezależny review w Standard tylko gdy diff > ustalony próg albo powierzchnia publiczna/migrująca; poniżej progu self-review plus obowiązkowe affected checks. Koszt: dla obecnego rozmiaru projektu akceptowalne; ryzyko: subiektywny próg.
- Publikacja całkowicie bez oferty: Done samo wykonuje sekwencję i raportuje (B już to daje dla nazwanej sekwencji; C usuwa też opcjonalne warianty skrócone).
- Selection: oparty na dowodach, nie estetyce; B jest rekomendowane, bo C oszczędza marginalnie (postój spec+plan i wybór scope verify nie pojawiły się jako koszt w sesji), a osłabia niezależny przegląd, który w tym repo jest jedyną obroną przed self-confirming review przy Standard.

## 14. Expected impact

Oparte wyłącznie na znacznikach z sesji; bez inventowanych procentów i bez czasu pojedynczych narzędzi.

- Przez throughput: Wariant B eliminuje z tej sesji postoje 20:40 (11:53), 2:27 (13:10) i 2:58 (13:13): 26:05 z 84:40; czas do ostatniego commitu skróciłby się z ~84 min do ok. 58 min (ok. 52 min z przewidywalnym blockerem SSH przez PREFLIGHT-P) przy identycznych wynikach, bo praca agenta wyglądała na zbieżną. Effect: throughput, latency.
- Preflight-P i `wsl.md`: blocker SSH (6:41 postoju i 3 min pracy) staje się przewidywalny przed ofertą; po jednorazowej konfiguracji znika jako klasa. Effect: latency, reduced rework.
- RC1 fix: usuwa shim (13:10:18-13:10:34) i ryzyko fałszywych dowodów z pustego venv. Effect: quality, safety, reduced rework.
- Rejestr inwariantów i raport: nie skraca sesji; zapobiega klasie "milestone zielony, sedno niepodłączone", która w dwóch kolejnych sesjach kosztowała rundy korekt i erodowała sens formalnego `completed`. Effect: quality.
- Reguła celu (pozycja 8): usuwa przebieg na złym repo i skraca rundę korygującą (13:06 przerwy, w większości czas użytkownika). Effect: reduced rework, latency.
- Batchowanie (pozycja 9): mniej rund narzędzi w fazach inspekcji; wall-clock nie przeliczalny z eksportu. Effect: context efficiency, latency.
- Handoff rozszerzony: szybszy i bezpieczniejszy resume przy granicy kontekstu; koszt kilku linii. Effect: context efficiency, quality.

## 15. Workflow validation plan

Zasada architektoniczna: każda reguła flow, która da się wyrazić wykonywalnie, ma żyć w walidatorze (tak już jest z `task-status`, `verification_subject`, `publication-status`, `handoff-status`); proza pozostaje tylko dla osądu. Testy samego flow:

1. Replay sesji jako scenariusz: z eksportu wyciąć sekwencję zdarzeń (umowna lista: kontynuacja, publikacja, blocker SSH, pytania, README, defect, fix, blocker dirty) i przejść flow v2 krok po kroku na kopii repo; sprawdzenie, że w każdym punkcie decyzji system wszedł w oczekiwany poziom autonomii.
2. Scena błędnej ścieżki repo: pytanie o `../projects-template`; oczekiwane: brak substitute, dowód nieistnienia, pytanie lub wynik sparametryzowany.
3. Scena Windows/WSL mismatch: pusty `.venv/bin/python` i brak `py`; oczekiwane: PREFLIGHT-0 raportuje oba przed pierwszą mutacją; verify przechodzi przez `{python}` bez shims.
4. Scena green tests, unmet invariant: task domykający zmianę w sensorach z pełną suite zieloną; oczekiwane: task-close raportuje I1 unmet w Done; brak wypowiedzenia o ukończeniu sedna produktu.
5. Scena dirty worktree przed publikacją: niescommitowany katalog artefaktów użytkownika; oczekiwane: safe-auto remediacja (`.gitignore` dla znanego katalogu produktu) albo jawne ograniczenie oferty do prefiksu wykonalnego, bez `--allow-dirty`.
6. Scena prawdziwego approval: deploy albo pierwszy push do nowego remote; oczekiwane: pytanie z numerowanymi opcjami, mimo obowiązującej stałej autoryzacji.
7. Scena kontynuacji bez pytania: druga publikacja tego samego dnia po zielonym task-close; oczekiwane: automatyczna sekwencja z raportem, zero pytań.
8. Testy jednostkowe rozszerzonego `preflight` (checki z fałszywym drzewem plików) i walidacja szablonu handoff przez `handoff-status --check`.

Sceny 1-7 są dziś checklistą ręczną; punkty styku z maszyną (preflight, publication-status, walidatory rekordów) pokrywają część automatycznie. Jeśli flow ma być testowalny automatycznie w całości, proste wyjście: opisać sceny jako fixtures dla walidatorów (np. fixtura rekordu + fixtura statusu -> oczekiwana decyzja), co jest realistyczne dla pozycji 4-7, a dla polityki czysto tekstowej pozostaje przegląd człowieka. To nie jest wada wykluczająca; jest limitem, który warto znać.

## 16. Recommended implementation order

1. Pozycja 1 (profil `{python}`): jednozdaniowa, natychmiastowa, usuwa aktywne ryzyko fałszywych dowodów.
2. Pozycja 2 + 3 (preflight rozszerzony + `wsl.md`): wykrywa środowisko raz, na starcie.
3. Pozycja 5 (`docs/product/invariants.md`): niezależna od polityki, czysto dokumentacyjna, domyka RC4 po stronie treści.
4. Pozycja 4 (stała autoryzacja publikacji w `safety.md`): największy zysk czasu; wymaga decyzji użytkownika.
5. Pozycje 6, 7 (task-close invariant report, handoff template): egzekwowanie i przenoszenie stanu.
6. Pozycje 8, 9 (reguła celu, batchowanie): drobne dopiski kanoniczne, jedna wspólna akceptacja.
7. Pozycja 10 (harness w gicie): decyzja, nie implementacja.

## 17. Open questions

1. Czy akceptujesz stałą autoryzację publikacji w podanym brzmieniu (sekcja 8), czy wolisz węższy zakres (np. bez push, tylko commit+bump)? Bez tej decyzji pozycja 4 nie wchodzi.
2. Czy harness (`AGENTS.md`, `.agents/`, `.claude/`) ma zostać poza gitem celowo, czy wprowadzamy jego śledzenie (pozycja 12.10)? To decyduje o audytowalności zmian reguł.
3. Czy niespełniony I1 (prawdziwy JEV) ma status `deferred by decision` z planem, czy `unmet` blokujący kolejne oznaczanie MVP za domknięte w komunikacji? Treść statusu jest decyzją produktową, której nie da się wywieść z repo.

## Tabela priorytetów

| Priority | Change | Files | Expected effect | Risk |
|---|---|---|---|---|
| P0 | `{python}` w komendach weryfikacji | `.agents/project-profile.yaml` | quality, safety: koniec faili verify w WSL | minimalne |
| P0 | PREFLIGHT-0 + PREFLIGHT-P | `.agents/scripts/preflight` | latency, reduced rework: środowisko wykryte przed pracą | niskie (skip zamiast fail) |
| P1 | Referencja środowiska WSL | `.agents/environments/wsl.md` (nowy) | reduced rework: wiedza środowiskowa w jednym miejscu | brak |
| P1 | Rejestr inwariantów produktowych | `docs/product/invariants.md` (nowy) | quality: koniec local correctness / global wrongness | niskie (konieczna dyscyplina) |
| P1 | Stała autoryzacja publikacji | `.agents/safety.md` | throughput: 20-26 min mniej postojów na sesję | średnie (wymaga ostrego katalogu wyjątków) |
| P2 | Raport inwariantów w task-close | `.agents/skills/task-close/SKILL.md` | quality: egzekwowanie rejestru | niskie |
| P2 | Handoff: invariants + assumptions | `.agents/templates/handoff.md` | context efficiency, quality: pełniejszy resume | niskie |
| P2 | Reguła celu użytkownika | `AGENTS.md` | reduced rework: koniec substitute'ów | niskie |
| P3 | Batchowanie inspekcji read-only | `.agents/engineering.md` | latency, context efficiency | niskie |
| P3 | Decyzja o śledzeniu harness w git | `.gitignore` | auditability zmian reguł | decyzja użytkownika |
