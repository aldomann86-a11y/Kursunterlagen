# Kursunterlagen – Datenschutz

Regeln und Begründungen: globales Konzept `dotfiles/docs/DATENSCHUTZ.md`
(Datenklassen §3, KI §4, Register der Dienste §6, Basis-Standard §7, Fristen §8).
Hier steht nur, was für dieses Projekt gilt.

## Rollen

| | |
|---|---|
| Verantwortlicher | KIMAS GmbH (Aldo Mann), eigener Betrieb |
| KIMAS | Verantwortliche, nicht Auftragsbearbeiterin |
| Betroffene | Kursteilnehmer – nur indirekt: sie melden sich nicht an |
| EU-Bezug | nein |

## Datenklassen

Höchste Klasse dieses Projekts: **D1**, und das nur wegen des Admin-Kontos und der
Server-Protokolle. Zu den Teilnehmern wird nichts gespeichert.

| Tabelle / Feld / Upload | Klasse | Zweck | Frist | Löschung umgesetzt |
|---|---|---|---|---|
| `kurs` (Name, Datum, Code-Hash) | D0 | Unterlagen gruppieren, Zugang prüfen | 12 Mon. nach `offen_bis` | offen (B9) |
| `unterlage` + Datei im Volume | D0 | Unterlage bereitstellen | mit dem Kurs | offen (B9) |
| `download` (Zeit, Kurs, Unterlage) | D0 | Zähler, wie oft etwas geholt wurde | 12 Mon. | offen (B9) |
| `versuch` (Zeit, IP als HMAC) | D1 | Erraten des Codes bremsen | 24 Std. | offen (mit E6) |
| `admin` (Passwort-Hash, TOTP) | D1 | Admin-Login | mit dem Projekt | – |
| Reverse-Proxy-Protokoll (IP) | D1 | Betrieb | nach Host-Vorgabe | Host |

**Bewusst nicht gespeichert:** Name, E-Mail, Firma oder IP der Teilnehmer. Der
Download-Zähler ist anonym und lässt sich keiner Person zuordnen. Wer das ändern will
(«wer hat was geholt?»), braucht zuerst einen neuen Eintrag in `ENTSCHEIDE.md`: das macht
die Teilnehmer zu Betroffenen mit Hinweispflicht, Auskunftsrecht und Löschfrist.

## Dienste und Empfänger

Nur Dienste aus dem Register im Konzept (§6). Neue Dienste zuerst dort eintragen.

| Dienst | Was geht dorthin | Land | Garantie |
|---|---|---|---|
| Hetzner | alle Daten (Hosting) | DE/FI | angemessen |
| GitHub | Quellcode (public), keine Daten, keine Unterlagen | US | SCC |

## KI

Keine. Die App verarbeitet nichts mit einem Modell.

## Basis-Standard (Konzept §7)

| # | Baustein | Stand |
|---|---|---|
| B1 | diese Datei | ✓ |
| B2 | Datenschutzhinweis in der App | offen (mit E6) |
| B3 | keine CDNs/externen Fonts | offen (HTMX ins Repo, mit E3) |
| B4 | Uploads nur mit Rechteprüfung | offen (mit E6: Download nur über geprüften Endpunkt, kein StaticFiles auf dem Upload-Ordner) |
| B6 | 2FA Pflicht (ab D2) | nicht Pflicht (D1); umschaltbar über `ADMIN_2FA` |
| B8 | keine Personendaten in Logs | offen (mit E1: nie Zugangscode oder IP ins Log) |
| B9 | Löschfristen als Job | offen (nach E6) |
| B10 | Belege nicht hart löschbar | – (keine Belege; Unterlagen werden deaktiviert, nicht gelöscht) |
| B11 | Auskunftsexport je Person | – (keine Personendaten) |
| B12 | Backup verschlüsselt ausser Haus, Wiederherstellung geprüft | offen (mit E2) |
| B13 | Leseprotokoll (nur D3) | – |
| B14 | Gerätespeicher beim Abmelden leeren | – |
| B15 | Testdaten erfunden, keine Echtdaten auf Dev | offen (Tests nur mit erfundenen Kursen und Dateien) |
