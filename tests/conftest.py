"""Gemeinsame Vorrichtungen. Jeder Test bekommt einen eigenen, leeren Datenordner.

Testdaten sind immer erfunden (Datenschutz-Basis B15): keine echten Kursnamen,
keine echten Unterlagen, keine Personendaten.
"""
import pytest
from fastapi.testclient import TestClient

from app import config, db
from app.main import erzeuge_app


@pytest.fixture
def einstellungen(tmp_path) -> config.Einstellungen:
    return config.lade({
        "SECRET_KEY": "nur-fuer-tests",
        "HTTPS_ONLY": "0",
        "DATA_DIR": str(tmp_path / "daten"),
        "GIT_SHA": "testlauf",
    })


@pytest.fixture
def client(einstellungen) -> TestClient:
    # Der with-Block löst den lifespan aus: Datenbank und Upload-Ordner entstehen.
    with TestClient(erzeuge_app(einstellungen)) as c:
        yield c


@pytest.fixture
def datenbank(einstellungen) -> db.Datenbank:
    d = db.Datenbank(einstellungen.db_pfad)
    d.einrichten()
    return d
