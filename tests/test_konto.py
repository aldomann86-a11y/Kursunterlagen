import pyotp
import pytest

from app import konto

PASSWORT = "kurs-probe-2026!"


def test_hash_und_pruefung():
    h = konto.hash_passwort(PASSWORT)
    assert h != PASSWORT
    assert konto.passwort_stimmt(PASSWORT, h)
    assert not konto.passwort_stimmt("etwas-anderes-12", h)


def test_leeres_passwort_stimmt_nie():
    h = konto.hash_passwort(PASSWORT)
    assert not konto.passwort_stimmt("", h)
    assert not konto.passwort_stimmt(PASSWORT, "")


def test_kaputter_hash_wirft_nicht():
    assert konto.passwort_stimmt(PASSWORT, "kein-bcrypt-hash") is False


def test_zu_kurzes_passwort():
    with pytest.raises(ValueError, match="mindestens 12"):
        konto.hash_passwort("kurz")


def test_zu_langes_passwort():
    """Über 72 Bytes schneidet bcrypt ab – das lehnen wir ab, statt es zu verschweigen."""
    with pytest.raises(ValueError, match="zu lang"):
        konto.hash_passwort("a" * 73)
    # Umlaute zählen doppelt: 40 Zeichen sind 80 Bytes.
    with pytest.raises(ValueError, match="zu lang"):
        konto.hash_passwort("ä" * 40)


def test_konto_anlegen_und_lesen(datenbank):
    with datenbank.verbindung() as conn:
        assert konto.lesen(conn) is None
        konto.anlegen(conn, PASSWORT)
        k = konto.lesen(conn)
        assert k is not None
        assert konto.passwort_stimmt(PASSWORT, k["passwort_hash"])
        assert k["totp_bestaetigt"] == 0


def test_bestehendes_konto_wird_nicht_ueberschrieben(datenbank):
    with datenbank.verbindung() as conn:
        konto.anlegen(conn, PASSWORT)
        konto.anlegen(conn, "ein-anderes-passwort")
        k = konto.lesen(conn)
        assert konto.passwort_stimmt(PASSWORT, k["passwort_hash"])


def test_passwort_setzen_aendert(datenbank):
    with datenbank.verbindung() as conn:
        konto.anlegen(conn, PASSWORT)
        konto.passwort_setzen(conn, "neues-passwort-2026")
        k = konto.lesen(conn)
        assert konto.passwort_stimmt("neues-passwort-2026", k["passwort_hash"])


def test_totp_ablauf(datenbank):
    with datenbank.verbindung() as conn:
        konto.anlegen(conn, PASSWORT)
        geheimnis = konto.neues_totp_secret()
        konto.totp_secret_setzen(conn, geheimnis)
        k = konto.lesen(conn)
        assert k["totp_secret"] == geheimnis
        assert k["totp_bestaetigt"] == 0

        assert konto.totp_stimmt(geheimnis, pyotp.TOTP(geheimnis).now())
        assert not konto.totp_stimmt(geheimnis, "000000")
        assert not konto.totp_stimmt(None, "000000")
        assert not konto.totp_stimmt(geheimnis, "")

        konto.totp_bestaetigen(conn)
        assert konto.lesen(conn)["totp_bestaetigt"] == 1


def test_totp_code_mit_leerzeichen():
    geheimnis = konto.neues_totp_secret()
    code = pyotp.TOTP(geheimnis).now()
    assert konto.totp_stimmt(geheimnis, f"{code[:3]} {code[3:]}")


def test_qr_ist_svg_ohne_fremdquelle():
    svg = konto.qr_svg(konto.totp_uri(konto.neues_totp_secret()))
    assert svg.lstrip().startswith("<svg")
    # Nichts, womit der Browser etwas nachladen würde. Das `xmlns` ist nur eine Kennung.
    assert "href" not in svg
    assert "<image" not in svg
    assert "<script" not in svg


def test_qr_enthaelt_das_geheimnis_nicht_im_klartext():
    """Der QR trägt die Adresse als Grafik, nicht als lesbaren Text im Markup."""
    geheimnis = konto.neues_totp_secret()
    assert geheimnis not in konto.qr_svg(konto.totp_uri(geheimnis))
