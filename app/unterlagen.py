"""Unterlagen: Datei ablegen, auflisten, ausliefern, zählen.

Die Datei liegt im Dateisystem (`DATA_DIR/unterlagen/`), die Datenbank hält nur die
Angaben dazu. Der Name im Dateisystem wird **selbst vergeben** – nie der Name, den jemand
hochgeladen hat (CLAUDE.md).
"""
import re
import sqlite3
import uuid
from pathlib import Path

from app import db

# Positivliste: was nicht hier steht, wird nicht angenommen.
ERLAUBT = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".zip": "application/zip",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
}


class Abgelehnt(ValueError):
    """Die Datei wird nicht angenommen – die Meldung ist für die Oberfläche gedacht."""


def endung_von(dateiname: str) -> str:
    return Path(dateiname or "").suffix.lower()


def pruefen(dateiname: str, groesse: int, max_bytes: int) -> str:
    """Gibt die Endung zurück oder wirft `Abgelehnt` mit einem Satz für die Oberfläche."""
    endung = endung_von(dateiname)
    if endung not in ERLAUBT:
        erlaubt = ", ".join(sorted(ERLAUBT))
        raise Abgelehnt(f"Dieser Dateityp geht nicht. Erlaubt sind: {erlaubt}")
    if groesse <= 0:
        raise Abgelehnt("Die Datei ist leer.")
    if groesse > max_bytes:
        raise Abgelehnt(f"Die Datei ist zu gross (höchstens {max_bytes // (1024 * 1024)} MB).")
    return endung


def anzeigename(dateiname: str) -> str:
    """Name für den Download: ohne Pfad, ohne Steuerzeichen, nicht leer.

    Der Pfad wird selbst abgeschnitten, nicht mit `Path(...).name`: unter Windows gilt
    `a:b.pdf` als Laufwerksangabe, auf dem Server nicht – der Name soll überall gleich
    herauskommen.
    """
    nur_name = re.split(r"[\\/]", dateiname or "")[-1]
    sauber = re.sub(r'[\x00-\x1f"\\/:*?<>|]', "_", nur_name).strip(" .")
    return sauber or "unterlage"


def ablagename(endung: str) -> str:
    """Eigener Name im Dateisystem – damit kein Hochgeladenes den Pfad bestimmt."""
    return f"{uuid.uuid4().hex}{endung}"


def pfad(ordner: Path, ablage: str) -> Path:
    """Immer über diese Funktion: `ablage` darf den Ordner nicht verlassen können."""
    ziel = (ordner / Path(ablage).name).resolve()
    if ordner.resolve() not in ziel.parents:
        raise ValueError("Ablagename zeigt aus dem Ordner heraus.")
    return ziel


def speichern(
    conn: sqlite3.Connection,
    ordner: Path,
    kurs_id: int,
    titel: str,
    dateiname: str,
    daten: bytes,
    max_bytes: int,
    beschreibung: str = "",
) -> int:
    """Legt die Datei ab und schreibt die Zeile. Schlägt eines fehl, bleibt nichts zurück."""
    titel = (titel or "").strip()
    if not titel:
        raise Abgelehnt("Die Unterlage braucht einen Titel.")
    endung = pruefen(dateiname, len(daten), max_bytes)

    ordner.mkdir(parents=True, exist_ok=True)
    ablage = ablagename(endung)
    ziel = pfad(ordner, ablage)
    ziel.write_bytes(daten)
    try:
        cursor = conn.execute(
            "INSERT INTO unterlage (kurs_id, titel, beschreibung, dateiname, ablage, mime,"
            " groesse, sortierung, hochgeladen_am)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                kurs_id,
                titel,
                (beschreibung or "").strip() or None,
                anzeigename(dateiname),
                ablage,
                ERLAUBT[endung],
                len(daten),
                naechste_sortierung(conn, kurs_id),
                db.iso(db.jetzt()),
            ),
        )
    except sqlite3.Error:
        ziel.unlink(missing_ok=True)   # keine Datei ohne Zeile
        raise
    return int(cursor.lastrowid)


def naechste_sortierung(conn: sqlite3.Connection, kurs_id: int) -> int:
    zeile = conn.execute(
        "SELECT coalesce(max(sortierung), 0) + 10 FROM unterlage WHERE kurs_id = ?", (kurs_id,)
    ).fetchone()
    return int(zeile[0])


def alle_fuer(
    conn: sqlite3.Connection, kurs_id: int, nur_sichtbare: bool = False
) -> list[sqlite3.Row]:
    bedingung = " AND sichtbar = 1" if nur_sichtbare else ""
    return list(
        conn.execute(
            f"SELECT * FROM unterlage WHERE kurs_id = ?{bedingung}"
            " ORDER BY sortierung, id",
            (kurs_id,),
        )
    )


def finden(conn: sqlite3.Connection, unterlage_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM unterlage WHERE id = ?", (unterlage_id,)).fetchone()


def fuer_kurs(
    conn: sqlite3.Connection, kurs_id: int, unterlage_id: int
) -> sqlite3.Row | None:
    """Die Rechteprüfung beim Download: gehört diese Unterlage wirklich zu diesem Kurs?"""
    return conn.execute(
        "SELECT * FROM unterlage WHERE id = ? AND kurs_id = ? AND sichtbar = 1",
        (unterlage_id, kurs_id),
    ).fetchone()


def aendern(
    conn: sqlite3.Connection, unterlage_id: int, titel: str, beschreibung: str = ""
) -> None:
    titel = (titel or "").strip()
    if not titel:
        raise Abgelehnt("Die Unterlage braucht einen Titel.")
    conn.execute(
        "UPDATE unterlage SET titel = ?, beschreibung = ? WHERE id = ?",
        (titel, (beschreibung or "").strip() or None, unterlage_id),
    )


def sichtbar_setzen(conn: sqlite3.Connection, unterlage_id: int, sichtbar: bool) -> None:
    """Ausblenden statt löschen (CLAUDE.md). Die Datei bleibt liegen."""
    conn.execute(
        "UPDATE unterlage SET sichtbar = ? WHERE id = ?",
        (1 if sichtbar else 0, unterlage_id),
    )


def verschieben(conn: sqlite3.Connection, unterlage_id: int, schritte: int) -> None:
    """Sortierung ändern: negativ nach oben, positiv nach unten."""
    conn.execute(
        "UPDATE unterlage SET sortierung = max(0, sortierung + ?) WHERE id = ?",
        (schritte * 15, unterlage_id),
    )


def download_merken(conn: sqlite3.Connection, kurs_id: int, unterlage_id: int) -> None:
    """Anonym: Zeit, Kurs, Unterlage – keine IP, kein Name (docs/DATENSCHUTZ.md)."""
    conn.execute(
        "INSERT INTO download (zeit, kurs_id, unterlage_id) VALUES (?, ?, ?)",
        (db.iso(db.jetzt()), kurs_id, unterlage_id),
    )


def downloads_je_unterlage(conn: sqlite3.Connection, kurs_id: int) -> dict[int, int]:
    return {
        int(z["unterlage_id"]): int(z["anzahl"])
        for z in conn.execute(
            "SELECT unterlage_id, count(*) AS anzahl FROM download WHERE kurs_id = ?"
            " GROUP BY unterlage_id",
            (kurs_id,),
        )
    }


def lesbare_groesse(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_} B"
    if bytes_ < 1024 * 1024:
        return f"{bytes_ / 1024:.0f} KB"
    return f"{bytes_ / (1024 * 1024):.1f} MB".replace(".", ",")
