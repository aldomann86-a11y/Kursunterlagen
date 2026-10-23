# Stand der Umsetzung

Was hier nicht steht, ist nicht gebaut. Nachgeführt bei jedem `/abschluss`.

**Letzter Stand:** 2026-10-23, E1 und E3 gebaut, Unterbau für E4–E6 gebaut, 96 Tests grün.
**Deployed:** noch nicht.

## Etappen

Vor dem Kurs wird gebaut, was Zeit kostet und niemanden etwas lehrt (Gerüst, Datenbank,
Deploy-Strecke). Im Kurs entsteht die Fachlogik live, mit den Teilnehmern.

| Etappe | Inhalt | Wann | Stand |
|---|---|---|---|
| E0 | Projektgerüst, Entscheide, Datenmodell, Doku | vorher | ✅ 2026-10-23 |
| E1 | Gerüst lauffähig: `pyproject.toml`, `app/config.py`, `app/db.py` mit dem Schema, `/health`, Startseite, Tests, `Dockerfile` | vorher | ✅ 2026-10-23 |
| E2 | Deploy-Strecke: Instanz, Domain, Volume, Sicherung, Health-Nachweis – leere App live erreichbar | vorher | offen (blockiert: F1) |
| E3 | Admin-Login (Passwort, 2FA umschaltbar), Grundlayout | vorgezogen | ✅ 2026-10-23 |
| E4 | Kurse anlegen, Zugangscode erzeugen und anzeigen | im Kurs | 🔵 `app/kurse.py` + Tests fertig, Oberfläche im Kurs |
| E5 | Unterlagen hochladen, umbenennen, sortieren, deaktivieren | im Kurs | 🔵 `app/unterlagen.py` + Tests fertig, Oberfläche im Kurs |
| E6 | Teilnehmerseite: Code eingeben, Liste, geschützter Download, Zähler | im Kurs | 🔵 Teilnehmer-Sitzung und Rechteprüfung fertig, Oberfläche im Kurs |
| E7 | Wünsche der Teilnehmer (werden im Kurs gesammelt) | im Kurs | offen |

## Zuletzt geändert

- 2026-10-23: Projekt angelegt, vier Entscheide festgehalten (Stack, Zugang, Upload,
  Datenmodell), Etappen geschnitten.
- 2026-10-23: E1 gebaut – Einstellungen (mit eigenem .env-Leser), Datenbank mit dem
  vollständigen Schema, `/health`, Startseite, eigenes CSS, `Dockerfile`, 26 Tests.
  Lokal geprüft auf http://127.0.0.1:8050: `/health` meldet `datenbank: schreibbar`,
  Datenbank und `unterlagen/` entstehen beim Start.
- 2026-10-23: E3 vorgezogen – Admin-Konto, Anmeldung, zweiter Faktor (TOTP mit QR-Code),
  Bremse gegen Durchprobieren, Verwaltungsseite als Gerüst. 62 Tests. Lokal gegen den
  laufenden Server durchgespielt: Anmeldung, Einrichtung des Faktors, falscher Code (401),
  richtiger Code, Abmelden, erneute Anmeldung verlangt den Code. Die Spalte `versuch.art`
  wurde an der bestehenden Datenbank per `nachziehen()` ergänzt.
- 2026-10-23: Unterbau für den Unterricht gebaut – `app/kurse.py` (Codes als HMAC, Fristen,
  Sperren), `app/unterlagen.py` (Positivliste, eigener Ablagename, Rechteprüfung, anonymer
  Zähler), Teilnehmer-Sitzung in `app/sitzung.py`. 96 Tests. Die Prompts für die drei
  Oberflächen stehen in [KURS_PROMPTS.md](KURS_PROMPTS.md).
