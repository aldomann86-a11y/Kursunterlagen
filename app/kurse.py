"""Kurse und ihre Zugangscodes.

Ein Kurs ist die Klammer um die Unterlagen. Wer den Code des Kurses kennt, sieht dessen
Unterlagen – mehr Zugang gibt es nicht (docs/ENTSCHEIDE.md).

Der Code steht nur als HMAC in der Datenbank: so lässt sich mit einer Abfrage prüfen,
ob ein eingegebener Code passt, ohne ihn im Klartext zu halten.
"""
import hashlib
import hmac
import re
import secrets
import sqlite3
from datetime import datetime, timezone

from app import db

# Codes zum Vorlesen und Abtippen: keine Verwechslung von 0/O und 1/l/I.
ZEICHEN = "abcdefghjkmnpqrstuvwxyz23456789"
CODE_LAENGE = 8


def neuer_code() -> str:
    """Zum Beispiel «k7m3-rp29» – kurz genug fürs Beamer-Bild, lang genug gegen Raten."""
    rohwert = "".join(secrets.choice(ZEICHEN) for _ in range(CODE_LAENGE))
    return f"{rohwert[:4]}-{rohwert[4:]}"


def saeubern(code: str) -> str:
    """Nur Buchstaben und Zahlen zählen.

    So kommt auch hinein, wer «K7M3 RP29» tippt oder den Bindestrich vergisst – vom
    Beamer abgelesen passiert genau das.
    """
    return re.sub(r"[^a-z0-9]", "", (code or "").lower())


def code_hash(secret_key: str, code: str) -> str:
    return hmac.new(
        secret_key.encode("utf-8"), saeubern(code).encode("utf-8"), hashlib.sha256
    ).hexdigest()


def anlegen(
    conn: sqlite3.Connection,
    secret_key: str,
    name: str,
    datum: str | None = None,
    offen_bis: str | None = None,
) -> tuple[int, str]:
    """Legt den Kurs an und gibt (id, Code im Klartext) zurück.

    Der Klartext wird **nirgends** gespeichert – wer ihn verliert, lässt einen neuen
    erzeugen (`code_neu_setzen`).
    """
    name = name.strip()
    if not name:
        raise ValueError("Der Kurs braucht einen Namen.")
    for _ in range(5):
        code = neuer_code()
        try:
            cursor = conn.execute(
                "INSERT INTO kurs (name, datum, code_hash, offen_bis, erstellt_am)"
                " VALUES (?, ?, ?, ?, ?)",
                (name, datum or None, code_hash(secret_key, code), offen_bis or None,
                 db.iso(db.jetzt())),
            )
            return int(cursor.lastrowid), code
        except sqlite3.IntegrityError:
            continue        # derselbe Code zweimal: neu würfeln
    raise RuntimeError("Es liess sich kein freier Zugangscode finden.")


def code_neu_setzen(conn: sqlite3.Connection, secret_key: str, kurs_id: int) -> str:
    code = neuer_code()
    conn.execute("UPDATE kurs SET code_hash = ? WHERE id = ?",
                 (code_hash(secret_key, code), kurs_id))
    return code


def alle(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM kurs ORDER BY aktiv DESC, id DESC"))


def finden(conn: sqlite3.Connection, kurs_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM kurs WHERE id = ?", (kurs_id,)).fetchone()


def ist_offen(kurs: sqlite3.Row, jetzt: datetime | None = None) -> bool:
    """Offen heisst: aktiv und nicht abgelaufen. `offen_bis` ist ein Tag (JJJJ-MM-TT)."""
    if not kurs["aktiv"]:
        return False
    if not kurs["offen_bis"]:
        return True
    heute = (jetzt or db.jetzt()).astimezone(timezone.utc).strftime("%Y-%m-%d")
    return heute <= kurs["offen_bis"]


def mit_code(
    conn: sqlite3.Connection, secret_key: str, code: str
) -> sqlite3.Row | None:
    """Der Kurs zu diesem Code – oder None, wenn er falsch, gesperrt oder abgelaufen ist."""
    if not saeubern(code):
        return None
    kurs = conn.execute(
        "SELECT * FROM kurs WHERE code_hash = ?", (code_hash(secret_key, code),)
    ).fetchone()
    if kurs is None or not ist_offen(kurs):
        return None
    return kurs


def aendern(
    conn: sqlite3.Connection,
    kurs_id: int,
    name: str,
    datum: str | None = None,
    offen_bis: str | None = None,
) -> None:
    name = name.strip()
    if not name:
        raise ValueError("Der Kurs braucht einen Namen.")
    conn.execute(
        "UPDATE kurs SET name = ?, datum = ?, offen_bis = ? WHERE id = ?",
        (name, datum or None, offen_bis or None, kurs_id),
    )


def aktiv_setzen(conn: sqlite3.Connection, kurs_id: int, aktiv: bool) -> None:
    """Sperren statt löschen: die Unterlagen und der Zähler bleiben erhalten."""
    conn.execute("UPDATE kurs SET aktiv = ? WHERE id = ?", (1 if aktiv else 0, kurs_id))
