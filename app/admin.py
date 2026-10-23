"""Der Admin-Bereich: anmelden, zweiter Faktor, abmelden.

E3 baut nur den Zugang. Was danach im Bereich steht – Kurse (E4), Unterlagen (E5) –
kommt im Kurs dazu (docs/STAND.md).

Ablauf beim Anmelden:
    Passwort richtig
      └─ ADMIN_2FA=0 ................................. fertig
      └─ ADMIN_2FA=1, Faktor bestätigt ............... Code eingeben  (/admin/2fa)
      └─ ADMIN_2FA=1, Faktor fehlt oder unbestätigt .. einrichten     (/admin/2fa/einrichten)

Es gibt absichtlich keine Protokollzeile und keine Meldung, die verrät, ob ein Konto
besteht oder welcher Teil der Eingabe falsch war.
"""
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import bremse, konto
from app.config import Einstellungen
from app.db import Datenbank
from app.sitzung import Sitzungen

ART = "login"
FALSCH = "Passwort oder Code stimmt nicht."
GESPERRT = (
    "Zu viele Fehlversuche. Bitte in einer Stunde erneut versuchen – oder vorher "
    "im Betrieb nachsehen (docs/BETRIEB.md)."
)


def router(
    e: Einstellungen,
    datenbank: Datenbank,
    vorlagen: Jinja2Templates,
    sitzungen: Sitzungen,
) -> APIRouter:
    r = APIRouter(prefix="/admin")

    def seite(request: Request, name: str, inhalt: dict, status: int = 200) -> HTMLResponse:
        return vorlagen.TemplateResponse(request, name, inhalt, status_code=status)

    def weiter(ziel: str) -> RedirectResponse:
        # 303: nach einem Formular folgt ein GET, kein zweites POST beim Neuladen.
        return RedirectResponse(ziel, status_code=303)

    def zweiter_faktor_noetig(conn) -> bool:
        """Zweiter Faktor nur, wenn eingeschaltet *und* fertig eingerichtet."""
        if not e.admin_2fa:
            return False
        k = konto.lesen(conn)
        return bool(k and k["totp_secret"] and k["totp_bestaetigt"])

    # --- Anmelden ------------------------------------------------------------------

    @r.get("/anmelden")
    async def anmeldeformular(request: Request):
        if sitzungen.admin_ist_fertig(request):
            return weiter("/admin")
        with datenbank.verbindung() as conn:
            kein_konto = konto.lesen(conn) is None
        return seite(request, "admin_anmelden.html", {"kein_konto": kein_konto})

    @r.post("/anmelden")
    async def anmelden(request: Request, passwort: str = Form("")):
        with datenbank.verbindung() as conn:
            quelle = bremse.absender(request, e.secret_key)
            if bremse.gesperrt(conn, ART, quelle, e.limit_login_stunde):
                return seite(request, "admin_anmelden.html", {"fehler": GESPERRT}, 429)

            k = konto.lesen(conn)
            if k is None or not konto.passwort_stimmt(passwort, k["passwort_hash"]):
                bremse.merken(conn, ART, quelle)
                return seite(
                    request,
                    "admin_anmelden.html",
                    {"fehler": FALSCH, "kein_konto": k is None},
                    401,
                )

            bremse.zuruecksetzen(conn, ART, quelle)
            faktor_noetig = zweiter_faktor_noetig(conn)
            faktor_fehlt = e.admin_2fa and not faktor_noetig

        antwort = weiter(
            "/admin/2fa/einrichten" if faktor_fehlt
            else "/admin/2fa" if faktor_noetig
            else "/admin"
        )
        sitzungen.admin_anmelden(antwort, zweiter_faktor_offen=e.admin_2fa)
        return antwort

    @r.post("/abmelden")
    async def abmelden():
        antwort = weiter("/")
        sitzungen.admin_abmelden(antwort)
        return antwort

    # --- Zweiter Faktor ------------------------------------------------------------

    @r.get("/2fa")
    async def faktorformular(request: Request):
        if sitzungen.admin_lesen(request) is None:
            return weiter("/admin/anmelden")
        if sitzungen.admin_ist_fertig(request):
            return weiter("/admin")
        return seite(request, "admin_2fa.html", {})

    @r.post("/2fa")
    async def faktor_pruefen(request: Request, code: str = Form("")):
        if sitzungen.admin_lesen(request) is None:
            return weiter("/admin/anmelden")

        with datenbank.verbindung() as conn:
            quelle = bremse.absender(request, e.secret_key)
            if bremse.gesperrt(conn, ART, quelle, e.limit_login_stunde):
                return seite(request, "admin_2fa.html", {"fehler": GESPERRT}, 429)

            k = konto.lesen(conn)
            if k is None or not konto.totp_stimmt(k["totp_secret"], code):
                bremse.merken(conn, ART, quelle)
                return seite(request, "admin_2fa.html", {"fehler": FALSCH}, 401)

            bremse.zuruecksetzen(conn, ART, quelle)

        antwort = weiter("/admin")
        sitzungen.admin_anmelden(antwort, zweiter_faktor_offen=False)
        return antwort

    @r.get("/2fa/einrichten")
    async def faktor_einrichten(request: Request):
        if sitzungen.admin_lesen(request) is None:
            return weiter("/admin/anmelden")

        with datenbank.verbindung() as conn:
            k = konto.lesen(conn)
            if k is None:
                return weiter("/admin/anmelden")
            # Ein bestätigter Faktor wird hier nicht ersetzt – sonst könnte eine halb
            # offene Sitzung den zweiten Faktor einfach austauschen.
            if k["totp_secret"] and k["totp_bestaetigt"]:
                return weiter("/admin/2fa")
            geheimnis = k["totp_secret"] or konto.neues_totp_secret()
            if not k["totp_secret"]:
                konto.totp_secret_setzen(conn, geheimnis)

        uri = konto.totp_uri(geheimnis)
        return seite(
            request,
            "admin_2fa_einrichten.html",
            {"qr": konto.qr_svg(uri), "geheimnis": geheimnis},
        )

    @r.post("/2fa/einrichten")
    async def faktor_bestaetigen(request: Request, code: str = Form("")):
        if sitzungen.admin_lesen(request) is None:
            return weiter("/admin/anmelden")

        with datenbank.verbindung() as conn:
            k = konto.lesen(conn)
            if k is None or not k["totp_secret"]:
                return weiter("/admin/2fa/einrichten")
            if not konto.totp_stimmt(k["totp_secret"], code):
                uri = konto.totp_uri(k["totp_secret"])
                return seite(
                    request,
                    "admin_2fa_einrichten.html",
                    {
                        "qr": konto.qr_svg(uri),
                        "geheimnis": k["totp_secret"],
                        "fehler": FALSCH,
                    },
                    401,
                )
            konto.totp_bestaetigen(conn)

        antwort = weiter("/admin")
        sitzungen.admin_anmelden(antwort, zweiter_faktor_offen=False)
        return antwort

    # --- Übersicht -----------------------------------------------------------------

    @r.get("")
    async def uebersicht(request: Request):
        if sitzungen.admin_lesen(request) is None:
            return weiter("/admin/anmelden")
        if not sitzungen.admin_ist_fertig(request):
            with datenbank.verbindung() as conn:
                ziel = "/admin/2fa" if zweiter_faktor_noetig(conn) else "/admin/2fa/einrichten"
            return weiter(ziel)
        return seite(request, "admin_start.html", {"zwei_faktoren": e.admin_2fa})

    return r
