# Entscheide

Jeder Eintrag: Datum, Entscheid, Grund, Alternativen. Neueste oben. Wer davon abweicht,
ergänzt einen neuen Eintrag, statt den alten zu ändern.

## 2026-10-23 – Prod auf EasyPanel, kurs.kimas.ch

**Entscheid:** Die App läuft auf dem bestehenden EasyPanel-Server (ATSOBL, 46.225.160.97),
Projekt `kursunterlagen` / Dienst `app`, Build aus dem Dockerfile, Git-Quelle `main` des
öffentlichen Repos, Volume `data` auf `/data`, Domain `kurs.kimas.ch`. Ein Push allein
rollt **nicht** aus; ausgerollt wird von Hand über `/deploy`. In Produktion ist der zweite
Faktor eingeschaltet (`ADMIN_2FA=1`), weil die Bremse hinter dem Reverse-Proxy über einen
mitgeschickten `X-Forwarded-For` aushebelbar ist.
**Grund:** Der Server läuft, die Volume-Sicherung des Hosts greift, und eine Instanz steht
in einer Stunde. Ein eigener Stack auf dem KIMAS-Kern bräuchte Servervorlage, Deploy-
Schlüssel, restic und DNS – für ein Kursportal unverhältnismässig (F1, erledigt).
**Verworfen:** KIMAS-Kern (Aufwand, s. o.); nur im Schulnetz (nach dem Kurs nicht mehr
erreichbar – und genau dann holen die Teilnehmer die Unterlagen).

## 2026-10-23 – Zugangscode als HMAC, nicht als bcrypt-Hash

**Entscheid:** Der Zugangscode eines Kurses steht als HMAC-SHA256 (Schlüssel: `SECRET_KEY`)
in `kurs.code_hash`, mit Unique-Index. Die Prüfung ist damit **eine** Abfrage. Gesäubert
wird auf Buchstaben und Zahlen, also kommt auch hinein, wer «K7M3 RP29» tippt oder den
Bindestrich vergisst. Das Admin-Passwort bleibt bcrypt.
**Grund:** Mit bcrypt müsste jede Eingabe gegen *jeden* Kurs einzeln gerechnet werden –
bei 20 Kursen mehrere Sekunden je Versuch, und eine Handvoll Aufrufe genügte, um die App
auszubremsen. Ein Zugangscode ist ein geteiltes Kennwort ohne Personenbezug: der Schutz
gegen Durchprobieren kommt aus der Bremse (`LIMIT_CODE_STUNDE`), nicht aus der Rechenzeit.
Ohne `SECRET_KEY` ist der HMAC nicht rückrechenbar – ein nackter SHA-256 über ein
achtstelliges Wort wäre es.
**Verworfen:** bcrypt je Kurs (zu langsam, s. o.); Code im Klartext in der Datenbank (ein
Blick in die Sicherung zeigte alle Kurse); Code nur im Cookie ohne Datenbankprüfung.

## 2026-10-23 – Funktionsschicht vor dem Kurs, Oberfläche im Kurs

**Entscheid:** `app/kurse.py` und `app/unterlagen.py` (Codes, Ablage, Positivliste,
Rechteprüfung, Zähler) sind samt Tests **vor** dem Kurs gebaut. Im Unterricht entstehen nur
noch Routen und Vorlagen – die Prompts dafür stehen in `docs/KURS_PROMPTS.md`.
**Grund:** In rund 15 Minuten Bauzeit muss jeder Schritt sitzen. Was schiefgehen kann
(Dateinamen, Pfadausbruch, Positivliste, Fristen, anonymes Zählen), ist geprüft; was man
sehen will (Formular, Liste, Download), entsteht live. Zwei Fehler, die genau so nur hier
auffielen: `Path(...).name` liest unter Windows `a:b.pdf` als Laufwerk, und ein Code ohne
Bindestrich passte nicht – beides wäre im Unterricht Zeitverlust gewesen.
**Verworfen:** alles vorher bauen (dann bleibt nichts zu zeigen); alles live bauen
(15 Minuten reichen nicht, und ein Fehlschlag vor der Klasse kostet den Rest der Lektion).

## 2026-10-23 – Admin-Zugang: ein Konto, Cookie-Sitzung, zweiter Faktor umschaltbar

