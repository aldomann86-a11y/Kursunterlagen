"""Bremse gegen Durchprobieren – für das Admin-Passwort und später für Zugangscodes.

Gezählt werden nur **Fehlversuche**, je Art und Absender, in einem gleitenden Fenster von
einer Stunde. Die Absender-IP wird nie im Klartext gespeichert, sondern als HMAC mit dem
SECRET_KEY: damit lässt sich ein Versuch derselben Quelle zuordnen, aber keine IP
zurückrechnen (docs/DATENSCHUTZ.md, `versuch`).
"""
import hashlib
import hmac
import sqlite3
from datetime import timedelta

from fastapi import Request

from app import db

AUFBEWAHRUNG_STUNDEN = 24


def ip_hash(secret_key: str, ip: str | None) -> str:
    quelle = (ip or "unbekannt").encode("utf-8")
    return hmac.new(secret_key.encode("utf-8"), quelle, hashlib.sha256).hexdigest()


def absender(request: Request, secret_key: str) -> str:
    """Hinter dem Reverse-Proxy liefert uvicorn mit --proxy-headers die echte IP."""
    ip = request.client.host if request.client else None
    return ip_hash(secret_key, ip)


def merken(conn: sqlite3.Connection, art: str, absender_hash: str) -> None:
    conn.execute(
        "INSERT INTO versuch (zeit, art, ip_hash) VALUES (?, ?, ?)",
        (db.iso(db.jetzt()), art, absender_hash),
    )


def anzahl(conn: sqlite3.Connection, art: str, absender_hash: str) -> int:
    seit = db.iso(db.jetzt() - timedelta(hours=1))
    zeile = conn.execute(
        "SELECT count(*) FROM versuch WHERE art = ? AND ip_hash = ? AND zeit >= ?",
        (art, absender_hash, seit),
    ).fetchone()
    return int(zeile[0])


def gesperrt(conn: sqlite3.Connection, art: str, absender_hash: str, grenze: int) -> bool:
    return anzahl(conn, art, absender_hash) >= grenze


def zuruecksetzen(conn: sqlite3.Connection, art: str, absender_hash: str) -> None:
    """Nach erfolgreicher Anmeldung sind die Fehlversuche dieser Quelle erledigt."""
    conn.execute("DELETE FROM versuch WHERE art = ? AND ip_hash = ?", (art, absender_hash))


def aufraeumen(conn: sqlite3.Connection) -> int:
    """Alles älter als 24 Stunden löschen (Löschfrist aus docs/DATENSCHUTZ.md)."""
    grenze = db.iso(db.jetzt() - timedelta(hours=AUFBEWAHRUNG_STUNDEN))
    cursor = conn.execute("DELETE FROM versuch WHERE zeit < ?", (grenze,))
    return cursor.rowcount or 0
