"""Zurücklesen vor dem Schreiben (read_before_write laut al1590_description.yaml).

Für jeden kompilierten Request wird der Ist-Wert vom Gerät gelesen und mit dem Soll-Wert
verglichen. Ergebnis je Request ("decision"):
  write       Ist weicht vom Soll ab -> senden
  skip        Ist entspricht dem Soll -> nicht senden
  unverified  kein Vergleich möglich (kein Lesepfad oder Lesen fehlgeschlagen) -> senden

Wertformate am AL1590 (FW 1.7.0.2, live gelesen 2026-11-19):
  leere Texte -> null, Gateway ohne Wert -> "0.0.0.0", Status-Strings running/stopped,
  /connections/opcua_server/settings -> {"port", "security_profiles": [{name, enabled}], "enable_anonymous"}.
"""
import base64
import hashlib
import re

from service_definitions import (
    CERT_KEY_PEM_SUFFIX, MONITOR_ADD, MONITOR_GETITEMS, MONITOR_REMOVE_UNLISTED, normalize_monitor_item,
    normalize_mqtt_trusted_server_certificates, public_monitor_item,
)
from service_definitions import FIELDBUS_ENABLE, FIELDBUS_TYPE_STATUS, FIELDBUS_TYPES

# setdata-Pfade ohne getdata-Gegenstück: immer schreiben
ALWAYS_WRITE = {
    "/connections/mqttcommandchannel/mqttcmdchannel/mqttcmdchannelsetup/password/setdata",
    "/security/password/setdata",
}
OPCUA_BASE = "/connections/opcua_server"
OPCUA_SETTINGS_SET = OPCUA_BASE + "/settings/setdata"
OPCUA_CERT_UPLOAD = OPCUA_BASE + "/upload_certificate"
OPCUA_STATUS_GET = OPCUA_BASE + "/status/getdata"
NETWORK_SET = "/network/br0/ipv4/setnetwork"
STATUS_ACTION = re.compile(r"^(?P<base>.+)/status/(?P<act>start|stop)$")
PEM_BLOCK = re.compile(r"-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----")


class DeviceReader:
    """Liest Werte mit Cache; read_fn(adr) -> RPC-Antwort (dict)."""

    def __init__(self, read_fn, opcua_cert_fn=None):
        self._read_fn = read_fn
        self._opcua_cert_fn = opcua_cert_fn
        self._cache = {}

    def opcua_certificate(self):
        """DER-Zertifikat des laufenden OPC-UA-Servers oder None."""
        if "__opcua_cert__" not in self._cache:
            try:
                self._cache["__opcua_cert__"] = self._opcua_cert_fn(self) if self._opcua_cert_fn else None
            except Exception:
                self._cache["__opcua_cert__"] = None
        return self._cache["__opcua_cert__"]

    def entries(self):
        """Alle bisher gelesenen Pfade: {adr: {"ok", "value", "code"}} (für die Backup-Rohdatei)."""
        return {adr: {"ok": ok, "value": value, "code": code}
                for adr, (ok, value, code) in ((a, e) for a, e in self._cache.items() if not a.startswith("__"))}

    def read_service(self, adr):
        """Dienst ohne getdata-Form (z. B. /monitor/getitems): (ok, data, code)."""
        key = "svc:" + adr
        if key not in self._cache:
            try:
                resp = self._read_fn(adr)
            except Exception as exc:
                resp = {"code": 500, "error": str(exc)[:200]}
            ok = str(resp.get("code", "")) == "200"
            self._cache[key] = (ok, resp.get("data") if ok else None, resp.get("code"))
        return self._cache[key]

    def read(self, adr):
        if adr not in self._cache:
            try:
                resp = self._read_fn(adr)
            except Exception as exc:  # Netzwerkfehler -> nicht vergleichbar
                resp = {"code": 500, "error": str(exc)[:200]}
            ok = str(resp.get("code", "")) == "200"
            data = resp.get("data")
            value = data.get("value") if ok and isinstance(data, dict) else None
            self._cache[adr] = (ok, value, resp.get("code"))
        return self._cache[adr]


def _decision(kind, current=None, target=None, reason=""):
    return {"decision": kind, "current": current, "target": target, "reason": reason}


# ---------------------------------------------------------------------------
# Vergleiche
# ---------------------------------------------------------------------------
def _pem_blocks(value):
    if value in (None, "", []):
        return []
    text = "\n".join(value) if isinstance(value, list) else str(value)
    text = text.replace("\r\n", "\n").replace("\\n", "\n")
    return ["\n".join(line.strip() for line in block.strip().splitlines()) for block in PEM_BLOCK.findall(text)]


