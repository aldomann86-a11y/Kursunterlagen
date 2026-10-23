from datetime import timedelta

from app import bremse, db

SCHLUESSEL = "nur-fuer-tests"


def test_ip_hash_ist_stabil_und_verbirgt_die_ip():
    a = bremse.ip_hash(SCHLUESSEL, "203.0.113.7")
    b = bremse.ip_hash(SCHLUESSEL, "203.0.113.7")
    c = bremse.ip_hash(SCHLUESSEL, "203.0.113.8")
    assert a == b
    assert a != c
    assert "203.0.113" not in a


def test_anderer_schluessel_ergibt_anderen_hash():
    assert bremse.ip_hash(SCHLUESSEL, "203.0.113.7") != bremse.ip_hash("anders", "203.0.113.7")


def test_fehlende_ip_ist_kein_fehler():
    assert bremse.ip_hash(SCHLUESSEL, None)


def test_zaehlt_und_sperrt(datenbank):
    quelle = bremse.ip_hash(SCHLUESSEL, "203.0.113.7")
    with datenbank.verbindung() as conn:
        assert bremse.anzahl(conn, "login", quelle) == 0
        bremse.merken(conn, "login", quelle)
        bremse.merken(conn, "login", quelle)
        assert bremse.anzahl(conn, "login", quelle) == 2
        assert not bremse.gesperrt(conn, "login", quelle, 3)
        bremse.merken(conn, "login", quelle)
        assert bremse.gesperrt(conn, "login", quelle, 3)


def test_arten_zaehlen_getrennt(datenbank):
    quelle = bremse.ip_hash(SCHLUESSEL, "203.0.113.7")
    with datenbank.verbindung() as conn:
        bremse.merken(conn, "login", quelle)
        bremse.merken(conn, "login", quelle)
        assert bremse.anzahl(conn, "code", quelle) == 0


def test_quellen_zaehlen_getrennt(datenbank):
    eine = bremse.ip_hash(SCHLUESSEL, "203.0.113.7")
    andere = bremse.ip_hash(SCHLUESSEL, "203.0.113.8")
    with datenbank.verbindung() as conn:
        bremse.merken(conn, "login", eine)
        assert bremse.anzahl(conn, "login", andere) == 0


def test_alte_versuche_zaehlen_nicht_mehr(datenbank):
    quelle = bremse.ip_hash(SCHLUESSEL, "203.0.113.7")
    with datenbank.verbindung() as conn:
        vorhin = db.iso(db.jetzt() - timedelta(hours=2))
        conn.execute(
            "INSERT INTO versuch (zeit, art, ip_hash) VALUES (?, 'login', ?)", (vorhin, quelle)
        )
        assert bremse.anzahl(conn, "login", quelle) == 0


def test_zuruecksetzen_loescht_nur_diese_quelle(datenbank):
    eine = bremse.ip_hash(SCHLUESSEL, "203.0.113.7")
    andere = bremse.ip_hash(SCHLUESSEL, "203.0.113.8")
    with datenbank.verbindung() as conn:
        bremse.merken(conn, "login", eine)
        bremse.merken(conn, "login", andere)
        bremse.zuruecksetzen(conn, "login", eine)
        assert bremse.anzahl(conn, "login", eine) == 0
        assert bremse.anzahl(conn, "login", andere) == 1


def test_aufraeumen_loescht_nur_ueber_24_stunden(datenbank):
    quelle = bremse.ip_hash(SCHLUESSEL, "203.0.113.7")
    with datenbank.verbindung() as conn:
        alt = db.iso(db.jetzt() - timedelta(hours=25))
        conn.execute(
            "INSERT INTO versuch (zeit, art, ip_hash) VALUES (?, 'login', ?)", (alt, quelle)
        )
        bremse.merken(conn, "login", quelle)
        assert bremse.aufraeumen(conn) == 1
        assert conn.execute("SELECT count(*) FROM versuch").fetchone()[0] == 1
