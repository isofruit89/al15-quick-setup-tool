"""Zweisprachige Texte (de/en): Meldungen des Backends und Fehlermeldungen.

Validierungen werfen LocalizedError(key, **params). str(exc) liefert Deutsch; die
Flask-Endpunkte übersetzen mit error_text(exc, lang) in die Sprache der Oberfläche.
"""

ERRORS = {
    # service_definitions.py
    "required_fields": ("{context}: Pflichtfelder fehlen: {fields}",
                        "{context}: required fields missing: {fields}"),
    "network_mode": ("Network: Modus muss 'dhcp' oder 'static' sein.",
                     "Network: mode must be 'dhcp' or 'static'."),
    "http_action": ("HTTP: Aktion muss 'none', 'start' oder 'stop' sein.",
                    "HTTP: action must be 'none', 'start' or 'stop'."),
    "opcua_cert_no_pem": ('OPC UA Zertifikat: kein PEM-Block "BEGIN CERTIFICATE" gefunden.',
                          'OPC UA certificate: no PEM block "BEGIN CERTIFICATE" found.'),
    "opcua_cert_invalid": ("OPC UA Zertifikat: keine gültige DER-/PEM-Zertifikatsdatei.",
                           "OPC UA certificate: not a valid DER/PEM certificate file."),
    "opcua_cert_entry": ("OPC UA Zertifikat: ungültiger Profileintrag.",
                         "OPC UA certificate: invalid profile entry."),
    "opcua_cert_cert_missing": ("OPC UA Zertifikat fehlt. Zertifikat (.der/.pem) und Private Key (.pfx) werden gemeinsam benötigt.",
                                "OPC UA certificate is missing. Certificate (.der/.pem) and private key (.pfx) are required together."),
    "opcua_cert_key_missing": ("OPC UA Private Key fehlt. Zertifikat (.der/.pem) und Private Key (.pfx) werden gemeinsam benötigt.",
                               "OPC UA private key is missing. Certificate (.der/.pem) and private key (.pfx) are required together."),
    "opcua_cert_cert_base64": ("OPC UA Zertifikat: ungültige Base64-Daten.", "OPC UA certificate: invalid Base64 data."),
    "opcua_cert_key_base64": ("OPC UA Private Key: ungültige Base64-Daten.", "OPC UA private key: invalid Base64 data."),
    "opcua_cert_cert_size": ("OPC UA Zertifikat: Datei ist größer als 64 KB.", "OPC UA certificate: file exceeds 64 KB."),
    "opcua_cert_key_size": ("OPC UA Private Key: Datei ist größer als 64 KB.", "OPC UA private key: file exceeds 64 KB."),
    "opcua_key_format": ("OPC UA Private Key: bitte eine PKCS#12-Datei (.pfx) ohne Passwort verwenden.",
                         "OPC UA private key: please use a PKCS#12 file (.pfx) without password."),
    "opcua_port": ("OPC UA Port muss zwischen 1 und 65535 liegen.", "OPC UA port must be between 1 and 65535."),
    "opcua_profiles_list": ("OPC UA Security Profiles müssen eine Liste sein.", "OPC UA security profiles must be a list."),
    "opcua_anonymous": ("OPC UA Anonymous ist nur zulässig, wenn Security Profile 'None' aktiviert ist.",
                        "OPC UA anonymous access is only allowed if security profile 'None' is enabled."),
    "mqtt_certs_strings": ("MQTT Trusted Server Certificates müssen Strings im PEM-Format sein.",
                           "MQTT trusted server certificates must be strings in PEM format."),
    "mqtt_certs_format": ("MQTT Trusted Server Certificates müssen im PEM-Format angegeben werden. Unterstützt werden echte Zeilenumbrüche sowie aus JSON kopierte \\n-Sequenzen.",
                          "MQTT trusted server certificates must be given in PEM format. Real line breaks and \\n sequences copied from JSON are supported."),
    "mqtt_certs_pem": ("MQTT Trusted Server Certificates müssen im PEM-Format angegeben werden.",
                       "MQTT trusted server certificates must be given in PEM format."),
    "cert_begin": ("Ungültiger Zertifikatsanfang.", "Invalid certificate start."),
    "cert_end": ("Ungültiges Zertifikatsende.", "Invalid certificate end."),
    "ports_list": ("Portkonfiguration: Ports müssen eine Liste sein.", "Port configuration: ports must be a list."),
    "port_pin4": ("Port {port}: Pin 4 muss 0, 1, 2 oder 3 sein.", "Port {port}: Pin 4 must be 0, 1, 2 or 3."),
    "port_pin2": ("Port {port}: Pin 2 muss 0, 1 oder 2 sein.", "Port {port}: Pin 2 must be 0, 1 or 2."),
    # app.py: IODD
    "iodd_list": ("IODD-Dateien müssen eine Liste sein.", "IODD files must be a list."),
    "iodd_entry": ("Ungültiger IODD-Eintrag.", "Invalid IODD entry."),
    "iodd_missing": ("IODD-Dateiname oder Inhalt fehlt.", "IODD filename or content is missing."),
    "iodd_type": ("Nicht unterstützte IODD-Datei: {name}. Es werden nur ZIP-Archive angenommen.",
                  "Unsupported IODD file: {name}. Only ZIP archives are accepted."),
    "iodd_size": ("IODD-Datei ist zu groß: {name}.", "IODD file is too large: {name}."),
    "base64_invalid": ("Ungültiger Base64-Inhalt in {name}.", "Invalid Base64 content for {name}."),
    # app.py: Node-RED Paletten
    "palette_list": ("Node-RED-Palettendateien müssen eine Liste sein.", "Node-RED palette files must be a list."),
    "palette_entry": ("Ungültiger Node-RED-Paletteneintrag.", "Invalid Node-RED palette entry."),
    "palette_file": ("Ungültige Node-RED-Palettendatei: {name}.", "Invalid Node-RED palette file: {name}."),
    "palette_size": ("Node-RED-Palettendatei ist zu groß: {name}.", "Node-RED palette file is too large: {name}."),
    # app.py: Node-RED Flows
    "flow_structure": ("Node-RED Flow {name}: erwartet wird ein JSON-Array oder ein v2-Objekt mit einem flows-Array.",
                       "Node-RED Flow {name}: expected a JSON array or a v2 object with a flows array."),
    "flow_nodes": ("Node-RED Flow {name}: jeder Knoten muss ein JSON-Objekt sein.",
                   "Node-RED Flow {name}: every node must be a JSON object."),
    "flow_list": ("Node-RED-Flow-Dateien müssen eine Liste sein.", "Node-RED flow files must be a list."),
    "flow_entry": ("Ungültiger Node-RED-Flow-Eintrag.", "Invalid Node-RED flow entry."),
    "flow_type": ("Nicht unterstützte Node-RED-Flow-Datei: {name}. Es wird nur JSON angenommen.",
                  "Unsupported Node-RED flow file: {name}. Only JSON is accepted."),
    "flow_size": ("Node-RED-Flow-Datei ist zu groß: {name}.", "Node-RED flow file is too large: {name}."),
    "flow_duplicate_id": ("Doppelte Node-RED-Knoten-ID '{node_id}' in den ausgewählten Flow-Dateien.",
                          "Duplicate Node-RED node id '{node_id}' in selected flow files."),
    "flow_host": ("Ungültiger AL15-Host für den Node-RED-Flow-Import.", "Invalid AL15 host for Node-RED flow import."),
    "nodered_no_token": ("Die Node-RED-Anmeldung hat kein Access Token geliefert.",
                         "Node-RED authentication did not return an access token."),
    # app.py: Verbindung
    "host_missing": ("Host / IP fehlt.", "Host / IP is missing."),
    # app.py: vorgefertigte Paletten und Paketierung
    "prebuilt_index": ("Ungültiger Index der vorgefertigten Paletten.", "Invalid prebuilt palette index."),
    "prebuilt_missing": ("Vorgefertigtes Artefakt fehlt: {path}", "Prebuilt artifact is missing: {path}"),
    "prebuilt_manifest_missing": ("Manifest des vorgefertigten Artefakts fehlt: {path}", "Prebuilt manifest is missing: {path}"),
    "prebuilt_sha_invalid": ("Ungültiger SHA-256 im Index für {name}.", "Invalid SHA-256 in prebuilt index for {name}."),
    "prebuilt_sha_mismatch": ("SHA-256 stimmt nicht für {name}: erwartet {expected}, erhalten {actual}",
                              "SHA-256 mismatch for {name}: expected {expected}, got {actual}"),
    "prebuilt_manifest_sha": ("SHA-256 des Manifests stimmt nicht für {name}.", "Manifest SHA-256 mismatch for {name}."),
    "prebuilt_not_released": ("Vorgefertigtes Artefakt ist nicht freigegeben: {name}", "Prebuilt artifact is not released: {name}"),
    "pack_runtime_failed": ("Runtime-Test fehlgeschlagen: {detail}", "Runtime test failed: {detail}"),
    "pack_dependency_ambiguous": ("Keine eindeutige reparierbare Abhängigkeit für {name}: {count} Kandidat(en), Versionen {versions}",
                                  "No unique repairable dependency for {name}: {count} candidate(s), versions {versions}"),
    "pack_dependency_unloadable": ("{name} ist am Ziel vorhanden, aber weiterhin nicht ladbar.",
                                   "{name} exists at the target but still cannot be loaded."),
    "pack_hoisting_limit": ("Maximale Anzahl automatischer Hoisting-Schritte erreicht.",
                            "Maximum number of automatic hoisting steps reached."),
    "pack_unsafe_path": ("Unsicherer Pfad im erzeugten Archiv.", "Unsafe path in generated archive."),
    "pack_tgz_runtime_failed": ("TGZ-Runtime-Test fehlgeschlagen: {detail}", "TGZ runtime test failed: {detail}"),
    "pack_tgz_incomplete": ("TGZ enthält nicht alle geprüften Top-Level-Abhängigkeiten: {names}",
                            "TGZ does not contain all checked top-level dependencies: {names}"),
    "pack_installed_missing": ("Installiertes Palettenpaket wurde nicht gefunden.", "The installed palette package was not found."),
}


