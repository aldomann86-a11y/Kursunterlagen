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
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import bremse, konto, kurse, unterlagen
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

    # --- Wächter -------------------------------------------------------------------

    def abgewiesen(request: Request) -> RedirectResponse | None:
        """Gibt die Weiterleitung zurück, wenn jemand (noch) nicht hineindarf."""
        if sitzungen.admin_lesen(request) is None:
            return weiter("/admin/anmelden")
        if not sitzungen.admin_ist_fertig(request):
            with datenbank.verbindung() as conn:
                ziel = "/admin/2fa" if zweiter_faktor_noetig(conn) else "/admin/2fa/einrichten"
            return weiter(ziel)
        return None

    def uebersicht_inhalt(conn, **zusatz) -> dict:
        anzahl = {
            int(z["kurs_id"]): int(z["anzahl"])
            for z in conn.execute(
                "SELECT kurs_id, count(*) AS anzahl FROM unterlage GROUP BY kurs_id"
            )
        }
        return {
            "zwei_faktoren": e.admin_2fa,
            "kursliste": kurse.alle(conn),
            "anzahl": anzahl,
            **zusatz,
        }

    # --- Übersicht und Kurse -------------------------------------------------------

    @r.get("")
    async def uebersicht(request: Request):
        if (ab := abgewiesen(request)) is not None:
            return ab
        with datenbank.verbindung() as conn:
            return seite(request, "admin_start.html", uebersicht_inhalt(conn))

    @r.post("/kurse")
    async def kurs_anlegen(
        request: Request,
        name: str = Form(""),
        datum: str = Form(""),
        offen_bis: str = Form(""),
    ):
        if (ab := abgewiesen(request)) is not None:
            return ab
        with datenbank.verbindung() as conn:
            try:
                kurs_id, code = kurse.anlegen(conn, e.secret_key, name, datum, offen_bis)
            except ValueError as grund:
                return seite(request, "admin_start.html",
                             uebersicht_inhalt(conn, fehler=str(grund)), 400)
            # Kein Redirect: der Klartext-Code wird einmal angezeigt und nirgends
            # gespeichert – in einer Adresszeile hätte er nichts zu suchen.
            return seite(request, "admin_start.html",
                         uebersicht_inhalt(conn, neuer_code=code,
                                           code_kurs=kurse.finden(conn, kurs_id)))

    @r.post("/kurse/{kurs_id}/code")
    async def code_erneuern(request: Request, kurs_id: int):
        if (ab := abgewiesen(request)) is not None:
            return ab
        with datenbank.verbindung() as conn:
            if kurse.finden(conn, kurs_id) is None:
                return weiter("/admin")
            code = kurse.code_neu_setzen(conn, e.secret_key, kurs_id)
            return seite(request, "admin_start.html",
                         uebersicht_inhalt(conn, neuer_code=code,
                                           code_kurs=kurse.finden(conn, kurs_id)))

    @r.post("/kurse/{kurs_id}/sperren")
    async def kurs_sperren(request: Request, kurs_id: int):
        if (ab := abgewiesen(request)) is not None:
            return ab
        with datenbank.verbindung() as conn:
            kurs = kurse.finden(conn, kurs_id)
            if kurs is not None:
                kurse.aktiv_setzen(conn, kurs_id, not kurs["aktiv"])
        return weiter("/admin")

    # --- Unterlagen eines Kurses ---------------------------------------------------

    def kurs_inhalt(conn, kurs, **zusatz) -> dict:
        return {
            "kurs": kurs,
            "liste": unterlagen.alle_fuer(conn, kurs["id"]),
            "downloads": unterlagen.downloads_je_unterlage(conn, kurs["id"]),
            "lesbar": unterlagen.lesbare_groesse,
            "max_mb": e.max_upload_mb,
            "erlaubt": ", ".join(sorted(unterlagen.ERLAUBT)),
            **zusatz,
        }

    @r.get("/kurse/{kurs_id}")
    async def kursseite(request: Request, kurs_id: int):
        if (ab := abgewiesen(request)) is not None:
            return ab
        with datenbank.verbindung() as conn:
            kurs = kurse.finden(conn, kurs_id)
            if kurs is None:
                return weiter("/admin")
            return seite(request, "admin_kurs.html", kurs_inhalt(conn, kurs))

    @r.post("/kurse/{kurs_id}/unterlagen")
    async def hochladen(
        request: Request,
        kurs_id: int,
        titel: str = Form(""),
        beschreibung: str = Form(""),
        datei: UploadFile = File(None),
    ):
        if (ab := abgewiesen(request)) is not None:
            return ab
        with datenbank.verbindung() as conn:
            kurs = kurse.finden(conn, kurs_id)
            if kurs is None:
                return weiter("/admin")
            if datei is None or not datei.filename:
                return seite(request, "admin_kurs.html",
                             kurs_inhalt(conn, kurs, fehler="Bitte eine Datei wählen."), 400)
            inhalt = await datei.read()
            try:
                unterlagen.speichern(
                    conn, e.unterlagen_ordner, kurs_id, titel, datei.filename, inhalt,
                    e.max_upload_bytes, beschreibung,
                )
            except unterlagen.Abgelehnt as grund:
                return seite(request, "admin_kurs.html",
                             kurs_inhalt(conn, kurs, fehler=str(grund)), 400)
        return weiter(f"/admin/kurse/{kurs_id}")

    @r.post("/unterlagen/{unterlage_id}/sichtbarkeit")
    async def sichtbarkeit(request: Request, unterlage_id: int):
        if (ab := abgewiesen(request)) is not None:
            return ab
        with datenbank.verbindung() as conn:
            zeile = unterlagen.finden(conn, unterlage_id)
            if zeile is None:
                return weiter("/admin")
            unterlagen.sichtbar_setzen(conn, unterlage_id, not zeile["sichtbar"])
            kurs_id = zeile["kurs_id"]
        return weiter(f"/admin/kurse/{kurs_id}")

    @r.post("/unterlagen/{unterlage_id}/verschieben")
    async def verschieben(request: Request, unterlage_id: int, schritte: int = Form(0)):
        if (ab := abgewiesen(request)) is not None:
            return ab
        with datenbank.verbindung() as conn:
            zeile = unterlagen.finden(conn, unterlage_id)
            if zeile is None:
                return weiter("/admin")
            unterlagen.verschieben(conn, unterlage_id, 1 if schritte > 0 else -1)
            kurs_id = zeile["kurs_id"]
        return weiter(f"/admin/kurse/{kurs_id}")

    return r
