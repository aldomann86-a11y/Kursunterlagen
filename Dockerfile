FROM python:3.13-slim

# Commit-Hash des Builds (setzt der Deploy-Workflow); /health meldet ihn als "version".
ARG GIT_SHA=
ENV GIT_SHA=$GIT_SHA

WORKDIR /app
# Erst alles kopieren, dann installieren: pip install . braucht das Paketverzeichnis app/
# bereits beim Build (setuptools packages=["app"]) – Muster aus ../kimas-post/Dockerfile.
COPY . .
RUN pip install --no-cache-dir .

# Datenbank und hochgeladene Unterlagen. Ohne Volume ist nach jedem Deploy alles weg
# (docs/BETRIEB.md).
VOLUME ["/data"]
ENV DATA_DIR=/data
EXPOSE 8000

# Kein curl und kein wget im Image, darum Python. 503 heisst «läuft, Datenbank klemmt»
# und zählt hier nicht als lebendig – anders als bei kimas-post, wo nur ein externes
# Relais fehlen kann.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import http.client as h,sys;c=h.HTTPConnection('127.0.0.1',8000,timeout=5);c.request('GET','/health');sys.exit(0 if c.getresponse().status==200 else 1)"

# --factory: app.main stellt erzeuge_app() bereit, kein fertiges App-Objekt (app/main.py).
# --proxy-headers: hinter dem Reverse-Proxy die echte Client-IP lesen, sonst teilen sich
# alle Besucher die Proxy-IP und das Limit auf die Code-Eingabe greift nicht.
CMD uvicorn app.main:erzeuge_app --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
