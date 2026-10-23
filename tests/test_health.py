def test_health_meldet_version_und_datenbank(client):
    antwort = client.get("/health")
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["status"] == "ok"
    assert daten["version"] == "testlauf"
    assert daten["datenbank"] == "schreibbar"
    assert daten["gestartet"].endswith("Z")


def test_startseite_laedt(client):
    antwort = client.get("/")
    assert antwort.status_code == 200
    assert "Kursunterlagen" in antwort.text


def test_stil_wird_ausgeliefert(client):
    antwort = client.get("/static/stil.css")
    assert antwort.status_code == 200
    # Keine Fremdquellen im CSS (Datenschutz-Basis B3).
    assert "http://" not in antwort.text
    assert "https://" not in antwort.text


def test_unsinnspfad_ist_404(client):
    assert client.get("/gibt-es-nicht").status_code == 404


def test_keine_api_oberflaeche(client):
    """Kein /docs und kein /openapi.json – die App hat keine öffentliche Schnittstelle."""
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_datenordner_entsteht_beim_start(client, einstellungen):
    assert einstellungen.db_pfad.exists()
    assert einstellungen.unterlagen_ordner.is_dir()
