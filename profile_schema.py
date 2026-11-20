"""Profilschema des Quick-Setup-Tools.

Schema v2 ("Keine Aktion"):
- Jede Parameterklasse (Abschnitt) hat ``apply``: ``False`` bedeutet "Keine Aktion" für die
  ganze Klasse; die eingetragenen Werte bleiben im Profil erhalten, werden aber nicht übertragen.
- Ein einzelner Parameter mit dem Wert ``None`` (JSON ``null``) wird nicht geschrieben. Der Editor
  erzeugt ``None`` für leere Felder; einen eigenen Schalter pro Parameter gibt es seit 1.8 nicht mehr.
  Neue Parametersätze starten mit FACTORY_PROFILE (Werkseinstellungen).
- Start/Stop-Aktionen behalten ``"none"`` als "Keine Aktion".

Profile ohne ``schema_version`` (v1, Tool <= 1.6) werden beim Laden so umgewandelt,
dass sie exakt dieselben Requests erzeugen wie bisher.
"""
import copy

SCHEMA_VERSION = 2

SECTIONS = [
    "device_tags", "port_configuration", "fieldbus_type", "system_ntp", "system_nodered", "system_security",
    "connections_http", "connections_https", "connections_opcua", "connections_mqtt_client",
    "connections_mqtt_command_channel", "service_monitor", "hostname", "network", "iodd", "node_red_flows", "node_red_palettes",
]
FILE_SECTIONS = ("iodd", "node_red_flows", "node_red_palettes")

DEFAULT_PROFILE = {
    "schema_version": SCHEMA_VERSION,
    "name": "quick_setup_demo",
    "device_tags": {"apply": True, "application_tag": None, "function_tag": None, "location_tag": None},
    "port_configuration": {"apply": True, "ports": [{"port": p, "pin4": None, **({"pin2": None} if p <= 4 else {})} for p in range(1, 9)]},
    # Feldbus-Umschaltung: type 0 = PROFINET, 2 = EtherNet/IP
    "fieldbus_type": {"apply": True, "type": None},
    "system_ntp": {"apply": True, "servers": None, "action": "none"},
    "system_nodered": {"apply": True, "action": "none"},
    "system_security": {"apply": True, "credentials_enabled": None},
    "connections_http": {"apply": True, "port": None, "action": "none"},
    # HTTPS-Server (httpserver1). certificate = {"certificate": {name, pem}, "private_key": {name, pem}, "password"}
    "connections_https": {"apply": True, "port": None, "secure": None, "certificate": None,
                          "validate_client_certificate": None, "trustedclientcertificates": None},
    "connections_opcua": {"apply": True, "port": None, "enable_anonymous": None, "security_profiles": None, "certificate": None, "action": "none"},
    "connections_mqtt_client": {"apply": True, "version": None, "qos": None, "clientid": None, "keepalive": None,
                                "willtopic": None, "willmessage": None, "retain": None, "validate_server_certificate": None,
                                "trustedservercertificates": None, "client_certificate": None, "action": "none"},
    "connections_mqtt_command_channel": {"apply": True, "brokerip": None, "brokerport": None, "version": None, "qos": None,
                                         "keepalive": None, "cmdtopic": None, "defaultreplytopic": None, "clientid": None,
                                         "willtopic": None, "willmessage": None, "secure": None,
                                         "validate_server_certificate": None, "trustedservercertificates": None,
                                         "client_certificate": None, "user": None, "password": None, "action": "none"},
    # Service Monitor: items = [{id, data_points, sample_interval, notify_interval, data_changed, sample_condition,
    #   description, persist, recipient: {scheme, host, port, topic, user, password}}]
    "service_monitor": {"apply": True, "items": [], "remove_unlisted": False},
    "hostname": {"apply": True, "hostname": None},
    "network": {"apply": True, "mode": None, "address": "", "subnetmask": "", "gateway": "", "dns_servers": []},
    "iodd": {"apply": True, "files": []},
    "node_red_flows": {"apply": True, "files": []},
    "node_red_palettes": {"apply": True, "files": []},
}


