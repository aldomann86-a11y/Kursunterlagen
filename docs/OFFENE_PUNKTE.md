# Offene Punkte

Was hier steht, ist nicht entschieden oder nicht erledigt. Entschiedenes wandert nach
`ENTSCHEIDE.md`, Gebautes nach `STAND.md` – hier wird es dann gestrichen.

## Fachliche Entscheide (blockieren Etappen)

| # | Frage | Empfehlung | Betrifft Etappe | Seit |
|---|---|---|---|---|
| F2 | Bleibt das Repository public? | Ja. Die Teilnehmer sollen den Code ansehen können, das ist Teil des Kurses. Unterlagen und Secrets liegen ohnehin nicht im Repo. | – | 2026-10-23 |

## Pendenzen (blockieren nichts)

- [ ] **Bremse greift hinter dem Proxy nicht.** Am 23.10.2026 live geprüft: zwölf
      Fehlversuche mit wechselndem `X-Forwarded-For` ergaben zwölfmal 401, nie 429.
      Grund: der Start läuft mit `--forwarded-allow-ips='*'`, uvicorn nimmt dann den
      **ersten** (frei wählbaren) Eintrag der Kopfzeile als Absender. Bis zur Behebung
      ist `ADMIN_2FA=1` der eigentliche Schutz des Admin-Logins – nicht ausschalten.
      Fix: in `app/bremse.py` den **letzten** Eintrag von `X-Forwarded-For` nehmen
      (der stammt vom eigenen Proxy), statt der Client-IP von uvicorn zu vertrauen.
      – seit 2026-10-23

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

- [ ] **DNS:** A-Eintrag `kurs.kimas.ch` auf `46.225.160.97` setzen. Ohne ihn holt
      Let's Encrypt kein Zertifikat, und niemand erreicht die Seite.
- [ ] Erstes Admin-Passwort für die Instanz in `~/.claude/secrets.local.md` ablegen
