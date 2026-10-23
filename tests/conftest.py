"""Gemeinsame Vorrichtungen. Jeder Test bekommt einen eigenen, leeren Datenordner.

Testdaten sind immer erfunden (Datenschutz-Basis B15): keine echten Kursnamen,
keine echten Unterlagen, keine Personendaten.
"""
import pytest
from fastapi.testclient import TestClient

from app import config, db
from app.main import erzeuge_app

# Erfundenes Testpasswort, lang genug für die Mindestlänge.
PASSWORT = "kurs-probe-2026!"


@pytest.fixture
def mach_einstellungen(tmp_path):
    """Fabrik: `mach_einstellungen(ADMIN_2FA=1)` für Abweichungen vom Normalfall."""
    def bauen(**zusatz) -> config.Einstellungen:
        env = {
            "SECRET_KEY": "nur-fuer-tests",
            "HTTPS_ONLY": "0",
            "DATA_DIR": str(tmp_path / "daten"),
            "GIT_SHA": "testlauf",
        }
        env.update({name: str(wert) for name, wert in zusatz.items()})
        return config.lade(env)
    return bauen


@pytest.fixture
def einstellungen(mach_einstellungen) -> config.Einstellungen:
    return mach_einstellungen()


@pytest.fixture
def mach_client(mach_einstellungen):
    """Fabrik für einen Client mit eigenen Einstellungen (gleicher Datenordner)."""
    def bauen(**zusatz) -> TestClient:
        # Der with-Block löst den lifespan aus: Datenbank, Upload-Ordner, erstes Konto.
        return TestClient(erzeuge_app(mach_einstellungen(**zusatz)))
    return bauen


@pytest.fixture
def client(mach_client) -> TestClient:
    with mach_client() as c:
        yield c


@pytest.fixture
def client_mit_konto(mach_client) -> TestClient:
    with mach_client(ADMIN_INITIAL_PASSWORD=PASSWORT) as c:
        yield c


@pytest.fixture
def client_mit_2fa(mach_client) -> TestClient:
    with mach_client(ADMIN_INITIAL_PASSWORD=PASSWORT, ADMIN_2FA=1) as c:
        yield c


@pytest.fixture
def admin(client_mit_konto) -> TestClient:
    """Angemeldeter Admin ohne zweiten Faktor – für die Seiten dahinter."""
    client_mit_konto.post("/admin/anmelden", data={"passwort": PASSWORT})
    return client_mit_konto


@pytest.fixture
def datenbank(einstellungen) -> db.Datenbank:
    d = db.Datenbank(einstellungen.db_pfad)
    d.einrichten()
    return d
