# Kursunterlagen

Portal für die Unterlagen der KIMAS-Kurse: Aldo lädt im Admin-Bereich Handouts, Spickzettel
und Slides hoch, die Teilnehmer öffnen den Link, geben den Zugangscode ihres Kurses ein und
laden herunter. Keine Konten, keine Personendaten.

Die App entsteht im Kurs selbst, gemeinsam mit den Teilnehmern.

## Lokal starten

```bash
python -m venv .venv && .venv/Scripts/activate
pip install -e ".[test]"
copy .env.example .env
python -m uvicorn app.main:app --reload --port 8050
```

Dann http://127.0.0.1:8050 öffnen. Datenbank und Uploads entstehen unter `./data/`.

Was gebaut ist: [docs/STAND.md](docs/STAND.md) · Warum so: [docs/ENTSCHEIDE.md](docs/ENTSCHEIDE.md)
