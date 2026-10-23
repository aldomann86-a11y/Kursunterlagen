# Stand der Umsetzung

Was hier nicht steht, ist nicht gebaut. Nachgeführt bei jedem `/abschluss`.

**Letzter Stand:** 2026-10-23, E1 gebaut, 26 Tests grün.
**Deployed:** noch nicht.

## Etappen

Vor dem Kurs wird gebaut, was Zeit kostet und niemanden etwas lehrt (Gerüst, Datenbank,
Deploy-Strecke). Im Kurs entsteht die Fachlogik live, mit den Teilnehmern.

| Etappe | Inhalt | Wann | Stand |
|---|---|---|---|
| E0 | Projektgerüst, Entscheide, Datenmodell, Doku | vorher | ✅ 2026-10-23 |
| E1 | Gerüst lauffähig: `pyproject.toml`, `app/config.py`, `app/db.py` mit dem Schema, `/health`, Startseite, Tests, `Dockerfile` | vorher | ✅ 2026-10-23 |
| E2 | Deploy-Strecke: Instanz, Domain, Volume, Sicherung, Health-Nachweis – leere App live erreichbar | vorher | offen (blockiert: F1) |
| E3 | Admin-Login (Passwort, 2FA umschaltbar), Grundlayout | im Kurs | offen |
| E4 | Kurse anlegen, Zugangscode erzeugen und anzeigen | im Kurs | offen |
| E5 | Unterlagen hochladen, umbenennen, sortieren, deaktivieren | im Kurs | offen |
| E6 | Teilnehmerseite: Code eingeben, Liste, geschützter Download, Zähler | im Kurs | offen |
| E7 | Wünsche der Teilnehmer (werden im Kurs gesammelt) | im Kurs | offen |

## Zuletzt geändert

- 2026-10-23: Projekt angelegt, vier Entscheide festgehalten (Stack, Zugang, Upload,
  Datenmodell), Etappen geschnitten.
- 2026-10-23: E1 gebaut – Einstellungen (mit eigenem .env-Leser), Datenbank mit dem
  vollständigen Schema, `/health`, Startseite, eigenes CSS, `Dockerfile`, 26 Tests.
  Lokal geprüft auf http://127.0.0.1:8050: `/health` meldet `datenbank: schreibbar`,
  Datenbank und `unterlagen/` entstehen beim Start.
