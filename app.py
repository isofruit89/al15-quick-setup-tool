from flask import Flask, request, jsonify, render_template, Response, stream_with_context
import base64
import json
import hashlib
import os
import shutil
import sys
import subprocess
import tempfile
import time
import re
import zlib
from pathlib import Path
from urllib.parse import urlsplit

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

from service_definitions import (
    build_password_change_request,
    build_device_tags_requests,
    build_network_requests,
    build_ntp_requests,
    build_nodered_requests,
    build_auth_enabled_requests,
    build_http_requests,
    build_opcua_requests,
    build_mqtt_client_requests,
    build_mqtt_command_channel_requests,
    build_port_configuration_requests,
)

urllib3.disable_warnings(InsecureRequestWarning)
app = Flask(__name__)

APP_VERSION = "1.7"

SOURCE_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", SOURCE_DIR))
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else SOURCE_DIR
BASE_DIR = APP_DIR
PREBUILT_PALETTE_DIR = RESOURCE_DIR / "prebuilt_palettes"
PROFILE_DIR = APP_DIR / "profiles"
EXPORT_DIR = APP_DIR / "exports"
PROFILE_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)
PALETTE_DIR = APP_DIR / "palettes"
PALETTE_DIR.mkdir(exist_ok=True)

TIMEOUT = 90
IODD_COPY_ADR = "/ioddmanager/copy_iodd"
IODD_MAX_BYTES = int(os.getenv("AL15_IODD_MAX_BYTES", str(10 * 1024 * 1024)))


ORDER_GROUPS = [
    "device_tags", "port_configuration", "system_ntp", "system_nodered", "system_security",
    "connections_http", "connections_opcua", "connections_mqtt_client",
    "connections_mqtt_command_channel",
    # Immer zuletzt ausführen
    "network",
]

# Profilschema v2 ("Keine Aktion" pro Klasse und Parameter) und Migration alter Profile
from messages import LocalizedError, error_text, msg
# Node-RED (Paletten, Flows) und Offline-Paketierung von Paletten
from nodered import (
    NODERED_DEPLOYMENT_TYPE, validate_palette_files, palette_details, build_palette_preview, install_node_red_palette,
    validate_flow_files, publish_node_red_flows, build_flow_preview,
)
from palette_packager import (
    repair_runtime_resolution, update_bundled_dependencies, direct_archive_name, create_direct_archive, validate_packed_archive,
)
from profile_schema import DEFAULT_PROFILE, migrate_profile, effective_profile
# Zurücklesen vor dem Schreiben (nur notwendige Änderungen senden)
from readback import DeviceReader, plan_requests
from opcua_client import get_server_certificate
from service_definitions import OPCUA_CERT_ADR


def get_lang(default="de"):
    lang = request.args.get("lang") or request.headers.get("X-UI-Lang") or default
    if request.is_json:
        lang = (request.get_json(silent=True) or {}).get("lang") or lang
    return "en" if str(lang).lower().strip().startswith("en") else "de"


WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def safe_name(name, fallback="quick_setup_profile"):
    """Dateisicherer Profilname: Leerzeichen -> _, nur Buchstaben (auch Umlaute), Ziffern, _ - . erlaubt."""
    value = re.sub(r"\s+", "_", str(name or "").strip())
    value = "".join(ch for ch in value if ch.isalnum() or ch in ("_", "-", "."))
    value = re.sub(r"_{2,}", "_", value).strip("._")[:80]
    if value.split(".")[0].upper() in WINDOWS_RESERVED_NAMES:
        value += "_"
    return value or fallback


def b64(value):
    return base64.b64encode(str(value).encode()).decode()


def build_auth(user, password):
    return {"user": b64(user), "passwd": b64(password)} if user and password else None


def make_payload(adr, user, password, data=None, top_level=False):
    payload = {"code": "request", "cid": 1, "adr": adr}
    if data is not None:
        payload["data"] = data
    auth = build_auth(user, password)
    if auth:
        if top_level:
            payload["user"], payload["passwd"] = auth["user"], auth["passwd"]
        else:
            payload["auth"] = auth
    return payload


def rpc_post(ip, payload):
    response = requests.post(ip.rstrip("/") + "/rpc", json=payload, timeout=TIMEOUT, verify=False)
    response.raise_for_status()
    return response.json()


def validate_iodd_files(profile):
    files = ((profile.get("iodd") or {}).get("files") or [])
    if not isinstance(files, list): raise LocalizedError("iodd_list")
    for item in files:
        if not isinstance(item, dict): raise LocalizedError("iodd_entry")
        name, content = Path(str(item.get("name") or "")).name, item.get("content_base64") or ""
        if not name or not content: raise LocalizedError("iodd_missing")
        if not name.lower().endswith(".zip"): raise LocalizedError("iodd_type", name=name)
        try: raw = base64.b64decode(content, validate=True)
        except Exception as exc: raise LocalizedError("base64_invalid", name=name) from exc
        if len(raw) > IODD_MAX_BYTES: raise LocalizedError("iodd_size", name=name)
    return files


def iodd_details(item):
    filename = Path(str(item.get("name") or "")).name
    raw = base64.b64decode(item.get("content_base64") or "", validate=True)
    return filename, raw, zlib.crc32(raw) & 0xFFFFFFFF


def build_iodd_rpc_payload(username, password, item):
    filename, raw, crc32_value = iodd_details(item)
    return {"code": 10, "cid": 1, "adr": IODD_COPY_ADR,
            "auth": {"user": b64(username), "passwd": b64(password)},
            "data": {"filename": filename, "crc32": crc32_value, "value": base64.b64encode(raw).decode()}}


def upload_iodd(ip, username, password, item):
    response = requests.post(ip.rstrip("/"), json=build_iodd_rpc_payload(username, password, item), timeout=TIMEOUT, verify=False)
    response.raise_for_status()
    try: return response.json()
    except ValueError: return {"code": response.status_code, "data": {"msg": response.text[:500]}}


def build_iodd_preview(profile):
    rows = []
    for item in validate_iodd_files(profile):
        filename, raw, crc32_value = iodd_details(item)
        rows.append({"section": "iodd", "label": "IODD Upload: " + filename, "adr": IODD_COPY_ADR,
                     "data": {"filename": filename, "sizeBytes": len(raw), "crc32": crc32_value, "value": "*** embedded IODD data ***"}, "auth_mode": "auth"})
    return rows


def sync_asset_directories(profile_name, profile):
    iodd_files, flow_files, palette_files = validate_iodd_files(profile), validate_flow_files(profile), validate_palette_files(profile)
    for root in (PROFILE_DIR, EXPORT_DIR):
        project = root / profile_name
        if project.exists(): shutil.rmtree(project)
        iodd_dir, flow_dir, palette_dir = project / "iodd", project / "flows", project / "palettes"
        iodd_dir.mkdir(parents=True, exist_ok=True)
        flow_dir.mkdir(parents=True, exist_ok=True)
        palette_dir.mkdir(parents=True, exist_ok=True)
        for item in iodd_files:
            filename, raw, _ = iodd_details(item)
            (iodd_dir / filename).write_bytes(raw)
        for item in flow_files:
            filename = Path(str(item.get("name") or "")).name
            (flow_dir / filename).write_text(json.dumps(item.get("content_json"), indent=2, ensure_ascii=False), encoding="utf-8")
        for item in palette_files:
            filename, raw = palette_details(item)
            (palette_dir / filename).write_bytes(raw)


def remove_profile_assets(profile_name):
    for root in (PROFILE_DIR, EXPORT_DIR):
        directory = root / profile_name
        if directory.exists(): shutil.rmtree(directory)


