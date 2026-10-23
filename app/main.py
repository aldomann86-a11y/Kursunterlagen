"""Die Anwendung. E1: Startseite und /health – der Rest entsteht im Kurs (docs/STAND.md).

`erzeuge_app()` nimmt die Einstellungen als Argument, damit die Tests mit einem eigenen
Datenordner arbeiten können, ohne Umgebungsvariablen zu setzen.

Gestartet wird die App als Fabrik, nicht als fertiges Objekt im Modul:

    uvicorn app.main:erzeuge_app --factory --port 8050

So verlangt schon der Import keine Umgebungsvariablen – sonst liesse sich das Modul
weder testen noch in einem Lauf ohne .env überhaupt laden.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config, db

HIER = Path(__file__).parent


def erzeuge_app(einstellungen: config.Einstellungen | None = None) -> FastAPI:
    e = einstellungen or config.lade()
    datenbank = db.Datenbank(e.db_pfad)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        datenbank.einrichten()
        e.unterlagen_ordner.mkdir(parents=True, exist_ok=True)
        yield

    # Keine automatische API-Oberfläche: die App hat keine öffentliche Schnittstelle,
    # /docs und /openapi.json wären nur zusätzliche Fläche.
    app = FastAPI(
        title="Kursunterlagen",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.einstellungen = e
    app.state.db = datenbank
    app.state.gestartet = db.iso(db.jetzt())

    # Nur das eigene CSS. Die hochgeladenen Unterlagen werden **nie** so ausgeliefert,
    # sondern über einen Endpunkt mit Rechteprüfung (CLAUDE.md, docs/DATENSCHUTZ.md B4).
    app.mount("/static", StaticFiles(directory=HIER / "static"), name="static")
    vorlagen = Jinja2Templates(directory=str(HIER / "templates"))

    @app.get("/")
    async def startseite(request: Request):
        return vorlagen.TemplateResponse(request, "start.html", {})

    @app.get("/health")
    async def health():
        schreibbar = datenbank.schreibbar()
        antwort = {
            "status": "ok" if schreibbar else "degraded",
            "version": e.version,
            "gestartet": app.state.gestartet,
            "datenbank": "schreibbar" if schreibbar else "nicht schreibbar",
        }
        return JSONResponse(antwort, status_code=200 if schreibbar else 503)

    return app
