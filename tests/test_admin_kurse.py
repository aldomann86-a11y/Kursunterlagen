"""Kursverwaltung und Upload im Admin-Bereich (E4 und E5)."""
import re

PDF = b"%PDF-1.4 erfundene Probedatei"


def code_aus(html: str) -> str:
    treffer = re.search(r'<p class="code">([a-z0-9-]+)</p>', html)
    assert treffer, "Der Zugangscode steht nicht auf der Seite"
    return treffer.group(1)


def kurs_anlegen(admin, name="Probekurs", **felder) -> tuple[str, str]:
    antwort = admin.post("/admin/kurse", data={"name": name, **felder})
    assert antwort.status_code == 200
    return code_aus(antwort.text), antwort.text


def kurs_id_aus(admin) -> int:
    treffer = re.search(r'href="/admin/kurse/(\d+)"', admin.get("/admin").text)
    assert treffer
    return int(treffer.group(1))


# --- Zugang ----------------------------------------------------------------------------

def test_ohne_anmeldung_kein_kurs(client_mit_konto):
    antwort = client_mit_konto.post("/admin/kurse", data={"name": "Heimlich"},
                                    follow_redirects=False)
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/admin/anmelden"


def test_ohne_anmeldung_kein_upload(client_mit_konto):
    antwort = client_mit_konto.post(
        "/admin/kurse/1/unterlagen",
        data={"titel": "Heimlich"},
        files={"datei": ("a.pdf", PDF, "application/pdf")},
        follow_redirects=False,
    )
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/admin/anmelden"


# --- Kurse -----------------------------------------------------------------------------

def test_kurs_anlegen_zeigt_den_code_einmal(admin):
    code, seite = kurs_anlegen(admin, "KI-Probekurs", datum="2026-11-04")
    assert len(code) == 9
    assert "KI-Probekurs" in seite
    assert "nicht nochmals anzeigen" in seite

    # Beim nächsten Aufruf ist der Code weg – er steht nirgends gespeichert.
    assert code not in admin.get("/admin").text


def test_kurs_ohne_namen_wird_abgelehnt(admin):
    antwort = admin.post("/admin/kurse", data={"name": "   "})
    assert antwort.status_code == 400
    assert "Namen" in antwort.text


def test_neuer_code_ist_ein_anderer(admin):
    alt, _ = kurs_anlegen(admin)
    kurs_id = kurs_id_aus(admin)
    neu = code_aus(admin.post(f"/admin/kurse/{kurs_id}/code").text)
    assert neu != alt


def test_sperren_und_freigeben(admin):
    kurs_anlegen(admin)
    kurs_id = kurs_id_aus(admin)

    admin.post(f"/admin/kurse/{kurs_id}/sperren")
    assert "gesperrt" in admin.get("/admin").text

    admin.post(f"/admin/kurse/{kurs_id}/sperren")
    assert "Sperren" in admin.get("/admin").text


def test_kursliste_zaehlt_unterlagen(admin):
    kurs_anlegen(admin)
    kurs_id = kurs_id_aus(admin)
    admin.post(
        f"/admin/kurse/{kurs_id}/unterlagen",
        data={"titel": "Handout"},
        files={"datei": ("handout.pdf", PDF, "application/pdf")},
    )
    assert ">1</td>" in admin.get("/admin").text


# --- Upload ----------------------------------------------------------------------------

def test_hochladen_erscheint_in_der_liste(admin):
    kurs_anlegen(admin)
    kurs_id = kurs_id_aus(admin)

    antwort = admin.post(
        f"/admin/kurse/{kurs_id}/unterlagen",
        data={"titel": "Aufgabenblatt", "beschreibung": "Zum Mitarbeiten"},
        files={"datei": ("aufgaben.pdf", PDF, "application/pdf")},
        follow_redirects=False,
    )
    assert antwort.status_code == 303

    seite = admin.get(f"/admin/kurse/{kurs_id}").text
    assert "Aufgabenblatt" in seite
    assert "aufgaben.pdf" in seite
    assert "Zum Mitarbeiten" in seite


def test_falscher_dateityp_wird_abgelehnt(admin):
    kurs_anlegen(admin)
    kurs_id = kurs_id_aus(admin)

    antwort = admin.post(
        f"/admin/kurse/{kurs_id}/unterlagen",
        data={"titel": "Programm"},
        files={"datei": ("programm.exe", b"MZ...", "application/octet-stream")},
    )
    assert antwort.status_code == 400
    assert "Dateityp" in antwort.text
    assert "Programm" not in admin.get(f"/admin/kurse/{kurs_id}").text.split("<h2>")[1]


def test_zu_grosse_datei_wird_abgelehnt(mach_client):
    from tests.conftest import PASSWORT

    with mach_client(ADMIN_INITIAL_PASSWORD=PASSWORT, MAX_UPLOAD_MB=1) as c:
        c.post("/admin/anmelden", data={"passwort": PASSWORT})
        kurs_anlegen(c)
        kurs_id = kurs_id_aus(c)
        antwort = c.post(
            f"/admin/kurse/{kurs_id}/unterlagen",
            data={"titel": "Zu gross"},
            files={"datei": ("gross.pdf", b"x" * (1024 * 1024 + 1), "application/pdf")},
        )
        assert antwort.status_code == 400
        assert "zu gross" in antwort.text


def test_upload_ohne_datei(admin):
    kurs_anlegen(admin)
    kurs_id = kurs_id_aus(admin)
    antwort = admin.post(f"/admin/kurse/{kurs_id}/unterlagen", data={"titel": "Ohne"})
    assert antwort.status_code == 400
    assert "Datei wählen" in antwort.text


def test_ausblenden_und_einblenden(admin):
    kurs_anlegen(admin)
    kurs_id = kurs_id_aus(admin)
    admin.post(
        f"/admin/kurse/{kurs_id}/unterlagen",
        data={"titel": "Handout"},
        files={"datei": ("a.pdf", PDF, "application/pdf")},
    )
    seite = admin.get(f"/admin/kurse/{kurs_id}").text
    unterlage_id = int(re.search(r"/admin/unterlagen/(\d+)/sichtbarkeit", seite).group(1))

    admin.post(f"/admin/unterlagen/{unterlage_id}/sichtbarkeit")
    assert "ausgeblendet" in admin.get(f"/admin/kurse/{kurs_id}").text

    admin.post(f"/admin/unterlagen/{unterlage_id}/sichtbarkeit")
    assert "ausgeblendet" not in admin.get(f"/admin/kurse/{kurs_id}").text


def test_reihenfolge_aendern(admin):
    kurs_anlegen(admin)
    kurs_id = kurs_id_aus(admin)
    for titel, name in (("Erste", "a.pdf"), ("Zweite", "b.pdf")):
        admin.post(
            f"/admin/kurse/{kurs_id}/unterlagen",
            data={"titel": titel},
            files={"datei": (name, PDF, "application/pdf")},
        )

    seite = admin.get(f"/admin/kurse/{kurs_id}").text
    assert seite.index("Erste") < seite.index("Zweite")

    erste_id = int(re.search(r"/admin/unterlagen/(\d+)/verschieben", seite).group(1))
    admin.post(f"/admin/unterlagen/{erste_id}/verschieben", data={"schritte": "1"})

    seite = admin.get(f"/admin/kurse/{kurs_id}").text
    assert seite.index("Zweite") < seite.index("Erste")