def compile_requests(profile):
    out = []
    # Klassen mit "Keine Aktion" (apply = false) erzeugen keine Requests.
    profile = effective_profile(profile)

    for section in ORDER_GROUPS:
        data = profile.get(section, {}) or {}

        if section == "device_tags":
            reqs = build_device_tags_requests(data)
        elif section == "port_configuration":
            reqs = build_port_configuration_requests(data)
        elif section == "system_ntp":
            reqs = build_ntp_requests(data)
        elif section == "system_nodered":
            reqs = build_nodered_requests(data)
        elif section == "system_security":
            reqs = build_auth_enabled_requests({"enabled": data.get("credentials_enabled")})
        elif section == "connections_http":
            reqs = build_http_requests(data)
        elif section == "connections_opcua":
            reqs = build_opcua_requests(data)
        elif section == "connections_mqtt_client":
            reqs = build_mqtt_client_requests(data)
        elif section == "connections_mqtt_command_channel":
            reqs = build_mqtt_command_channel_requests(data)
        elif section == "network":
            reqs = build_network_requests(data)
        else:
            reqs = []

        for req in reqs:
            entry = {
                "section": section,
                "label": req.label,
                "adr": req.adr,
                "auth_mode": req.auth_mode,
            }
            if req.data is not None:
                entry["data"] = req.data
            out.append(entry)

    # Doppelte Absicherung: Network bleibt selbst dann am Ende,
    # wenn ORDER_GROUPS später versehentlich geändert wird.
    other_requests = [r for r in out if r.get("section") != "network"]
    network_requests = [r for r in out if r.get("section") == "network"]
    return other_requests + network_requests

OPCUA_STATUS_ADR = "/connections/opcua_server/status/getdata"
OPCUA_STOP_ADR = "/connections/opcua_server/status/stop"
HTTP_ALLOWED_SERVICES_ADR = "/connections/httpserver0/httpserver/allowed_services/setdata"


def is_success_code(code, adr=None): return str(code) == "200" or (adr == HTTP_ALLOWED_SERVICES_ADR and str(code) == "230")
def is_opcua_conditional_stop(req): return req.get("adr") == OPCUA_STOP_ADR and str(req.get("label", "")).startswith("OPC UA Stop")

def read_opcua_server_status(ip, username, password):
    resp = rpc_post(ip, make_payload(OPCUA_STATUS_ADR, username, password))
    return str(((resp.get("data") or {}).get("value") or "")).lower().strip(), resp


def make_factory_password_change_payload(username, current_password, new_password):
    return {"code": "request", "cid": 1, "adr": "/security/password/setdata", "data": {"newvalue": b64(new_password)}, "auth": {"user": b64(username), "passwd": b64(current_password)}}


# ---------------------------------------------------------------------------
# Vorprüfung (Erreichbarkeit, Werkszustand, Anmeldung, Geräteidentität)
# Grundlage: al1590_description.yaml (runtime_contract.device_identity,
# authentication.factory_state) und Live-Test am AL1590 (FW 1.7.0.2):
# /getidentity antwortet ohne Login und meldet im Werkszustand
# security.passwordstatus = "must_change".
# ---------------------------------------------------------------------------
FACTORY_PASSWORD = "password"
PRECHECK_TIMEOUT = (5, 15)  # (connect, read) in Sekunden
PRODUCT_PATTERN = re.compile(r"^AL159\d$", re.IGNORECASE)
MIN_FIRMWARE = (1, 7)
REFERENCE_FIRMWARE = "1.7.0.2"
IDENTITY_PATHS = {
    "product": "/deviceinfo/productcode/getdata",
    "firmware": "/software/firmware/version/getdata",
    "serial": "/deviceinfo/serialnumber/getdata",
}


def normalize_device_url(ip):
    value = str(ip or "").strip()
    if not value:
        raise LocalizedError("host_missing")
    if "://" not in value:
        value = "https://" + value
    return value.rstrip("/")


def precheck_rpc(ip, adr, username=None, password=None):
    response = requests.post(ip.rstrip("/") + "/rpc", json=make_payload(adr, username, password), timeout=PRECHECK_TIMEOUT, verify=False)
    response.raise_for_status()
    return response.json()


def rpc_value(resp):
    if str((resp or {}).get("code", "")) != "200":
        return None
    data = resp.get("data")
    return data.get("value") if isinstance(data, dict) else data


def parse_firmware(value):
    return tuple(int(x) for x in re.findall(r"\d+", str(value or ""))[:4])


def _check(result, key, level, value, lang, code=200):
    """level: ok | error | warning | info"""
    status_key = {"ok": "status_ok", "error": "status_error", "warning": "status_warning", "info": "status_info"}[level]
    row = {"key": key, "level": level, "path": msg("pc_prefix", lang) + " → " + msg("pc_" + key, lang),
           "value": value, "code": code, "status": msg(status_key, lang)}
    result["checks"].append(row)
    if level == "error":
        result["errors"].append(value)
    elif level == "warning":
        result["warnings"].append(value)
    return row


def check_device_identity(ip, username, password, lang, result):
    """Produkt, Firmware und Seriennummer lesen (nur mit gültiger Anmeldung möglich)."""
    identity = result["identity"]
    values = {}
    for item, adr in IDENTITY_PATHS.items():
        try:
            resp = precheck_rpc(ip, adr, username, password)
        except Exception as exc:
            resp = {"code": 500, "error": str(exc)[:300]}
        value = rpc_value(resp)
        if value in (None, ""):
            _check(result, item, "error", msg("precheck_identity_read_failed", lang, item=msg("pc_" + item, lang), response=resp), lang, resp.get("code", 500))
        values[item] = value
    product, firmware, serial = values.get("product"), values.get("firmware"), values.get("serial")
    if product:
        identity["product"] = str(product)
        if PRODUCT_PATTERN.match(str(product).strip()):
            _check(result, "product", "ok", str(product), lang)
        else:
            _check(result, "product", "error", msg("precheck_wrong_product", lang, name=product), lang, 412)
    if firmware:
        identity["firmware"] = str(firmware)
        fw = parse_firmware(firmware)
        if fw[:2] < MIN_FIRMWARE:
            _check(result, "firmware", "error", msg("precheck_firmware_too_old", lang, value=firmware, minimum=".".join(map(str, MIN_FIRMWARE))), lang, 412)
        elif fw != parse_firmware(REFERENCE_FIRMWARE):
            _check(result, "firmware", "warning", msg("precheck_firmware_unverified", lang, value=firmware, ref=REFERENCE_FIRMWARE), lang)
        else:
            _check(result, "firmware", "ok", str(firmware), lang)
    if serial:
        serial = str(serial).strip()
        known = identity.get("serial")
        if known and known != serial:
            _check(result, "serial", "error", msg("precheck_serial_mismatch", lang, a=known, b=serial), lang, 412)
        else:
            identity["serial"] = serial
            _check(result, "serial", "ok", serial, lang)
    return result


