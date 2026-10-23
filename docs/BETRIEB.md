# Betrieb

## Instanzen

| Instanz | URL | Wo | Deploy-Auslöser |
|---|---|---|---|
| Lokal | http://127.0.0.1:8020 | `python -m uvicorn app.main:app --reload --port 8020`, Eintrag `kursunterlagen` in `_Claude/.claude/launch.json` | – |
| Prod | noch offen (Empfehlung `kurs.kimas.ch`) | noch offen – siehe OFFENE_PUNKTE F1 | Push allein deployt **nicht**; Deploy von Hand über `/deploy` |

**Achtung:** Sobald Prod steht, gehört der Auslöser hier hinein. Steht dort je «Push», muss
die Sicherung **vor** dem Push entstehen.

Keine Dev-Instanz: lokal reicht die Datenbankdatei unter `./data/`.

## Einrichtung Prod (E2, sobald F1 entschieden ist)

Für EasyPanel (Empfehlung), per API wie bei `feedbackbox` und `kimas-post`:

1. Projekt `kursunterlagen`, Dienst `app`, Git-Quelle `main`, Dockerfile-Build.
2. Volume `data` auf `/data`. **Darin liegen Datenbank und alle Unterlagen** – ohne Volume
   ist nach jedem Deploy alles weg.
3. ENV aus `.env.example`: `SECRET_KEY` neu erzeugen, `ADMIN_INITIAL_PASSWORD` einmal setzen,
   `HTTPS_ONLY=1`, `DATA_DIR=/data`, `ADMIN_2FA` nach Wunsch.
4. Domain auf Port 8000, DNS-Eintrag der Subdomain.
5. Erster Deploy, anmelden, `ADMIN_INITIAL_PASSWORD` wieder leeren.

## Sicherung

Keine Migrationen, keine Datenbank-Instanz. Das Volume `/data` enthält
`kursunterlagen.sqlite3` **und** `unterlagen/` mit allen Dateien. Verlust bedeutet:
Unterlagen neu hochladen, Codes neu vergeben.

- Vor jedem Deploy und vor jeder Schema-Änderung: Kopie des Volumes ziehen
  (EasyPanel-Volume-Sicherung des Hosts, `dotfiles/server/easypanel/`).
- Konsistente Kopie der Datenbank über die SQLite-Backup-API, nicht `cp` auf die laufende
  Datei. Auf dem Server, im Dienst `app`:

      python -c "import sqlite3; q=sqlite3.connect('/data/kursunterlagen.sqlite3'); z=sqlite3.connect('/data/sicherung.sqlite3'); q.backup(z); z.close(); q.close()"

- Restore-Probe: Kopie in einen Wegwerf-Ordner, dann `select count(*) from unterlage`
  vergleichen. Nie auf Produktivdaten testen.

## Deploy-Nachweis

- `GET /health` meldet `version` gleich dem ausgerollten Commit (`GIT_SHA` im Image).
- Ein Pfad, den es nur im neuen Stand gibt, antwortet 200; ein Unsinnspfad 404.
- EasyPanel: `services.app.inspectService` → `commit.hash` gegen lokalen HEAD vergleichen.
- Fachprüfung: Code eines Kurses eingeben, eine Unterlage herunterladen, Datei öffnet sich.

## Diagnose

- `GET /health` zeigt Version, Startzeit und ob die Datenbank schreibbar ist.
- Logs: EasyPanel-Konsole des Dienstes `app`.
- «Datei nicht gefunden» beim Download: ein Eintrag in `unterlage` zeigt auf eine `ablage`,
  die im Volume fehlt – meist ein Deploy ohne Volume oder ein wiederhergestellter
  Mischstand. Prüfen: Zeilen in `unterlage` gegen Dateien in `/data/unterlagen/`.
- Admin-Konto zurücksetzen (auf dem Server; Kurse und Unterlagen bleiben):

      python -c "import sqlite3; c=sqlite3.connect('/data/kursunterlagen.sqlite3'); c.execute('DELETE FROM admin'); c.commit()"

  dann `ADMIN_INITIAL_PASSWORD` setzen, Dienst neu starten, anmelden, Variable leeren.

## Umgebungsvariablen

Siehe `.env.example`. Werte in `~/.claude/secrets.local.md`, nie hier – das Repository ist
public.
