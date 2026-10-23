# Offene Punkte

Was hier steht, ist nicht entschieden oder nicht erledigt. Entschiedenes wandert nach
`ENTSCHEIDE.md`, Gebautes nach `STAND.md` – hier wird es dann gestrichen.

## Fachliche Entscheide (blockieren Etappen)

| # | Frage | Empfehlung | Betrifft Etappe | Seit |
|---|---|---|---|---|
| F1 | Wohin wird deployt und unter welcher Adresse? | EasyPanel-Server (ATSOBL) wie `feedbackbox`, Subdomain `kurs.kimas.ch`. Steht in einer Stunde, die Volume-Sicherung des Hosts läuft bereits. Der KIMAS-Kern wäre sauberer, kostet aber Servervorlage, Deploy-Schlüssel, restic und DNS – für eine Kurs-App zu viel. | E2 | 2026-10-23 |
| F2 | Bleibt das Repository public? | Ja. Die Teilnehmer sollen den Code ansehen können, das ist Teil des Kurses. Unterlagen und Secrets liegen ohnehin nicht im Repo. | – | 2026-10-23 |

## Pendenzen (blockieren nichts)

- [ ] HTMX-Datei ins Repo legen statt CDN (DS-Basis B3) – mit E3 – seit 2026-10-23
- [ ] Datenschutzhinweis auf der Teilnehmerseite (B2), ein Satz: keine Anmeldung, anonymer
      Download-Zähler – mit E6 – seit 2026-10-23
- [ ] Löschfrist der Kurse als Job (B9): Kurs 12 Monate nach `offen_bis` samt Unterlagen weg
      – nach E6 – seit 2026-10-23
- [ ] Warnung im Testlauf: `starlette.testclient` empfiehlt `httpx2` statt `httpx`.
      Erst wechseln, wenn es wirklich bricht – neue Abhängigkeit ohne Not
      – seit 2026-10-23
- [ ] Startbestand: die Unterlagen aus `KI_Schulung/01_Claude_Code_Grundkurs` hochladen,
      sobald E5 steht – seit 2026-10-23

## Bei Aldo

- [ ] F1 entscheiden (Instanz und Subdomain), damit E2 vor dem Kurs fertig wird
- [ ] Kursdatum nennen – danach richtet sich, was vorher gebaut sein muss
- [ ] Erstes Admin-Passwort in `~/.claude/secrets.local.md` ablegen (bei E2)