def device_precheck(ip, username, password, new_password="", confirm="", lang="de"):
    """Prüft, ob das Gerät erreichbar ist, ob es im Werkszustand ist, ob die Anmeldung
    funktioniert und ob Produkt/Firmware passen. Schreibt nichts auf das Gerät."""
    result = {"ok": False, "reachable": False, "factory_state": None, "auth_ok": False, "mode": None,
              "identity": {}, "checks": [], "errors": [], "warnings": []}
    # 1) Erreichbarkeit + Werkszustand über /getidentity (ohne Anmeldung)
    try:
        ident = precheck_rpc(ip, "/getidentity")
    except Exception as exc:
        _check(result, "reachable", "error", msg("precheck_unreachable", lang, host=ip), lang, 503)
        result["error_detail"] = str(exc)[:300]
        return result
    data = ident.get("data") if isinstance(ident.get("data"), dict) else {}
    name = str((data.get("iot") or {}).get("name") or "")
    if str(ident.get("code", "")) != "200" or not name:
        _check(result, "reachable", "error", msg("precheck_unexpected", lang, response=str(ident)[:300]), lang, ident.get("code", 500))
        return result
    result["reachable"] = True
    identity = result["identity"]
    identity["hostname"] = name
    match = re.match(r"^ifm-(AL\d{4})-(\d{12})$", name, re.IGNORECASE)
    if match:
        identity["product_hint"], identity["serial"] = match.group(1).upper(), match.group(2)
    _check(result, "reachable", "ok", msg("precheck_reachable", lang, name=name), lang)
    if identity.get("product_hint") and not PRODUCT_PATTERN.match(identity["product_hint"]):
        _check(result, "device", "error", msg("precheck_wrong_product", lang, name=name), lang, 412)
        return result

    status = str((data.get("security") or {}).get("passwordstatus") or "").strip().lower()
    identity["passwordstatus"] = status or None
    if status == "must_change":
        result["factory_state"] = True
        _check(result, "factory", "info", msg("precheck_factory", lang), lang)
    elif status:
        result["factory_state"] = False
        _check(result, "factory", "ok", msg("precheck_not_factory", lang, status=status), lang)
    else:
        _check(result, "factory", "warning", msg("precheck_factory_unknown", lang), lang)

    # 2) Werkszustand: nur das neue Passwort prüfen (alles außer getidentity antwortet 401)
    if result["factory_state"]:
        if password and password != FACTORY_PASSWORD:
            _check(result, "auth", "info", msg("precheck_factory_password_ignored", lang), lang)
        _check_new_password(result, new_password, confirm, lang)
        result["mode"] = "factory_password_change"
        result["ok"] = not result["errors"]
        return result

    # 3) Anmeldung mit den eingegebenen Zugangsdaten
    if not password:
        _check(result, "auth", "error", msg("precheck_password_missing", lang), lang, 401)
        return result
    try:
        auth = precheck_rpc(ip, "/devicetag/applicationtag/getdata", username, password)
    except Exception as exc:
        _check(result, "auth", "error", msg("precheck_auth_unexpected", lang, response=str(exc)[:300]), lang, 500)
        return result
    code = str(auth.get("code", ""))
    if code == "401":
        if result["factory_state"] is None and password == FACTORY_PASSWORD:
            # Ältere Firmware ohne passwordstatus: Verhalten laut YAML (401 = Werkszustand ODER falsches Passwort)
            _check(result, "auth", "warning", msg("precheck_auth_ambiguous", lang), lang, 401)
            _check_new_password(result, new_password, confirm, lang)
            result["mode"] = "factory_password_change"
            result["ok"] = not result["errors"]
            return result
        _check(result, "auth", "error", msg("precheck_auth_failed", lang, user=username), lang, 401)
        return result
    if code != "200":
        _check(result, "auth", "error", msg("precheck_auth_unexpected", lang, response=str(auth)[:300]), lang, code or 500)
        return result
    result["auth_ok"] = True
    _check(result, "auth", "ok", msg("precheck_auth_ok", lang, user=username), lang)

    # 4) Geräteidentität (Produkt, Firmware, Seriennummer)
    check_device_identity(ip, username, password, lang, result)
    result["mode"] = "normal_auth"
    result["ok"] = not result["errors"]
    return result


def _check_new_password(result, new_password, confirm, lang):
    if not new_password or not confirm:
        _check(result, "password", "error", msg("factory_apply_need_new_password", lang), lang, 400)
    elif new_password != confirm:
        _check(result, "password", "error", msg("new_password_mismatch", lang), lang, 400)
    elif new_password == FACTORY_PASSWORD:
        _check(result, "password", "error", msg("precheck_new_password_is_factory", lang), lang, 400)
    else:
        _check(result, "password", "ok", msg("precheck_new_password_ok", lang), lang)


def precheck_summary(result, lang):
    ident = result.get("identity") or {}
    if not result.get("ok"):
        return result["errors"][0] if result.get("errors") else msg("precheck_failed", lang)
    if result.get("mode") == "factory_password_change":
        return msg("precheck_ok_factory", lang, name=ident.get("hostname", ""))
    return msg("precheck_ok", lang, name=ident.get("hostname", ""), product=ident.get("product", "?"), firmware=ident.get("firmware", "?"))


@app.route("/")
def index(): return render_template("index.html", app_version=APP_VERSION, default_profile_json=json.dumps(DEFAULT_PROFILE, ensure_ascii=False), default_ip="")


@app.route("/save", methods=["POST"])
def save_profile():
    try:
        profile = migrate_profile(request.json or {}); name = safe_name(profile.get("name")); profile["name"] = name
        validate_iodd_files(profile); validate_palette_files(profile); validate_flow_files(profile)
        active = effective_profile(profile)
        export_preview = [public_request(r) for r in compile_requests(active)] + build_iodd_preview(active) + build_palette_preview(active) + build_flow_preview(active)
        (PROFILE_DIR / f"{name}.json").write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
        (EXPORT_DIR / f"{name}_requests.json").write_text(json.dumps(export_preview, indent=2, ensure_ascii=False), encoding="utf-8")
        sync_asset_directories(name, profile)
        return jsonify({"ok": True, "name": name, "requests_count": len(export_preview)})
    except Exception as exc: return jsonify({"ok": False, "error": error_text(exc, get_lang())}), 400


@app.route("/profiles", methods=["GET"])
def list_profiles(): return jsonify({"ok": True, "profiles": sorted(p.stem for p in PROFILE_DIR.glob("*.json"))})


@app.route("/profiles/load/<name>", methods=["GET"])
def load_profile(name):
    file = PROFILE_DIR / f"{safe_name(name)}.json"
    if not file.exists(): return jsonify({"ok": False, "error": msg("profile_not_found", get_lang())}), 404
    return jsonify({"ok": True, "config": migrate_profile(json.loads(file.read_text(encoding="utf-8")))})


@app.route("/profiles/delete/<name>", methods=["DELETE"])
def delete_profile(name):
    name = safe_name(name); file = PROFILE_DIR / f"{name}.json"; export = EXPORT_DIR / f"{name}_requests.json"
    if not file.exists(): return jsonify({"ok": False, "error": msg("profile_not_found", get_lang())}), 404
    file.unlink()
    if export.exists(): export.unlink()
    remove_profile_assets(name)
    return jsonify({"ok": True, "name": name})


@app.route("/profiles/copy/<name>", methods=["POST"])
def copy_profile(name):
    source_name = safe_name(name); source = PROFILE_DIR / f"{source_name}.json"
    if not source.exists(): return jsonify({"ok": False, "error": msg("profile_not_found", get_lang())}), 404
    body = request.json or {}
    new_name = safe_name(body.get("new_name"), f"{source_name}_copy")
    if (PROFILE_DIR / f"{new_name}.json").exists() and not body.get("overwrite"):
        return jsonify({"ok": False, "exists": True, "name": new_name, "error": msg("profile_exists", get_lang(), name=new_name)}), 409
    profile = migrate_profile(json.loads(source.read_text(encoding="utf-8"))); profile["name"] = new_name
    validate_iodd_files(profile); validate_palette_files(profile); validate_flow_files(profile)
    active = effective_profile(profile)
    export_preview = [public_request(r) for r in compile_requests(active)] + build_iodd_preview(active) + build_palette_preview(active) + build_flow_preview(active)
    (PROFILE_DIR / f"{new_name}.json").write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    (EXPORT_DIR / f"{new_name}_requests.json").write_text(json.dumps(export_preview, indent=2, ensure_ascii=False), encoding="utf-8")
    sync_asset_directories(new_name, profile)
    return jsonify({"ok": True, "name": new_name, "requests_count": len(export_preview)})


