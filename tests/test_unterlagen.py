import pytest

from app import kurse, unterlagen

SCHLUESSEL = "nur-fuer-tests"
MAX = 5 * 1024 * 1024
INHALT = b"%PDF-1.4 erfundene Probedatei"


@pytest.fixture
def kurs_id(datenbank):
    with datenbank.verbindung() as conn:
        kid, _ = kurse.anlegen(conn, SCHLUESSEL, "Probekurs")
    return kid


@pytest.fixture
def ordner(tmp_path):
    ziel = tmp_path / "unterlagen"
    ziel.mkdir()
    return ziel


# --- Prüfung ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["handout.pdf", "folien.pptx", "Spickzettel.MD", "bild.jpeg"])
def test_erlaubte_typen(name):
    assert unterlagen.pruefen(name, 100, MAX)


@pytest.mark.parametrize("name", ["programm.exe", "skript.sh", "ohne-endung", "seite.html"])
def test_abgelehnte_typen(name):
    with pytest.raises(unterlagen.Abgelehnt, match="Dateityp"):
        unterlagen.pruefen(name, 100, MAX)


def test_leere_datei_abgelehnt():
    with pytest.raises(unterlagen.Abgelehnt, match="leer"):
        unterlagen.pruefen("handout.pdf", 0, MAX)


def test_zu_grosse_datei_abgelehnt():
    with pytest.raises(unterlagen.Abgelehnt, match="zu gross"):
        unterlagen.pruefen("handout.pdf", MAX + 1, MAX)


# --- Namen -----------------------------------------------------------------------------

def test_anzeigename_entfernt_pfad_und_sonderzeichen():
    assert unterlagen.anzeigename("C:\\Temp\\handout.pdf") == "handout.pdf"
    assert unterlagen.anzeigename("../../etc/passwd.pdf") == "passwd.pdf"
    assert unterlagen.anzeigename("a:b*c?.pdf") == "a_b_c_.pdf"
    assert unterlagen.anzeigename("") == "unterlage"


def test_ablagename_ist_eigen_und_eindeutig():
    einer = unterlagen.ablagename(".pdf")
    assert einer.endswith(".pdf")
    assert len({unterlagen.ablagename(".pdf") for _ in range(20)}) == 20


def test_pfad_laesst_niemanden_aus_dem_ordner(ordner):
    assert unterlagen.pfad(ordner, "abc.pdf").parent == ordner.resolve()
    # Ein Ausbruchsversuch endet trotzdem im Ordner, weil nur der Name zählt.
    assert unterlagen.pfad(ordner, "../../geheim.pdf").name == "geheim.pdf"
    assert unterlagen.pfad(ordner, "../../geheim.pdf").parent == ordner.resolve()


# --- Speichern -------------------------------------------------------------------------

def test_speichern_legt_datei_und_zeile_an(datenbank, ordner, kurs_id):
    with datenbank.verbindung() as conn:
        uid = unterlagen.speichern(
            conn, ordner, kurs_id, "Teilnehmer-Handout", "handout.pdf", INHALT, MAX,
            beschreibung="Zum Nachlesen",
        )
        zeile = unterlagen.finden(conn, uid)

    assert zeile["titel"] == "Teilnehmer-Handout"
    assert zeile["dateiname"] == "handout.pdf"
    assert zeile["mime"] == "application/pdf"
    assert zeile["groesse"] == len(INHALT)
    assert zeile["sichtbar"] == 1
    assert zeile["beschreibung"] == "Zum Nachlesen"
    datei = unterlagen.pfad(ordner, zeile["ablage"])
    assert datei.read_bytes() == INHALT
    assert zeile["ablage"] != "handout.pdf"      # eigener Name im Dateisystem


def test_speichern_ohne_titel_geht_nicht(datenbank, ordner, kurs_id):
    with datenbank.verbindung() as conn:
        with pytest.raises(unterlagen.Abgelehnt, match="Titel"):
            unterlagen.speichern(conn, ordner, kurs_id, " ", "handout.pdf", INHALT, MAX)


def test_abgelehnte_datei_hinterlaesst_nichts(datenbank, ordner, kurs_id):
    with datenbank.verbindung() as conn:
        with pytest.raises(unterlagen.Abgelehnt):
            unterlagen.speichern(conn, ordner, kurs_id, "Böse", "virus.exe", INHALT, MAX)
        assert unterlagen.alle_fuer(conn, kurs_id) == []
    assert list(ordner.iterdir()) == []


def test_sortierung_waechst(datenbank, ordner, kurs_id):
    with datenbank.verbindung() as conn:
        erste = unterlagen.speichern(conn, ordner, kurs_id, "Eins", "a.pdf", INHALT, MAX)
        zweite = unterlagen.speichern(conn, ordner, kurs_id, "Zwei", "b.pdf", INHALT, MAX)
        reihenfolge = [z["id"] for z in unterlagen.alle_fuer(conn, kurs_id)]
        assert reihenfolge == [erste, zweite]

        unterlagen.verschieben(conn, erste, +1)
        assert [z["id"] for z in unterlagen.alle_fuer(conn, kurs_id)] == [zweite, erste]


# --- Rechteprüfung ---------------------------------------------------------------------

def test_unterlage_eines_fremden_kurses_ist_nicht_zu_holen(datenbank, ordner, kurs_id):
    with datenbank.verbindung() as conn:
        fremder, _ = kurse.anlegen(conn, SCHLUESSEL, "Fremder Kurs")
        uid = unterlagen.speichern(conn, ordner, kurs_id, "Handout", "a.pdf", INHALT, MAX)

        assert unterlagen.fuer_kurs(conn, kurs_id, uid) is not None
        assert unterlagen.fuer_kurs(conn, fremder, uid) is None


def test_ausgeblendete_unterlage_ist_nicht_zu_holen(datenbank, ordner, kurs_id):
    with datenbank.verbindung() as conn:
        uid = unterlagen.speichern(conn, ordner, kurs_id, "Handout", "a.pdf", INHALT, MAX)
        unterlagen.sichtbar_setzen(conn, uid, False)

        assert unterlagen.fuer_kurs(conn, kurs_id, uid) is None
        assert unterlagen.alle_fuer(conn, kurs_id, nur_sichtbare=True) == []
        assert len(unterlagen.alle_fuer(conn, kurs_id)) == 1      # im Admin weiter sichtbar
        # Die Datei bleibt liegen: ausblenden ist kein Löschen.
        assert unterlagen.pfad(ordner, unterlagen.finden(conn, uid)["ablage"]).exists()


# --- Zähler ----------------------------------------------------------------------------

def test_downloads_werden_anonym_gezaehlt(datenbank, ordner, kurs_id):
    with datenbank.verbindung() as conn:
        uid = unterlagen.speichern(conn, ordner, kurs_id, "Handout", "a.pdf", INHALT, MAX)
        unterlagen.download_merken(conn, kurs_id, uid)
        unterlagen.download_merken(conn, kurs_id, uid)

        assert unterlagen.downloads_je_unterlage(conn, kurs_id) == {uid: 2}
        spalten = {z["name"] for z in conn.execute("PRAGMA table_info(download)")}
        assert "ip_hash" not in spalten and "name" not in spalten


def test_lesbare_groesse():
    assert unterlagen.lesbare_groesse(512) == "512 B"
    assert unterlagen.lesbare_groesse(2048) == "2 KB"
    assert unterlagen.lesbare_groesse(3 * 1024 * 1024) == "3,0 MB"
