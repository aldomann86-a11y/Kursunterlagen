"""Der Zugang zum Admin-Bereich (E3).

Der zweite Faktor wird mit pyotp gerechnet, also genau so, wie es eine Authenticator-App
täte – kein nachgebauter Code.
"""
import re

import pyotp

from tests.conftest import PASSWORT


def geheimnis_aus(html: str) -> str:
    """Das Einrichtungsformular zeigt das Geheimnis zum Abtippen – von dort lesen wir es."""
    treffer = re.search(r"<code>([A-Z2-7]{16,})</code>", html)
    assert treffer, "Geheimnis steht nicht auf der Seite"
    return treffer.group(1)


def code_fuer(geheimnis: str) -> str:
    return pyotp.TOTP(geheimnis).now()


# --- ohne Konto ------------------------------------------------------------------------

def test_anmeldeformular_meldet_fehlendes_konto(client):
    antwort = client.get("/admin/anmelden")
    assert antwort.status_code == 200
    assert "noch kein Konto" in antwort.text
    assert "ADMIN_INITIAL_PASSWORD" in antwort.text


def test_ohne_konto_fuehrt_kein_passwort_hinein(client):
    antwort = client.post("/admin/anmelden", data={"passwort": PASSWORT})
    assert antwort.status_code == 401


# --- Weiterleitungen -------------------------------------------------------------------

def test_admin_ohne_anmeldung_leitet_um(client_mit_konto):
    antwort = client_mit_konto.get("/admin", follow_redirects=False)
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/admin/anmelden"


def test_zweiter_faktor_ohne_anmeldung_leitet_um(client_mit_konto):
    for pfad in ("/admin/2fa", "/admin/2fa/einrichten"):
        antwort = client_mit_konto.get(pfad, follow_redirects=False)
        assert antwort.status_code == 303
        assert antwort.headers["location"] == "/admin/anmelden"


# --- Anmelden ohne zweiten Faktor ------------------------------------------------------

def test_falsches_passwort_gibt_keinen_zugang(client_mit_konto):
    antwort = client_mit_konto.post("/admin/anmelden", data={"passwort": "falsch-falsch-123"})
    assert antwort.status_code == 401
    assert "stimmt nicht" in antwort.text
    assert not client_mit_konto.cookies.get("kursunterlagen_admin")


def test_richtiges_passwort_fuehrt_in_die_verwaltung(client_mit_konto):
    antwort = client_mit_konto.post(
        "/admin/anmelden", data={"passwort": PASSWORT}, follow_redirects=False
    )
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/admin"

    gesetzt = antwort.headers["set-cookie"]
    assert "httponly" in gesetzt.lower()
    assert "samesite=lax" in gesetzt.lower()
    assert "secure" not in gesetzt.lower()      # lokal ohne HTTPS

    verwaltung = client_mit_konto.get("/admin")
    assert verwaltung.status_code == 200
    assert "Verwaltung" in verwaltung.text


def test_abmelden_sperrt_wieder(client_mit_konto):
    client_mit_konto.post("/admin/anmelden", data={"passwort": PASSWORT})
    assert client_mit_konto.get("/admin").status_code == 200

    client_mit_konto.post("/admin/abmelden")
    antwort = client_mit_konto.get("/admin", follow_redirects=False)
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/admin/anmelden"


def test_gefaelschtes_cookie_gibt_keinen_zugang(client_mit_konto):
    client_mit_konto.cookies.set("kursunterlagen_admin", "selbst-gebastelt")
    antwort = client_mit_konto.get("/admin", follow_redirects=False)
    assert antwort.status_code == 303


def test_cookie_ist_in_produktion_nur_ueber_https(mach_client):
    with mach_client(
        ADMIN_INITIAL_PASSWORD=PASSWORT, HTTPS_ONLY=1, SECRET_KEY="nur-fuer-tests"
    ) as c:
        antwort = c.post(
            "/admin/anmelden", data={"passwort": PASSWORT}, follow_redirects=False
        )
        assert "secure" in antwort.headers["set-cookie"].lower()


# --- Bremse ----------------------------------------------------------------------------

