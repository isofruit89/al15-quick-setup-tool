# Änderungen am AL15 Quick-Setup-Tool

## Version 1.8 (2026-11-20)

### Geräte-Backup

- Neue Kachel „Geräte-Backup“ auf der Startseite (englisch „Device backup“).
- Ablauf:
  1. Host/IP, Benutzer und Passwort eingeben.
  2. Vorprüfung durchführen.
  3. „Backup erstellen“.
- Das Tool liest alle Einstellungen, die ein Parametersatz enthalten kann. Dazu gehören:
  - Device Tags und Network
  - Portkonfiguration (Pin 4 für Port 1–8, Pin 2 für Port 1–4)
  - NTP, Node-RED, Credentials und HTTP
  - OPC UA (Port, Anonymous, Security Profiles)
  - MQTT Client und MQTT Command Channel
  - optional die Node-RED-Flows
- Den Zustand der Dienste (`running`/`stopped`) übernimmt das Tool als Aktion „Start“/„Stop“.
- Ergebnis:
  - ein normales Profil in `profiles/`, Name vorbelegt mit `backup_<Seriennummer>_<Datum_Uhrzeit>`
  - eine Rohdatei `backups/<Name>_raw.json` mit allen gelesenen Pfaden, Codes und Werten sowie Geräteidentität und Tool-Version
  - Beide lassen sich herunterladen, das Profil lässt sich direkt im Editor öffnen.
- Wiederherstellen: Das Backup-Profil unter „Parametersatz übertragen“ wählen. Durch das Zurücklesen werden nur abweichende Werte gesendet.
- Network wird gespeichert, steht im Profil aber auf „Keine Aktion“. So wird eine statische IP beim Einspielen auf ein anderes Gerät nicht doppelt vergeben.
- Nicht auslesbar, im Ergebnis als „Nicht gesichert“ markiert:
  - MQTTCC-Passwort
  - OPC-UA-Zertifikat mit Private Key
  - IODD-Dateien
  - Node-RED-Paletten (installierte Paletten werden mit Version aufgelistet)
- Im Werkszustand bricht das Backup mit einem Hinweis ab, weil ohne gesetztes Passwort nichts lesbar ist.
- Alle Lesepfade und Wertformate wurden am AL1590 (FW 1.7.0.2, 192.168.0.77) verifiziert.

### HTTP-/HTTPS-Server und MQTT

Alle Pfade und Formate wurden am 2026-11-20 am AL1590 (FW 1.7.0.2) geprüft.

- **HTTP-Server:** Den Port (`httpserver0/httpserver/port`) kann man jetzt setzen.
- **Neue Karte „HTTPS“** (`httpserver1`) mit diesen Einstellungen:
  - Port
  - Security Mode (0 = disabled, 1 = enabled)
  - Validate Client Certificate (0 = none, 1 = require)
  - Trusted Client Certificates
  - Serverzertifikat mit Private Key (PEM), optional mit Passwort für einen verschlüsselten Key
- **Format des Serverzertifikats:**
  - Request: `setdata` auf `securesetup/certificate_key_pem` mit `{"certificate": PEM, "key": PEM[, "password"]}`
  - Das Gerät verlangt im Zertifikat die Extended Key Usage „TLS Web Server Authentication“ (OID 1.3.6.1.5.5.7.3.1), sonst antwortet es mit 422. Das Tool prüft das schon vor dem Senden.
  - Beim Zurücklesen liefert das Gerät nur das Zertifikat, nie den Key. Ist das Zertifikat identisch, überspringt das Tool den Upload.
  - Ein hochgeladenes Zertifikat lässt sich am Gerät nicht löschen (Code 500), nur ersetzen.
  - Nach einem Neustart liefert das Gerät das hochgeladene Zertifikat aus, auch bei Security Mode 0 (geprüft am 2026-11-20). Die HTTPS-Karte weist darauf hin.
- **„Validate Client Certificate = require“:** Damit erreicht weder dieses Tool noch der Browser das Gerät über HTTPS. Die Oberfläche warnt davor, und HTTPS wird erst kurz vor Network übertragen.
- **Code 230** („übernommen, wirksam nach Neustart“):
  - zählt jetzt bei allen Requests als Erfolg
  - wird als „OK (Neustart nötig)“ angezeigt
  - Die Abschlussmeldung weist auf den nötigen Neustart hin.