@app.route("/preview", methods=["POST"])
def preview():
    try:
        p = effective_profile(request.json or {}); return jsonify({"ok": True, "requests": [public_request(r) for r in compile_requests(p)] + build_iodd_preview(p) + build_palette_preview(p) + build_flow_preview(p)})
    except Exception as exc: return jsonify({"ok": False, "error": error_text(exc, get_lang())}), 400


@app.route("/deploy/connect", methods=["POST"])
def deploy_connect():
    lang = get_lang()
    try:
        body = request.json or {}; ip = normalize_device_url(body.get("ip")); username = body.get("username") or "admin"; password = body.get("password") or ""
        result = device_precheck(ip, username, password, body.get("new_password") or "", body.get("confirm_new_password") or "", lang)
        summary = precheck_summary(result, lang)
        # HTTP 200 auch bei negativem Ergebnis: das Ergebnis steht strukturiert in "precheck".
        return jsonify({"ok": result["ok"], "mode": result["mode"], "message": summary, "error": None if result["ok"] else summary,
                        "precheck": result, "result": {"code": 200 if result["ok"] else "PRECHECK", "message": summary}})
    except Exception as exc: return jsonify({"ok": False, "error": error_text(exc, get_lang())}), 500


@app.route("/config/dry-run", methods=["POST"])
def dry_run():
    try:
        lang = get_lang(); body = request.json or {}; rows = []
        if body.get("new_password"): rows.append({"section": "password_change", "label": msg("dryrun_password_change_label", lang), "adr": "/security/password/setdata", "data": msg("masked", lang), "auth_mode": "top_level"})
        config = effective_profile(body.get("config", {}))

        compiled_requests = compile_requests(config)
        regular_requests = [r for r in compiled_requests if r.get("section") != "network"]
        network_requests = [r for r in compiled_requests if r.get("section") == "network"]

        # Optional: Ist-Werte vom Gerät lesen (nur lesend; im Werkszustand nicht möglich).
        planned, info = None, None
        if body.get("readback") and body.get("ip"):
            ip = normalize_device_url(body.get("ip")); username = body.get("username") or "admin"; password = body.get("password") or ""
            pre = device_precheck(ip, username, password, body.get("new_password") or "", body.get("confirm_new_password") or "", lang)
            if pre["ok"] and pre["mode"] == "normal_auth":
                planned = plan_requests(make_reader(ip, username, password), regular_requests + network_requests)
                info = msg("dryrun_with_device", lang, name=pre["identity"].get("hostname", ""), **plan_summary(planned))
            elif pre.get("factory_state") or pre.get("mode") == "factory_password_change":
                info = msg("dryrun_factory", lang)
            else:
                info = msg("dryrun_offline", lang, reason=precheck_summary(pre, lang))
        decisions = [d for _, d in planned] if planned else [None] * len(compiled_requests)

        def with_decision(req, decision):
            row = public_request(req)
            if decision and req["adr"] in SECRET_SETDATA:
                decision = dict(decision, target="*** masked ***")
            if decision:
                row.update({"decision": decision["decision"], "status": decision_status(decision, lang), "current": decision.get("current"),
                            "target": decision.get("target"), "reason": decision_reason(decision, lang)})
            else:
                row["status"] = msg("status_planned", lang)
            return row

        rows += (
            [with_decision(r, d) for r, d in zip(regular_requests, decisions)]
            + [dict(r, status=msg("status_planned", lang)) for r in build_iodd_preview(config) + build_palette_preview(config, body.get("ip")) + build_flow_preview(config, body.get("ip"))]
            + [with_decision(r, d) for r, d in zip(network_requests, decisions[len(regular_requests):])]
        )
        return jsonify({"ok": True, "preview": rows, "info": info, "readback": planned is not None})
    except Exception as exc: return jsonify({"ok": False, "error": error_text(exc, get_lang())}), 400


def prepare_active_password(ip, username, password, new_password, confirm, lang, results, factory_state=False):
    active = password
    if factory_state:
        if not new_password or not confirm: raise ValueError(msg("factory_apply_need_new_password", lang))
        if new_password != confirm: raise ValueError(msg("new_password_mismatch", lang))
        if new_password == FACTORY_PASSWORD: raise ValueError(msg("precheck_new_password_is_factory", lang))
        resp = rpc_post(ip, make_factory_password_change_payload(username, FACTORY_PASSWORD, new_password))
        results.append({"path": msg("password_change_path", lang), "value": msg("masked", lang), "code": resp.get("code", ""), "request_adr": "/security/password/setdata", "request_data": msg("masked", lang), "response": resp})
        if str(resp.get("code", "")) != "200": raise RuntimeError(msg("factory_password_change_failed", lang, response=resp))
        active = new_password
    elif new_password and confirm and new_password == confirm and new_password != password:
        req = build_password_change_request(new_password); resp = rpc_post(ip, make_payload(req.adr, username, password, req.data))
        results.append({"path": msg("password_change_path", lang), "value": msg("masked", lang), "code": resp.get("code", ""), "request_adr": req.adr, "request_data": msg("masked", lang), "response": resp})
        if str(resp.get("code", "")) != "200": raise RuntimeError(msg("password_change_failed", lang, response=resp))
        active = new_password
    return active


def precheck_rows(pre):
    return [{"path": c["path"], "value": c["value"], "code": c["code"], "status": c["status"],
             "warning": c["level"] == "warning", "precheck": True, "request_adr": None, "request_data": None}
            for c in pre.get("checks", [])]


def run_apply_precheck(ip, username, body, lang, results):
    """Serverseitige Vorprüfung vor jeder Übertragung.
    Gibt (aktives Passwort, Fehlermeldung) zurück; alle Prüfzeilen landen in results."""
    password = body.get("password") or ""
    new_password = body.get("new_password") or ""
    confirm = body.get("confirm_new_password") or ""
    pre = device_precheck(ip, username, password, new_password, confirm, lang)
    results.extend(precheck_rows(pre))
    if not pre["ok"]:
        return None, precheck_summary(pre, lang)
    expected = str(body.get("expected_serial") or "").strip()
    found = str(pre["identity"].get("serial") or "")
    if expected and found and expected != found:
        error = msg("precheck_device_changed", lang, expected=expected, found=found)
        results.append({"path": msg("pc_prefix", lang) + " → " + msg("pc_serial", lang), "value": error, "code": 409,
                        "status": msg("status_error", lang), "precheck": True, "request_adr": None, "request_data": None})
        return None, error
    factory = pre["mode"] == "factory_password_change"
    active = prepare_active_password(ip, username, password, new_password, confirm, lang, results, factory_state=factory)
    if factory:
        # Im Werkszustand sind Produkt und Firmware erst nach dem Passwortwechsel lesbar.
        post = {"identity": dict(pre["identity"]), "checks": [], "errors": [], "warnings": []}
        check_device_identity(ip, username, active, lang, post)
        results.extend(precheck_rows(post))
        if post["errors"]:
            return None, post["errors"][0]
    return active, None


