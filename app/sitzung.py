"""Sitzungen als signiertes Cookie – kein Sitzungsspeicher auf dem Server.

Der Inhalt ist nicht geheim, aber signiert: wer am Cookie dreht, fliegt raus. Mehr braucht
es nicht, weil im Cookie nur steht, *dass* jemand angemeldet ist, nie Personendaten.
"""
from dataclasses import dataclass
from typing import Any

from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

ADMIN_COOKIE = "kursunterlagen_admin"
# Zwölf Stunden: ein Arbeitstag am Stück, danach neu anmelden.
ADMIN_DAUER = 12 * 60 * 60

TEILNEHMER_COOKIE = "kursunterlagen_kurs"
# Dreissig Tage: nach dem Kurs soll niemand den Code suchen müssen, um etwas nachzuladen.
TEILNEHMER_DAUER = 30 * 24 * 60 * 60


@dataclass(frozen=True)
class Sitzungen:
    secret_key: str
    https_only: bool

    @property
    def _siegel(self) -> URLSafeTimedSerializer:
        return URLSafeTimedSerializer(self.secret_key, salt="kursunterlagen")

    def setzen(self, antwort: Response, name: str, daten: dict[str, Any], dauer: int) -> None:
        antwort.set_cookie(
            name,
            self._siegel.dumps(daten),
            max_age=dauer,
            httponly=True,          # kein Zugriff aus JavaScript
            samesite="lax",
            secure=self.https_only,  # in Produktion nur über HTTPS
            path="/",
        )

    def lesen(self, request: Request, name: str, dauer: int) -> dict[str, Any] | None:
        rohwert = request.cookies.get(name)
        if not rohwert:
            return None
        try:
            daten = self._siegel.loads(rohwert, max_age=dauer)
        except (BadSignature, SignatureExpired):
            return None
        return daten if isinstance(daten, dict) else None

    def loeschen(self, antwort: Response, name: str) -> None:
        antwort.delete_cookie(name, path="/")

    # --- Admin ---------------------------------------------------------------------

    def admin_anmelden(self, antwort: Response, zweiter_faktor_offen: bool) -> None:
        self.setzen(
            antwort,
            ADMIN_COOKIE,
            {"admin": True, "totp": "offen" if zweiter_faktor_offen else "ok"},
            ADMIN_DAUER,
        )

    def admin_lesen(self, request: Request) -> dict[str, Any] | None:
        daten = self.lesen(request, ADMIN_COOKIE, ADMIN_DAUER)
        return daten if daten and daten.get("admin") is True else None

    def admin_ist_fertig(self, request: Request) -> bool:
        """Angemeldet **und** zweiter Faktor erledigt."""
        daten = self.admin_lesen(request)
        return bool(daten and daten.get("totp") == "ok")

    def admin_abmelden(self, antwort: Response) -> None:
        self.loeschen(antwort, ADMIN_COOKIE)

    # --- Teilnehmer ----------------------------------------------------------------

    def kurs_freigeben(self, antwort: Response, kurs_id: int) -> None:
        """Nach richtigem Zugangscode: im Cookie steht nur die Kursnummer."""
        self.setzen(antwort, TEILNEHMER_COOKIE, {"kurs_id": int(kurs_id)}, TEILNEHMER_DAUER)

    def kurs_id(self, request: Request) -> int | None:
        daten = self.lesen(request, TEILNEHMER_COOKIE, TEILNEHMER_DAUER)
        if not daten:
            return None
        wert = daten.get("kurs_id")
        return int(wert) if isinstance(wert, int) else None

    def kurs_vergessen(self, antwort: Response) -> None:
        self.loeschen(antwort, TEILNEHMER_COOKIE)