def values_equal(adr, current, target):
    if "trustedservercertificates" in adr or "trustedclientcertificates" in adr:
        return _pem_blocks(current) == _pem_blocks(target)
    if isinstance(target, bool):
        return isinstance(current, bool) and current == target
    if isinstance(target, int):
        try:
            return current is not None and not isinstance(current, bool) and int(current) == target
        except (TypeError, ValueError):
            return False
    if isinstance(target, list):
        return isinstance(current, list) and [str(x) for x in current] == [str(x) for x in target]
    return str(current if current is not None else "") == str(target if target is not None else "")


def _profiles_map(profiles):
    return {str(p.get("name")): bool(p.get("enabled")) for p in (profiles or []) if isinstance(p, dict)}


def opcua_settings_equal(current, target):
    current = current if isinstance(current, dict) else {}
    diff = {}
    for key, want in target.items():
        have = current.get(key)
        if key == "security_profiles":
            want_map, have_map = _profiles_map(want), _profiles_map(have)
            if any(have_map.get(name) != enabled for name, enabled in want_map.items()):
                diff[key] = have
        elif key == "port":
            if have is None or int(have) != int(want):
                diff[key] = have
        elif bool(have) != bool(want) or have is None:
            diff[key] = have
    return not diff, {k: current.get(k) for k in target}


# ---------------------------------------------------------------------------
# Entscheidung je Request
# ---------------------------------------------------------------------------
def _cert_fingerprint(pem):
    blocks = _pem_blocks(pem)
    return hashlib.sha256("\n".join(blocks).encode()).hexdigest() if blocks else None


def decide_certificate_key_pem(reader, req):
    """certificate_key_pem: Das Gerät liefert nur das Zertifikat zurück (key/password immer null).
    Gleiches Zertifikat -> überspringen; der Key gehört zwingend zum Zertifikat."""
    adr = req["adr"]
    target = ((req.get("data") or {}).get("newvalue") or {})
    target_fp = _cert_fingerprint(target.get("certificate"))
    shown_target = {"certificate_sha256": target_fp}
    ok, current, code = reader.read(adr[: -len("/setdata")] + "/getdata")
    if not ok:
        return _decision("unverified", None, shown_target, f"read_failed:{code}")
    current_fp = _cert_fingerprint((current or {}).get("certificate") if isinstance(current, dict) else None)
    if current_fp and current_fp == target_fp:
        return _decision("skip", {"certificate_sha256": current_fp}, shown_target, "cert_key_unchanged")
    return _decision("write", {"certificate_sha256": current_fp}, shown_target)


def decide_setdata(reader, req):
    adr, data = req["adr"], req.get("data") or {}
    target = data.get("newvalue")
    if adr in ALWAYS_WRITE:
        return _decision("unverified", None, target, "no_read_path")
    if adr.endswith(CERT_KEY_PEM_SUFFIX):
        return decide_certificate_key_pem(reader, req)
    ok, current, code = reader.read(adr[: -len("/setdata")] + "/getdata")
    if not ok:
        return _decision("unverified", None, target, f"read_failed:{code}")
    if "trustedservercertificates" in adr:
        target = normalize_mqtt_trusted_server_certificates(target)
    return _decision("skip" if values_equal(adr, current, target) else "write", current, target)


def decide_status_action(reader, req):
    match = STATUS_ACTION.match(req["adr"])
    want = "running" if match.group("act") == "start" else "stopped"
    ok, current, code = reader.read(match.group("base") + "/status/getdata")
    if not ok or str(current).lower() not in ("running", "stopped"):
        return _decision("unverified", current, want, f"read_failed:{code}" if not ok else "unknown_state")
    return _decision("skip" if str(current).lower() == want else "write", current, want)