def execute_config_request(ip, username, password, req):
    rows = []
    if is_opcua_conditional_stop(req):
        status_value, status_resp = read_opcua_server_status(ip, username, password)
        rows.append({"path": "OPC UA Status Check → " + OPCUA_STATUS_ADR, "value": status_value or status_resp, "code": status_resp.get("code", ""), "request_adr": OPCUA_STATUS_ADR, "request_data": None, "response": status_resp})
        if status_value != "running":
            rows.append({"path": req["label"] + " → " + req["adr"], "value": "skipped - OPC UA server is not running", "code": 200, "request_adr": req["adr"], "request_data": req.get("data"), "response": {"code": 200, "message": "Skipped because OPC UA server status is not running", "opcua_status": status_value}})
            return rows
    resp = rpc_post(ip, make_payload(req["adr"], username, password, req.get("data"), top_level=(req.get("auth_mode") == "top_level")))
    if req["adr"] == OPCUA_CERT_ADR and opcua_pki_missing(resp):
        # Verifiziert am AL1590: Vor dem ersten Start des OPC-UA-Servers fehlt der PKI-Ordner
        # (Code 550 "Could not find a part of the path"). Einmal starten + stoppen, dann erneut hochladen.
        rows.append(public_request({"path": req["label"] + " (PKI fehlt, wird angelegt) → " + req["adr"], "value": req.get("data"), "code": 200,
                                    "request_adr": req["adr"], "request_data": req.get("data"), "response": resp}))
        rows.extend(initialize_opcua_pki(ip, username, password))
        resp = rpc_post(ip, make_payload(req["adr"], username, password, req.get("data")))
    rows.append(public_request({"path": req["label"] + " → " + req["adr"], "value": req.get("data"), "code": resp.get("code", ""), "request_adr": req["adr"], "request_data": req.get("data"), "response": resp}))
    return rows


def opcua_pki_missing(resp):
    return str(resp.get("code")) == "550" and "Could not find a part of the path" in json.dumps(resp)


def initialize_opcua_pki(ip, username, password, timeout_s=30):
    """OPC-UA-Server einmal starten (legt die PKI an) und wieder stoppen."""
    rows = []
    for action in ("start", "stop"):
        adr = f"/connections/opcua_server/status/{action}"
        resp = rpc_post(ip, make_payload(adr, username, password))
        rows.append({"path": f"OPC UA PKI anlegen ({action}) → {adr}", "value": None, "code": resp.get("code", ""), "request_adr": adr, "request_data": None, "response": resp})
        want = "running" if action == "start" else "stopped"
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            status, _ = read_opcua_server_status(ip, username, password)
            if status == want:
                break
            time.sleep(1)
        if action == "start":
            time.sleep(3)  # Zeit zum Anlegen der PKI-Ordner
    return rows


def make_reader(ip, username, password):
    def opcua_cert(reader):
        ok, settings, _ = reader.read("/connections/opcua_server/settings/getdata")
        port = int((settings or {}).get("port") or 4843) if ok else 4843
        return get_server_certificate(urlsplit(ip).hostname, port)
    return DeviceReader(lambda adr: precheck_rpc(ip, adr, username, password), opcua_cert)


SECRET_SETDATA = {"/connections/mqttcommandchannel/mqttcmdchannel/mqttcmdchannelsetup/password/setdata"}


def public_data(adr, data):
    """Daten für Anzeige, Vorschau und Export: Geheimnisse maskieren."""
    if adr == OPCUA_CERT_ADR and isinstance(data, dict):
        try:
            cert = base64.b64decode(data.get("certificate_value") or "")
        except Exception:
            cert = b""
        return {"certificate_sha256": hashlib.sha256(cert).hexdigest(), "certificate_bytes": len(cert),
                "certificate_crc32": data.get("certificate_crc32"), "private_key_value": "*** masked ***",
                "private_key_crc32": data.get("private_key_crc32")}
    if adr in SECRET_SETDATA and isinstance(data, dict):
        return {"newvalue": "*** masked ***"}
    return data


def public_request(entry):
    out = dict(entry)
    for key in ("data", "request_data", "value"):
        if key in out:
            out[key] = public_data(out.get("adr") or out.get("request_adr"), out[key])
    return out


def decision_reason(decision, lang):
    reason = decision.get("reason") or ""
    if reason.startswith("read_failed:"):
        return msg("rb_read_failed", lang, code=reason.split(":", 1)[1])
    return msg("rb_" + reason, lang) if reason else ""


def decision_status(decision, lang):
    return msg({"skip": "status_unchanged", "write": "status_change", "unverified": "status_unverified"}[decision["decision"]], lang)


def plan_summary(planned):
    counts = {"write": 0, "skip": 0, "unverified": 0}
    for _, decision in planned:
        counts[decision["decision"]] += 1
    return {"change": counts["write"], "skip": counts["skip"], "unverified": counts["unverified"]}


def execute_planned_request(ip, username, password, req, decision, lang):
    """Führt einen Request nur aus, wenn der Ist-Wert abweicht (oder nicht vergleichbar ist)."""
    base = {"current": decision.get("current"), "target": decision.get("target"), "decision": decision["decision"],
            "reason": decision_reason(decision, lang)}
    if req["adr"] in SECRET_SETDATA:
        base.update(current=None, target="*** masked ***")
    if decision["decision"] == "skip":
        return [public_request({"path": req["label"] + " → " + req["adr"], "value": req.get("data"), "code": 200, "skipped": True,
                                "status": msg("status_unchanged", lang), "request_adr": req["adr"], "request_data": req.get("data"), **base})]
    rows = execute_config_request(ip, username, password, req)
    rows[-1].update(base)
    return rows


def deploy_assets(ip, username, password, config, lang, results):
    for item in validate_iodd_files(config):
        filename, _, _ = iodd_details(item); resp = upload_iodd(ip, username, password, item)
        row = {"path": "IODD → " + filename, "value": filename, "code": resp.get("code", ""), "request_adr": IODD_COPY_ADR, "request_data": {"filename": filename}, "response": resp}; results.append(row)
        if str(resp.get("code", "")) != "200": raise RuntimeError(msg("iodd_upload_failed", lang, filename=filename, response=resp))
    for item in validate_palette_files(config):
        filename, _ = palette_details(item); resp = install_node_red_palette(ip, username, password, item)
        palette_ok = str(resp.get("code", "")) == "200"
        results.append({"path":"Node-RED Palette → " + filename,"value":filename,"code":resp.get("code",""),"status":msg("status_ok", lang) if palette_ok else msg("status_warning", lang),"warning":not palette_ok,"request_adr":"/nodes","request_data":{"filename":filename},"response":resp})
        # Option A: a failed palette is recorded as a warning. Remaining palettes,
        # the Node-RED flow and the network configuration are still processed.
    if validate_flow_files(config):
        resp = publish_node_red_flows(ip, username, password, config)
        names = [Path(str(x.get("name") or "")).name for x in validate_flow_files(config)]
        row = {"path": "Node-RED Flow → /flows", "value": names, "code": resp.get("code", ""), "request_adr": "/flows", "request_data": {"files": names, "deploymentType": NODERED_DEPLOYMENT_TYPE}, "response": resp}; results.append(row)
        if str(resp.get("code", "")) != "200": raise RuntimeError(msg("flow_upload_failed", lang, response=resp))


