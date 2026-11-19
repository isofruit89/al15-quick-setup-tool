# Änderungen am AL15 Quick-Setup-Tool

## Version 1.7 (2026-11-19)

Basis: Tool v1.6. Geprüft gegen die Gerätebeschreibung `al1590_description.yaml` (rc12) und den GetTree eines AL1590 mit Firmware 1.7.0.2.

## 1. Vorprüfung und Werkszustand

- Die Vorprüfung fragt das Gerät jetzt tatsächlich ab. Bisher wurde bei Passwort `password` gar nicht verbunden.
- Ablauf:
  1. `/getidentity` ohne Login abfragen (Erreichbarkeit, Timeout 5 s).
  2. Werkszustand über `security.passwordstatus` bestimmen (`must_change` = Werkszustand, `required` = Passwort gesetzt).
  3. Anmelden.
  4. Produkt (AL159x), Firmware (mindestens 1.7; Abweichung von 1.7.0.2 = Warnung) und Seriennummer prüfen.
- Im Werkszustand muss ein neues Passwort gesetzt werden, das nicht `password` sein darf. Produkt und Firmware prüft das Tool direkt nach dem Passwortwechsel.
- „Konfiguration übernehmen“ wird erst nach einer erfolgreichen Vorprüfung freigegeben. Jede Änderung an Host oder Zugangsdaten setzt die Freigabe zurück.
- Die Übertragung wiederholt die Vorprüfung serverseitig. Hat sich die Seriennummer seit der Vorprüfung geändert, bricht sie ab.

## 2. „Keine Aktion“ pro Klasse und Parameter

- Neues Profilschema v2 (`profile_schema.py`):
  - `apply: false` je Klasse bedeutet „Keine Aktion“ für den ganzen Abschnitt.
  - `null` je Parameter bedeutet „Keine Aktion“ für diesen Parameter.
- Oberfläche:
  - Klassen-Schalter „Konfigurieren | Keine Aktion“ in allen 13 Abschnitten.
  - Checkbox „Keine Aktion“ an Textfeldern.
  - Option „Keine Aktion“ in allen Auswahllisten, auch bei den Port-Pins.
  - Credentials und OPC UA Anonymous haben jetzt drei Zustände.
- Ein neues Profil erzeugt standardmäßig 0 Requests.
- Alte Profile (v1) werden beim Laden verlustfrei migriert und erzeugen dieselben Requests wie bisher.
- Behobene Fehler:
  - DHCP wurde mit `mode: 0` (= Disable) gesendet. Jetzt wird `mode: 2` mit `gateway_mode: 1` und `dns_mode: 3` gesendet: Ohne `gateway_mode` lehnt das Gerät mit 422 „Gateway mode 0 is not supported“ ab, obwohl der GetTree das Feld als optional führt. Statische Adressen werden mit `Address`/`Subnetmask` gesendet. Beides am Gerät verifiziert: static gesetzt, danach zurück auf DHCP.
  - QoS und Validate = 0 ließen sich nicht schreiben.
  - OPC UA startete nach geänderten Settings trotz gewählter Aktion „Stop“.
  - Der Dry Run ignorierte Quick Edit und die Paletten.
  - Die Überschriften „System Setting“ und „Connections“ blieben in der englischen Oberfläche deutsch.

## 3. Zurücklesen vor dem Schreiben

- Vor jeder Übertragung liest das Tool die Ist-Werte (`readback.py`) und sendet nur echte Abweichungen. Die Feedback-Tabelle zeigt pro Request Ist → Soll.
- Der Dry Run liest die Ist-Werte ebenfalls (nur lesend) und zeigt Status, Ist und Soll.
- Start/Stop wird übersprungen, wenn der Dienst schon im Zielzustand ist.
- OPC UA wird nur gestoppt und gestartet, wenn sich etwas ändert. Ein vorher gestoppter Server bleibt gestoppt, außer „Start“ ist gewählt.
- Node-RED-Paletten werden übersprungen, wenn Name und Version schon installiert sind. Flows werden übersprungen, wenn sie identisch sind.
- Immer gesendet werden: das MQTTCC-Passwort (kein Lesepfad), IODDs und Werte, die sich nicht lesen lassen.

## 4. OPC-UA-Zertifikat

- Im OPC-UA-Block lassen sich Zertifikat (`.der`/`.pem`/`.crt`) und Private Key (`.pfx`/`.p12` ohne Passwort) auswählen, mit eigenem „Keine Aktion“.
- Request `/connections/opcua_server/upload_certificate`: Datei-Bytes als Base64 mit CRC32. Das Format stammt aus der Web-UI des Geräts.
- Wurde der Server noch nie gestartet (Code 550, PKI-Ordner fehlt), startet und stoppt das Tool ihn einmal und lädt dann erneut hoch.
- Läuft der Server, prüft das Tool über OPC UA `GetEndpoints` (`opcua_client.py`), ob das Zertifikat schon aktiv ist, und überspringt den Upload dann.
- Private Key und MQTTCC-Passwort sind in Vorschau, Dry Run, Export und Feedback maskiert.

## 5. Sicherheit und Übersetzung (Review)