# Werkseinstellungen AL1590 FW 1.7.0.2 (am 2026-11-20 nach Werksreset ausgelesen,
# Profil profiles/werkszustand_AL1590_fw1702.json). Sie dienen nur als Vorbelegung des
# Editors für einen neuen Parametersatz. DEFAULT_PROFILE bleibt die Basis für das Laden
# und Ergänzen älterer Profile, damit dort keine Werte dazukommen, die bisher nicht geschrieben wurden.
# Bewusst nicht vorbelegt:
# - gerätespezifische Texte (Tags, Client-ID, Broker-IP, Benutzer, Passwort, Will-Topic/-Message): leer = nicht schreiben
# - Zertifikate: keine Datei = nicht schreiben
# - Start/Stop-Aktionen: "none", damit laufende Dienste nur auf ausdrücklichen Wunsch gestartet/gestoppt werden
# - Hostname: gerätespezifisch, leer = nicht schreiben
# - Network: Modus "Keine Aktion", sonst würde ein statisch adressiertes Gerät auf DHCP umgestellt
FACTORY_PROFILE = copy.deepcopy(DEFAULT_PROFILE)
FACTORY_PROFILE["name"] = ""
FACTORY_PROFILE["port_configuration"]["ports"] = [{"port": p, "pin4": 3, **({"pin2": 0} if p <= 4 else {})} for p in range(1, 9)]
# Feldbus: Werkswert EtherNet/IP, Bereich aber auf "Keine Aktion" – ein vergessener Bereich soll
# eine PROFINET-Anlage nicht umschalten (Verbindung zur Steuerung).
FACTORY_PROFILE["fieldbus_type"].update({"apply": False, "type": 2})
FACTORY_PROFILE["system_ntp"]["servers"] = ["0.pool.ntp.org", "1.pool.ntp.org", "2.pool.ntp.org"]
FACTORY_PROFILE["system_security"]["credentials_enabled"] = True
FACTORY_PROFILE["connections_http"]["port"] = 80
FACTORY_PROFILE["connections_https"].update({"port": 443, "secure": 0, "validate_client_certificate": 0})
FACTORY_PROFILE["connections_opcua"].update({
    "port": 4843, "enable_anonymous": False,
    "security_profiles": [{"name": "Basic256Sha256", "enabled": True}, {"name": "Aes128Sha256RsaOaep", "enabled": True},
                          {"name": "Aes256Sha256RsaPss", "enabled": True}, {"name": "None", "enabled": False}]})
FACTORY_PROFILE["connections_mqtt_client"].update({"version": 1, "qos": 0, "keepalive": 15, "retain": False,
                                                   "validate_server_certificate": 0})
FACTORY_PROFILE["connections_mqtt_command_channel"].update({
    "brokerport": 1883, "version": 1, "qos": 0, "keepalive": 15, "cmdtopic": "iotcore-request",
    "defaultreplytopic": "iotcore-response", "secure": 0, "validate_server_certificate": 0})


def _empty(value):
    return value is None or value == "" or value == [] or value == {}


def _none_if(value, *skip_values):
    """v1-Semantik: leere Werte und die genannten Werte bedeuteten "nicht schreiben"."""
    if _empty(value):
        return None
    if any(str(value) == str(s) for s in skip_values):
        return None
    return value