@app.route("/config/apply", methods=["POST"])
def apply_config():
    results = []
    try:
        lang = get_lang(); body = request.json or {}; ip = normalize_device_url(body.get("ip")); username = body.get("username") or "admin"; config = effective_profile(body.get("config", {}))
        validate_iodd_files(config); validate_palette_files(config); validate_flow_files(config)
        active, precheck_error = run_apply_precheck(ip, username, body, lang, results)
        if precheck_error:
            return jsonify({"ok": False, "error": precheck_error, "results": results}), 412
        compiled_requests = compile_requests(config)
        regular_requests = [req for req in compiled_requests if req.get("section") != "network"]
        network_requests = [req for req in compiled_requests if req.get("section") == "network"]
        planned = plan_requests(make_reader(ip, username, active), regular_requests + network_requests)
        decisions = [d for _, d in planned]

        for req, decision in zip(regular_requests, decisions):
            results.extend(execute_planned_request(ip, username, active, req, decision, lang))

        # IODDs und Node-RED-Flows werden vor Network übertragen, weil eine
        # IP-Änderung die bestehende Verbindung zum Gerät unterbrechen kann.
        deploy_assets(ip, username, active, config, lang, results)

        for req, decision in zip(network_requests, decisions[len(regular_requests):]):
            results.extend(execute_planned_request(ip, username, active, req, decision, lang))
        has_error = any(not r.get("warning") and not is_success_code(r.get("code", ""), r.get("request_adr")) for r in results)
        has_warning = any(r.get("warning") for r in results)
        return jsonify({"ok": not has_error, "warning": has_warning, "message": msg("config_done_with_warning", lang) if has_warning and not has_error else msg("config_done", lang), "results": results})
    except Exception as exc: return jsonify({"ok": False, "error": error_text(exc, get_lang()), "results": results}), 500


@app.route("/config/apply_stream", methods=["POST"])
def apply_config_stream():
    lang = get_lang(); body = request.get_json(silent=True) or {}
    def ndjson(obj): return json.dumps(obj, ensure_ascii=False) + "\n"
    @stream_with_context
    def generate():
        results = []
        try:
            ip = normalize_device_url(body.get("ip")); username = body.get("username") or "admin"; config = effective_profile(body.get("config", {}))
            iodd_files, palette_files, flow_files = validate_iodd_files(config), validate_palette_files(config), validate_flow_files(config)
            yield ndjson({"type": "status", "message": msg("stream_started", lang)})
            before = len(results); precheck_error = None
            try:
                active, precheck_error = run_apply_precheck(ip, username, body, lang, results)
            except Exception as exc:
                active, precheck_error = None, error_text(exc, get_lang())
            for row in results[before:]:
                row["type"] = "row"
                row.setdefault("status", msg("status_ok", lang) if str(row.get("code")) == "200" else msg("status_error", lang))
                yield ndjson(row)
            if precheck_error:
                yield ndjson({"type": "done", "ok": False, "error": precheck_error, "results": results}); return
            compiled_requests = compile_requests(config)
            regular_requests = [req for req in compiled_requests if req.get("section") != "network"]
            network_requests = [req for req in compiled_requests if req.get("section") == "network"]
            total = len(compiled_requests) + len(iodd_files) + len(palette_files) + (1 if flow_files else 0)

            # Zurücklesen: Ist-Werte für alle Requests einmalig lesen und Plan bilden.
            yield ndjson({"type": "status", "message": msg("readback_running", lang)})
            planned = plan_requests(make_reader(ip, username, active), regular_requests + network_requests)
            decisions = [d for _, d in planned]
            yield ndjson({"type": "status", "message": msg("readback_summary", lang, **plan_summary(planned))})

            for index, (req, decision) in enumerate(zip(regular_requests, decisions), start=1):
                label, adr = req.get("label") or req.get("section") or "Request", req["adr"]
                yield ndjson({"type": "step_start", "index": index, "total": total, "path": label + " → " + adr, "message": msg("request_running", lang, index=index, total=total, label=label)})
                for row in execute_planned_request(ip, username, active, req, decision, lang):
                    if not row.get("skipped"):
                        row["status"] = msg("status_ok", lang) if is_success_code(row.get("code"), row.get("request_adr")) else msg("status_error", lang)
                    row.update({"type": "row", "index": index, "total": total}); results.append(row); yield ndjson(row)
            for offset, item in enumerate(iodd_files, start=1):
                index = len(regular_requests) + offset; filename, _, _ = iodd_details(item); path = "IODD → " + filename
                yield ndjson({"type": "step_start", "index": index, "total": total, "path": path, "message": msg("iodd_upload_running", lang, index=offset, total=len(iodd_files), filename=filename)})
                try:
                    resp = upload_iodd(ip, username, active, item); code = resp.get("code", "")
                    row = {"type": "row", "index": index, "total": total, "path": path, "value": filename, "code": code, "status": msg("status_ok", lang) if str(code) == "200" else msg("status_error", lang), "request_adr": IODD_COPY_ADR, "request_data": {"filename": filename}, "response": resp}
                except Exception as exc:
                    row = {"type": "row", "index": index, "total": total, "path": path, "value": filename, "code": 500, "status": msg("status_error", lang), "error": error_text(exc, get_lang()), "request_adr": IODD_COPY_ADR, "request_data": {"filename": filename}}
                results.append(row); yield ndjson(row)
                if str(row.get("code", "")) != "200":
                    yield ndjson({"type": "done", "ok": False, "error": msg("iodd_upload_failed", lang, filename=filename, response=row.get("response") or row.get("error") or row), "results": results}); return
            for offset, item in enumerate(palette_files, start=1):
                index = len(regular_requests) + len(iodd_files) + offset; filename, _ = palette_details(item); path = "Node-RED Palette → " + filename
                yield ndjson({"type":"step_start","index":index,"total":total,"path":path,"message":msg("palette_upload_running",lang,index=offset,total=len(palette_files),filename=filename)})
                try:
                    resp=install_node_red_palette(ip,username,active,item); code=resp.get("code","")
                    palette_ok = str(code) == "200"
                    row={"type":"row","index":index,"total":total,"path":path,"value":filename,"code":code,"status":msg("status_ok",lang) if palette_ok else msg("status_warning",lang),"warning":not palette_ok,"request_adr":"/nodes","request_data":{"filename":filename},"response":resp}
                    if resp.get("skipped"):
                        row.update({"skipped": True, "status": msg("status_unchanged", lang), "reason": msg("palette_already_installed", lang, package=resp.get("package"), version=resp.get("version"))})
                except Exception as exc:
                    row={"type":"row","index":index,"total":total,"path":path,"value":filename,"code":500,"status":msg("status_warning",lang),"warning":True,"error":error_text(exc, get_lang()),"request_adr":"/nodes","request_data":{"filename":filename}}
                results.append(row); yield ndjson(row)
                if row.get("warning"):
                    yield ndjson({"type":"status","message":msg("palette_upload_warning",lang,filename=filename)})
                # Option A: do not terminate the stream for an individual palette failure.
            if flow_files:
                index = len(regular_requests) + len(iodd_files) + len(palette_files) + 1; names = [Path(str(x.get("name") or "")).name for x in flow_files]; path = "Node-RED Flow → /flows"
                yield ndjson({"type": "step_start", "index": index, "total": total, "path": path, "message": msg("flow_upload_running", lang, files=", ".join(names))})
                try:
                    resp = publish_node_red_flows(ip, username, active, config); code = resp.get("code", "")
                    row = {"type": "row", "index": index, "total": total, "path": path, "value": names, "code": code, "status": msg("status_ok", lang) if str(code) == "200" else msg("status_error", lang), "request_adr": "/flows", "request_data": {"files": names, "deploymentType": NODERED_DEPLOYMENT_TYPE}, "response": resp}
                    if resp.get("skipped"):
                        row.update({"skipped": True, "status": msg("status_unchanged", lang), "reason": msg("flow_unchanged", lang)})
                except Exception as exc:
                    row = {"type": "row", "index": index, "total": total, "path": path, "value": names, "code": 500, "status": msg("status_error", lang), "error": error_text(exc, get_lang()), "request_adr": "/flows", "request_data": {"files": names}}
                results.append(row); yield ndjson(row)
                if str(row.get("code", "")) != "200":
                    yield ndjson({"type": "done", "ok": False, "error": msg("flow_upload_failed", lang, response=row.get("response") or row.get("error") or row), "results": results}); return
            # Network wird bewusst als letzter Schritt ausgeführt.
            network_start_index = len(regular_requests) + len(iodd_files) + len(palette_files) + (1 if flow_files else 0)
            for offset, (req, decision) in enumerate(zip(network_requests, decisions[len(regular_requests):]), start=1):
                index = network_start_index + offset
                label = req.get("label") or "Network"
                adr = req["adr"]
                path = label + " → " + adr
                yield ndjson({
                    "type": "step_start",
                    "index": index,
                    "total": total,
                    "path": path,
                    "message": msg("request_running", lang, index=index, total=total, label=label),
                })
                for row in execute_planned_request(ip, username, active, req, decision, lang):
                    if not row.get("skipped"):
                        row["status"] = msg("status_ok", lang) if is_success_code(row.get("code"), row.get("request_adr")) else msg("status_error", lang)
                    row.update({"type": "row", "index": index, "total": total})
                    results.append(row)
                    yield ndjson(row)

            has_error = any(not r.get("warning") and not is_success_code(r.get("code", ""), r.get("request_adr")) for r in results if r.get("type") == "row")
            has_warning = any(r.get("warning") for r in results if r.get("type") == "row")
            final_message = msg("config_done_with_error", lang) if has_error else (msg("config_done_with_warning", lang) if has_warning else msg("config_done", lang))
            yield ndjson({"type": "done", "ok": not has_error, "warning": has_warning, "message": final_message, "results": results})
        except Exception as exc: yield ndjson({"type": "done", "ok": False, "error": error_text(exc, get_lang()), "results": results})
    response = Response(generate(), mimetype="application/x-ndjson"); response.headers["Cache-Control"] = "no-cache, no-transform"; response.headers["X-Accel-Buffering"] = "no"; return response


