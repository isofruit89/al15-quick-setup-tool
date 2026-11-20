"""Geräte-Backup: liest alle Einstellungen, die ein Parametersatz enthalten kann, vom AL159x
und baut daraus ein Profil im Schema v2.

Das Backup-Profil lässt sich über "Parametersatz übertragen" wieder einspielen. Das Zurücklesen
(readback.py) überspringt dabei alle Werte, die schon stimmen.

Lesepfade und Wertformate am 2026-11-20 am AL1590 (FW 1.7.0.2) verifiziert:
  mode 1 = static, 2 = dhcp, 0 = disable; Gateway ohne Wert "" oder "0.0.0.0";
  leere Texte -> null; allowed_services 0 = HTTP an, 1 = aus; Status "running"/"stopped";
  port[5..8]/powercontrol/mode_ua existiert nicht (404).

Nicht lesbar und deshalb nicht im Backup: MQTTCC-Passwort, OPC-UA-Private-Key,
IODD-Dateien und Node-RED-Paletten (nur Name und Version lesbar).
"""
import copy
import re

from profile_schema import DEFAULT_PROFILE, SCHEMA_VERSION
from service_definitions import FIELDBUS_TYPE_STATUS, FIELDBUS_TYPES, HOSTNAME_ADR
from service_definitions import MONITOR_GETITEMS, mask_recipient, parse_monitor_recipient, relative_data_point

MQTT = "/connections/mqttclient/mqttsetup"
MQTTCC = "/connections/mqttcommandchannel/mqttcmdchannel/mqttcmdchannelsetup"
OPCUA = "/connections/opcua_server"
IPV4 = "/network/br0/ipv4"
HTTPS = "/connections/httpserver1/httpserver"
PEM_BLOCK = re.compile(r"-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----")

# Zustände je Ergebniszeile
READ, NOT_READABLE, NOT_BACKED_UP, INFO = "read", "not_readable", "not_backed_up", "info"


def g(path):
    return path + "/getdata"


# ---------------------------------------------------------------------------
# Umwandlung Gerätewert -> Profilwert
# ---------------------------------------------------------------------------
def to_text(value):
    """Leere Texte liefert das Gerät als null; im Profil "" (= leer schreiben, nicht "Keine Aktion")."""
    return "" if value is None else str(value)


def to_int(value):
    if value is None or isinstance(value, bool):
        raise ValueError("no int")
    return int(value)


def to_bool(value):
    if isinstance(value, bool):
        return value
    if str(value).lower() in ("true", "1"):
        return True
    if str(value).lower() in ("false", "0"):
        return False
    raise ValueError("no bool")


def to_certs(value):
    """Zertifikatskette als Liste einzelner PEM-Blöcke (so lädt sie auch der Editor). Leer -> None."""
    if value in (None, "", []):
        return None
    text = "\n".join(value) if isinstance(value, list) else str(value)
    text = text.replace("\r\n", "\n").replace("\\n", "\n")
    blocks = PEM_BLOCK.findall(text)
    return blocks or None


def to_list(value):
    if value in (None, ""):
        return None
    items = value if isinstance(value, list) else str(value).split(",")
    items = [str(x).strip() for x in items if str(x).strip()]
    return items or None


def status_to_action(value):
    state = str(value or "").lower().strip()
    if state == "running":
        return "start"
    if state == "stopped":
        return "stop"
    raise ValueError("unknown state")


def http_to_action(value):
    return {0: "start", 1: "stop"}[to_int(value)]