def decide_network(reader, req):
    target = req.get("data") or {}
    keys = {"mode": "/network/br0/ipv4/mode/getdata", "gateway": "/network/br0/ipv4/gateway/getdata",
            "address": "/network/br0/ipv4/address0/address/getdata",
            "subnetmask": "/network/br0/ipv4/address0/subnetmask/getdata",
            "staticdnsservers": "/network/br0/ipv4/staticdnsservers/getdata",
            "gateway_mode": "/network/br0/ipv4/gateway_mode/getdata", "dns_mode": "/network/br0/ipv4/dns_mode/getdata"}
    current = {}
    for key, adr in keys.items():
        ok, value, code = reader.read(adr)
        if not ok and (key not in ("gateway_mode", "dns_mode") or key in target):
            return _decision("unverified", None, target, f"read_failed:{code}")
        current[key] = value if ok else None
    shown = {"mode": current["mode"], "gateway": current["gateway"],
             "address": [{"Address": current["address"], "Subnetmask": current["subnetmask"]}],
             "staticdnsservers": current["staticdnsservers"],
             "gateway_mode": current["gateway_mode"], "dns_mode": current["dns_mode"]}
    same = str(current["mode"]) == str(target.get("mode"))
    if same and target.get("mode") == 1:
        addr = (target.get("address") or [{}])[0]
        gw_have = "" if current["gateway"] in (None, "0.0.0.0") else str(current["gateway"])
        same = (str(current["address"]) == str(addr.get("Address")) and str(current["subnetmask"]) == str(addr.get("Subnetmask"))
                and gw_have == str(target.get("gateway") or ""))
    for key in ("gateway_mode", "dns_mode"):
        if same and key in target:
            same = str(current.get(key)) == str(target[key])
    if same and "staticdnsservers" in target:
        same = [str(x) for x in current["staticdnsservers"] or []] == [str(x) for x in target["staticdnsservers"]]
    return _decision("skip" if same else "write", shown, target)


# ---------------------------------------------------------------------------
# Service Monitor
# ---------------------------------------------------------------------------
def monitor_items(reader):
    ok, data, code = reader.read_service(MONITOR_GETITEMS)
    items = (data or {}).get("items") if isinstance(data, dict) else None
    return (ok and isinstance(items, list)), (items or []), code


def _monitor_matches(device_item, target):
    """Gleicher Inhalt; die description vergleicht das Tool nur, wenn das Gerät sie zurückliefert."""
    if normalize_monitor_item(device_item) != normalize_monitor_item(target):
        return False
    if "description" in device_item and str(device_item.get("description") or "") != str(target.get("description") or ""):
        return False
    return True


def decide_monitor_add(reader, req):
    target = req.get("data") or {}
    shown_target = public_monitor_item(target)
    ok, items, code = monitor_items(reader)
    if not ok:
        return _decision("unverified", None, shown_target, f"read_failed:{code}")
    if "id" in target:
        current = next((i for i in items if i.get("id") == target["id"]), None)
        if current is None:
            return _decision("write", None, shown_target, "monitor_new")
        return _decision("skip" if _monitor_matches(current, target) else "write", public_monitor_item(current), shown_target)
    same = next((i for i in items if _monitor_matches(i, target)), None)
    if same is not None:
        return _decision("skip", public_monitor_item(same), shown_target, "monitor_same_content")
    return _decision("write", None, shown_target, "monitor_new")


def monitor_unlisted(items, keep):
    """Geräteeinträge, die weder per ID noch per Inhalt im Profil stehen."""
    keep_ids = {k.get("id") for k in keep if "id" in k}
    return [i for i in items if i.get("id") not in keep_ids and not any(_monitor_matches(i, k) for k in keep)]


def decide_monitor_remove_unlisted(reader, req):
    keep = (req.get("data") or {}).get("keep") or []
    ok, items, code = monitor_items(reader)
    if not ok:
        return _decision("unverified", None, None, f"read_failed:{code}")
    remove = monitor_unlisted(items, keep)
    if not remove:
        return _decision("skip", None, {"remove_ids": []}, "monitor_nothing_to_remove")
    return _decision("write", [public_monitor_item(i) for i in remove], {"remove_ids": [i.get("id") for i in remove]})


def decide_fieldbus_type(reader, req):
    target = FIELDBUS_ENABLE[req["adr"]]
    ok, current, code = reader.read(FIELDBUS_TYPE_STATUS + "/getdata")
    if not ok:
        return _decision("unverified", None, FIELDBUS_TYPES[target][0], f"read_failed:{code}")
    try:
        current = int(current)
    except (TypeError, ValueError):
        return _decision("unverified", current, FIELDBUS_TYPES[target][0], "unknown_value")
    shown = FIELDBUS_TYPES.get(current, (str(current),))[0]
    return _decision("skip" if current == target else "write", shown, FIELDBUS_TYPES[target][0])