def load_prebuilt_palette_index():
    index_file = PREBUILT_PALETTE_DIR / "index.json"
    if not index_file.exists():
        return {"schemaVersion": "1.0", "packages": []}
    data = json.loads(index_file.read_text(encoding="utf-8-sig"))
    if not isinstance(data.get("packages"), list):
        raise LocalizedError("prebuilt_index")
    return data


def find_prebuilt_palette(package_name, source_version):
    for entry in load_prebuilt_palette_index().get("packages", []):
        if (str(entry.get("name") or "").lower() == str(package_name or "").lower()
                and str(entry.get("sourceVersion") or "") == str(source_version or "")
                and entry.get("released") is True):
            return entry
    return None


def available_prebuilt_versions(package_name):
    return [str(entry.get("sourceVersion"))
            for entry in load_prebuilt_palette_index().get("packages", [])
            if str(entry.get("name") or "").lower() == str(package_name or "").lower()
            and entry.get("released") is True]


def publish_prebuilt_palette(entry):
    filename = Path(str(entry.get("fileName") or "")).name
    manifest_name = Path(str(entry.get("manifestFileName") or (filename + ".manifest.json"))).name
    source = PREBUILT_PALETTE_DIR / filename
    manifest_source = PREBUILT_PALETTE_DIR / manifest_name
    if not source.exists():
        raise LocalizedError("prebuilt_missing", path=source)
    if not manifest_source.exists():
        raise LocalizedError("prebuilt_manifest_missing", path=manifest_source)
    expected_sha = str(entry.get("sha256") or "").lower().strip()
    actual_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        raise LocalizedError("prebuilt_sha_invalid", name=filename)
    if actual_sha != expected_sha:
        raise LocalizedError("prebuilt_sha_mismatch", name=filename, expected=expected_sha, actual=actual_sha)
    manifest = json.loads(manifest_source.read_text(encoding="utf-8-sig"))
    manifest_sha = str(((manifest.get("artifact") or {}).get("sha256") or "")).lower().strip()
    if manifest_sha != actual_sha:
        raise LocalizedError("prebuilt_manifest_sha", name=filename)
    if not bool((manifest.get("integrity") or {}).get("artifactReleased")):
        raise LocalizedError("prebuilt_not_released", name=filename)
    target = PALETTE_DIR / filename
    manifest_target = PALETTE_DIR / manifest_name
    shutil.copy2(source, target)
    shutil.copy2(manifest_source, manifest_target)
    return target, actual_sha, manifest_name


def run_process_stream(command, cwd, timeout_seconds=300):
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    started = __import__("time").monotonic()
    output_lines = []
    while True:
        line = process.stdout.readline() if process.stdout else ""
        if line:
            clean = line.rstrip()
            output_lines.append(clean)
            yield {"type": "log", "message": clean}
        elif process.poll() is not None:
            break
        else:
            if __import__("time").monotonic() - started > timeout_seconds:
                process.kill()
                raise TimeoutError("npm operation timed out")
            __import__("time").sleep(0.2)
    if process.returncode != 0:
        raise RuntimeError("\n".join(output_lines[-40:]) or f"Process failed with code {process.returncode}")

@app.route("/palette-packager/create-stream",methods=["POST"])
def create_palette_package_stream():
    lang=get_lang();body=request.get_json(silent=True) or {};name=str(body.get('package') or '').strip();version=str(body.get('version') or '').strip().rstrip('.')
    def ndjson(x):return json.dumps(x,ensure_ascii=False)+'\n'
    @stream_with_context
    def generate():
        work=None
        try:
            if not re.fullmatch(r'(?:@[A-Za-z0-9._-]+/)?[A-Za-z0-9._-]+',name) or not re.fullmatch(r'[0-9A-Za-z.+_-]+',version):raise ValueError('Ungültiger Paketname oder Version.' if lang=='de' else 'Invalid package name or version.')
            prebuilt=find_prebuilt_palette(name,version)
            if prebuilt:
                total=5
                yield ndjson({'type':'info','key':'packagerStrategy','value':'prebuilt-runtime-payload-wrapper'})
                yield ndjson({'type':'step','step':1,'total':total,'key':'packagerStepPrebuiltFind'})
                yield ndjson({'type':'step','step':2,'total':total,'key':'packagerStepPrebuiltVerify'})
                output,sha,manifest_name=publish_prebuilt_palette(prebuilt)
                yield ndjson({'type':'step','step':3,'total':total,'key':'packagerStepPrebuiltSha'})
                yield ndjson({'type':'log','message':'SHA-256: '+sha})
                yield ndjson({'type':'step','step':4,'total':total,'key':'packagerStepPrebuiltPublish'})
                yield ndjson({'type':'step','step':5,'total':total,'key':'packagerStepSave'})
                yield ndjson({'type':'done','ok':True,'filename':output.name,'size':output.stat().st_size,'dependencies':int(prebuilt.get('runtimeDependencyCount') or 0),'repairs':0,'sha256':sha,'strategy':'prebuilt-runtime-payload-wrapper','artifactVersion':prebuilt.get('artifactVersion'),'manifest':manifest_name})
                return
            if name.lower()=='node-red-contrib-opcua':
                versions=available_prebuilt_versions(name)
                detail=', '.join(versions) if versions else ('keine' if lang=='de' else 'none')
                raise ValueError((f'Für node-red-contrib-opcua {version} liegt kein freigegebenes AL15-Offline-Artefakt vor. Verfügbare Versionen: {detail}') if lang=='de' else (f'No released AL15 offline artifact is available for node-red-contrib-opcua {version}. Available versions: {detail}'))
            npm=npm_executable()
            if not shutil.which('node') or not npm:raise RuntimeError('Node.js und npm fehlen.' if lang=='de' else 'Node.js and npm are missing.')
            work=Path(tempfile.mkdtemp(prefix='al15_palette_'))
            yield ndjson({'type':'step','step':1,'total':7,'key':'packagerStepInit'})
            for e in run_process_stream([npm,'init','-y'],work,90):yield ndjson(e)
            yield ndjson({'type':'step','step':2,'total':7,'key':'packagerStepDownload'})
            for e in run_process_stream([npm,'install',f'{name}@{version}','--save-exact','--omit=dev','--loglevel=info'],work,300):yield ndjson(e)
            source=work/'node_modules'/Path(*name.split('/'));package=work/'package'
            if not source.exists():raise LocalizedError('pack_installed_missing')
            shutil.copytree(source,package);shutil.copytree(work/'node_modules',package/'node_modules');nested=package/'node_modules'/Path(*name.split('/'))
            if nested.exists():shutil.rmtree(nested)
            yield ndjson({'type':'step','step':3,'total':7,'key':'packagerStepRuntimeTest'});_,repairs=repair_runtime_resolution(package)
            for r in repairs:yield ndjson({'type':'log','message':f"Hoisting: {r['package']} {r['version']} -> {r['target']}"})
            yield ndjson({'type':'step','step':4,'total':7,'key':'packagerStepDependencies'});bundled=update_bundled_dependencies(package);yield ndjson({'type':'info','key':'packagerDependenciesFound','value':len(bundled)})
            yield ndjson({'type':'step','step':5,'total':7,'key':'packagerStepPack'});output=PALETTE_DIR/direct_archive_name(package);create_direct_archive(package,output);yield ndjson({'type':'log','message':'Direktes TGZ-Archiv aus der geprüften Arbeitskopie erstellt.' if lang=='de' else 'Direct TGZ archive created from the validated workspace.'})
            yield ndjson({'type':'step','step':6,'total':7,'key':'packagerStepArchiveTest'});validate_packed_archive(output,package)
            yield ndjson({'type':'step','step':7,'total':7,'key':'packagerStepSave'});sha=hashlib.sha256(output.read_bytes()).hexdigest();manifest={'success':True,'package':name,'version':version,'repairs':repairs,'workspaceRuntimeTest':'passed','archiveRuntimeTest':'passed','archiveMethod':'direct-tar-gzip','sha256':sha,'artifact':output.name};output.with_suffix(output.suffix+'.manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8');yield ndjson({'type':'done','ok':True,'filename':output.name,'size':output.stat().st_size,'dependencies':len(bundled),'repairs':len(repairs),'sha256':sha})
        except Exception as exc:yield ndjson({'type':'done','ok':False,'error':error_text(exc, get_lang())})
        finally:
            if work and work.exists():shutil.rmtree(work,ignore_errors=True)
    response=Response(generate(),mimetype='application/x-ndjson');response.headers['Cache-Control']='no-cache, no-transform';response.headers['X-Accel-Buffering']='no';return response

