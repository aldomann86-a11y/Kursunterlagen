import pytest

from app import config


def test_secret_key_ist_in_produktion_pflicht():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        config.lade({"HTTPS_ONLY": "1"})


def test_lokal_entsteht_ein_zufaelliger_secret_key():
    a = config.lade({"HTTPS_ONLY": "0"})
    b = config.lade({"HTTPS_ONLY": "0"})
    assert a.secret_key and a.secret_key != b.secret_key


def test_vorgaben():
    e = config.lade({"HTTPS_ONLY": "0"})
    assert e.max_upload_mb == 50
    assert e.max_upload_bytes == 50 * 1024 * 1024
    assert e.limit_code_stunde == 20
    assert e.admin_2fa is False
    assert e.https_only is False


def test_pfade_haengen_am_datenordner(tmp_path):
    e = config.lade({"HTTPS_ONLY": "0", "DATA_DIR": str(tmp_path)})
    assert e.db_pfad == tmp_path / "kursunterlagen.sqlite3"
    assert e.unterlagen_ordner == tmp_path / "unterlagen"


def test_https_only_ist_standardmaessig_an():
    """Vergessene Variable darf nicht heimlich unsichere Cookies bedeuten."""
    e = config.lade({"SECRET_KEY": "x"})
    assert e.https_only is True


@pytest.mark.parametrize("wert", ["null", "0", "-5"])
def test_unsinnige_obergrenze_wird_abgelehnt(wert):
    with pytest.raises(RuntimeError, match="MAX_UPLOAD_MB"):
        config.lade({"HTTPS_ONLY": "0", "MAX_UPLOAD_MB": wert})


def test_env_datei_wird_gelesen(tmp_path):
    datei = tmp_path / ".env"
    datei.write_text(
        "# Kommentar\nHTTPS_ONLY=0\nSECRET_KEY=\"aus-der-datei\"\n\nMAX_UPLOAD_MB=5\n",
        encoding="utf-8",
    )
    e = config.lade(pfad=datei)
    assert e.secret_key == "aus-der-datei"
    assert e.max_upload_mb == 5


def test_fehlende_env_datei_ist_kein_fehler(tmp_path):
    assert config.env_datei(tmp_path / "gibt-es-nicht") == {}


def test_umgebungsvariable_gewinnt_gegen_datei(tmp_path, monkeypatch):
    datei = tmp_path / ".env"
    datei.write_text("HTTPS_ONLY=0\nSECRET_KEY=aus-der-datei\n", encoding="utf-8")
    monkeypatch.setenv("SECRET_KEY", "aus-der-umgebung")
    assert config.lade(pfad=datei).secret_key == "aus-der-umgebung"


def test_2fa_schalter(tmp_path):
    assert config.lade({"HTTPS_ONLY": "0", "ADMIN_2FA": "1"}).admin_2fa is True
    assert config.lade({"HTTPS_ONLY": "0", "ADMIN_2FA": "ja"}).admin_2fa is True
    assert config.lade({"HTTPS_ONLY": "0", "ADMIN_2FA": "0"}).admin_2fa is False