# (Abschnitt, Profilfeld, Anzeigename, Lesepfad, Umwandlung)
SIMPLE_FIELDS = [
    ("device_tags", "application_tag", "Application Tag", g("/devicetag/applicationtag"), to_text),
    ("device_tags", "function_tag", "Function Tag", g("/devicetag/functiontag"), to_text),
    ("device_tags", "location_tag", "Location Tag", g("/devicetag/locationtag"), to_text),
    ("system_ntp", "servers", "NTP Server", g("/application/ntp/settings/serverlist"), to_list),
    ("system_ntp", "action", "NTP Status", g("/application/ntp/status"), status_to_action),
    ("system_nodered", "action", "Node-RED Status", g("/application/node-red/status"), status_to_action),
    ("system_security", "credentials_enabled", "Credentials", g("/security/authentication_enabled"), to_bool),
    ("connections_http", "port", "HTTP Port", g("/connections/httpserver0/httpserver/port"), to_int),
    ("connections_http", "action", "HTTP", g("/connections/httpserver0/httpserver/allowed_services"), http_to_action),
    ("connections_https", "port", "HTTPS Port", g(HTTPS + "/port"), to_int),
    ("connections_https", "secure", "HTTPS Security", g(HTTPS + "/securesetup/secure"), to_int),
    ("connections_https", "trustedclientcertificates", "HTTPS Trusted Client Certificates",
     g(HTTPS + "/securesetup/trustedclientcertificates"), to_certs),
    ("connections_https", "validate_client_certificate", "HTTPS Validate Client Certificate",
     g(HTTPS + "/securesetup/validateclientcertificate"), to_int),
    ("connections_mqtt_client", "version", "MQTT Version", g(MQTT + "/version"), to_int),
    ("connections_mqtt_client", "qos", "MQTT QoS", g(MQTT + "/qos"), to_int),
    ("connections_mqtt_client", "keepalive", "MQTT Keep Alive", g(MQTT + "/keepalive"), to_int),
    ("connections_mqtt_client", "willtopic", "MQTT Will Topic", g(MQTT + "/willtopic"), to_text),
    ("connections_mqtt_client", "willmessage", "MQTT Will Message", g(MQTT + "/willmessage"), to_text),
    ("connections_mqtt_client", "retain", "MQTT Retain", g(MQTT + "/retain"), to_bool),
    ("connections_mqtt_client", "clientid", "MQTT Client ID", g(MQTT + "/clientid"), to_text),
    ("connections_mqtt_client", "validate_server_certificate", "MQTT Validate Server Certificate",
     g(MQTT + "/securesetup/validateservercertificate"), to_int),
    ("connections_mqtt_client", "trustedservercertificates", "MQTT Trusted Server Certificates",
     g(MQTT + "/securesetup/trustedservercertificates"), to_certs),
    ("connections_mqtt_client", "action", "MQTT Client Status", g("/connections/mqttclient/status"), status_to_action),
    ("connections_mqtt_command_channel", "brokerip", "MQTTCC Broker", g(MQTTCC + "/brokerip"), to_text),
    ("connections_mqtt_command_channel", "brokerport", "MQTTCC Broker Port", g(MQTTCC + "/brokerport"), to_int),
    ("connections_mqtt_command_channel", "version", "MQTTCC Version", g(MQTTCC + "/version"), to_int),
    ("connections_mqtt_command_channel", "qos", "MQTTCC QoS", g(MQTTCC + "/qos"), to_int),
    ("connections_mqtt_command_channel", "keepalive", "MQTTCC Keep Alive", g(MQTTCC + "/keepalive"), to_int),
    ("connections_mqtt_command_channel", "willtopic", "MQTTCC Will Topic", g(MQTTCC + "/willtopic"), to_text),
    ("connections_mqtt_command_channel", "willmessage", "MQTTCC Will Message", g(MQTTCC + "/willmessage"), to_text),
    ("connections_mqtt_command_channel", "cmdtopic", "MQTTCC Command Topic", g(MQTTCC + "/cmdtopic"), to_text),
    ("connections_mqtt_command_channel", "defaultreplytopic", "MQTTCC Response Topic", g(MQTTCC + "/defaultreplytopic"), to_text),
    ("connections_mqtt_command_channel", "clientid", "MQTTCC Client ID", g(MQTTCC + "/clientid"), to_text),
    ("connections_mqtt_command_channel", "secure", "MQTTCC Security Mode", g(MQTTCC + "/securesetup/secure"), to_int),
    ("connections_mqtt_command_channel", "validate_server_certificate", "MQTTCC Validate Server Certificate",
     g(MQTTCC + "/securesetup/validateservercertificate"), to_int),
    ("connections_mqtt_command_channel", "trustedservercertificates", "MQTTCC Trusted Server Certificates",
     g(MQTTCC + "/securesetup/trustedservercertificates"), to_certs),
    ("connections_mqtt_command_channel", "user", "MQTTCC User", g(MQTTCC + "/user"), to_text),
    ("connections_mqtt_command_channel", "action", "MQTTCC Status", g("/connections/mqttcommandchannel/status"), status_to_action),
]

# Reihenfolge der Abschnitte in der Ergebnistabelle
SECTION_ORDER = [
    "device_tags", "hostname", "network", "port_configuration", "fieldbus_type", "system_ntp", "system_nodered", "system_security",
    "connections_http", "connections_https", "connections_opcua", "connections_mqtt_client", "connections_mqtt_command_channel",
    "service_monitor",
    "iodd", "node_red_flows", "node_red_palettes",
]