- **MQTT Client:** neu sind Version (V3.1.0/V3.1.1/V5.0.0), Keep Alive, Will Topic, Will Message, Retain und das Client-Zertifikat (PEM).
- **MQTT Command Channel:** neu sind Version, Keep Alive, Will Topic, Will Message und das Client-Zertifikat (PEM).
- **Geräte-Backup:**
  - Es liest alle neuen Werte.
  - Installierte Zertifikate meldet es als „Nicht gesichert“, weil der Key nicht lesbar ist.
- **„Passwörter und Private Key nicht im Profil speichern“** gilt jetzt auch für die neuen Zertifikate.
- **Behobener Fehler:** Bei der Aktion „Keine Aktion“ hat das Tool den HTTP-Port verworfen. Gefunden beim Live-Test.
- **Neue Tests:** `tests/test_https_mqtt.py`. Die Testzertifikate liegen in `tests/fixtures/https/`.

### Service Monitor

Am 2026-11-20 am AL1590 geprüft.

- **Neuer Abschnitt „Service Monitor“** im Editor mit einer Liste von Einträgen. Je Eintrag gibt es:
  - ID (leer = vergibt das Gerät)
  - Beschreibung
  - Datenpunkte
  - Sample- und Notify-Intervall
  - „Nur bei Änderung senden“
  - „Nach Neustart erhalten“
  - eine optionale Sample-Bedingung
  - den Empfänger: mqtt/mqtts, Broker, Port, Topic, Benutzer, Passwort
- **Datenpunkte stehen im Profil ohne Gerätenamen** (`/devicestatus/...`). Beim Übertragen setzt das Tool den Namen des Zielgeräts davor, so wie die Web-UI die Einträge anlegt. Damit lässt sich ein Profil auf andere Geräte übertragen.
- **Übertragung:**
  - `/monitor/add` mit ID ersetzt einen vorhandenen Eintrag.
  - Das Zurücklesen über `/monitor/getitems` überspringt identische Einträge.
  - Einträge ohne ID gleicht das Tool über den Inhalt ab, damit wiederholte Übertragungen keine Duplikate erzeugen.
- **Optionales Entfernen:** „Einträge am Gerät entfernen, die nicht im Profil stehen“ (standardmäßig aus) löscht per `/monitor/remove` nur Einträge, die weder per ID noch per Inhalt im Profil stehen.
- **Kein Start/Stop:** Den Monitor selbst startet oder stoppt das Tool bewusst nicht.
- **Geräte-Backup:**
  - Es übernimmt alle Monitor-Einträge.
  - Zugangsdaten im Empfänger liefert das Gerät im Klartext. Sie stehen damit unverschlüsselt im Backup-Profil, und die Ergebnistabelle weist darauf hin.
- **Datenschutz:**
  - Passwörter der Empfänger sind in Vorschau, Dry Run und Feedback maskiert.
  - Die Option „Passwörter … nicht im Profil speichern“ entfernt sie beim Speichern.
- **Beschreibung:** Die description liefert das Gerät nur bei Einträgen mit „Nach Neustart erhalten“ zurück. Fehlt sie beim Zurücklesen, ignoriert das Tool sie beim Vergleich.
- **Neue Tests:** `tests/test_monitor.py`.

### Editor: Werkseinstellungen statt „Keine Aktion“ pro Feld

- Die Schalter „Keine Aktion“ an einzelnen Feldern sind entfallen. „Keine Aktion“ gibt es nur noch pro Bereich.
- Innerhalb eines Bereichs gilt: Ein leeres Feld oder ein Zertifikatsbereich ohne Datei wird nicht geschrieben.
- Ein neuer Parametersatz ist mit den Werkseinstellungen vorbelegt (`FACTORY_PROFILE` in `profile_schema.py`). Ausgelesen am 2026-11-20 an einem AL1590 mit FW 1.7.0.2 direkt nach dem Werksreset. Ein Dry Run gegen dieses Gerät ergab 0 Änderungen und 34 unveränderte Werte.
- Auswahllisten (Ports, Version, QoS, Security usw.) haben keine Option „Keine Aktion“ mehr. Ausnahme: der Netzwerk-Modus.
- Bewusst nicht vorbelegt:
  - Gerätespezifische Texte wie Tags, Client-ID, Broker-IP, Benutzer und Will-Topic.
  - Start/Stop-Aktionen. Sie bleiben auf „Keine Aktion“, damit laufende Dienste nicht ungewollt gestoppt werden.
  - Der Netzwerk-Modus.
