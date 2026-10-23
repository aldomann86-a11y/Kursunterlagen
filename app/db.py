"""SQLite ohne ORM. Fünf Tabellen, eine Verbindung je Anfrage.

Warum so: docs/ENTSCHEIDE.md (23.10.2026). Kein Alembic – das Schema entsteht mit
CREATE TABLE IF NOT EXISTS. Kommt später eine Spalte dazu, wird sie in `nachziehen()`
mit einem geprüften ALTER TABLE ergänzt (Muster ../kimas-post/app/db.py).

Die hochgeladenen Dateien liegen **nicht** hier, sondern unter DATA_DIR/unterlagen/.
Die Tabelle `unterlage` hält nur den Ablagenamen.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

SCHWEIZ = ZoneInfo("Europe/Zurich")

SCHEMA = """
CREATE TABLE IF NOT EXISTS kurs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    datum         TEXT,
    code_hash     TEXT    NOT NULL UNIQUE,
    aktiv         INTEGER NOT NULL DEFAULT 1,
    offen_bis     TEXT,
    erstellt_am   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS unterlage (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    kurs_id        INTEGER NOT NULL REFERENCES kurs(id),
    titel          TEXT    NOT NULL,
    beschreibung   TEXT,
    dateiname      TEXT    NOT NULL,
    ablage         TEXT    NOT NULL UNIQUE,
    mime           TEXT    NOT NULL,
    groesse        INTEGER NOT NULL,
    sortierung     INTEGER NOT NULL DEFAULT 0,
    sichtbar       INTEGER NOT NULL DEFAULT 1,
    hochgeladen_am TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_unterlage_kurs ON unterlage(kurs_id, sortierung);

CREATE TABLE IF NOT EXISTS download (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    zeit          TEXT    NOT NULL,
    kurs_id       INTEGER NOT NULL,
    unterlage_id  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_download_zeit ON download(zeit);

CREATE TABLE IF NOT EXISTS admin (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    passwort_hash   TEXT    NOT NULL,
    totp_secret     TEXT,
    totp_bestaetigt INTEGER NOT NULL DEFAULT 0,
    erstellt_am     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS versuch (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    zeit          TEXT    NOT NULL,
    art           TEXT    NOT NULL DEFAULT 'code',   -- 'code' oder 'login'
    ip_hash       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_versuch_zeit ON versuch(art, zeit, ip_hash);
"""

TABELLEN = ("kurs", "unterlage", "download", "admin", "versuch")


def jetzt() -> datetime:
    return datetime.now(timezone.utc)


def iso(t: datetime) -> str:
    """Immer UTC, immer gleiches Format – damit Zeichenkettenvergleiche in SQL stimmen."""
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def aus_iso(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def anzeige(text: str) -> str:
    """Gespeicherte UTC-Zeit als Schweizer Ortszeit, z. B. «23.10.2026 09:05»."""
    return aus_iso(text).astimezone(SCHWEIZ).strftime("%d.%m.%Y %H:%M")


class Datenbank:
    def __init__(self, pfad: Path):
        self.pfad = pfad

    def einrichten(self) -> None:
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        with self.verbindung() as conn:
            conn.executescript(SCHEMA)
            nachziehen(conn)

    @contextmanager
    def verbindung(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.pfad, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        # Fremdschlüssel sind in SQLite je Verbindung abzuschalten/einzuschalten.
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

    def schreibbar(self) -> bool:
        """Für /health: lässt sich die Datei wirklich beschreiben, nicht nur öffnen?"""
        try:
            with self.verbindung() as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS probe (id INTEGER PRIMARY KEY)")
                conn.execute("DROP TABLE probe")
            return True
        except sqlite3.Error:
            return False


def spalten(conn: sqlite3.Connection, tabelle: str) -> set[str]:
    return {z["name"] for z in conn.execute(f"PRAGMA table_info({tabelle})")}


def nachziehen(conn: sqlite3.Connection) -> None:
    """Spalten, die nach dem ersten Ausrollen dazukamen. Jede Ergänzung mit einem Datum."""
    # 23.10.2026 (E3): `versuch` zählt jetzt auch Fehlversuche beim Admin-Login, nicht nur
    # beim Zugangscode. Bestehende Zeilen sind Code-Versuche.
    if "art" not in spalten(conn, "versuch"):
        conn.execute("ALTER TABLE versuch ADD COLUMN art TEXT NOT NULL DEFAULT 'code'")