**Entscheid:**
- **Ein** Admin-Konto (`admin`, `id = 1`), Passwort als bcrypt-Hash, mindestens 12 Zeichen
  und höchstens 72 Bytes – länger schneidet bcrypt stillschweigend ab, darum lehnen wir es ab.
- Erstes Passwort über `ADMIN_INITIAL_PASSWORD` beim Start. Ein **bestehendes** Konto wird
  nie überschrieben, also darf die Variable gesetzt bleiben.
- Sitzung als signiertes Cookie (itsdangerous, 12 Stunden, `httponly`, `samesite=lax`,
  `secure` sobald `HTTPS_ONLY=1`). Kein Sitzungsspeicher auf dem Server; im Cookie steht
  nur, *dass* jemand angemeldet ist.
- Zweiter Faktor über `ADMIN_2FA` umschaltbar (TOTP mit **pyotp**, QR-Code lokal mit
  **segno**). Er wird erst scharf, wenn die erste Eingabe stimmt (`totp_bestaetigt`); ein
  bestätigter Faktor lässt sich nicht aus einer halb offenen Sitzung ersetzen.
- Fehlversuche je Stunde und Quelle begrenzt (`LIMIT_LOGIN_STUNDE`, Vorgabe 10). Die
  Tabelle `versuch` bekommt dafür die Spalte `art` (`'code'` oder `'login'`); bestehende
  Zeilen gelten als Code-Versuche (`app/db.py`, `nachziehen()`).
- Die Oberfläche verrät nie, *was* falsch war oder ob ein Konto besteht.

**Grund:** Die globale Regel will einen eigenen Login mit umschaltbarer 2FA, kein Authelia.
Das Muster steht in `../kimas-post` – gleiche Bausteine, gleiche Begriffe, zwei kleine
Pakete (pyotp, segno), beide reines Python ohne Übersetzer.
**Verworfen:** 2FA-Pflicht (D1 verlangt sie nicht; der Schalter genügt); Benutzertabelle mit
mehreren Konten (es gibt eine Person); Sitzungen in der Datenbank (ein Cookie reicht, nichts
zu putzen); Passwort-Reset per Mail (dafür gibt es `kimas-post`, erst wenn jemand ihn braucht).

## 2026-10-23 – Datenmodell (fünf Tabellen)

**Entscheid:** Das Schema entsteht in `app/db.py` als `CREATE TABLE IF NOT EXISTS`, ohne ORM
und ohne Alembic. Spätere Spalten kommen über ein geprüftes `ALTER TABLE` dazu (Muster
`../kimas-post/app/db.py`). Zeiten als ISO-Text in UTC, damit Vergleiche in SQL stimmen.

```sql
-- Ein Kurs ist die Klammer um die Unterlagen und trägt den Zugangscode.
CREATE TABLE kurs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,          -- "Claude Code Grundkurs Z-Part"
    datum         TEXT,                      -- Kursdatum, nur Anzeige
    code_hash     TEXT    NOT NULL UNIQUE,   -- bcrypt, Klartext nur einmal bei der Vergabe
    aktiv         INTEGER NOT NULL DEFAULT 1,
    offen_bis     TEXT,                      -- ab dann kein Zugang mehr (leer = unbefristet)
    erstellt_am   TEXT    NOT NULL
);

-- Eine Unterlage ist eine Datei. Die Datei selbst liegt im Dateisystem.
CREATE TABLE unterlage (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kurs_id       INTEGER NOT NULL REFERENCES kurs(id),
    titel         TEXT    NOT NULL,          -- "Teilnehmer-Handout"
    beschreibung  TEXT,
    dateiname     TEXT    NOT NULL,          -- Name beim Herunterladen
    ablage        TEXT    NOT NULL UNIQUE,   -- Name unter DATA_DIR/unterlagen/, selbst vergeben
    mime          TEXT    NOT NULL,
    groesse       INTEGER NOT NULL,
    sortierung    INTEGER NOT NULL DEFAULT 0,
    sichtbar      INTEGER NOT NULL DEFAULT 1, -- deaktivieren statt löschen
    hochgeladen_am TEXT   NOT NULL
);
CREATE INDEX ix_unterlage_kurs ON unterlage(kurs_id, sortierung);

-- Download-Protokoll, anonym: zeigt was gezogen wurde, nie von wem.
CREATE TABLE download (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    zeit          TEXT    NOT NULL,
    kurs_id       INTEGER NOT NULL,
    unterlage_id  INTEGER NOT NULL
);
CREATE INDEX ix_download_zeit ON download(zeit);

-- Ein Admin-Konto, wie in kimas-post.
CREATE TABLE admin (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    passwort_hash   TEXT    NOT NULL,
    totp_secret     TEXT,
    totp_bestaetigt INTEGER NOT NULL DEFAULT 0,
    erstellt_am     TEXT    NOT NULL
);

-- Fehlversuche bei der Code-Eingabe, für das Stundenlimit. Älteres wird gelöscht.
CREATE TABLE versuch (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    zeit          TEXT    NOT NULL,
    ip_hash       TEXT    NOT NULL           -- HMAC mit SECRET_KEY, nicht rückrechenbar
);
CREATE INDEX ix_versuch_zeit ON versuch(zeit, ip_hash);
```