- Ein vorhandenes Will-Topic am Gerät lässt sich über ein leeres Feld nicht mehr löschen.
- Gespeicherte Profile laden unverändert. `null` bedeutet weiterhin „nicht schreiben“, fehlende Felder werden nicht mit Werkswerten ergänzt.
- Das Werks-Backup liegt als Profil `profiles/werkszustand_AL1590_fw1702.json` bei.
- **Neue Tests:** `tests/test_factory_profile.py`.

### Feldbus-Umschaltung und Hostname

- **Feldbus** ist ein neuer Bereich: Umschaltung zwischen PROFINET und EtherNet/IP über `/devicesettings/fieldbustype/<Typ>/enable`.
  - Den aktuellen Typ liest das Tool vorher aus `/devicesettings/fieldbustype/status` (0 = PROFINET, 2 = EtherNet/IP). Ist er schon aktiv, wird nichts gesendet.
  - Am Gerät dauert der Wechsel etwa 60 Sekunden. Der Aufruf blockiert so lange; das Tool wartet dafür bis zu 180 Sekunden. Ein Neustart ist nicht nötig.
  - Werkswert ist EtherNet/IP. Bei einem neuen Parametersatz steht der Bereich trotzdem auf „Keine Aktion“, damit ein vergessener Bereich eine PROFINET-Anlage nicht umschaltet.
  - Das Geräte-Backup sichert den Feldbus-Typ mit.
- **Hostname** (`/network/br0/hostname`) ist ein eigener Bereich vor Network. Ein leeres Feld lässt den Namen am Gerät unverändert.
  - Prüfregeln, live am Gerät ermittelt:
    - höchstens 63 Zeichen aus Buchstaben, Ziffern, Bindestrich und Punkt
    - Beginn mit einem Buchstaben
    - kein Bindestrich am Ende eines Abschnitts, kein Punkt am Ende
  - Der Gerätename in `/getidentity` ändert sich dabei nicht, die Service-Monitor-Datenpunkte bleiben also gültig.
  - Die .local-Adresse übernimmt den neuen Namen nicht sofort.
  - Im Geräte-Backup steht der Hostname wie Network auf „Keine Aktion“, damit ein zweites Gerät nicht denselben Namen bekommt.
- **Live geprüft** am AL1590:
  - Umschaltung auf PROFINET und zurück auf EtherNet/IP über das Tool: je ca. 65 s, Code 200, der Dry Run danach zeigt 0 Änderungen.
  - Hostname geändert und wieder zurückgesetzt.
- **Neue Tests:** `tests/test_fieldbus_hostname.py`.

### Vorprüfung

- Firmware 1.8.0.1 gilt als verifiziert und erzeugt keine Warnung mehr (`REFERENCE_FIRMWARE` in `app.py` enthält jetzt 1.7.0.2 und 1.8.0.1). Am 2026-11-27 rein lesend am AL1590 geprüft: Alle Lesepfade antworten mit 200, der Backup-Rundlauf ergibt 0 Änderungen, und alle Schreibpfade des Tools stehen im GetTree. Schreiben unter 1.8.0.1 ist noch nicht live getestet.
- Meldet das Gerät `passwordstatus = not_required` (Anmeldung deaktiviert), ist kein Passwort nötig. Das gilt für Backup und Übertragung.

### Wartbarkeit

- Speichern, Kopieren und Backup nutzen die gemeinsame Funktion `write_profile()` in `app.py`.
- Neue Datei `backup.py`, neue Tests `tests/test_backup.py`. Dazu gehört ein Rundlauf-Test: Ein Backup, das gegen dasselbe Gerät eingespielt wird, ergibt 0 Änderungen.

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