def plan_requests(reader, requests):
    """Gibt [(request, decision)] zurück. OPC UA (Stop/Settings/Start) wird als Gruppe entschieden."""
    planned = []
    i = 0
    while i < len(requests):
        req = requests[i]
        adr = req["adr"]
        # OPC-UA-Gruppe: Stop (conditional) -> [Settings] -> [Zertifikat] -> [Start]
        if adr == OPCUA_BASE + "/status/stop" and str(req.get("label", "")).startswith("OPC UA Stop") \
                and i + 1 < len(requests) and requests[i + 1]["adr"] in (OPCUA_SETTINGS_SET, OPCUA_CERT_UPLOAD):
            group = {"stop": req}
            j = i + 1
            for key, group_adr in (("settings", OPCUA_SETTINGS_SET), ("cert", OPCUA_CERT_UPLOAD), ("start", OPCUA_BASE + "/status/start")):
                if j < len(requests) and requests[j]["adr"] == group_adr:
                    group[key] = requests[j]
                    j += 1
            planned.extend(_plan_opcua_group(reader, group))
            i = j
            continue
        if adr == MONITOR_ADD:
            planned.append((req, decide_monitor_add(reader, req)))
        elif adr == MONITOR_REMOVE_UNLISTED:
            planned.append((req, decide_monitor_remove_unlisted(reader, req)))
        elif adr in FIELDBUS_ENABLE:
            planned.append((req, decide_fieldbus_type(reader, req)))
        elif adr == NETWORK_SET:
            planned.append((req, decide_network(reader, req)))
        elif STATUS_ACTION.match(adr):
            planned.append((req, decide_status_action(reader, req)))
        elif adr.endswith("/setdata") and isinstance(req.get("data"), dict) and "newvalue" in req["data"]:
            planned.append((req, decide_setdata(reader, req)))
        else:
            planned.append((req, _decision("unverified", None, req.get("data"), "no_read_path")))
        i += 1
    return planned


def _plan_opcua_group(reader, group):
    """Stop nur wenn nötig und laufend; Start nur bei expliziter Aktion oder wenn der Server vorher lief."""
    ok_r, status, _ = reader.read(OPCUA_STATUS_GET)
    running = str(status).lower() == "running" if ok_r else None
    out_mid = []
    any_change = False

    settings_req = group.get("settings")
    if settings_req:
        target = (settings_req.get("data") or {}).get("value") or {}
        ok_s, current_settings, code_s = reader.read(OPCUA_BASE + "/settings/getdata")
        if not ok_s:
            out_mid.append((settings_req, _decision("unverified", None, target, f"read_failed:{code_s}")))
            any_change = True
        else:
            equal, shown = opcua_settings_equal(current_settings, target)
            out_mid.append((settings_req, _decision("skip" if equal else "write", shown, target)))
            any_change |= not equal

    cert_req = group.get("cert")
    if cert_req:
        decision = decide_opcua_certificate(reader, cert_req, running)
        out_mid.append((cert_req, decision))
        any_change |= decision["decision"] != "skip"

    stop_req, start_req = group["stop"], group.get("start")
    explicit = bool(start_req) and start_req.get("label") == "OPC UA Start"
    if not any_change:
        out = [(stop_req, _decision("skip", status, status, "settings_unchanged"))] + out_mid
        if start_req:
            out.append((start_req, _decision("write" if explicit and running is not True else "skip", status,
                                             "running" if explicit else status, "" if explicit else "settings_unchanged")))
        return out
    if running is None:
        out = [(stop_req, _decision("unverified", status, "stopped", "conditional"))] + out_mid
    else:
        out = [(stop_req, _decision("write" if running else "skip", status, "stopped", "" if running else "already_stopped"))] + out_mid
    if start_req:
        # Ohne explizite Start-Aktion den vorherigen Zustand wiederherstellen.
        if explicit or running or running is None:
            out.append((start_req, _decision("write", "stopped", "running")))
        else:
            out.append((start_req, _decision("skip", status, status, "keep_stopped")))
    return out


def decide_opcua_certificate(reader, req, running):
    """Vergleich über das vom laufenden Server ausgelieferte Zertifikat (OPC UA GetEndpoints)."""
    data = req.get("data") or {}
    try:
        target = base64.b64decode(data.get("certificate_value") or "")
    except Exception:
        target = b""
    target_fp = hashlib.sha256(target).hexdigest()
    shown_target = {"sha256": target_fp}
    if not running:
        return _decision("unverified", None, shown_target, "opcua_cert_not_running")
    current = reader.opcua_certificate()
    if current is None:
        return _decision("unverified", None, shown_target, "opcua_cert_not_readable")
    current_fp = hashlib.sha256(current).hexdigest()
    return _decision("skip" if current_fp == target_fp else "write", {"sha256": current_fp}, shown_target)