def npm_executable():
    return shutil.which("npm.cmd") or shutil.which("npm")

@app.route("/palette-packager/create", methods=["POST"])
def create_palette_package():
    work_dir = None
    lang = get_lang()
    try:
        body = request.get_json(silent=True) or {}
        package_name = str(body.get("package") or "").strip()
        version = str(body.get("version") or "").strip().rstrip(".")
        if not package_name or not version:
            raise ValueError("Bitte den genauen Namen der Palette und die genaue Version eingeben." if lang == "de" else "Enter the exact palette name and exact version.")
        if not re.fullmatch(r"(?:@[A-Za-z0-9._-]+/)?[A-Za-z0-9._-]+", package_name):
            raise ValueError("Ungültiger npm-Paketname." if lang == "de" else "Invalid npm package name.")
        if not re.fullmatch(r"[0-9A-Za-z.+_-]+", version):
            raise ValueError("Ungültige Versionsangabe." if lang == "de" else "Invalid version.")
        npm_cmd = npm_executable()
        if not shutil.which("node") or not npm_cmd:
            raise RuntimeError("Node.js und npm müssen auf dem PC des Quick-Setup-Tools installiert sein." if lang == "de" else "Node.js and npm must be installed on the Quick-Setup Tool host.")
        work_dir = Path(tempfile.mkdtemp(prefix="al15_palette_"))
        subprocess.run([npm_cmd, "init", "-y"], cwd=work_dir, check=True, capture_output=True, text=True, timeout=TIMEOUT)
        install = subprocess.run([npm_cmd, "install", f"{package_name}@{version}", "--save-exact", "--omit=dev"], cwd=work_dir, check=True, capture_output=True, text=True, timeout=300)
        source = work_dir / "node_modules" / Path(*package_name.split("/"))
        package_dir = work_dir / "package"
        if not source.exists():
            raise RuntimeError("Installiertes Palettenpaket wurde nicht gefunden." if lang == "de" else "The installed palette package was not found.")
        shutil.copytree(source, package_dir)
        shutil.copytree(work_dir / "node_modules", package_dir / "node_modules")
        nested_main = package_dir / "node_modules" / Path(*package_name.split("/"))
        if nested_main.exists(): shutil.rmtree(nested_main)
        package_json_path = package_dir / "package.json"
        package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
        bundled = []
        for child in (package_dir / "node_modules").iterdir():
            if child.name.startswith("@") and child.is_dir():
                bundled.extend(f"{child.name}/{sub.name}" for sub in child.iterdir() if sub.is_dir())
            elif child.is_dir(): bundled.append(child.name)
        package_json["bundledDependencies"] = sorted(bundled)
        package_json_path.write_text(json.dumps(package_json, indent=2, ensure_ascii=False), encoding="utf-8")
        packed = subprocess.run([npm_cmd, "pack", "--pack-destination", str(PALETTE_DIR)], cwd=package_dir, check=True, capture_output=True, text=True, timeout=300)
        filename = Path(packed.stdout.strip().splitlines()[-1]).name
        output_file = PALETTE_DIR / filename
        if not output_file.exists():
            raise RuntimeError("npm pack hat keine TGZ-Datei erzeugt." if lang == "de" else "npm pack did not create a TGZ file.")
        return jsonify({"ok": True, "filename": filename, "size": output_file.stat().st_size, "dependencies": len(bundled)})
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "Zeitüberschreitung bei npm." if lang == "de" else "npm operation timed out."}), 504
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc))[-4000:]
        return jsonify({"ok": False, "error": detail}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": error_text(exc, get_lang())}), 400
    finally:
        if work_dir and work_dir.exists(): shutil.rmtree(work_dir, ignore_errors=True)

@app.route("/palette-packager/files", methods=["GET"])
def list_palette_packages():
    try:
        files = [{"name": p.name, "size": p.stat().st_size} for p in sorted(PALETTE_DIR.glob("*.tgz"), key=lambda x: x.stat().st_mtime, reverse=True)]
        return jsonify({"ok": True, "files": files})
    except Exception as exc:
        return jsonify({"ok": False, "error": error_text(exc, get_lang())}), 500

@app.route("/palette-packager/download/<name>", methods=["GET"])
def download_palette_package(name):
    from flask import send_from_directory
    return send_from_directory(PALETTE_DIR, Path(name).name, as_attachment=True)

@app.errorhandler(404)
def json_not_found(error):
    if request.path.startswith("/palette-packager/"):
        return jsonify({"ok": False, "error": "API-Endpunkt nicht gefunden. Bitte das Quick-Setup-Tool neu starten." if get_lang() == "de" else "API endpoint not found. Restart the Quick-Setup Tool."}), 404
    return error

@app.errorhandler(500)
def json_internal_error(error):
    if request.path.startswith("/palette-packager/"):
        return jsonify({"ok": False, "error": "Interner Serverfehler beim Paletten Packager." if get_lang() == "de" else "Internal server error in the Palette Packager."}), 500
    return error

if __name__ == "__main__":
    print(f"AL15 Quick-Setup-Tool v{APP_VERSION}: http://127.0.0.1:5010")
    app.run(host="127.0.0.1", port=5010, debug=False)
