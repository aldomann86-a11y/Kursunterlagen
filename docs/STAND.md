# Stand der Umsetzung

Was hier nicht steht, ist nicht gebaut. Nachgeführt bei jedem `/abschluss`.

**Letzter Stand:** 2026-10-23, **alle Etappen bis E6 gebaut**, 124 Tests grün.
**Deployed:** https://kurs.dev.kimas.ch, Commit `f3eea07`, 23.10.2026 (EasyPanel, Projekt `kursunterlagen` / Dienst `app`).

## Etappen

Vor dem Kurs wird gebaut, was Zeit kostet und niemanden etwas lehrt (Gerüst, Datenbank,
Deploy-Strecke). Im Kurs entsteht die Fachlogik live, mit den Teilnehmern.

| Etappe | Inhalt | Wann | Stand |
|---|---|---|---|
| E0 | Projektgerüst, Entscheide, Datenmodell, Doku | vorher | ✅ 2026-10-23 |
| E1 | Gerüst lauffähig: `pyproject.toml`, `app/config.py`, `app/db.py` mit dem Schema, `/health`, Startseite, Tests, `Dockerfile` | vorher | ✅ 2026-10-23 |
| E2 | Deploy-Strecke: Instanz, Domain, Volume, Health-Nachweis | vorher | ✅ 2026-10-23 (DNS-Eintrag offen) |
| E3 | Admin-Login (Passwort, 2FA umschaltbar), Grundlayout | vorgezogen | ✅ 2026-10-23 |
| E4 | Kurse anlegen, Zugangscode erzeugen und anzeigen | vorgezogen | ✅ 2026-10-23 |
| E5 | Unterlagen hochladen, sortieren, ausblenden | vorgezogen | ✅ 2026-10-23 |
| E6 | Teilnehmerseite: Code eingeben, Liste, geschützter Download, Zähler | vorgezogen | ✅ 2026-10-23 |
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
- 2026-10-23: E4, E5 und E6 gebaut – Kursverwaltung mit Zugangscodes, Upload mit
  Positivliste und Sortierung, Teilnehmerseite mit Code-Eingabe, Liste und geschütztem
  Download. 124 Tests. Lokal durchgespielt: falscher Code 401, richtiger Code (auch gross
  und ohne Bindestrich) öffnet die Liste, Download liefert die Datei unter ihrem
  Originalnamen, fremde Unterlage 404, gesperrter Kurs schliesst den Zugang sofort.
- 2026-10-23: Zwei Kurse angelegt und die Unterlagen des Kurstags hochgeladen
  (KI: 5 Dateien, Datenmanagement: 2). **Läuft nur lokal** – kein Deploy, siehe F1.
- 2026-10-23: **Erstmals ausgerollt** auf EasyPanel (Projekt `kursunterlagen`, Dienst
  `app`, Volume `data` → `/data`, Domain kurs.dev.kimas.ch). `/health` meldet den
  ausgerollten Commit, Unsinnspfad 404, Startseite und Anmeldung 200 – geprüft über die
  Server-IP, weil der A-Eintrag für kurs.dev.kimas.ch noch fehlt. Zwei Kurse angelegt und die
  Unterlagen eingefüllt (KI 5, Datenmanagement 2); zwei Kurse aus einem abgebrochenen
  ersten Versuch sind gesperrt. Teilnehmerweg live durchgespielt bis zum Download
  (425 KB PDF, richtiger Dateiname). Admin-Login mit zweitem Faktor, Startpasswort-
  Variable wieder geleert.
