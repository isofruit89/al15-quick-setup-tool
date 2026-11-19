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
| `test_texts_and_profiles.py` | Übersetzungen de/en, Fehlerkatalog, UTF-8, Umlaute, Profilnamen, Kopierschutz |

`fixtures/opcua/` enthält ein selbst erzeugtes Testzertifikat („AL15 Quick-Setup Tool Unit Test“) mit Schlüssel.
Es wurde nur für die Tests erzeugt, ist auf keinem Gerät installiert und darf nicht produktiv verwendet werden.
`fixtures/migration_v1.json` enthält die erwarteten Requests alter v1-Profile. Sie wurden am 2026-11-19 gegen das alte Tool (v1.6 vor Phase 2) verglichen.
