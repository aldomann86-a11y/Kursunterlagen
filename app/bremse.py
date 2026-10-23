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
    """Die Absender-IP, so wie sie der **eigene** Reverse-Proxy gesehen hat.

    `X-Forwarded-For` ist eine Liste: links steht, was der Client selbst mitgeschickt
    hat – das ist frei erfindbar –, und rechts hängt jeder Proxy an, von wem er die
    Anfrage bekommen hat. Der **letzte** Eintrag stammt also vom eigenen Proxy und ist
    der einzige, dem zu trauen ist.

    Warum das zählt: am 23.10.2026 live geprüft, dass zwölf Fehlversuche mit wechselndem
    `X-Forwarded-For` nie zur Sperre führten, weil uvicorn mit `--forwarded-allow-ips='*'`
    den ersten Eintrag nimmt (docs/OFFENE_PUNKTE.md). Ohne Proxy – lokal und in den
    Tests – gibt es die Kopfzeile nicht, dann zählt die Verbindungsadresse.
    """
    weitergereicht = request.headers.get("x-forwarded-for", "")
    kette = [teil.strip() for teil in weitergereicht.split(",") if teil.strip()]
    ip = kette[-1] if kette else (request.client.host if request.client else None)
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
