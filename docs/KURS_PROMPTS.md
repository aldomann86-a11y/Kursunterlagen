# Prompts für den Unterricht

Drei Prompts, rund fünfzehn Minuten. Alles darunter ist gebaut und geprüft
(`app/kurse.py`, `app/unterlagen.py`, Login, Bremse, Datenbank) – im Unterricht entstehen
nur noch die Seiten, die man sieht.

**Vorher einmal prüfen** (eine Minute, bevor die Klasse zuschaut):

```bash
cd C:\Users\aldom\_Claude\kursunterlagen; .venv\Scripts\python.exe -m pytest -q
```

Dann die App starten und `http://127.0.0.1:8050` offen lassen:

```bash
cd C:\Users\aldom\_Claude\kursunterlagen; .venv\Scripts\python.exe -m uvicorn app.main:erzeuge_app --factory --port 8050 --reload
```

Anmelden unter `/admin` mit dem Passwort aus deiner `.env` (`ADMIN_INITIAL_PASSWORD`).
Die Unterlagen für heute liegen hochladebereit in `_hochladen/` (KI und Datenmanagement,
als PDF gedruckt) – Übersicht und Titel in `_hochladen/LIESMICH.md`.
Der zweite Faktor ist für den Unterricht ausgeschaltet (`ADMIN_2FA=0`) – kein Handy nötig.

Jeder Prompt sagt ausdrücklich «direkt bauen, keine Rückfragen». Ohne diesen Satz hält sich
Claude an die Hausregel, erst zu fragen und einen Plan zu zeigen – das kostet im Unterricht
die halbe Zeit.

---

## 1 – Kurse anlegen und Codes vergeben (rund 4 Minuten)

```text
Baue die Kursverwaltung im Admin-Bereich. Kleiner Auftrag: direkt bauen, keine Rückfragen, keinen Plan zeigen.

Nutze app/kurse.py – dort ist alles fertig (anlegen, alle, finden, aendern, aktiv_setzen, code_neu_setzen, ist_offen). Nichts davon neu schreiben.

In app/admin.py ergänzen:
- GET /admin zeigt zusätzlich die Liste aller Kurse (Name, Datum, offen bis, aktiv/gesperrt) und ein Formular zum Anlegen mit Name, Datum und «offen bis».
- POST /admin/kurse legt den Kurs an. kurse.anlegen gibt den Zugangscode im Klartext zurück: zeige ihn danach einmalig gross an, mit dem Hinweis, dass er nirgends gespeichert ist.
- POST /admin/kurse/{kurs_id}/code erzeugt einen neuen Code und zeigt ihn genauso an.
- POST /admin/kurse/{kurs_id}/sperren schaltet aktiv um.
Alle neuen Routen nur für angemeldete Admins, genau wie die bestehende Übersicht.

Vorlage app/templates/admin_start.html erweitern, Gestaltung mit dem vorhandenen app/static/stil.css, keine neuen Abhängigkeiten.

Danach: python -m pytest -q muss grün bleiben. Ergänze zwei Tests in tests/test_admin.py: einen Kurs anlegen zeigt den Code auf der Seite, und ohne Anmeldung ist POST /admin/kurse gesperrt.
```

**Vorzeigen:** Zwei Kurse anlegen – «KI in der Betriebsleiterschule» und
«Datenmanagement in der Landwirtschaft». Den Code des KI-Kurses am Beamer zeigen:
das ist der Moment, in dem die Klasse den Zugang bekommt.

---

## 2 – Unterlagen hochladen (rund 4 Minuten)

```text
Baue das Hochladen der Unterlagen. Kleiner Auftrag: direkt bauen, keine Rückfragen, keinen Plan zeigen.

Nutze app/unterlagen.py – dort ist alles fertig (speichern, alle_fuer, aendern, sichtbar_setzen, verschieben, lesbare_groesse, Abgelehnt). Nichts davon neu schreiben.

In app/admin.py ergänzen:
- GET /admin/kurse/{kurs_id} zeigt den Kurs mit seinen Unterlagen (Titel, Dateiname, Grösse über lesbare_groesse, sichtbar ja/nein) und darunter ein Upload-Formular mit Titel, Beschreibung und Datei (enctype multipart/form-data).
- POST /admin/kurse/{kurs_id}/unterlagen nimmt die Datei als UploadFile an, liest sie mit await datei.read() und ruft unterlagen.speichern mit e.max_upload_bytes auf. Ein unterlagen.Abgelehnt wird als Meldung auf derselben Seite angezeigt, nicht als Absturz.
- POST /admin/unterlagen/{unterlage_id}/sichtbarkeit schaltet ein und aus.
- POST /admin/unterlagen/{unterlage_id}/verschieben mit Formularfeld schritte (-1 oder 1) ändert die Reihenfolge.
Alle Routen nur für angemeldete Admins. Von der Kursliste auf /admin je Kurs auf diese Seite verlinken.

Neue Vorlage app/templates/admin_kurs.html, Gestaltung wie bisher.

Danach: python -m pytest -q grün, plus zwei Tests in tests/test_admin.py: eine PDF-Datei hochladen erscheint in der Liste, eine .exe-Datei wird mit Meldung abgelehnt und landet nicht in der Datenbank.
```

