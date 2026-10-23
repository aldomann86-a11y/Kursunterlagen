# Offene Punkte

Was hier steht, ist nicht entschieden oder nicht erledigt. Entschiedenes wandert nach
`ENTSCHEIDE.md`, Gebautes nach `STAND.md` – hier wird es dann gestrichen.

## Fachliche Entscheide (blockieren Etappen)

| # | Frage | Empfehlung | Betrifft Etappe | Seit |
|---|---|---|---|---|
| F2 | Bleibt das Repository public? | Ja. Die Teilnehmer sollen den Code ansehen können, das ist Teil des Kurses. Unterlagen und Secrets liegen ohnehin nicht im Repo. | – | 2026-10-23 |

## Pendenzen (blockieren nichts)

- [ ] **Bremse hinter dem Proxy:** Fix gebaut am 23.10.2026 (`app/bremse.py` nimmt jetzt
      den letzten `X-Forwarded-For`-Eintrag), **live erst nach dem nächsten Ausrollen**.
      Danach gegenprüfen: zwölf Fehlversuche mit wechselndem Vorderteil müssen in 429
      enden. `ADMIN_2FA=1` bleibt in jedem Fall an.

- [ ] HTMX-Datei ins Repo legen, sobald eine Seite sie braucht (E3 kam mit reinen
      Formularen aus; DS-Basis B3) – seit 2026-10-23
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

- [ ] Beim ersten Anmelden den zweiten Faktor auf dem Handy einrichten (Passwort und
      Schlüssel stehen in `~/.claude/secrets.local.md` unter «Kursunterlagen»)