class LocalizedError(ValueError, RuntimeError):
    """Fehler mit Übersetzungsschlüssel. str() liefert die deutsche Meldung."""

    def __init__(self, key, **params):
        self.key, self.params = key, params
        super().__init__(self.text("de"))

    def text(self, lang="de"):
        de, en = ERRORS[self.key]
        return (en if lang == "en" else de).format(**self.params)


def error_text(exc, lang="de"):
    """Meldung einer Exception in der gewünschten Sprache."""
    if isinstance(exc, LocalizedError):
        return exc.text(lang)
    cause = exc.__cause__ or exc.__context__
    if isinstance(cause, LocalizedError) and str(exc) == str(cause):
        return cause.text(lang)
    return str(exc)


# ---------------------------------------------------------------------------
# Status- und Ablaufmeldungen des Backends
# ---------------------------------------------------------------------------
BACKEND_I18N = {
    "de": {
        "profile_not_found": "Profil nicht gefunden.",
        "auth_failed": "Authentifizierung fehlgeschlagen – Benutzer oder Passwort falsch.",
        "new_password_mismatch": "Neues Passwort und Bestätigung stimmen nicht überein.",
        "dryrun_password_change_label": "Passwort ändern",
        "stream_started": "Konfiguration gestartet...",
        "factory_apply_need_new_password": "Für Geräte im Werkszustand muss zuerst ein neues Passwort gesetzt und bestätigt werden.",
        "password_change_path": "Passwort ändern → /security/password/setdata",
        "factory_password_change_failed": "Passwortwechsel im Werkszustand fehlgeschlagen. Response: {response}",
        "password_change_failed": "Passwortwechsel fehlgeschlagen. Response: {response}",
        "request_running": "Request {index}/{total}: {label}",
        "config_done": "Konfiguration abgeschlossen.",
        "config_done_with_error": "Konfiguration abgeschlossen, aber mindestens ein Request meldet Fehler.",
        "config_done_with_warning": "Konfiguration abgeschlossen. Mindestens eine Node-RED Palette konnte nicht installiert werden.",
        "status_ok": "OK", "status_error": "Fehler", "status_warning": "Warnung", "masked": "*** masked ***",
        "iodd_upload_running": "IODD {index}/{total} wird übertragen: {filename}",
        "iodd_upload_failed": "IODD-Übertragung fehlgeschlagen: {filename}. Antwort: {response}",
        "flow_upload_running": "Node-RED Flow wird übertragen: {files}",
        "flow_upload_failed": "Node-RED Flow-Übertragung fehlgeschlagen. Antwort: {response}",
          "palette_upload_running": "Node-RED Palette {index}/{total} wird übertragen: {filename}",
          "palette_upload_warning": "Node-RED Palette {filename} konnte nicht installiert werden. Das Deployment wird fortgesetzt.",
        "pc_reachable": "Erreichbarkeit", "pc_factory": "Werkszustand", "pc_auth": "Anmeldung", "pc_product": "Produkt",
        "pc_firmware": "Firmware", "pc_serial": "Seriennummer", "pc_password": "Neues Passwort", "pc_device": "Geräteidentität",
        "pc_prefix": "Vorprüfung",
        "precheck_reachable": "Gerät erreichbar: {name}",
        "precheck_unreachable": "Gerät unter {host} nicht erreichbar. Bitte prüfen: Kabel an XI1/XI2, PC-Netzwerkadapter auf DHCP bzw. im gleichen Subnetz; bei 169.254.x.x nur einen Link-Local-Adapter aktiv lassen (WLAN, Bluetooth, virtuelle Adapter deaktivieren).",
        "precheck_unexpected": "Unerwartete Antwort von /getidentity: {response}",
        "precheck_wrong_product": "Gerät {name} ist kein AL159x. Übertragung gesperrt.",
        "precheck_factory": "Werkszustand erkannt (passwordstatus = must_change). Beim Übertragen wird zuerst das neue Passwort gesetzt; Produkt und Firmware werden danach geprüft.",
        "precheck_not_factory": "Kein Werkszustand (passwordstatus = {status}).",
        "precheck_factory_unknown": "Werkszustand nicht eindeutig bestimmbar: Das Gerät meldet keinen passwordstatus.",
        "precheck_factory_password_ignored": "Im Werkszustand wird mit dem Werkspasswort angemeldet; das eingegebene Passwort wird dafür nicht verwendet.",
        "precheck_new_password_is_factory": "Das neue Passwort darf nicht dem Werkspasswort entsprechen.",
        "precheck_new_password_ok": "Neues Passwort eingegeben und bestätigt.",
        "precheck_auth_ok": "Anmeldung als {user} erfolgreich.",
        "precheck_auth_ambiguous": "Anmeldung mit dem Werkspasswort abgelehnt (401): Werkszustand oder falsches Passwort. Wenn das Gerät im Werkszustand ist, neues Passwort eingeben und erneut prüfen.",
        "precheck_auth_failed": "Anmeldung als {user} abgelehnt (401): Benutzer oder Passwort falsch.",
        "precheck_password_missing": "Bitte das Gerätepasswort eingeben.",
        "precheck_auth_unexpected": "Unerwartete Antwort bei der Anmeldung: {response}",
        "precheck_firmware_too_old": "Firmware {value} wird nicht unterstützt (mindestens {minimum}). Übertragung gesperrt.",
        "precheck_firmware_unverified": "Firmware {value} weicht von der Referenz {ref} ab und ist nicht verifiziert.",
        "precheck_serial_mismatch": "Seriennummer aus /getidentity ({a}) passt nicht zu /deviceinfo/serialnumber ({b}).",
        "precheck_identity_read_failed": "{item} konnte nicht gelesen werden: {response}",
        "precheck_ok": "Vorprüfung erfolgreich: {name}, {product}, Firmware {firmware}.",
        "precheck_ok_factory": "Vorprüfung erfolgreich: {name} im Werkszustand. Beim Übertragen wird zuerst das Passwort geändert.",
        "precheck_failed": "Vorprüfung fehlgeschlagen.",
        "precheck_device_changed": "Das Gerät hat sich seit der Vorprüfung geändert (erwartet SN {expected}, gefunden {found}). Bitte Vorprüfung wiederholen.",
        "status_info": "Info",
        "status_unchanged": "Unverändert", "status_change": "Ändern", "status_unverified": "Schreiben (ohne Vergleich)", "status_planned": "Geplant",
        "rb_no_read_path": "kein Lesepfad am Gerät", "rb_read_failed": "Ist-Wert nicht lesbar (Code {code})",
        "rb_unknown_state": "Zustand unbekannt", "rb_keep_stopped": "OPC UA war gestoppt und bleibt gestoppt",
        "rb_already_stopped": "bereits gestoppt", "rb_settings_unchanged": "OPC UA (Settings/Zertifikat) unverändert",
        "rb_conditional": "Stop nur, falls der Server läuft",
        "rb_opcua_cert_not_running": "OPC-UA-Server gestoppt: aktives Zertifikat nicht vergleichbar",
        "rb_opcua_cert_not_readable": "aktives OPC-UA-Zertifikat nicht lesbar",
        "readback_running": "Ist-Werte werden vom Gerät gelesen...",
        "readback_summary": "Ist-Werte gelesen: {change} ändern, {skip} unverändert, {unverified} ohne Vergleich.",
        "dryrun_with_device": "Dry Run mit Ist-Werten von {name}: {change} ändern, {skip} unverändert, {unverified} ohne Vergleich.",
        "dryrun_offline": "Dry Run ohne Ist-Werte: {reason}",
        "dryrun_factory": "Gerät im Werkszustand – Ist-Werte sind erst nach dem Passwortwechsel lesbar. Alle Requests werden gesendet.",
        "palette_already_installed": "Palette {package} {version} ist bereits installiert.",
        "flow_unchanged": "Node-RED Flows sind bereits identisch auf dem Gerät.",
    },
    "en": {
        "profile_not_found": "Profile not found.",
        "auth_failed": "Authentication failed – user or password is incorrect.",
        "new_password_mismatch": "New password and confirmation do not match.",
        "dryrun_password_change_label": "Change password",
        "stream_started": "Configuration started...",
        "factory_apply_need_new_password": "For devices in factory state, a new password must be set and confirmed first.",
        "password_change_path": "Change password → /security/password/setdata",
        "factory_password_change_failed": "Password change in factory state failed. Response: {response}",
        "password_change_failed": "Password change failed. Response: {response}",
        "request_running": "Request {index}/{total}: {label}",
        "config_done": "Configuration completed.",
        "config_done_with_error": "Configuration completed, but at least one request returned an error.",
        "config_done_with_warning": "Configuration completed. At least one Node-RED palette could not be installed.",
        "status_ok": "OK", "status_error": "Error", "status_warning": "Warning", "masked": "*** masked ***",
        "iodd_upload_running": "Uploading IODD {index}/{total}: {filename}",
        "iodd_upload_failed": "IODD upload failed: {filename}. Response: {response}",
        "flow_upload_running": "Uploading Node-RED flow: {files}",
        "flow_upload_failed": "Node-RED flow upload failed. Response: {response}",
          "palette_upload_running": "Uploading Node-RED palette {index}/{total}: {filename}",
          "palette_upload_warning": "Node-RED palette {filename} could not be installed. Deployment will continue.",
        "pc_reachable": "Reachability", "pc_factory": "Factory state", "pc_auth": "Login", "pc_product": "Product",
        "pc_firmware": "Firmware", "pc_serial": "Serial number", "pc_password": "New password", "pc_device": "Device identity",
        "pc_prefix": "Pre-check",
        "precheck_reachable": "Device reachable: {name}",
        "precheck_unreachable": "Device not reachable at {host}. Check: cable on XI1/XI2, PC network adapter set to DHCP or in the same subnet; with 169.254.x.x keep only one link-local adapter active (disable WLAN, Bluetooth, virtual adapters).",
        "precheck_unexpected": "Unexpected response from /getidentity: {response}",
        "precheck_wrong_product": "Device {name} is not an AL159x. Transfer blocked.",
        "precheck_factory": "Factory state detected (passwordstatus = must_change). The new password is set first during transfer; product and firmware are checked afterwards.",
        "precheck_not_factory": "Not in factory state (passwordstatus = {status}).",
        "precheck_factory_unknown": "Factory state cannot be determined: the device reports no passwordstatus.",
        "precheck_factory_password_ignored": "In factory state the factory password is used for login; the entered password is not used for that.",
        "precheck_new_password_is_factory": "The new password must not equal the factory password.",
        "precheck_new_password_ok": "New password entered and confirmed.",
        "precheck_auth_ok": "Login as {user} successful.",
        "precheck_auth_ambiguous": "Login with the factory password rejected (401): factory state or wrong password. If the device is in factory state, enter a new password and check again.",
        "precheck_auth_failed": "Login as {user} rejected (401): user or password is incorrect.",
        "precheck_password_missing": "Please enter the device password.",
        "precheck_auth_unexpected": "Unexpected response during login: {response}",
        "precheck_firmware_too_old": "Firmware {value} is not supported (minimum {minimum}). Transfer blocked.",
        "precheck_firmware_unverified": "Firmware {value} differs from reference {ref} and is not verified.",
        "precheck_serial_mismatch": "Serial number from /getidentity ({a}) does not match /deviceinfo/serialnumber ({b}).",
        "precheck_identity_read_failed": "{item} could not be read: {response}",
        "precheck_ok": "Pre-check successful: {name}, {product}, firmware {firmware}.",
        "precheck_ok_factory": "Pre-check successful: {name} in factory state. The password is changed first during transfer.",
        "precheck_failed": "Pre-check failed.",
        "precheck_device_changed": "The device changed since the pre-check (expected SN {expected}, found {found}). Please repeat the pre-check.",
        "status_info": "Info",
        "status_unchanged": "Unchanged", "status_change": "Change", "status_unverified": "Write (no comparison)", "status_planned": "Planned",
        "rb_no_read_path": "no read path on the device", "rb_read_failed": "current value not readable (code {code})",
        "rb_unknown_state": "state unknown", "rb_keep_stopped": "OPC UA was stopped and stays stopped",
        "rb_already_stopped": "already stopped", "rb_settings_unchanged": "OPC UA (settings/certificate) unchanged",
        "rb_conditional": "stop only if the server is running",
        "rb_opcua_cert_not_running": "OPC UA server stopped: active certificate cannot be compared",
        "rb_opcua_cert_not_readable": "active OPC UA certificate not readable",
        "readback_running": "Reading current values from the device...",
        "readback_summary": "Current values read: {change} to change, {skip} unchanged, {unverified} without comparison.",
        "dryrun_with_device": "Dry run with current values of {name}: {change} to change, {skip} unchanged, {unverified} without comparison.",
        "dryrun_offline": "Dry run without current values: {reason}",
        "dryrun_factory": "Device in factory state – current values can only be read after the password change. All requests will be sent.",
        "palette_already_installed": "Palette {package} {version} is already installed.",
        "flow_unchanged": "Node-RED flows are already identical on the device.",
    },
}

BACKEND_I18N["de"]["profile_exists"] = "Ein Profil mit dem Namen {name} existiert bereits."
BACKEND_I18N["en"]["profile_exists"] = "A profile named {name} already exists."


def msg(key, lang="de", **kwargs):
    text = BACKEND_I18N.get(lang, BACKEND_I18N["de"]).get(key, BACKEND_I18N["de"].get(key, key))
    return text.format(**kwargs) if kwargs else text
