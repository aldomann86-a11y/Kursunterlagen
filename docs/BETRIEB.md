# Betrieb

## Instanzen

| Instanz | URL | Wo | Deploy-Auslöser |
|---|---|---|---|
| Lokal | http://127.0.0.1:8050 | `python -m uvicorn app.main:erzeuge_app --factory --reload --port 8050`, Eintrag `kursunterlagen` in `_Claude/.claude/launch.json` | – |
| Prod | https://kurs.kimas.ch | EasyPanel-Server (ATSOBL, 46.225.160.97), Projekt `kursunterlagen` / Dienst `app`, Git `main`, Dockerfile-Build, Volume `data` → `/data` | Push allein deployt **nicht** (Auto-Deploy bleibt aus); ausgerollt wird von Hand über `/deploy` |

**Achtung:** Steht hier je «Push», muss die Sicherung **vor** dem Push entstehen.

Keine Dev-Instanz: lokal reicht die Datenbankdatei unter `./data/`.

## Einrichtung Prod (E2, entschieden am 23.10.2026)

Für EasyPanel, per API wie bei `feedbackbox` und `kimas-post`. Vorher muss der A-Eintrag
`kurs.kimas.ch` auf `46.225.160.97` zeigen, sonst gibt es kein Zertifikat:

1. Projekt `kursunterlagen`, Dienst `app`, Git-Quelle `main`, Dockerfile-Build.
   Auto-Deploy **aus** – sonst stimmt die Zeile oben nicht mehr.
2. Volume `data` auf `/data`. **Darin liegen Datenbank und alle Unterlagen** – ohne Volume
   ist nach jedem Deploy alles weg.
3. ENV aus `.env.example`:
   - `SECRET_KEY` **einmal** erzeugen und in `~/.claude/secrets.local.md` ablegen.
     Er signiert nicht nur die Sitzungen, er ist auch der HMAC-Schlüssel der Zugangscodes:
     **wird er später geändert, passt kein ausgegebener Code mehr** (`app/kurse.py`).
   - `ADMIN_INITIAL_PASSWORD` einmal setzen, nach der ersten Anmeldung leeren.
   - `HTTPS_ONLY=1` (sonst sind die Cookies nicht `secure`), `DATA_DIR=/data`.
   - `ADMIN_2FA=1` empfohlen: hinter dem Reverse-Proxy lässt sich die Bremse über einen
     mitgeschickten `X-Forwarded-For` aushebeln (der Start nutzt `--forwarded-allow-ips='*'`),
     dann ist der zweite Faktor der eigentliche Schutz des Admin-Logins.
   - `GIT_SHA` auf den ausgerollten Commit setzen, sonst meldet `/health` eine leere
     `version` und der Deploy-Nachweis unten greift nicht.
4. Domain auf Port 8000, A-Eintrag der Subdomain auf 46.225.160.97.
5. Erster Deploy, anmelden, `ADMIN_INITIAL_PASSWORD` wieder leeren.
6. Bremse prüfen: zehnmal ein falsches Passwort mit `-H "X-Forwarded-For: 1.2.3.4"`
   schicken. Greift die Sperre trotzdem, ist alles gut; greift sie nicht, bleibt
   `ADMIN_2FA=1` Pflicht.

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