- Sicherheit:
  - Das Passwortfeld des MQTT Command Channel ist jetzt ein echtes Passwortfeld.
  - Das Gerätepasswort im Bereich „Parametersatz übertragen“ ist nicht mehr mit `password` vorbelegt. Bei leerem Feld meldet die Vorprüfung „Bitte das Gerätepasswort eingeben“. Im Werkszustand ist kein Passwort nötig.
  - Neue Option „Passwörter und Private Key nicht im Profil speichern“. Ist sie aktiv, werden MQTTCC-Passwort sowie OPC-UA-Zertifikat und Private Key nicht gespeichert und damit auch nicht übertragen. Ohne die Option zeigt das Speichern einen Hinweis, dass diese Daten unverschlüsselt im Profil liegen.
- Übersetzung:
  - Fehlermeldungen kommen aus einem zweisprachigen Katalog (`messages.py`) und erscheinen in der Sprache der Oberfläche. Das betrifft die Prüfungen für OPC UA, MQTT-Zertifikate, Netzwerk, Ports, IODD, Flows, Paletten und Paketierung. Bisher waren sie teils nur deutsch und teils nur englisch.
  - Diese Request-Bezeichnungen werden jetzt übersetzt: „Credentials ein/aus“, „OPC UA Zertifikat“ und „OPC UA Start (nach Settings)“.
  - Die Statuszeile wechselt beim Umschalten der Sprache in beide Richtungen mit.
  - „System Setting“ heißt jetzt „Systemeinstellungen“, „Value“ heißt „Wert“. Das Paletten-Log zeigt „Fehler“ statt „error“.
  - Der Status „Schreiben (ohne Vergleich)“ wird farbig markiert.
  - Ungenutzte Texte wurden entfernt.

## 6. Bedienung und Wartbarkeit (Review)

- Bedienung:
  - Profilnamen: Leerzeichen werden zu `_`, reservierte Windows-Namen (z. B. `CON`) bekommen ein `_` angehängt, maximal 80 Zeichen. Weicht der gespeicherte Name von der Eingabe ab, meldet das Speichern den angepassten Namen.
  - Kopieren überschreibt ein vorhandenes Profil nur nach Rückfrage.
  - Application Tag: Ein Hinweis erscheint, wenn der Wert kein gültiger Hostname ist (nur A–Z, a–z, 0–9 und Bindestrich, maximal 63 Zeichen). Gespeichert wird trotzdem.
  - Die Start/Stop-Schalter der Dienste haben die Überschrift „Dienst“.
  - Host/IP ist nicht mehr mit `https://ifm-al1590.local/` vorbelegt; dieser Name ist im Netz nicht auflösbar. Das Feld zeigt das richtige Format als Platzhalter. Nach einer erfolgreichen Vorprüfung wird der Host gespeichert und beim nächsten Start vorbelegt.
- Wartbarkeit:
  - Der Node-RED-Code aus `app.py` liegt jetzt in `nodered.py` (Paletten, Flows) und `palette_packager.py` (Offline-Paketierung); die dichten Einzeiler sind dabei lesbar formatiert. Die Texte des Backends liegen in `messages.py`. `app.py` ist von 1.492 auf rund 1.100 Zeilen geschrumpft.
  - Neuer Ordner `tests/` mit 25 Unit-Tests (ohne Gerät und ohne Zusatzpakete). Ausführen mit `run_tests.bat`.
  - `requirements.txt` gibt feste Versionen vor.
  - `start_local.bat` installiert Pakete nur beim ersten Start oder nach einer geänderten `requirements.txt`, ohne pip-Update. Danach startet das Tool auch offline. Der Browser öffnet sich erst, wenn der Server läuft.
  - Alle Python-Dateien haben einheitliche Zeilenenden (LF).

## Neue Dateien

| Datei | Zweck |
|---|---|
| `profile_schema.py` | Profilschema v2, Standardprofil, Migration alter Profile |
| `readback.py` | Ist-/Soll-Vergleich je Request |
| `opcua_client.py` | Minimaler OPC-UA-Client zum Lesen des Server-Zertifikats |
| `messages.py` | Zweisprachige Texte: Backend-Meldungen und Fehlermeldungen (de/en) |
| `nodered.py` | Node-RED: Paletten installieren, Flows deployen, jeweils mit Zurücklesen |
| `palette_packager.py` | Offline-Paketierung von Node-RED-Paletten |
| `tests/`, `run_tests.bat` | Unit-Tests (siehe `tests/README.md`) |
| `build_release.bat`, `requirements-build.txt`, `release/` | EXE-Build und Release-ZIP |
| `README.md`, `LICENSE`, `NOTICE` | Veröffentlichung auf GitHub unter Apache License 2.0 |

`served-app.js` war eine unbenutzte, veraltete Kopie von `static/app.js` und wurde entfernt.

## Release und EXE

- Die Versionsnummer steht in `app.py` (`APP_VERSION = "1.7"`) und erscheint im Kopf der Oberfläche.
- Die EXE heißt jetzt `AL15-Quick-Setup-Tool.exe` statt `app.exe`.
- `build_release.bat` baut sie mit PyInstaller 6.22.3, führt vorher die Tests aus und erzeugt `dist\AL15-Quick-Setup-Tool-v1.7.zip` mit `readme.txt`, `start.bat`, `LICENSE.txt` und `NOTICE.txt`.
- `start.bat` im Release wartet jetzt korrekt, bevor der Browser öffnet (bisher `timeout t 2 nul`).
- `readme.txt` nennt den richtigen EXE-Namen.
- Die Ordner `profiles`, `exports` und `palettes` sind im Release leer; das Tool legt sie beim ersten Start an.
