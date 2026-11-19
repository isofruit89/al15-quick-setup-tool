# AL15 Quick-Setup-Tool

Lokales Web-Tool zur schnellen Inbetriebnahme des IO-Link-Masters **ifm AL159x** (ab Firmware 1.7).
Parametersätze werden offline erstellt, als Profil gespeichert und später mit Vorprüfung, Dry Run und
Zurücklesen auf das Gerät übertragen. Die Oberfläche gibt es auf Deutsch und Englisch.

> **Disclaimer**
> This software is not an official ifm product. The AL15 Quick-Setup Tool is provided for demonstration and
> evaluation purposes only. It has been developed as an internal/prototype tool to simplify configuration
> workflows and showcase possible approaches for device setup.
>
> This software is not released, supported, or maintained by ifm. It is not tested according to official
> product quality or security standards. The application is not digitally signed, which means your operating
> system or antivirus software may display a warning when starting it. Use of this tool is entirely at your own risk.

## Download und Start (Windows)

1. Auf der Seite [Releases](../../releases) das aktuelle `AL15-Quick-Setup-Tool-v<Version>.zip` herunterladen.
2. Entpacken, zum Beispiel nach `C:\Tools\`.
3. `start.bat` ausführen. Das Tool startet im Hintergrund und der Browser öffnet `http://127.0.0.1:5010`.

Keine Installation nötig. Zum Beenden `AL15-Quick-Setup-Tool.exe` im Task-Manager beenden.

## Funktionen

- **Parametersatz erstellen:** Device Tags, Netzwerk (DHCP/statisch), Portkonfiguration, NTP, Node-RED,
  Credentials, HTTP, OPC UA (inkl. Serverzertifikat), MQTT Client, MQTT Command Channel, IODDs,
  Node-RED-Flows und -Paletten.
- **„Keine Aktion“** pro Bereich und pro Parameter: Es wird nur gesendet, was ausdrücklich gesetzt ist.
- **Vorprüfung vor dem Übertragen:** Erreichbarkeit, Werkszustand (`/getidentity`, `passwordstatus`),
  Anmeldung, Produkt (AL159x), Firmware und Seriennummer. Im Werkszustand wird zuerst das Passwort gesetzt.
- **Zurücklesen vor dem Schreiben:** Das Tool liest die Ist-Werte und sendet nur echte Änderungen.
  Der Dry Run zeigt Ist und Soll je Request.
- **Profilverwaltung:** Profile laden, bearbeiten, kopieren, löschen.
- **Paletten-Packager:** Node-RED-Paletten offline für den AL15 paketieren (benötigt Node.js und npm).

Profile werden unverschlüsselt im Ordner `profiles` gespeichert. Passwörter und den OPC-UA-Private-Key
kann man beim Speichern über eine Option ausschließen.

## Aus dem Quellcode starten

Voraussetzung: Windows mit Python 3.12 oder neuer.

```
start_local.bat
```

Das Skript legt beim ersten Start eine virtuelle Umgebung `.venv` an, installiert die Pakete aus
`requirements.txt` und startet das Tool auf `http://127.0.0.1:5010`. Danach startet es auch ohne Internet.

## Tests

```
run_tests.bat
```

Die Unit-Tests laufen ohne Gerät und ohne Zusatzpakete. Details stehen in [tests/README.md](tests/README.md).

## EXE und Release bauen

```
build_release.bat
```

Das Skript installiert PyInstaller (`requirements-build.txt`), führt die Tests aus, baut die EXE mit `app.spec`
und erzeugt `dist\AL15-Quick-Setup-Tool-v<Version>.zip`. Dieses ZIP wird auf GitHub als Release-Asset
hochgeladen. Die Versionsnummer steht in `app.py` (`APP_VERSION`).

## Aufbau

| Datei / Ordner | Inhalt |
|---|---|
| `app.py` | Flask-App: Routen, Vorprüfung, Übertragung, Dry Run |
| `service_definitions.py` | Erzeugt die IoT-Core-Requests aus einem Profil |
| `profile_schema.py` | Profilschema v2 und Migration alter Profile |
| `readback.py` | Ist-/Soll-Vergleich vor dem Schreiben |
| `opcua_client.py` | Minimaler OPC-UA-Client zum Lesen des Serverzertifikats |
| `nodered.py` | Node-RED: Paletten installieren, Flows deployen |
| `palette_packager.py` | Offline-Paketierung von Node-RED-Paletten |
| `messages.py` | Texte und Fehlermeldungen (de/en) |
| `static/`, `templates/` | Oberfläche |
| `prebuilt_palettes/` | Vorgefertigte Palette `node-red-contrib-opcua` für den AL15 |
| `release/` | `readme.txt` und `start.bat` für das Release-ZIP |
| `tests/` | Unit-Tests |

Änderungen je Version stehen in [AENDERUNGEN.md](AENDERUNGEN.md).

## Lizenz

Apache License 2.0, siehe [LICENSE](LICENSE) und [NOTICE](NOTICE).
