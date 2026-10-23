"""Das Admin-Konto: Passwort, zweiter Faktor, Anlegen beim ersten Start.

Es gibt genau ein Konto (Tabelle `admin`, `id = 1`). Mehr braucht die App nicht: sie hat
eine Person, die Unterlagen hochlädt. Teilnehmer melden sich nie an (docs/ENTSCHEIDE.md).
"""
import io
import sqlite3

import bcrypt
import pyotp
import segno

from app import db

MINDESTLAENGE = 12
# bcrypt verarbeitet nur die ersten 72 Bytes. Ein längeres Passwort würde stillschweigend
# abgeschnitten – dann wäre ein Teil davon wirkungslos, ohne dass es jemand merkt.
MAX_BYTES = 72


def pruefe_passwortlaenge(klartext: str) -> str | None:
    """Gibt den Grund zurück, warum das Passwort nicht geht – oder None, wenn es geht."""
    if len(klartext) < MINDESTLAENGE:
        return f"Das Passwort braucht mindestens {MINDESTLAENGE} Zeichen."
    if len(klartext.encode("utf-8")) > MAX_BYTES:
        return "Das Passwort ist zu lang (höchstens 72 Zeichen, Umlaute zählen doppelt)."
    return None


def hash_passwort(klartext: str) -> str:
    grund = pruefe_passwortlaenge(klartext)
    if grund:
        raise ValueError(grund)
    return bcrypt.hashpw(klartext.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def passwort_stimmt(klartext: str, gespeichert: str) -> bool:
    if not klartext or not gespeichert:
        return False
    if len(klartext.encode("utf-8")) > MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(klartext.encode("utf-8"), gespeichert.encode("ascii"))
    except ValueError:
        # Kaputter Hash in der Datenbank: dann stimmt eben nichts.
        return False


def lesen(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM admin WHERE id = 1").fetchone()


def anlegen(conn: sqlite3.Connection, klartext: str) -> None:
    """Legt das Konto an. Ein bestehendes Konto wird **nie** überschrieben."""
    if lesen(conn) is not None:
        return
    conn.execute(
        "INSERT INTO admin (id, passwort_hash, erstellt_am) VALUES (1, ?, ?)",
        (hash_passwort(klartext), db.iso(db.jetzt())),
    )


def passwort_setzen(conn: sqlite3.Connection, klartext: str) -> None:
    conn.execute(
        "UPDATE admin SET passwort_hash = ? WHERE id = 1", (hash_passwort(klartext),)
    )


# --- Zweiter Faktor ----------------------------------------------------------------

def neues_totp_secret() -> str:
    return pyotp.random_base32()


def totp_secret_setzen(conn: sqlite3.Connection, secret: str) -> None:
    """Noch unbestätigt: erst die erste richtige Eingabe schaltet den Faktor scharf."""
    conn.execute(
        "UPDATE admin SET totp_secret = ?, totp_bestaetigt = 0 WHERE id = 1", (secret,)
    )


def totp_bestaetigen(conn: sqlite3.Connection) -> None:
    conn.execute("UPDATE admin SET totp_bestaetigt = 1 WHERE id = 1")


def totp_stimmt(secret: str | None, code: str) -> bool:
    if not secret or not code:
        return False
    # valid_window=1: ein Schritt (30 s) Toleranz, weil Handy-Uhren leicht abweichen.
    return pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=1)


def totp_uri(secret: str, konto: str = "admin", herausgeber: str = "Kursunterlagen") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=konto, issuer_name=herausgeber)


def qr_svg(uri: str) -> str:
    """QR-Code als SVG-Text, direkt ins Template – kein externer Dienst (DS-Basis B3).

    segno schreibt Bytes, darum BytesIO und decode. Das `xmlns` im SVG ist eine Kennung,
    keine Adresse, von der etwas geladen wird.
    """
    puffer = io.BytesIO()
    segno.make(uri, error="m").save(puffer, kind="svg", scale=5, border=2, xmldecl=False)
    return puffer.getvalue().decode("utf-8")
