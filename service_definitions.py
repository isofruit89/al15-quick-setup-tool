from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import re
import base64
import zlib

from messages import LocalizedError

@dataclass
class RequestDef:
    adr: str
    data: Optional[Dict[str, Any]] = None
    auth_mode: str = "auth"
    label: str = ""


def require_fields(data: dict, required: list[str], context: str):
    missing = [f for f in required if data.get(f) in (None, '', [])]
    if missing:
        raise LocalizedError("required_fields", context=context, fields=', '.join(missing))


def build_password_change_request(new_password: str) -> RequestDef:
    encoded = base64.b64encode(new_password.encode()).decode()
    return RequestDef(
        '/security/password/setdata',
        {'newvalue': encoded},
        auth_mode='auth',
        label='Passwort ändern'
    )


def _set(value) -> bool:
    """Profilschema v2: None bedeutet "Keine Aktion"; jeder andere Wert wird geschrieben."""
    return value is not None


def _int_or_skip(value):
    """None oder leerer String -> None (Keine Aktion), sonst int."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return int(value)


def build_device_tags_requests(data: dict) -> List[RequestDef]:
    reqs = []
    for key, adr, label in (('application_tag', '/devicetag/applicationtag/setdata', 'Application Tag'),
                            ('function_tag', '/devicetag/functiontag/setdata', 'Function Tag'),
                            ('location_tag', '/devicetag/locationtag/setdata', 'Location Tag')):
        if _set(data.get(key)):
            reqs.append(RequestDef(adr, {'newvalue': str(data[key])}, label=label))
    return reqs


def build_network_requests(data: dict) -> List[RequestDef]:
    """IPv4 über /network/br0/ipv4/setnetwork.
    Live-Modell (gettree): mode 0=Disable, 1=Static, 2=Dhcp; Adressfelder heißen Address/Subnetmask."""
    mode = (data.get('mode') or '').lower().strip()
    if not mode:
        return []
    dns_servers = data.get('dns_servers') or []
    if isinstance(dns_servers, str):
        dns_servers = [x.strip() for x in dns_servers.split(',') if x.strip()]

    if mode == 'static':
        require_fields(data, ['address', 'subnetmask'], 'Network/static')
        payload = {
            'mode': 1,
            'gateway': data.get('gateway') or '',
            'address': [{'Address': data['address'], 'Subnetmask': data['subnetmask']}]
        }
    elif mode == 'dhcp':
        # Verifiziert am AL1590 (2026-11-19): ohne gateway_mode antwortet das Gerät mit
        # 422 "Gateway mode 0 is not supported". Werte wie im Werkszustand:
        # gateway_mode 1 = Gateway vom DHCP übernehmen, dns_mode 3 = DHCP-DNS-Server anhängen.
        payload = {'mode': 2, 'gateway': '', 'address': [], 'gateway_mode': 1, 'dns_mode': 3}
    else:
        raise LocalizedError("network_mode")

    if dns_servers:
        payload['staticdnsservers'] = dns_servers

    return [RequestDef('/network/br0/ipv4/setnetwork', payload, label='Network')]


def build_ntp_requests(data: dict) -> List[RequestDef]:
    reqs = []
    servers = data.get('servers')
    if isinstance(servers, str):
        servers = [x.strip() for x in servers.split(',') if x.strip()]
    if servers:
        reqs.append(RequestDef('/application/ntp/settings/serverlist/setdata', {'newvalue': servers}, label='NTP Server'))
    action = data.get('action')
    if action == 'start':
        reqs.append(RequestDef('/application/ntp/status/start', label='NTP Start'))
    elif action == 'stop':
        reqs.append(RequestDef('/application/ntp/status/stop', label='NTP Stop'))
    return reqs


def build_nodered_requests(data: dict) -> List[RequestDef]:
    reqs = []
    action = data.get('action')
    if action == 'start':
        reqs.append(RequestDef('/application/node-red/status/start', label='Node-RED Start'))
    elif action == 'stop':
        reqs.append(RequestDef('/application/node-red/status/stop', label='Node-RED Stop'))
    return reqs


def build_auth_enabled_requests(data: dict) -> List[RequestDef]:
    enabled = data.get('enabled')
    if enabled is None:
        return []
    return [RequestDef('/security/authentication_enabled/setdata', {'newvalue': bool(enabled)},
                       label='Credentials ein' if enabled else 'Credentials aus')]


def _port_or_skip(value, error_key):
    port = _int_or_skip(value)
    if port is not None and not 1 <= port <= 65535:
        raise LocalizedError(error_key)
    return port


def _enum_or_skip(value, allowed, error_key):
    number = _int_or_skip(value)
    if number is not None and number not in allowed:
        raise LocalizedError(error_key)
    return number


def build_http_requests(data: dict) -> List[RequestDef]:
    reqs = []
    port = _port_or_skip(data.get('port'), "http_port")
    if port is not None:
        reqs.append(RequestDef('/connections/httpserver0/httpserver/port/setdata', {'newvalue': port}, label='HTTP Port'))
    # Backwards compatibility: old profiles used {'enabled': true/false}.
    action = (data.get('action') or '').lower().strip()
    if not action:
        action = 'start' if data.get('enabled') is True else 'none'

    if action == 'start':
        reqs.append(RequestDef(
            '/connections/httpserver0/httpserver/allowed_services/setdata',
            {'newvalue': 0},
            label='HTTP Start'
        ))
    elif action == 'stop':
        reqs.append(RequestDef(
            '/connections/httpserver0/httpserver/allowed_services/setdata',
            {'newvalue': 1},
            label='HTTP Stop'
        ))
    elif action in ('none', ''):
        return reqs
    else:
        raise LocalizedError("http_action")
    return reqs

# ---------------------------------------------------------------------------
# Zertifikat + Private Key als PEM-Text (certificate_key_pem): HTTPS-Server und MQTT-Client-Zertifikate.
# Format laut Web-UI des AL1590 (am Gerät verifiziert 2026-11-20):
#   setdata {"newvalue": {"certificate": PEM, "key": PEM[, "password": Passwort des Keys]}} -> 230 (Neustart nötig)
#   getdata liefert das Zertifikat zurück, key und password immer null. Löschen ist nicht möglich.
# Der HTTPS-Server verlangt Extended Key Usage "TLS Server" (OID 1.3.6.1.5.5.7.3.1), sonst 422.
# ---------------------------------------------------------------------------
CERT_KEY_PEM_SUFFIX = '/securesetup/certificate_key_pem/setdata'
PEM_KEY_RE = re.compile(r'-----BEGIN ((?:RSA |EC |ENCRYPTED )?PRIVATE KEY)-----[\s\S]*?-----END \1-----')
PEM_CERT_MAX_BYTES = 64 * 1024
EKU_TLS_SERVER = bytes.fromhex('06082b06010505070301')


def _pem_text(value):
    return str(value or '').replace('\r\n', '\n').replace('\r', '\n').strip()


def build_certificate_key_pem(entry, context: str, require_server_auth: bool = False) -> Optional[Dict[str, Any]]:
    """Profilwert {"certificate": {name, pem}, "private_key": {name, pem}, "password"} -> setdata-Wert."""
    if entry in (None, {}):
        return None
    if not isinstance(entry, dict):
        raise LocalizedError("pem_pair_entry", context=context)
    cert = _pem_text((entry.get('certificate') or {}).get('pem'))
    key = _pem_text((entry.get('private_key') or {}).get('pem'))
    if not cert:
        raise LocalizedError("pem_pair_cert_missing", context=context)
    if not key:
        raise LocalizedError("pem_pair_key_missing", context=context)
    if len(cert) > PEM_CERT_MAX_BYTES or len(key) > PEM_CERT_MAX_BYTES:
        raise LocalizedError("pem_pair_size", context=context)
    blocks = PEM_CERT_RE.findall(cert)
    if not blocks:
        raise LocalizedError("pem_pair_cert_invalid", context=context)
    key_match = PEM_KEY_RE.search(key)
    if not key_match:
        raise LocalizedError("pem_pair_key_invalid", context=context)
    password = entry.get('password') or None
    if key_match.group(1) == 'ENCRYPTED PRIVATE KEY' and not password:
        raise LocalizedError("pem_pair_key_password", context=context)
    if require_server_auth:
        try:
            der = base64.b64decode(''.join(blocks[0].split()))
        except Exception as exc:
            raise LocalizedError("pem_pair_cert_invalid", context=context) from exc
        if EKU_TLS_SERVER not in der:
            raise LocalizedError("https_cert_eku")
    value = {'certificate': cert, 'key': key}
    if password:
        value['password'] = str(password)
    return value


def pem_certificate_list(value) -> Optional[List[str]]:
    """Liste einzelner PEM-Zertifikate (HTTPS Trusted Client Certificates). Leer -> None."""
    if value in (None, '', []):
        return None
    text = '\n'.join(value) if isinstance(value, list) else str(value)
    blocks = [_pem_text(m.group(0)) for m in PEM_CERT_RE.finditer(normalize_certificate_text(text))]
    if not blocks:
        raise LocalizedError("https_trusted_pem")
    return blocks


def build_https_requests(data: dict) -> List[RequestDef]:
    """HTTPS-Server (httpserver1). Änderungen meldet das Gerät mit 230 (wirksam nach Neustart).
    validateclientcertificate = 1 sperrt Clients ohne Zertifikat aus (auch dieses Tool); deshalb zuletzt."""
    reqs = []
    base = '/connections/httpserver1/httpserver'
    port = _port_or_skip(data.get('port'), "https_port")
    if port is not None:
        reqs.append(RequestDef(f'{base}/port/setdata', {'newvalue': port}, label='HTTPS Port'))
    secure = _enum_or_skip(data.get('secure'), (0, 1), "https_secure")
    if secure is not None:
        reqs.append(RequestDef(f'{base}/securesetup/secure/setdata', {'newvalue': secure}, label='HTTPS Security'))
    cert = build_certificate_key_pem(data.get('certificate'), 'HTTPS', require_server_auth=True)
    if cert:
        reqs.append(RequestDef(f'{base}/securesetup/certificate_key_pem/setdata', {'newvalue': cert}, label='HTTPS Zertifikat'))
    trusted = pem_certificate_list(data.get('trustedclientcertificates'))
    if trusted:
        reqs.append(RequestDef(f'{base}/securesetup/trustedclientcertificates/setdata', {'newvalue': trusted},
                               label='HTTPS Trusted Client Certificates'))
    validate = _enum_or_skip(data.get('validate_client_certificate'), (0, 1), "https_validate")
    if validate is not None:
        reqs.append(RequestDef(f'{base}/securesetup/validateclientcertificate/setdata', {'newvalue': validate},
                               label='HTTPS Validate Client Certificate'))
    return reqs


def _mqtt_common_requests(data: dict, base: str, prefix: str, with_retain: bool) -> List[RequestDef]:
    """MQTT-Version, Keep Alive, Last Will (und Retain beim MQTT Client)."""
    reqs = []
    version = _enum_or_skip(data.get('version'), (0, 1, 2), "mqtt_version")
    if version is not None:
        reqs.append(RequestDef(f'{base}/version/setdata', {'newvalue': version}, label=f'{prefix} Version'))
    keepalive = _int_or_skip(data.get('keepalive'))
    if keepalive is not None:
        if not 0 <= keepalive <= 65535:
            raise LocalizedError("mqtt_keepalive")
        reqs.append(RequestDef(f'{base}/keepalive/setdata', {'newvalue': keepalive}, label=f'{prefix} Keep Alive'))
    for key, label in (('willtopic', 'Will Topic'), ('willmessage', 'Will Message')):
        if _set(data.get(key)):
            reqs.append(RequestDef(f'{base}/{key}/setdata', {'newvalue': str(data[key])}, label=f'{prefix} {label}'))
    if with_retain and _set(data.get('retain')):
        reqs.append(RequestDef(f'{base}/retain/setdata', {'newvalue': bool(data['retain'])}, label=f'{prefix} Retain'))
    return reqs


OPCUA_CERT_ADR = '/connections/opcua_server/upload_certificate'
OPCUA_CERT_MAX_BYTES = 64 * 1024
PEM_CERT_RE = re.compile(r'-----BEGIN CERTIFICATE-----([\s\S]*?)-----END CERTIFICATE-----')


def opcua_certificate_der(raw: bytes) -> bytes:
    """Zertifikat als DER. PEM (.pem/.crt) wird ohne Zusatzbibliothek in DER umgewandelt."""
    text = raw[:100].decode('ascii', 'ignore')
    if '-----BEGIN' in text:
        match = PEM_CERT_RE.search(raw.decode('ascii', 'ignore'))
        if not match:
            raise LocalizedError("opcua_cert_no_pem")
        raw = base64.b64decode(''.join(match.group(1).split()))
    if not raw or raw[0] != 0x30:
        raise LocalizedError("opcua_cert_invalid")
    return raw


def opcua_certificate_files(cert_entry) -> Optional[Dict[str, Any]]:
    """Liest {certificate: {name, content_base64}, private_key: {name, content_base64}} und prüft beide Dateien."""
    if cert_entry in (None, {}):
        return None
    if not isinstance(cert_entry, dict):
        raise LocalizedError("opcua_cert_entry")
    out = {}
    for key, slot in (('certificate', 'cert'), ('private_key', 'key')):
        item = cert_entry.get(key) or {}
        if not item.get('content_base64'):
            raise LocalizedError(f"opcua_cert_{slot}_missing")
        try:
            raw = base64.b64decode(item['content_base64'], validate=True)
        except Exception as exc:
            raise LocalizedError(f"opcua_cert_{slot}_base64") from exc
        if len(raw) > OPCUA_CERT_MAX_BYTES:
            raise LocalizedError(f"opcua_cert_{slot}_size")
        out[key] = {'name': str(item.get('name') or ''), 'raw': raw}
    out['certificate']['raw'] = opcua_certificate_der(out['certificate']['raw'])
    key = out['private_key']
    if not key['name'].lower().endswith(('.pfx', '.p12')) or key['raw'][:1] != b'\x30':
        raise LocalizedError("opcua_key_format")
    return out


def build_opcua_certificate_payload(cert_entry) -> Optional[Dict[str, Any]]:
    """Payload laut Web-UI des AL1590: Datei-Bytes Base64 + CRC32 über die rohen Bytes."""
    files = opcua_certificate_files(cert_entry)
    if not files:
        return None
    cert, key = files['certificate']['raw'], files['private_key']['raw']
    return {'private_key_value': base64.b64encode(key).decode(), 'private_key_crc32': zlib.crc32(key) & 0xFFFFFFFF,
            'certificate_value': base64.b64encode(cert).decode(), 'certificate_crc32': zlib.crc32(cert) & 0xFFFFFFFF}


def build_opcua_requests(data: dict) -> List[RequestDef]:
    reqs = []
    settings = {}
    port = _int_or_skip(data.get('port'))
    if port is not None:
        if not 1 <= port <= 65535:
            raise LocalizedError("opcua_port")
        settings['port'] = port
    if _set(data.get('enable_anonymous')):
        settings['enable_anonymous'] = bool(data['enable_anonymous'])
    profiles = data.get('security_profiles')
    if _set(profiles):
        if not isinstance(profiles, list):
            raise LocalizedError("opcua_profiles_list")
        settings['security_profiles'] = profiles
    if settings.get('enable_anonymous') and 'security_profiles' in settings:
        none_enabled = any(isinstance(p, dict) and p.get('name') == 'None' and p.get('enabled') is True
                           for p in settings['security_profiles'])
        if not none_enabled:
            raise LocalizedError("opcua_anonymous")

    certificate = build_opcua_certificate_payload(data.get('certificate'))

    action = data.get('action')
    if settings or certificate:
        # Geräteverhalten (YAML opcua.settings): Stop falls laufend -> Settings/Zertifikat -> Start.
        # Ist als Aktion "Stop" gewählt, bleibt der Server nach dem Schreiben gestoppt.
        reqs.append(RequestDef('/connections/opcua_server/status/stop', label='OPC UA Stop (conditional)'))
        if settings:
            reqs.append(RequestDef('/connections/opcua_server/settings/setdata', {'value': settings}, label='OPC UA Settings'))
        if certificate:
            reqs.append(RequestDef(OPCUA_CERT_ADR, certificate, label='OPC UA Zertifikat'))
        if action == 'start':
            reqs.append(RequestDef('/connections/opcua_server/status/start', label='OPC UA Start'))
        elif action != 'stop':
            # Ohne Ist-Werte (offline) wird laut YAML immer gestartet; mit Rücklesen wird der
            # vorherige Zustand (gestoppt/laufend) beibehalten.
            reqs.append(RequestDef('/connections/opcua_server/status/start', label='OPC UA Start (nach Settings)'))
    elif action == 'start':
        reqs.append(RequestDef('/connections/opcua_server/status/start', label='OPC UA Start'))
    elif action == 'stop':
        reqs.append(RequestDef('/connections/opcua_server/status/stop', label='OPC UA Stop'))
    return reqs


def normalize_certificate_text(text: str) -> str:
    """
    Normalisiert Zertifikatstext aus UI, PEM-Dateien oder JSON-Beispielen.

    Unterstützt:
    - echtes PEM mit echten Zeilenumbrüchen
    - aus JSON kopierte sichtbare Escape-Sequenzen wie \\n    - Windows-Zeilenenden
    - gemischte Eingaben

    Ziel:
    Intern immer mit echten Newlines arbeiten, damit requests.post(..., json=payload)
    daraus korrekt JSON-Escape-Sequenzen erzeugt.
    """
    text = str(text or '').strip()

    # Erst echte Windows-Zeilenenden normalisieren
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Dann sichtbare JSON-Escapes aus kopierten Beispielen in echte Newlines umwandeln
    text = text.replace("\\r\\n", "\n")
    text = text.replace("\\r", "\n")
    text = text.replace("\\n", "\n")

    return text

def normalize_mqtt_trusted_server_certificates(value):
    """
    Normalisiert MQTT Trusted Server Certificates in das vom Gerät erwartete Format.

    Ergebnis:
    - ein Zertifikat:
      {'newvalue': ['CERT1']}

    - Zertifikatskette:
      {'newvalue': ['CERT1,\\nCERT2']}
    """
    if value in (None, ''):
        return []

    texts = []

    if isinstance(value, str):
        text = normalize_certificate_text(value)
        if text:
            texts.append(text)

    elif isinstance(value, list):
        for entry in value:
            if not isinstance(entry, str):
                raise LocalizedError("mqtt_certs_strings")

            text = normalize_certificate_text(entry)
            if text:
                texts.append(text)

    else:
        raise LocalizedError("mqtt_certs_format")

    if not texts:
        return []

    combined_text = "\n".join(texts)

    pem_matches = re.findall(
        r'-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----',
        combined_text
    )

    if not pem_matches:
        raise LocalizedError("mqtt_certs_pem")

    normalized_certs = []

    for cert in pem_matches:
        cert = normalize_certificate_text(cert)

        if not cert.startswith('-----BEGIN CERTIFICATE-----'):
            raise LocalizedError("cert_begin")

        if not cert.endswith('-----END CERTIFICATE-----'):
            raise LocalizedError("cert_end")

        normalized_certs.append(cert)

    return [",\n".join(normalized_certs)]


def build_mqtt_client_requests(data: dict) -> List[RequestDef]:
    reqs = []
    base = '/connections/mqttclient/mqttsetup'
    reqs.extend(_mqtt_common_requests(data, base, 'MQTT', with_retain=True))
    qos = _int_or_skip(data.get('qos'))
    if qos is not None:
        reqs.append(RequestDef(f'{base}/qos/setdata', {'newvalue': qos}, label='MQTT QoS'))
    if _set(data.get('clientid')):
        reqs.append(RequestDef(f'{base}/clientid/setdata', {'newvalue': str(data['clientid'])}, label='MQTT Client ID'))
    validate = _int_or_skip(data.get('validate_server_certificate'))
    if validate is not None:
        reqs.append(RequestDef(f'{base}/securesetup/validateservercertificate/setdata', {'newvalue': validate}, label='MQTT Validate Server Certificate'))
    certs = normalize_mqtt_trusted_server_certificates(data.get('trustedservercertificates'))
    if certs:
        reqs.append(RequestDef(f'{base}/securesetup/trustedservercertificates/setdata', {'newvalue': certs}, label='MQTT Trusted Server Certificates'))
    client_cert = build_certificate_key_pem(data.get('client_certificate'), 'MQTT Client')
    if client_cert:
        reqs.append(RequestDef(f'{base}{CERT_KEY_PEM_SUFFIX}', {'newvalue': client_cert}, label='MQTT Client-Zertifikat'))

    action = data.get('action')
    if action == 'start':
        reqs.append(RequestDef('/connections/mqttclient/status/start', label='MQTT Client Start'))
    elif action == 'stop':
        reqs.append(RequestDef('/connections/mqttclient/status/stop', label='MQTT Client Stop'))
    return reqs


def build_mqtt_command_channel_requests(data: dict) -> List[RequestDef]:
    reqs = []
    base = '/connections/mqttcommandchannel/mqttcmdchannel/mqttcmdchannelsetup'
    reqs.extend(_mqtt_common_requests(data, base, 'MQTTCC', with_retain=False))
    fields = (
        ('brokerip', 'brokerip', str, 'MQTTCC Broker'),
        ('brokerport', 'brokerport', int, 'MQTTCC Broker Port'),
        ('qos', 'qos', int, 'MQTTCC QoS'),
        ('cmdtopic', 'cmdtopic', str, 'MQTTCC Command Topic'),
        ('defaultreplytopic', 'defaultreplytopic', str, 'MQTTCC Response Topic'),
        ('clientid', 'clientid', str, 'MQTTCC Client ID'),
        ('secure', 'securesetup/secure', int, 'MQTTCC Security Mode'),
        ('validate_server_certificate', 'securesetup/validateservercertificate', int, 'MQTTCC Validate Server Certificate'),
    )
    for key, path, conv, label in fields:
        value = data.get(key)
        if conv is int:
            value = _int_or_skip(value)
        if value is None:
            continue
        reqs.append(RequestDef(f'{base}/{path}/setdata', {'newvalue': conv(value)}, label=label))
    certs = normalize_mqtt_trusted_server_certificates(data.get('trustedservercertificates'))
    if certs:
        reqs.append(RequestDef(f'{base}/securesetup/trustedservercertificates/setdata', {'newvalue': certs}, label='MQTTCC Trusted Server Certificates'))
    client_cert = build_certificate_key_pem(data.get('client_certificate'), 'MQTT Command Channel')
    if client_cert:
        reqs.append(RequestDef(f'{base}{CERT_KEY_PEM_SUFFIX}', {'newvalue': client_cert}, label='MQTTCC Client-Zertifikat'))
    if _set(data.get('user')):
        reqs.append(RequestDef(f'{base}/user/setdata', {'newvalue': str(data['user'])}, label='MQTTCC User'))
    if _set(data.get('password')):
        reqs.append(RequestDef(f'{base}/password/setdata', {'newvalue': str(data['password'])}, label='MQTTCC Passwort'))
    action = data.get('action')
    if action == 'start':
        reqs.append(RequestDef('/connections/mqttcommandchannel/status/start', label='MQTTCC Start'))
    elif action == 'stop':
        reqs.append(RequestDef('/connections/mqttcommandchannel/status/stop', label='MQTTCC Stop'))
    return reqs


def build_port_configuration_requests(data: dict) -> List[RequestDef]:
    reqs = []
    ports = data.get('ports') or []
    if not isinstance(ports, list):
        raise LocalizedError("ports_list")
    by_number = {int(x.get('port')): x for x in ports if isinstance(x, dict) and str(x.get('port', '')).isdigit()}
    for port in range(1, 9):
        item = by_number.get(port, {})
        pin4 = _int_or_skip(item.get('pin4'))
        if pin4 is not None:
            if pin4 not in (0, 1, 2, 3):
                raise LocalizedError("port_pin4", port=port)
            reqs.append(RequestDef(f'/iolinkmaster/port[{port}]/mode/setdata', {'newvalue': pin4}, label=f'Port {port} Pin 4'))
        pin2 = _int_or_skip(item.get('pin2')) if port <= 4 else None
        if pin2 is not None:
            if pin2 not in (0, 1, 2):
                raise LocalizedError("port_pin2", port=port)
            reqs.append(RequestDef(f'/iolinkmaster/port[{port}]/powercontrol/mode_ua/setdata', {'newvalue': pin2}, label=f'Port {port} Pin 2'))
    return reqs


# ---------------------------------------------------------------------------
# Service Monitor (/monitor): zyklische MQTT/MQTTS-Meldungen von Datenpunkten.
# Am AL1590 verifiziert (2026-11-20):
#   /monitor/add {id?, data_points, sample_interval, notify_interval, recipient, data_changed?, sample_condition?,
#                 description?, persist?} -> 200 {id}. Gleiche id ersetzt den Eintrag, ohne id vergibt das Gerät eine.
#   /monitor/remove {id} -> 200; unbekannte id -> 422.  /monitor/getitems -> {items: [...]} (Zugangsdaten im Klartext).
# Datenpunkte stehen im Profil ohne Gerätenamen ("/devicestatus/..."); beim Übertragen setzt das Tool den Namen
# des Zielgeräts davor (so wie die Web-UI sie anlegt: "ifm-AL1590-<SN>/devicestatus/...").
# Start/Stop des Monitors ist bewusst nicht Teil des Tools.
# ---------------------------------------------------------------------------
MONITOR_ADD = '/monitor/add'
MONITOR_REMOVE = '/monitor/remove'
MONITOR_GETITEMS = '/monitor/getitems'
MONITOR_REMOVE_UNLISTED = '/monitor/remove_unlisted'  # interner Schritt: wird über /monitor/remove ausgeführt
MONITOR_SCHEMES = ('mqtt', 'mqtts')
MONITOR_DEFAULT_PORTS = {'mqtt': 1883, 'mqtts': 8883}
RECIPIENT_RE = re.compile(r'^(mqtts?)://(?:([^:@/]*)(?::([^@/]*))?@)?([^:/@]+)(?::(\d+))?/(.*)$', re.IGNORECASE)


def relative_data_point(path) -> str:
    """'ifm-AL1590-.../devicestatus/x' -> '/devicestatus/x'; relative Pfade bleiben unverändert."""
    path = str(path or '').strip()
    if not path or path.startswith('/'):
        return path
    return '/' + path.split('/', 1)[1] if '/' in path else path


def bind_data_point(path, hostname: str) -> str:
    rel = relative_data_point(path)
    return f'{hostname}{rel}' if hostname and rel.startswith('/') else rel


def mask_recipient(url) -> str:
    return re.sub(r'(://[^:/@]*:)[^@/]*@', r'\1***@', str(url or ''))


def parse_monitor_recipient(url) -> Dict[str, Any]:
    match = RECIPIENT_RE.match(str(url or '').strip())
    if not match:
        return {'scheme': None, 'host': None, 'port': None, 'topic': None, 'user': None, 'password': None, 'raw': str(url or '')}
    scheme, user, password, host, port, topic = match.groups()
    return {'scheme': scheme.lower(), 'host': host, 'port': int(port) if port else None, 'topic': topic,
            'user': user or None, 'password': password if password not in (None, '') else None}


def monitor_recipient_url(recipient, label: str) -> str:
    if not isinstance(recipient, dict):
        raise LocalizedError("monitor_recipient", item=label)
    if recipient.get('raw') and not recipient.get('host'):
        return str(recipient['raw'])  # vom Gerät gelesen, aber nicht zerlegbar: unverändert übernehmen
    scheme = str(recipient.get('scheme') or 'mqtt').lower()
    if scheme not in MONITOR_SCHEMES:
        raise LocalizedError("monitor_scheme", item=label)
    host = str(recipient.get('host') or '').strip()
    topic = str(recipient.get('topic') or '').strip().lstrip('/')
    if not host or any(ch in host for ch in ':/@ '):
        raise LocalizedError("monitor_host", item=label)
    if not topic:
        raise LocalizedError("monitor_topic", item=label)
    port = _int_or_skip(recipient.get('port')) or MONITOR_DEFAULT_PORTS[scheme]
    if not 1 <= port <= 65535:
        raise LocalizedError("monitor_port", item=label)
    user, password = str(recipient.get('user') or ''), str(recipient.get('password') or '')
    if any(ch in user + password for ch in ':/@'):
        raise LocalizedError("monitor_credentials", item=label)
    auth = f'{user}:{password}@' if user or password else ''
    return f'{scheme}://{auth}{host}:{port}/{topic}'


def monitor_item_payload(item, index: int) -> Dict[str, Any]:
    label = str(item.get('id') or f'#{index}') if isinstance(item, dict) else f'#{index}'
    if not isinstance(item, dict):
        raise LocalizedError("monitor_item", item=label)
    points = item.get('data_points')
    if isinstance(points, str):
        points = [x.strip() for x in re.split(r'[\n,]', points) if x.strip()]
    points = [relative_data_point(p) for p in (points or []) if str(p).strip()]
    if not points:
        raise LocalizedError("monitor_datapoints", item=label)
    payload: Dict[str, Any] = {'data_points': points}
    for key in ('sample_interval', 'notify_interval'):
        value = _int_or_skip(item.get(key))
        if value is None or value < 1:
            raise LocalizedError("monitor_interval", item=label)
        payload[key] = value
    payload['recipient'] = monitor_recipient_url(item.get('recipient'), label)
    payload['data_changed'] = bool(item.get('data_changed'))
    payload['persist'] = item.get('persist') is not False
    if str(item.get('sample_condition') or '').strip():
        payload['sample_condition'] = relative_data_point(item['sample_condition'])
    if str(item.get('description') or '').strip():
        payload['description'] = str(item['description']).strip()
    item_id = _int_or_skip(item.get('id'))
    if item_id is not None:
        if item_id < 1:
            raise LocalizedError("monitor_id", item=label)
        payload['id'] = item_id
    return payload


def build_monitor_requests(data: dict) -> List[RequestDef]:
    items = data.get('items') or []
    if not isinstance(items, list):
        raise LocalizedError("monitor_items_list")
    reqs, seen = [], set()
    for index, item in enumerate(items, start=1):
        payload = monitor_item_payload(item, index)
        if 'id' in payload:
            if payload['id'] in seen:
                raise LocalizedError("monitor_id_duplicate", id=payload['id'])
            seen.add(payload['id'])
        label = f"Service Monitor ID {payload['id']}" if 'id' in payload else f'Service Monitor (neu {index})'
        reqs.append(RequestDef(MONITOR_ADD, payload, label=label))
    if data.get('remove_unlisted'):
        keep = [dict(r.data) for r in reqs]
        reqs.append(RequestDef(MONITOR_REMOVE_UNLISTED, {'keep': keep}, label='Service Monitor: nicht enthaltene Einträge entfernen'))
    return reqs


def normalize_monitor_item(item) -> Dict[str, Any]:
    """Vergleichsform eines Monitor-Eintrags (Gerät oder Profil): ohne Gerätenamen, ohne id und description."""
    item = item or {}
    return {'data_points': [relative_data_point(p) for p in item.get('data_points') or []],
            'sample_interval': _int_or_skip(item.get('sample_interval')), 'notify_interval': _int_or_skip(item.get('notify_interval')),
            'data_changed': bool(item.get('data_changed')), 'persist': item.get('persist') is not False,
            'sample_condition': relative_data_point(item.get('sample_condition')) or None,
            'recipient': str(item.get('recipient') or '')}


def public_monitor_item(item) -> Dict[str, Any]:
    out = dict(item or {})
    if 'recipient' in out:
        out['recipient'] = mask_recipient(out['recipient'])
    return out


# ---------------------------------------------------------------------------
# Hostname (/network/br0/hostname). Live geprüft am AL1590 FW 1.7.0.2 (2026-11-20).
# ---------------------------------------------------------------------------
HOSTNAME_ADR = '/network/br0/hostname'
# Live geprüft: max. 63 Zeichen, Buchstaben/Ziffern/Bindestrich/Punkt; Beginn mit Buchstabe,
# kein Bindestrich am Ende eines Abschnitts, kein Punkt am Ende ("1abc", "abc_d", "a-.b", "a." -> 422).
HOSTNAME_RE = re.compile(r'^(?=.{1,63}$)[A-Za-z](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*$')


def build_hostname_requests(data: dict) -> List[RequestDef]:
    value = data.get('hostname')
    if value is None or not str(value).strip():
        return []
    value = str(value).strip()
    if not HOSTNAME_RE.match(value):
        raise LocalizedError("hostname_invalid", value=value)
    return [RequestDef(f'{HOSTNAME_ADR}/setdata', {'newvalue': value}, label='Hostname')]


# ---------------------------------------------------------------------------
# Feldbus-Umschaltung PROFINET / EtherNet/IP (/devicesettings/fieldbustype).
# Live geprüft am AL1590 FW 1.7.0.2 (2026-11-20): status 0 = Profinet, 2 = EtherNet/IP (Werkszustand 2).
# Umschalten per <Typ>/enable ohne Daten; der Aufruf blockiert ca. 60 s und antwortet dann mit 200.
# Ist der Typ schon aktiv, antwortet das Gerät sofort. Kein Neustart nötig.
# ---------------------------------------------------------------------------
FIELDBUS_TYPE_STATUS = '/devicesettings/fieldbustype/status'
FIELDBUS_TYPES = {0: ('PROFINET', '/devicesettings/fieldbustype/Profinet/enable'),
                  2: ('EtherNet/IP', '/devicesettings/fieldbustype/EtherNetIP/enable')}
FIELDBUS_ENABLE = {adr: value for value, (_, adr) in FIELDBUS_TYPES.items()}
FIELDBUS_SWITCH_TIMEOUT = 180


def build_fieldbus_type_requests(data: dict) -> List[RequestDef]:
    value = _int_or_skip(data.get('type'))
    if value is None:
        return []
    if value not in FIELDBUS_TYPES:
        raise LocalizedError("fieldbus_type")
    name, adr = FIELDBUS_TYPES[value]
    return [RequestDef(adr, None, label=f'Fieldbus {name}')]

