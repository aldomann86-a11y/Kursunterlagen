"""Einstellungen aus der Umgebung. Ein Ort, keine Magie.

Muster: ../kimas-post/app/config.py. Werte kommen aus .env (lokal) oder aus den
Umgebungsvariablen des Dienstes (Produktion), nie aus dem Code.
"""
import os
import secrets
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Einstellungen:
    secret_key: str
    admin_initial_password: str
    admin_2fa: bool
    https_only: bool
    data_dir: Path
    max_upload_mb: int
    limit_code_stunde: int
    version: str            # Commit-Hash aus dem Image (GIT_SHA), leer in der Entwicklung

    @property
    def db_pfad(self) -> Path:
        return self.data_dir / "kursunterlagen.sqlite3"

    @property
    def unterlagen_ordner(self) -> Path:
        """Hier liegen die hochgeladenen Dateien – nie in der Datenbank, nie im Repo."""
        return self.data_dir / "unterlagen"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


def _bool(wert: str | None, vorgabe: bool) -> bool:
    if wert is None or wert == "":
        return vorgabe
    return wert.strip().lower() in ("1", "true", "ja", "yes")


def _zahl(wert: str | None, vorgabe: int, name: str) -> int:
    if wert is None or wert.strip() == "":
        return vorgabe
    try:
        zahl = int(wert)
    except ValueError:
        raise RuntimeError(f"{name} muss eine Zahl sein, nicht {wert!r}") from None
    if zahl < 1:
        raise RuntimeError(f"{name} muss mindestens 1 sein, nicht {zahl}")
    return zahl


def env_datei(pfad: Path) -> dict[str, str]:
    """Liest eine .env-Datei: NAME=wert je Zeile, # ist ein Kommentar.

    Zehn Zeilen statt einer Abhängigkeit. Gilt nur für die Entwicklung – in Produktion
    kommen die Werte aus den Umgebungsvariablen des Dienstes.
    """
    if not pfad.is_file():
        return {}
    werte: dict[str, str] = {}
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        name, _, wert = zeile.partition("=")
        werte[name.strip()] = wert.strip().strip('"').strip("'")
    return werte


def lade(umgebung: dict[str, str] | None = None, pfad: Path | None = None) -> Einstellungen:
    if umgebung is None:
        # Echte Umgebungsvariablen gewinnen gegen die Datei.
        env: dict[str, str] = {**env_datei(pfad or Path(".env")), **os.environ}
    else:
        env = umgebung

    # HTTPS_ONLY=1 heisst: läuft hinter einem Reverse-Proxy, also Produktion. Dort ist ein
    # fester SECRET_KEY Pflicht, sonst wären alle Sitzungen nach jedem Neustart ungültig –
    # und ein zufälliger Schlüssel je Prozess fällt erst im Betrieb auf.
    https_only = _bool(env.get("HTTPS_ONLY"), True)
    secret = (env.get("SECRET_KEY") or "").strip()
    if not secret:
        if https_only:
            raise RuntimeError(
                "SECRET_KEY fehlt. Ohne ihn sind die Sitzungs-Cookies nicht signiert. "
                "Lokal genügt HTTPS_ONLY=0 (siehe .env.example)."
            )
        secret = secrets.token_urlsafe(32)

    return Einstellungen(
        secret_key=secret,
        admin_initial_password=env.get("ADMIN_INITIAL_PASSWORD") or "",
        admin_2fa=_bool(env.get("ADMIN_2FA"), False),
        https_only=https_only,
        data_dir=Path(env.get("DATA_DIR") or "./data"),
        max_upload_mb=_zahl(env.get("MAX_UPLOAD_MB"), 50, "MAX_UPLOAD_MB"),
        limit_code_stunde=_zahl(env.get("LIMIT_CODE_STUNDE"), 20, "LIMIT_CODE_STUNDE"),
        version=(env.get("GIT_SHA") or "").strip()[:40],
    )
