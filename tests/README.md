# Tests

Die Tests laufen ohne Gerät und ohne zusätzliche Pakete (nur `unittest` aus der Standardbibliothek).

```
run_tests.bat
```

oder direkt:

```
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

| Datei | Prüft |
|---|---|
| `test_readback.py` | Ist-/Soll-Vergleich, Netzwerk (DHCP mit `gateway_mode`), OPC-UA-Gruppe Stop/Settings/Start |
| `test_requests.py` | Profilschema v2, Migration alter v1-Profile, Netzwerk-Payloads, OPC-UA-Zertifikat, Maskierung |
| `test_backup.py` | Geräte-Backup: Umwandlung der Gerätewerte, Rundlauf Backup → Übertragung ohne Änderungen |
| `test_https_mqtt.py` | HTTP-/HTTPS-Server, MQTT-Erweiterungen, Zertifikatspaare (PEM), Code 230, Maskierung |
| `test_monitor.py` | Service Monitor: Requests, Gerätename, Zurücklesen, Entfernen, Maskierung, Backup |
| `test_factory_profile.py` | Werkseinstellungen als Editor-Vorbelegung, Abgleich mit dem Werks-Backup |
| `test_fieldbus_hostname.py` | Feldbus-Umschaltung PROFINET/EtherNet/IP und Hostname: Requests, Prüfregeln, Zurücklesen, Reihenfolge, Backup |
| `test_texts_and_profiles.py` | Übersetzungen de/en, Fehlerkatalog, UTF-8, Umlaute, Profilnamen, Kopierschutz |

`fixtures/opcua/` enthält ein selbst erzeugtes Testzertifikat („AL15 Quick-Setup Tool Unit Test“) mit Schlüssel.
Es wurde nur für die Tests erzeugt, ist auf keinem Gerät installiert und darf nicht produktiv verwendet werden.
`fixtures/https/` enthält selbst erzeugte Testzertifikate mit Extended Key Usage „TLS Server/Client“, einen
unverschlüsselten und einen verschlüsselten Key (Passwort `Test1234`). `server_cert.pem` wurde beim Gerätetest am
2026-11-20 auf das Testgerät (SN 000251100049) hochgeladen, lässt sich dort nicht löschen und wird seit dem Neustart als
HTTPS-Zertifikat ausgeliefert (gültig bis 2026-12-20). Am selben Tag durch ein Gerätezertifikat mit 10 Jahren Laufzeit ersetzt. Nicht produktiv verwenden.
`fixtures/migration_v1.json` enthält die erwarteten Requests alter v1-Profile. Sie wurden am 2026-11-19 gegen das alte Tool (v1.6 vor Phase 2) verglichen.
