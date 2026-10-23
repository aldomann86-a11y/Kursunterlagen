"""Die Teilnehmerseite (E6): Code eingeben, Liste sehen, herunterladen."""
import re

from app import kurse, unterlagen

PDF = b"%PDF-1.4 erfundene Probedatei"
SCHLUESSEL = "nur-fuer-tests"


def kurs_mit_unterlage(einstellungen, name="Probekurs", titel="Handout", **felder):
    """Legt Kurs und Unterlage direkt in der Datenbank an – ohne den Admin-Bereich."""
    from app.db import Datenbank

    d = Datenbank(einstellungen.db_pfad)
    d.einrichten()
    with d.verbindung() as conn:
        kurs_id, code = kurse.anlegen(conn, einstellungen.secret_key, name, **felder)
        uid = unterlagen.speichern(
            conn, einstellungen.unterlagen_ordner, kurs_id, titel, "handout.pdf", PDF,
            einstellungen.max_upload_bytes,
        )
    return kurs_id, code, uid


# --- Zugang ----------------------------------------------------------------------------

def test_startseite_fragt_nach_dem_code(client):
    antwort = client.get("/")
    assert antwort.status_code == 200
    assert "Zugangscode" in antwort.text


def test_falscher_code_gibt_keinen_zugang(client, einstellungen):
    kurs_mit_unterlage(einstellungen)
    antwort = client.post("/zugang", data={"code": "abcd-1234"})
    assert antwort.status_code == 401
    assert "passt nicht" in antwort.text
    assert client.get("/unterlagen", follow_redirects=False).headers["location"] == "/"


def test_richtiger_code_oeffnet_die_liste(client, einstellungen):
    _, code, _ = kurs_mit_unterlage(einstellungen, name="KI-Probekurs", titel="Aufgabenblatt")

    antwort = client.post("/zugang", data={"code": code}, follow_redirects=False)
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/unterlagen"

    liste = client.get("/unterlagen")
    assert liste.status_code == 200
    assert "KI-Probekurs" in liste.text
    assert "Aufgabenblatt" in liste.text


def test_code_mit_leerzeichen_und_grossbuchstaben(client, einstellungen):
    _, code, _ = kurs_mit_unterlage(einstellungen)
    getippt = f" {code.upper().replace('-', ' ')} "
    assert client.post("/zugang", data={"code": getippt},
                       follow_redirects=False).status_code == 303


def test_wer_schon_drin_ist_landet_auf_der_liste(client, einstellungen):
    _, code, _ = kurs_mit_unterlage(einstellungen)
    client.post("/zugang", data={"code": code})
    antwort = client.get("/", follow_redirects=False)
    assert antwort.headers["location"] == "/unterlagen"


def test_zu_viele_versuche_sperren(mach_client, mach_einstellungen):
    e = mach_einstellungen(LIMIT_CODE_STUNDE=2)
    kurs_mit_unterlage(e)
    with mach_client(LIMIT_CODE_STUNDE=2) as c:
        assert c.post("/zugang", data={"code": "aaaa-1111"}).status_code == 401
        assert c.post("/zugang", data={"code": "bbbb-2222"}).status_code == 401
        gesperrt = c.post("/zugang", data={"code": "cccc-3333"})
        assert gesperrt.status_code == 429
        assert "Zu viele Versuche" in gesperrt.text


# --- Download --------------------------------------------------------------------------

def test_herunterladen_liefert_die_datei(client, einstellungen):
    _, code, uid = kurs_mit_unterlage(einstellungen)
    client.post("/zugang", data={"code": code})

    antwort = client.get(f"/unterlagen/{uid}")
    assert antwort.status_code == 200
    assert antwort.content == PDF
    assert antwort.headers["content-type"] == "application/pdf"
    # Der Name beim Speichern ist der hochgeladene, nicht der im Dateisystem.
    assert "handout.pdf" in antwort.headers["content-disposition"]


def test_unterlage_eines_fremden_kurses_gibt_404(client, einstellungen):
    _, code, _ = kurs_mit_unterlage(einstellungen, name="Eigener Kurs")
    from app.db import Datenbank

    d = Datenbank(einstellungen.db_pfad)
    with d.verbindung() as conn:
        fremd_id, _ = kurse.anlegen(conn, einstellungen.secret_key, "Fremder Kurs")
        fremde = unterlagen.speichern(
            conn, einstellungen.unterlagen_ordner, fremd_id, "Geheim", "geheim.pdf", PDF,
            einstellungen.max_upload_bytes,
        )

    client.post("/zugang", data={"code": code})
    assert client.get(f"/unterlagen/{fremde}").status_code == 404
    assert "Geheim" not in client.get("/unterlagen").text


def test_ohne_zugang_kein_download(client, einstellungen):
    _, _, uid = kurs_mit_unterlage(einstellungen)
    antwort = client.get(f"/unterlagen/{uid}", follow_redirects=False)
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/"


def test_ausgeblendete_unterlage_ist_weg(client, einstellungen):
    _, code, uid = kurs_mit_unterlage(einstellungen)
    from app.db import Datenbank

    with Datenbank(einstellungen.db_pfad).verbindung() as conn:
        unterlagen.sichtbar_setzen(conn, uid, False)

    client.post("/zugang", data={"code": code})
    assert client.get(f"/unterlagen/{uid}").status_code == 404


def test_download_wird_anonym_gezaehlt(client, einstellungen):
    kurs_id, code, uid = kurs_mit_unterlage(einstellungen)
    client.post("/zugang", data={"code": code})
    client.get(f"/unterlagen/{uid}")
    client.get(f"/unterlagen/{uid}")

    from app.db import Datenbank

    with Datenbank(einstellungen.db_pfad).verbindung() as conn:
        assert unterlagen.downloads_je_unterlage(conn, kurs_id) == {uid: 2}


# --- Kurs gesperrt oder abgelaufen ------------------------------------------------------

def test_gesperrter_kurs_schliesst_den_zugang_sofort(client, einstellungen):
    kurs_id, code, uid = kurs_mit_unterlage(einstellungen)
    client.post("/zugang", data={"code": code})
    assert client.get("/unterlagen").status_code == 200

    from app.db import Datenbank

    with Datenbank(einstellungen.db_pfad).verbindung() as conn:
        kurse.aktiv_setzen(conn, kurs_id, False)

    # Auch mit gültigem Cookie: Schluss.
    assert client.get("/unterlagen", follow_redirects=False).headers["location"] == "/"
    assert client.get(f"/unterlagen/{uid}", follow_redirects=False).headers["location"] == "/"


def test_abmelden_vergisst_den_kurs(client, einstellungen):
    _, code, _ = kurs_mit_unterlage(einstellungen)
    client.post("/zugang", data={"code": code})
    client.post("/abmelden")
    assert client.get("/unterlagen", follow_redirects=False).headers["location"] == "/"


def test_gefaelschtes_cookie_gibt_keinen_zugang(client, einstellungen):
    kurs_mit_unterlage(einstellungen)
    client.cookies.set("kursunterlagen_kurs", "selbst-gebastelt")
    assert client.get("/unterlagen", follow_redirects=False).headers["location"] == "/"


def test_admin_bleibt_getrennt(client_mit_konto, einstellungen):
    """Wer den Kurscode hat, kommt damit nicht in die Verwaltung."""
    _, code, _ = kurs_mit_unterlage(einstellungen)
    client_mit_konto.post("/zugang", data={"code": code})
    antwort = client_mit_konto.get("/admin", follow_redirects=False)
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/admin/anmelden"
