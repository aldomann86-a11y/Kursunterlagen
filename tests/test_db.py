import sqlite3

import pytest

from app import db


def test_schema_legt_alle_tabellen_an(datenbank):
    with datenbank.verbindung() as conn:
        vorhanden = {
            z["name"]
            for z in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert set(db.TABELLEN) <= vorhanden


def test_einrichten_ist_wiederholbar(datenbank):
    """Zweiter Start darf nichts kaputt machen – CREATE TABLE IF NOT EXISTS."""
    datenbank.einrichten()
    with datenbank.verbindung() as conn:
        assert conn.execute("SELECT count(*) FROM kurs").fetchone()[0] == 0


def test_unterlage_braucht_einen_kurs(datenbank):
    with datenbank.verbindung() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO unterlage (kurs_id, titel, dateiname, ablage, mime, groesse,"
                " hochgeladen_am) VALUES (999, 'Probe', 'probe.pdf', 'a1.pdf', 'application/pdf',"
                " 10, ?)",
                (db.iso(db.jetzt()),),
            )


def test_zugangscode_ist_eindeutig(datenbank):
    with datenbank.verbindung() as conn:
        conn.execute(
            "INSERT INTO kurs (name, code_hash, erstellt_am) VALUES ('Probekurs', 'hash-1', ?)",
            (db.iso(db.jetzt()),),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO kurs (name, code_hash, erstellt_am) VALUES ('Zweitkurs', 'hash-1', ?)",
                (db.iso(db.jetzt()),),
            )


def test_nur_ein_admin_konto(datenbank):
    with datenbank.verbindung() as conn:
        conn.execute(
            "INSERT INTO admin (id, passwort_hash, erstellt_am) VALUES (1, 'hash', ?)",
            (db.iso(db.jetzt()),),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO admin (id, passwort_hash, erstellt_am) VALUES (2, 'hash', ?)",
                (db.iso(db.jetzt()),),
            )


def test_zeiten_werden_als_utc_gespeichert_und_sortierbar():
    frueh = db.iso(db.aus_iso("2026-01-15T08:30:00.000000Z"))
    spaet = db.iso(db.aus_iso("2026-07-15T08:30:00.000000Z"))
    assert frueh < spaet          # Zeichenkettenvergleich stimmt mit der Zeitfolge
    assert frueh.endswith("Z")


def test_anzeige_rechnet_auf_schweizer_zeit():
    assert db.anzeige("2026-01-15T08:30:00.000000Z") == "15.01.2026 09:30"   # Winterzeit
    assert db.anzeige("2026-07-15T08:30:00.000000Z") == "15.07.2026 10:30"   # Sommerzeit


def test_schreibbar_meldet_wahr(datenbank):
    assert datenbank.schreibbar() is True