def test_zu_viele_fehlversuche_sperren(mach_client):
    with mach_client(ADMIN_INITIAL_PASSWORD=PASSWORT, LIMIT_LOGIN_STUNDE=2) as c:
        assert c.post("/admin/anmelden", data={"passwort": "falsch-falsch-1"}).status_code == 401
        assert c.post("/admin/anmelden", data={"passwort": "falsch-falsch-2"}).status_code == 401

        gesperrt = c.post("/admin/anmelden", data={"passwort": PASSWORT})
        assert gesperrt.status_code == 429
        assert "Fehlversuche" in gesperrt.text


def test_erfolg_loescht_die_fehlversuche(mach_client):
    with mach_client(ADMIN_INITIAL_PASSWORD=PASSWORT, LIMIT_LOGIN_STUNDE=3) as c:
        c.post("/admin/anmelden", data={"passwort": "falsch-falsch-1"})
        c.post("/admin/anmelden", data={"passwort": "falsch-falsch-2"})
        assert c.post("/admin/anmelden", data={"passwort": PASSWORT}).status_code == 200

        c.post("/admin/abmelden")
        # Nach dem Erfolg ist der Zähler leer: zwei neue Fehlversuche sperren noch nicht.
        c.post("/admin/anmelden", data={"passwort": "falsch-falsch-3"})
        assert c.post("/admin/anmelden", data={"passwort": PASSWORT}).status_code == 200


# --- Zweiter Faktor --------------------------------------------------------------------

def test_erste_anmeldung_fuehrt_zur_einrichtung(client_mit_2fa):
    antwort = client_mit_2fa.post(
        "/admin/anmelden", data={"passwort": PASSWORT}, follow_redirects=False
    )
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/admin/2fa/einrichten"

    formular = client_mit_2fa.get("/admin/2fa/einrichten")
    assert formular.status_code == 200
    assert "<svg" in formular.text
    assert geheimnis_aus(formular.text)


def test_ohne_faktor_kein_zugang_zur_verwaltung(client_mit_2fa):
    client_mit_2fa.post("/admin/anmelden", data={"passwort": PASSWORT})
    antwort = client_mit_2fa.get("/admin", follow_redirects=False)
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/admin/2fa/einrichten"


def test_einrichten_und_anmelden_mit_faktor(client_mit_2fa):
    client_mit_2fa.post("/admin/anmelden", data={"passwort": PASSWORT})
    geheimnis = geheimnis_aus(client_mit_2fa.get("/admin/2fa/einrichten").text)

    falsch = client_mit_2fa.post("/admin/2fa/einrichten", data={"code": "000000"})
    assert falsch.status_code == 401
    assert client_mit_2fa.get("/admin", follow_redirects=False).status_code == 303

    richtig = client_mit_2fa.post(
        "/admin/2fa/einrichten", data={"code": code_fuer(geheimnis)}, follow_redirects=False
    )
    assert richtig.status_code == 303
    assert richtig.headers["location"] == "/admin"

    verwaltung = client_mit_2fa.get("/admin")
    assert verwaltung.status_code == 200
    assert "zweitem Faktor" in verwaltung.text

    # Zweite Anmeldung: jetzt wird der Code verlangt, nicht mehr die Einrichtung.
    client_mit_2fa.post("/admin/abmelden")
    erneut = client_mit_2fa.post(
        "/admin/anmelden", data={"passwort": PASSWORT}, follow_redirects=False
    )
    assert erneut.headers["location"] == "/admin/2fa"

    assert client_mit_2fa.post("/admin/2fa", data={"code": "000000"}).status_code == 401
    weiter = client_mit_2fa.post(
        "/admin/2fa", data={"code": code_fuer(geheimnis)}, follow_redirects=False
    )
    assert weiter.headers["location"] == "/admin"
    assert client_mit_2fa.get("/admin").status_code == 200


def test_bestaetigter_faktor_kann_nicht_neu_eingerichtet_werden(client_mit_2fa):
    client_mit_2fa.post("/admin/anmelden", data={"passwort": PASSWORT})
    geheimnis = geheimnis_aus(client_mit_2fa.get("/admin/2fa/einrichten").text)
    client_mit_2fa.post("/admin/2fa/einrichten", data={"code": code_fuer(geheimnis)})

    client_mit_2fa.post("/admin/abmelden")
    client_mit_2fa.post("/admin/anmelden", data={"passwort": PASSWORT})
    antwort = client_mit_2fa.get("/admin/2fa/einrichten", follow_redirects=False)
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/admin/2fa"