def _migrate_v1(p):
    out = copy.deepcopy(DEFAULT_PROFILE)
    out["name"] = p.get("name") or out["name"]

    tags = p.get("device_tags") or {}
    for key in ("application_tag", "function_tag", "location_tag"):
        out["device_tags"][key] = _none_if(tags.get(key))

    # v1 schrieb immer alle 8 Ports (fehlende mit Pin4=3 / Pin2=0) -> Verhalten beibehalten.
    by_port = {}
    for item in (p.get("port_configuration") or {}).get("ports") or []:
        if isinstance(item, dict) and str(item.get("port", "")).isdigit():
            by_port[int(item["port"])] = item
    ports = []
    for port in range(1, 9):
        item = by_port.get(port, {})
        entry = {"port": port, "pin4": int(item.get("pin4", 3))}
        if port <= 4:
            entry["pin2"] = int(item.get("pin2", 0))
        ports.append(entry)
    out["port_configuration"]["ports"] = ports

    ntp = p.get("system_ntp") or {}
    servers = ntp.get("servers")
    if isinstance(servers, str):
        servers = [x.strip() for x in servers.split(",") if x.strip()]
    out["system_ntp"]["servers"] = servers or None
    out["system_ntp"]["action"] = ntp.get("action") or "none"

    out["system_nodered"]["action"] = (p.get("system_nodered") or {}).get("action") or "none"

    # v1 schrieb nur "aus"; "ein" erzeugte keinen Request.
    enabled = (p.get("system_security") or {}).get("credentials_enabled")
    out["system_security"]["credentials_enabled"] = False if enabled is False else None

    http = p.get("connections_http") or {}
    action = (http.get("action") or "").lower().strip() or ("start" if http.get("enabled") is True else "none")
    out["connections_http"]["action"] = action

    # v1 schrieb die OPC-UA-Settings, sobald Port oder Anonymous gesetzt waren (praktisch immer).
    opc = p.get("connections_opcua") or {}
    out["connections_opcua"]["port"] = None if opc.get("port") in (None, "") else int(opc["port"])
    out["connections_opcua"]["enable_anonymous"] = None if opc.get("enable_anonymous") is None else bool(opc["enable_anonymous"])
    out["connections_opcua"]["security_profiles"] = opc.get("security_profiles") or None
    out["connections_opcua"]["action"] = opc.get("action") or "none"

    mq = p.get("connections_mqtt_client") or {}
    out["connections_mqtt_client"].update({
        "qos": _none_if(mq.get("qos"), 0),
        "clientid": _none_if(mq.get("clientid")),
        "validate_server_certificate": _none_if(mq.get("validate_server_certificate"), 0),
        "trustedservercertificates": _none_if(mq.get("trustedservercertificates")),
        "action": mq.get("action") or "none",
    })

    cc = p.get("connections_mqtt_command_channel") or {}
    target = out["connections_mqtt_command_channel"]
    for key in ("brokerip", "brokerport", "cmdtopic", "defaultreplytopic", "clientid", "user", "password", "trustedservercertificates"):
        target[key] = _none_if(cc.get(key))
    for key in ("qos", "secure", "validate_server_certificate"):
        target[key] = _none_if(cc.get(key), 0)
    target["action"] = cc.get("action") or "none"

    net = p.get("network") or {}
    dns = net.get("dns_servers") or []
    if isinstance(dns, str):
        dns = [x.strip() for x in dns.split(",") if x.strip()]
    mode = (net.get("mode") or "").lower().strip()
    # v1: DHCP ohne weitere Angaben erzeugte keinen Request.
    if mode in ("", "dhcp") and not net.get("address") and not net.get("subnetmask") and not net.get("gateway") and not dns:
        mode = None
    out["network"].update({"mode": mode or None, "address": net.get("address") or "", "subnetmask": net.get("subnetmask") or "",
                           "gateway": net.get("gateway") or "", "dns_servers": dns})

    for key in FILE_SECTIONS:
        out[key]["files"] = list((p.get(key) or {}).get("files") or [])
    return out


def migrate_profile(profile):
    """Liefert ein Profil im aktuellen Schema (Kopie)."""
    p = profile or {}
    if int(p.get("schema_version") or 1) < SCHEMA_VERSION:
        out = _migrate_v1(p)
    else:
        out = copy.deepcopy(p)
        for section in SECTIONS:
            merged = copy.deepcopy(DEFAULT_PROFILE[section])
            merged.update(out.get(section) or {})
            out[section] = merged
        out["schema_version"] = SCHEMA_VERSION
    # Unbekannte Zusatzfelder (z. B. lang) nicht ins Profil übernehmen.
    out.pop("lang", None)
    return out


def section_active(profile, section):
    return (profile.get(section) or {}).get("apply", True) is not False


def effective_profile(profile):
    """Profil für Vorschau/Übertragung: Klassen mit "Keine Aktion" werden geleert."""
    p = migrate_profile(profile)
    for section in SECTIONS:
        if not section_active(p, section):
            p[section] = {"apply": False, **({"files": []} if section in FILE_SECTIONS else {})}
    return p