# Anzeigenamen mit "@" sind Textschlüssel (messages.py) und werden in der Sprache der Oberfläche ausgegeben.
def _row(section, label, adr, state, value=None, code=None, note=None):
    return {"section": section, "label": label, "adr": adr, "state": state, "value": value, "code": code, "note": note}


class DeviceBackup:
    """Liest das Gerät abschnittsweise. ``rows()`` liefert die Ergebniszeilen als Generator;
    danach steht das fertige Profil in ``profile``.

    reader:      readback.DeviceReader
    flows_fn:    () -> Flow-Dokument von Node-RED (GET /flows) oder None (nicht sichern)
    modules_fn:  () -> [{"module", "version"}] der nachinstallierten Paletten oder None
    """

    def __init__(self, reader, name, flows_fn=None, modules_fn=None):
        self.reader = reader
        self.flows_fn = flows_fn
        self.modules_fn = modules_fn
        self.profile = copy.deepcopy(DEFAULT_PROFILE)
        self.profile["schema_version"] = SCHEMA_VERSION
        self.profile["name"] = name
        self.extra = {"node_red_modules": None, "node_red_flows_nodes": None}

    # -- Hilfen -------------------------------------------------------------
    def _read(self, adr):
        return self.reader.read(adr)

    def _field(self, section, key, label, adr, convert):
        ok, value, code = self._read(adr)
        if not ok:
            return _row(section, label, adr, NOT_READABLE, code=code)
        try:
            converted = convert(value)
        except (ValueError, TypeError, KeyError):
            return _row(section, label, adr, NOT_READABLE, value=value, code=code, note="unknown_value")
        self.profile[section][key] = converted
        return _row(section, label, adr, READ, value=converted, code=code)

    # -- Abschnitte ---------------------------------------------------------
    def rows(self):
        simple = {}
        for entry in SIMPLE_FIELDS:
            simple.setdefault(entry[0], []).append(entry)
        for section in SECTION_ORDER:
            for entry in simple.get(section, []):
                yield self._field(*entry)
            special = getattr(self, "_section_" + section, None)
            if special:
                yield from special()

    def _section_network(self):
        section = "network"
        net = self.profile[section]
        values = {}
        paths = {"mode": g(IPV4 + "/mode"), "address": g(IPV4 + "/address0/address"),
                 "subnetmask": g(IPV4 + "/address0/subnetmask"), "gateway": g(IPV4 + "/gateway"),
                 "staticdnsservers": g(IPV4 + "/staticdnsservers")}
        for key, adr in paths.items():
            ok, value, code = self._read(adr)
            values[key] = (ok, value, code)
        ok, mode, code = values["mode"]
        mode_name = {1: "static", 2: "dhcp"}.get(_safe_int(mode)) if ok else None
        if not ok:
            yield _row(section, "Mode", paths["mode"], NOT_READABLE, code=code)
        else:
            net["mode"] = mode_name
            yield _row(section, "Mode", paths["mode"], READ if mode_name else NOT_READABLE,
                       value=mode_name or mode, code=code, note=None if mode_name else "unknown_value")
        if mode_name == "static":
            for key, label in (("address", "@bk_lbl_address"), ("subnetmask", "@bk_lbl_subnetmask"), ("gateway", "Gateway")):
                ok, value, code = values[key]
                value = "" if value in (None, "0.0.0.0") else str(value)
                if ok:
                    net[key] = value
                yield _row(section, label, paths[key], READ if ok else NOT_READABLE, value=value if ok else None, code=code)
        ok, dns, code = values["staticdnsservers"]
        if ok:
            net["dns_servers"] = to_list(dns) or []
        yield _row(section, "DNS Server", paths["staticdnsservers"], READ if ok else NOT_READABLE,
                   value=net["dns_servers"] if ok else None, code=code)
        # Sicherheit: Eine statische IP darf beim Einspielen auf ein zweites Gerät nicht doppelt
        # vergeben werden. Die Werte bleiben im Profil, die Klasse steht auf "Keine Aktion".
        net["apply"] = False
        yield _row(section, "Network", None, INFO, note="network_no_action")

    def _section_port_configuration(self):
        section = "port_configuration"
        ports = []
        for port in range(1, 9):
            entry = {"port": port, "pin4": None}
            pins = [("pin4", f"Port {port} Pin 4", g(f"/iolinkmaster/port[{port}]/mode"), (0, 1, 2, 3))]
            if port <= 4:
                entry["pin2"] = None
                pins.append(("pin2", f"Port {port} Pin 2", g(f"/iolinkmaster/port[{port}]/powercontrol/mode_ua"), (0, 1, 2)))
            for key, label, adr, allowed in pins:
                ok, value, code = self._read(adr)
                number = _safe_int(value) if ok else None
                if ok and number in allowed:
                    entry[key] = number
                    yield _row(section, label, adr, READ, value=number, code=code)
                else:
                    yield _row(section, label, adr, NOT_READABLE, value=value if ok else None, code=code,
                               note="unknown_value" if ok else None)
            ports.append(entry)
        self.profile[section]["ports"] = ports

    def _section_fieldbus_type(self):
        section = "fieldbus_type"
        adr = g(FIELDBUS_TYPE_STATUS)
        ok, value, code = self._read(adr)
        number = _safe_int(value) if ok else None
        if ok and number in FIELDBUS_TYPES:
            self.profile[section]["type"] = number
            yield _row(section, "Fieldbus", adr, READ, value=f"{number} = {FIELDBUS_TYPES[number][0]}", code=code)
        else:
            yield _row(section, "Fieldbus", adr, NOT_READABLE, value=value if ok else None, code=code,
                       note="unknown_value" if ok else None)

    def _section_hostname(self):
        """Hostname ist gerätespezifisch: gespeichert, aber auf "Keine Aktion" (wie Network)."""
        section = "hostname"
        adr = g(HOSTNAME_ADR)
        ok, value, code = self._read(adr)
        if ok and isinstance(value, str) and value:
            self.profile[section]["hostname"] = value
            yield _row(section, "Hostname", adr, READ, value=value, code=code)
        else:
            yield _row(section, "Hostname", adr, NOT_READABLE, value=value if ok else None, code=code)
        self.profile[section]["apply"] = False
        yield _row(section, "Hostname", None, INFO, note="hostname_no_action")

    def _section_connections_opcua(self):
        section = "connections_opcua"
        opc = self.profile[section]
        adr = g(OPCUA + "/settings")
        ok, settings, code = self._read(adr)
        if not ok or not isinstance(settings, dict):
            yield _row(section, "OPC UA Settings", adr, NOT_READABLE, code=code)
        else:
            if settings.get("port") is not None:
                opc["port"] = _safe_int(settings["port"])
                yield _row(section, "OPC UA Port", adr, READ, value=opc["port"], code=code)
            if settings.get("enable_anonymous") is not None:
                opc["enable_anonymous"] = bool(settings["enable_anonymous"])
                yield _row(section, "OPC UA Anonymous", adr, READ, value=opc["enable_anonymous"], code=code)
            profiles = settings.get("security_profiles")
            if isinstance(profiles, list):
                opc["security_profiles"] = [{"name": str(p.get("name")), "enabled": bool(p.get("enabled"))}
                                            for p in profiles if isinstance(p, dict) and p.get("name")]
                yield _row(section, "OPC UA Security Profiles", adr, READ, value=opc["security_profiles"], code=code)
        yield self._field(section, "action", "OPC UA Status", g(OPCUA + "/status"), status_to_action)
        yield _row(section, "@bk_lbl_opcua_cert", None, NOT_BACKED_UP, note="opcua_certificate")

    def _certificate_key_pem(self, section, label, base):
        """Zertifikat + Key (PEM): Das Gerät liefert nur das Zertifikat; ohne Key ist es nicht wiederherstellbar."""
        adr = g(base + "/securesetup/certificate_key_pem")
        ok, value, code = self._read(adr)
        if not ok:
            return _row(section, label, adr, NOT_READABLE, code=code)
        cert = value.get("certificate") if isinstance(value, dict) else None
        if cert:
            return _row(section, label, adr, NOT_BACKED_UP, code=code, note="cert_key_pem_present")
        return _row(section, label, adr, INFO, code=code, note="cert_key_pem_none")

    def _section_connections_https(self):
        yield self._certificate_key_pem("connections_https", "@bk_lbl_https_cert", HTTPS)

    def _section_connections_mqtt_client(self):
        yield self._certificate_key_pem("connections_mqtt_client", "@bk_lbl_mqtt_client_cert", MQTT)

    def _section_connections_mqtt_command_channel(self):
        yield self._certificate_key_pem("connections_mqtt_command_channel", "@bk_lbl_mqttcc_client_cert", MQTTCC)
        yield _row("connections_mqtt_command_channel", "@bk_lbl_mqttcc_password", None, NOT_BACKED_UP, note="mqttcc_password")

    def _section_service_monitor(self):
        """Monitor-Einträge über /monitor/getitems; Datenpunkte ohne Gerätenamen, damit das Profil übertragbar bleibt."""
        section = "service_monitor"
        ok, data, code = self.reader.read_service(MONITOR_GETITEMS)
        items = data.get("items") if ok and isinstance(data, dict) else None
        if not isinstance(items, list):
            yield _row(section, "Service Monitor", MONITOR_GETITEMS, NOT_READABLE, code=code)
            return
        if not items:
            yield _row(section, "Service Monitor", MONITOR_GETITEMS, INFO, code=code, note="monitor_none")
            return
        out = []
        for item in items:
            recipient = parse_monitor_recipient(item.get("recipient"))
            entry = {"id": item.get("id"), "data_points": [relative_data_point(p) for p in item.get("data_points") or []],
                     "sample_interval": item.get("sample_interval"), "notify_interval": item.get("notify_interval"),
                     "data_changed": bool(item.get("data_changed")),
                     "sample_condition": relative_data_point(item.get("sample_condition")) or None,
                     "description": item.get("description") or None, "persist": item.get("persist") is not False,
                     "recipient": recipient}
            out.append(entry)
            shown = {"data_points": entry["data_points"], "sample_interval": entry["sample_interval"],
                     "notify_interval": entry["notify_interval"], "recipient": mask_recipient(item.get("recipient"))}
            note = "monitor_credentials" if recipient.get("password") else ("monitor_raw" if recipient.get("raw") else None)
            yield _row(section, f"Service Monitor ID {item.get('id')}", MONITOR_GETITEMS, READ, value=shown, code=code, note=note)
        self.profile[section]["items"] = out
        self.profile[section]["remove_unlisted"] = False

    def _section_iodd(self):
        yield _row("iodd", "@bk_lbl_iodd", None, NOT_BACKED_UP, note="iodd")

    def _section_node_red_flows(self):
        section = "node_red_flows"
        if self.flows_fn is None:
            yield _row(section, "Node-RED Flows", "/flows", INFO, note="flows_skipped")
            return
        try:
            flows = self.flows_fn()
        except Exception as exc:
            yield _row(section, "Node-RED Flows", "/flows", NOT_READABLE, value=str(exc)[:200], code=500)
            return
        nodes = flows.get("flows") if isinstance(flows, dict) else flows
        if not isinstance(nodes, list):
            yield _row(section, "Node-RED Flows", "/flows", NOT_READABLE, code=500, note="unknown_value")
            return
        self.extra["node_red_flows_nodes"] = len(nodes)
        if not nodes:
            yield _row(section, "Node-RED Flows", "/flows", READ, value=0, code=200, note="flows_empty")
            return
        self.profile[section]["files"] = [{"name": f"{self.profile['name']}_flows.json", "content_json": nodes}]
        yield _row(section, "Node-RED Flows", "/flows", READ, value=len(nodes), code=200, note="flows_nodes")

    def _section_node_red_palettes(self):
        section = "node_red_palettes"
        modules = None
        if self.modules_fn is not None:
            try:
                modules = self.modules_fn()
            except Exception:
                modules = None
        self.extra["node_red_modules"] = modules
        if modules:
            for item in modules:
                yield _row(section, f"{item.get('module')} {item.get('version') or ''}".strip(), "/nodes", NOT_BACKED_UP,
                           value=item.get("version"), note="palette")
        else:
            yield _row(section, "@bk_lbl_palettes", "/nodes", INFO, note="palettes_none" if modules == [] else "palettes_unknown")


def _safe_int(value):
    try:
        return None if value is None or isinstance(value, bool) else int(value)
    except (TypeError, ValueError):
        return None


def summary(rows):
    counts = {READ: 0, NOT_READABLE: 0, NOT_BACKED_UP: 0, INFO: 0}
    for row in rows:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    return {"read": counts[READ], "not_readable": counts[NOT_READABLE], "not_backed_up": counts[NOT_BACKED_UP]}


def user_modules(nodes_response):
    """Nachinstallierte Node-RED-Module (user = true) aus GET /nodes, je Modul einmal."""
    seen = {}
    for item in nodes_response or []:
        if isinstance(item, dict) and item.get("user") and item.get("module"):
            seen.setdefault(str(item["module"]), str(item.get("version") or ""))
    return [{"module": name, "version": version} for name, version in sorted(seen.items())]
