# Claude Arbeitsregeln für Kursunterlagen

Kursunterlagen-Portal: Aldo lädt Handouts, Spickzettel und Slides hoch, Kursteilnehmer laden
sie nach Eingabe eines Zugangscodes herunter. Gebaut wird die App im Kurs selbst, gemeinsam
mit den Teilnehmern – sie bestimmen mit, was sie können soll.
Kontext: [README.md](README.md). **Vor Änderungen an bestehendem Verhalten zuerst
[docs/ENTSCHEIDE.md](docs/ENTSCHEIDE.md) lesen** – dort steht, warum etwas so gebaut ist.
Pendenzen: [docs/OFFENE_PUNKTE.md](docs/OFFENE_PUNKTE.md). Was gebaut ist:
[docs/STAND.md](docs/STAND.md). Deploy und Instanzen: [docs/BETRIEB.md](docs/BETRIEB.md).
Personendaten, Fristen, Dienste: [docs/DATENSCHUTZ.md](docs/DATENSCHUTZ.md).

Die globalen Regeln (Ablauf, Sperrliste, Sprache) gelten unverändert; hier steht nur,
was für dieses Projekt dazukommt.

## Stack (fix)

Python 3.12 oder neuer (lokal 3.13), FastAPI, **SQLite ohne ORM** (sqlite3, Schema als `CREATE TABLE IF NOT EXISTS`),
Jinja2 + HTMX, itsdangerous für Sitzungen, bcrypt für Passwort und Zugangscode, pytest,
Docker. Muster für Aufbau und Betrieb: `../kimas-post` (gleicher Stack, ohne ORM).

Gestartet wird als Fabrik: `uvicorn app.main:erzeuge_app --factory`. Das Modul `app.main`
stellt absichtlich **kein** fertiges App-Objekt bereit, damit schon der Import keine
Umgebungsvariablen verlangt (Tests, CI).

Kein Postgres, kein Alembic, keine SPA: eine Datei als Datenbank, damit das Projekt im Kurs
in einer Sitzung verständlich bleibt und lokal ohne Serverdienst läuft
(Begründung: docs/ENTSCHEIDE.md, 23.10.2026).

## Harte Regeln dieses Projekts

- **Dateien nie in die Datenbank.** Hochgeladenes liegt unter `DATA_DIR/unterlagen/`,
  die Datenbank hält nur Titel, Kurs, Dateiname und Ablagename.
- **Kein Download ohne Rechteprüfung.** Jeder Download läuft über einen Endpunkt, der die
  Sitzung gegen den Kurs prüft. Kein `StaticFiles` auf dem Upload-Ordner.
- **Zugangscodes nur als bcrypt-Hash** in der Datenbank, im Klartext nur einmal bei der
  Vergabe am Bildschirm. Gleiches gilt für das Admin-Passwort.
- **Keine Personendaten.** Teilnehmer melden sich nicht an; das Download-Protokoll hält
  Zeit und Unterlage, keine IP, keinen Namen (docs/DATENSCHUTZ.md).
- Zeiten UTC speichern, Anzeige Europe/Zurich. Unterlagen deaktivieren statt löschen.
- Nur Dateitypen aus einer Positivliste annehmen, Grösse begrenzt, Dateiname nie vom
  Benutzer übernehmen (eigener Ablagename).
- Keine CDNs, keine externen Fonts – HTMX liegt im Repo (DS-Basis B3).

## Was in diesem Projekt zusätzlich gesperrt ist

- Das Repository `aldomann86-a11y/Kursunterlagen` ist **public**: keine Secrets, keine
  echten Unterlagen, keine Kundennamen im Code, in Beispielen oder in der Doku.
- Deploy nur über `/deploy` nach ausdrücklichem «ja, deployen» (docs/BETRIEB.md).

## Prüfen vor Abschluss

```bash
python -m pytest -q
```

## Referenzen (nur lesen, nichts ändern)

- `../kimas-post` – FastAPI + SQLite ohne ORM, Admin-Login mit TOTP, Rate-Limit, Dockerfile,
  `betrieb/prod/` (Compose, Caddy, Sicherung), Deploy-Workflow
- `../feedbackbox` – kleiner FastAPI-Dienst mit SQLite und Jinja2
- `KI_Schulung/01_Claude_Code_Grundkurs` – die Unterlagen, die später in der App liegen
