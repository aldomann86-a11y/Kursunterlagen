from datetime import timedelta

import pytest

from app import db, kurse

SCHLUESSEL = "nur-fuer-tests"


def test_code_ist_lesbar():
    code = kurse.neuer_code()
    assert len(code) == 9 and code[4] == "-"
    # Keine Zeichen, die beim Vorlesen verwechselt werden.
    assert not set(code.replace("-", "")) & set("0o1li")


def test_codes_sind_verschieden():
    assert len({kurse.neuer_code() for _ in range(50)}) > 45


def test_anlegen_gibt_den_code_einmal_heraus(datenbank):
    with datenbank.verbindung() as conn:
        kurs_id, code = kurse.anlegen(conn, SCHLUESSEL, "Probekurs")
        kurs = kurse.finden(conn, kurs_id)
        assert kurs["name"] == "Probekurs"
        assert code not in kurs["code_hash"]
        assert kurs["code_hash"] == kurse.code_hash(SCHLUESSEL, code)


def test_kurs_ohne_namen_geht_nicht(datenbank):
    with datenbank.verbindung() as conn:
        with pytest.raises(ValueError, match="Namen"):
            kurse.anlegen(conn, SCHLUESSEL, "   ")


def test_code_findet_den_kurs(datenbank):
    with datenbank.verbindung() as conn:
        kurs_id, code = kurse.anlegen(conn, SCHLUESSEL, "Probekurs")
        assert kurse.mit_code(conn, SCHLUESSEL, code)["id"] == kurs_id


def test_falscher_code_findet_nichts(datenbank):
    with datenbank.verbindung() as conn:
        kurse.anlegen(conn, SCHLUESSEL, "Probekurs")
        assert kurse.mit_code(conn, SCHLUESSEL, "abcd-1234") is None
        assert kurse.mit_code(conn, SCHLUESSEL, "") is None
        assert kurse.mit_code(conn, SCHLUESSEL, "   ") is None


def test_gross_klein_und_leerzeichen_sind_egal(datenbank):
    with datenbank.verbindung() as conn:
        kurs_id, code = kurse.anlegen(conn, SCHLUESSEL, "Probekurs")
        getippt = f"  {code.upper()[:4]} {code[5:]}  "
        assert kurse.mit_code(conn, SCHLUESSEL, getippt)["id"] == kurs_id


def test_anderer_schluessel_oeffnet_nicht(datenbank):
    with datenbank.verbindung() as conn:
        _, code = kurse.anlegen(conn, SCHLUESSEL, "Probekurs")
        assert kurse.mit_code(conn, "anderer-schluessel", code) is None


def test_gesperrter_kurs_oeffnet_nicht(datenbank):
    with datenbank.verbindung() as conn:
        kurs_id, code = kurse.anlegen(conn, SCHLUESSEL, "Probekurs")
        kurse.aktiv_setzen(conn, kurs_id, False)
        assert kurse.mit_code(conn, SCHLUESSEL, code) is None

        kurse.aktiv_setzen(conn, kurs_id, True)
        assert kurse.mit_code(conn, SCHLUESSEL, code) is not None


def test_abgelaufener_kurs_oeffnet_nicht(datenbank):
    heute = db.jetzt().strftime("%Y-%m-%d")
    gestern = (db.jetzt() - timedelta(days=1)).strftime("%Y-%m-%d")
    with datenbank.verbindung() as conn:
        offen, code_offen = kurse.anlegen(conn, SCHLUESSEL, "Läuft noch", offen_bis=heute)
        _, code_zu = kurse.anlegen(conn, SCHLUESSEL, "Vorbei", offen_bis=gestern)
        assert kurse.mit_code(conn, SCHLUESSEL, code_offen)["id"] == offen
        assert kurse.mit_code(conn, SCHLUESSEL, code_zu) is None


def test_neuer_code_entwertet_den_alten(datenbank):
    with datenbank.verbindung() as conn:
        kurs_id, alt = kurse.anlegen(conn, SCHLUESSEL, "Probekurs")
        neu = kurse.code_neu_setzen(conn, SCHLUESSEL, kurs_id)
        assert neu != alt
        assert kurse.mit_code(conn, SCHLUESSEL, alt) is None
        assert kurse.mit_code(conn, SCHLUESSEL, neu)["id"] == kurs_id


def test_aendern_und_auflisten(datenbank):
    with datenbank.verbindung() as conn:
        erster, _ = kurse.anlegen(conn, SCHLUESSEL, "Erster")
        kurse.anlegen(conn, SCHLUESSEL, "Zweiter")
        kurse.aendern(conn, erster, "Erster, umbenannt", datum="2026-11-04")

        liste = kurse.alle(conn)
        assert len(liste) == 2
        geaendert = kurse.finden(conn, erster)
        assert geaendert["name"] == "Erster, umbenannt"
        assert geaendert["datum"] == "2026-11-04"


def test_gesperrte_kurse_stehen_hinten(datenbank):
    with datenbank.verbindung() as conn:
        erster, _ = kurse.anlegen(conn, SCHLUESSEL, "Erster")
        kurse.anlegen(conn, SCHLUESSEL, "Zweiter")
        kurse.aktiv_setzen(conn, erster, False)
        assert [z["aktiv"] for z in kurse.alle(conn)] == [1, 0]