**Vorzeigen:** Aus `_hochladen/KI/` hochladen – Aufgabenblatt, Zusammenfassung,
Praxis-Prompts, Quellen, Folien (Titel stehen in `_hochladen/LIESMICH.md`), dann
`_hochladen/Datenmanagement/` in den zweiten Kurs. Einmal absichtlich eine `.exe`
versuchen, damit die Positivliste sichtbar wird.

**Nicht hochladen:** den Referentenplan (nur für dich) und die Teilnehmerliste
(Personendaten) – beides steht in `_hochladen/LIESMICH.md`.

---

## 3 – Teilnehmerseite mit Code und Download (rund 5 Minuten)

```text
Baue die Teilnehmerseite. Kleiner Auftrag: direkt bauen, keine Rückfragen, keinen Plan zeigen.

Neue Datei app/teilnehmer.py nach demselben Muster wie app/admin.py: eine Funktion router(e, datenbank, vorlagen, sitzungen), die einen APIRouter zurückgibt, und in app/main.py mit include_router einbinden.

Nutze, was da ist: kurse.mit_code, unterlagen.alle_fuer(nur_sichtbare=True), unterlagen.fuer_kurs, unterlagen.download_merken, unterlagen.pfad, unterlagen.lesbare_groesse, bremse (art "code", Grenze e.limit_code_stunde) und sitzungen.kurs_freigeben / kurs_id / kurs_vergessen. Nichts neu schreiben.

- GET / zeigt das Formular für den Zugangscode (app/templates/start.html umbauen). Wer schon freigeschaltet ist, wird auf /unterlagen geleitet.
- POST /zugang prüft den Code. Vorher bremse.gesperrt prüfen, bei Fehlversuch bremse.merken und dieselbe Seite mit «Dieser Code passt nicht» zeigen. Bei Erfolg bremse.zuruecksetzen, sitzungen.kurs_freigeben und weiter auf /unterlagen.
- GET /unterlagen zeigt den Kursnamen und die sichtbaren Unterlagen mit Titel, Beschreibung, Grösse und einem Download-Knopf. Ohne Sitzung zurück auf /.
- GET /unterlagen/{unterlage_id} prüft mit unterlagen.fuer_kurs gegen die Kursnummer aus der Sitzung, zählt mit download_merken und liefert die Datei mit FileResponse aus, filename = der gespeicherte dateiname. Passt die Unterlage nicht zum Kurs: 404.
- POST /abmelden vergisst den Kurs und führt zurück auf /.
Unten auf /unterlagen ein Satz: keine Anmeldung nötig, der Download-Zähler ist anonym.

Danach: python -m pytest -q grün, plus drei Tests in einer neuen Datei tests/test_teilnehmer.py: falscher Code gibt keinen Zugang, richtiger Code zeigt nur die Unterlagen des eigenen Kurses, und der Download einer Unterlage aus einem anderen Kurs gibt 404.
```

**Vorzeigen:** Den Code vom Beamer in einem zweiten Browserfenster eingeben, das
Aufgabenblatt herunterladen. Fertig – die Klasse hat die Unterlagen des Tages.

---

## Wenn etwas klemmt

| Lage | Prompt |
|---|---|
| Tests rot | `Die Tests sind rot. Zeig mir die Fehlermeldung und repariere die Ursache, nicht den Test. Direkt machen, keine Rückfragen.` |
| Seite sieht kaputt aus | `Die Seite /admin sieht falsch aus. Schau sie dir im Browser an und bring die Gestaltung mit app/static/stil.css in Ordnung. Keine neuen Abhängigkeiten.` |
| Claude fängt an zu fragen | `Keine Rückfragen, kein Plan – bau es direkt wie beschrieben.` |
| Claude baut zu viel | `Nur das, was im Auftrag steht. Nichts umbauen, was schon läuft.` |
| Etwas ist halb fertig | `git stash` – und den Prompt neu geben. |
| Zeit wird knapp | Prompt 3 weglassen, dafür zeigen, wie der Admin die Unterlage herunterlädt. Die Teilnehmerseite kommt nach dem Kurs. |

## Danach

```text
/abschluss
```

Führt Stand, Entscheide und Pendenzen nach. Erst danach (und nur, wenn du es willst):
Deploy über `/deploy` – dafür braucht es vorher das Ziel aus `docs/OFFENE_PUNKTE.md`, F1.
