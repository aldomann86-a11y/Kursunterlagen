"""Die Seite für die Teilnehmer: Code eingeben, Unterlagen holen.

Keine Anmeldung, kein Konto, keine Personendaten. Im Cookie steht nur die Kursnummer
(docs/ENTSCHEIDE.md, docs/DATENSCHUTZ.md).

Jeder Download läuft über `/unterlagen/{id}` und prüft dort, ob die Unterlage wirklich
zu dem Kurs gehört, für den die Sitzung gilt. Der Upload-Ordner wird **nie** direkt
ausgeliefert (CLAUDE.md).
"""
from fastapi import APIRouter, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import bremse, kurse, unterlagen
from app.config import Einstellungen
from app.db import Datenbank
from app.sitzung import Sitzungen

ART = "code"
FALSCH = "Dieser Code passt nicht."
GESPERRT = "Zu viele Versuche. Bitte in einer Stunde nochmals – oder frag im Kurs nach."


def router(
    e: Einstellungen,
    datenbank: Datenbank,
    vorlagen: Jinja2Templates,
    sitzungen: Sitzungen,
) -> APIRouter:
    r = APIRouter()

    def seite(request: Request, name: str, inhalt: dict, status: int = 200) -> HTMLResponse:
        return vorlagen.TemplateResponse(request, name, inhalt, status_code=status)

    def weiter(ziel: str) -> RedirectResponse:
        return RedirectResponse(ziel, status_code=303)

    @r.get("/")
    async def startseite(request: Request):
        if sitzungen.kurs_id(request) is not None:
            return weiter("/unterlagen")
        return seite(request, "start.html", {})

    @r.post("/zugang")
    async def zugang(request: Request, code: str = Form("")):
        with datenbank.verbindung() as conn:
            quelle = bremse.absender(request, e.secret_key)
            if bremse.gesperrt(conn, ART, quelle, e.limit_code_stunde):
                return seite(request, "start.html", {"fehler": GESPERRT}, 429)

            kurs = kurse.mit_code(conn, e.secret_key, code)
            if kurs is None:
                bremse.merken(conn, ART, quelle)
                return seite(request, "start.html", {"fehler": FALSCH}, 401)

            bremse.zuruecksetzen(conn, ART, quelle)
            kurs_id = kurs["id"]

        antwort = weiter("/unterlagen")
        sitzungen.kurs_freigeben(antwort, kurs_id)
        return antwort

    @r.get("/unterlagen")
    async def liste(request: Request):
        kurs_id = sitzungen.kurs_id(request)
        if kurs_id is None:
            return weiter("/")
        with datenbank.verbindung() as conn:
            kurs = kurse.finden(conn, kurs_id)
            # Gesperrt oder abgelaufen: der Zugang endet sofort, auch mit altem Cookie.
            if kurs is None or not kurse.ist_offen(kurs):
                antwort = weiter("/")
                sitzungen.kurs_vergessen(antwort)
                return antwort
            inhalt = {
                "kurs": kurs,
                "liste": unterlagen.alle_fuer(conn, kurs_id, nur_sichtbare=True),
                "lesbar": unterlagen.lesbare_groesse,
            }
        return seite(request, "unterlagen.html", inhalt)

    @r.get("/unterlagen/{unterlage_id}")
    async def holen(request: Request, unterlage_id: int):
        kurs_id = sitzungen.kurs_id(request)
        if kurs_id is None:
            return weiter("/")
        with datenbank.verbindung() as conn:
            kurs = kurse.finden(conn, kurs_id)
            if kurs is None or not kurse.ist_offen(kurs):
                return weiter("/")
            # Die Rechteprüfung: gehört die Unterlage zu diesem Kurs und ist sie sichtbar?
            zeile = unterlagen.fuer_kurs(conn, kurs_id, unterlage_id)
            if zeile is None:
                return seite(request, "nicht_gefunden.html", {}, 404)
            pfad = unterlagen.pfad(e.unterlagen_ordner, zeile["ablage"])
            if not pfad.is_file():
                return seite(request, "nicht_gefunden.html", {}, 404)
            unterlagen.download_merken(conn, kurs_id, unterlage_id)
            name, mime = zeile["dateiname"], zeile["mime"]
        return FileResponse(pfad, media_type=mime, filename=name)

    @r.post("/abmelden")
    async def abmelden():
        antwort = weiter("/")
        sitzungen.kurs_vergessen(antwort)
        return antwort

    return r