**Grund:** Fünf Tabellen reichen für Hochladen, Zugang und Download. Ohne ORM ist jeder
Datenbankzugriff im Kurs am Bildschirm lesbar; SQLite braucht keinen zweiten Dienst.
**Verworfen:** Dateien als BLOB in der Datenbank (Sicherung und Speicher unnötig teuer);
Postgres mit SQLAlchemy und Alembic (drei Werkzeuge mehr, die im Kurs erklärt werden müssten);
Teilnehmer-Tabelle mit Konten (Personendaten, siehe nächster Eintrag).

## 2026-10-23 – Zugang über einen Code je Kurs, keine Konten

**Entscheid:** Teilnehmer geben einen Code je Kurs ein (z. B. `zpart-2026`), bekommen ein
signiertes Sitzungs-Cookie mit der `kurs_id` und sehen nur die Unterlagen dieses Kurses.
Keine Registrierung, keine E-Mail, kein Name. Ein Stundenlimit je IP gegen Erraten.
**Grund:** Ohne Konten gibt es keine Personendaten, also keine Benutzerverwaltung, kein
Passwort-Reset, keine Löschfristen – und im Kurs ist das in einer Lektion gebaut.
**Verworfen:** ganz offen (Unterlagen wären öffentlich im Netz); Login je Teilnehmer
(Personendaten D1, Benutzerverwaltung, Mailversand, Löschfristen – für ein Kurs-Handout
unverhältnismässig).

## 2026-10-23 – Unterlagen über einen Admin-Bereich hochladen

**Entscheid:** Unterlagen kommen über ein Upload-Formular im Admin-Bereich in die App, nicht
als Dateien ins Repository. Die Datei landet unter `DATA_DIR/unterlagen/` mit selbst vergebenem
Namen, die Datenbank hält Titel, Kurs und Herkunftsname.
**Grund:** Eine neue Unterlage soll keinen Deploy brauchen. Das Repository ist public –
Unterlagen gehören nicht hinein. Und Formular → Datei → Datenbank → geschützter Download ist
genau der Bogen, der im Kurs gezeigt werden soll.
**Verworfen:** Dateien im Repository (jede Änderung ein Deploy, alles öffentlich).

## 2026-10-23 – Python 3.12 + FastAPI + SQLite ohne ORM

**Entscheid:** Stack wie `../kimas-post`: FastAPI, sqlite3 direkt, Jinja2 + HTMX, bcrypt,
itsdangerous, pytest, Docker. Abweichung vom Projektstandard (PostgreSQL) ist gewollt.
**Grund:** Das Projekt ist Lehrmittel und Anwendung in einem. Eine Datenbankdatei ohne
zweiten Dienst läuft lokal sofort, ist in der Sicherung eine Datei und im Kurs erklärbar.
Die Datenmenge ist winzig (Dutzende Unterlagen, keine gleichzeitigen Schreiber).
**Verworfen:** Next.js + PostgreSQL (Node, pnpm, Prisma, Datenbank-Container – im Kurs
Reibung statt Inhalt); Next.js + SQLite (Frontend-Werkzeuge ohne Nutzen für ein Formular
und eine Liste).
