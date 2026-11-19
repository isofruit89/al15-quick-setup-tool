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


def build_http_requests(data: dict) -> List[RequestDef]:
    reqs = []
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
        return []
    else:
        raise LocalizedError("http_action")
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

    action = data.get('action')
    if action == 'start':
        reqs.append(RequestDef('/connections/mqttclient/status/start', label='MQTT Client Start'))
    elif action == 'stop':
        reqs.append(RequestDef('/connections/mqttclient/status/stop', label='MQTT Client Stop'))
    return reqs


def build_mqtt_command_channel_requests(data: dict) -> List[RequestDef]:
    reqs = []
    base = '/connections/mqttcommandchannel/mqttcmdchannel/mqttcmdchannelsetup'
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


