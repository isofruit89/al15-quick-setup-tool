"""Node-RED auf dem AL15: Paletten installieren und Flows deployen (inkl. Zurücklesen)."""
import base64
import io
import json
import os
import tarfile
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests

from messages import LocalizedError

NODERED_TIMEOUT = 90
PALETTE_UPLOAD_TIMEOUT = (10, 30)
PALETTE_FAST_VERIFY_ATTEMPTS = 3
PALETTE_FAST_VERIFY_INTERVAL = 1
PALETTE_RECOVERY_VERIFY_ATTEMPTS = 30
PALETTE_RECOVERY_VERIFY_INTERVAL = 2
PALETTE_VERIFY_TIMEOUT = 10
FLOW_MAX_BYTES = int(os.getenv("AL15_FLOW_MAX_BYTES", str(5 * 1024 * 1024)))
PALETTE_MAX_BYTES = int(os.getenv("AL15_PALETTE_MAX_BYTES", str(100 * 1024 * 1024)))
NODERED_PORT = int(os.getenv("AL15_NODERED_PORT", "1880"))
NODERED_DEPLOYMENT_TYPE = os.getenv("AL15_NODERED_DEPLOYMENT_TYPE", "full")


# ---------------------------------------------------------------------------
# Verbindung
# ---------------------------------------------------------------------------
def node_red_base_url(master_url):
    parsed = urlsplit(master_url if "://" in master_url else "https://" + master_url)
    if not parsed.hostname:
        raise LocalizedError("flow_host")
    host = f"{parsed.hostname}:{NODERED_PORT}"
    return urlunsplit((parsed.scheme or "https", host, "", "", ""))


def get_node_red_token(base_url, username, password):
    if not username or not password:
        return None
    body = {"client_id": "node-red-admin", "grant_type": "password", "scope": "*", "username": username, "password": password}
    response = requests.post(base_url.rstrip("/") + "/auth/token", data=body, timeout=NODERED_TIMEOUT, verify=False)
    response.raise_for_status()
    token = (response.json() or {}).get("access_token")
    if not token:
        raise LocalizedError("nodered_no_token")
    return token


def _api_headers(token):
    headers = {"Node-RED-API-Version": "v2"}
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


# ---------------------------------------------------------------------------
# Paletten
# ---------------------------------------------------------------------------
def validate_palette_files(profile):
    files = (profile.get("node_red_palettes") or {}).get("files") or []
    if not isinstance(files, list):
        raise LocalizedError("palette_list")
    for item in files:
        if not isinstance(item, dict):
            raise LocalizedError("palette_entry")
        name, content = Path(str(item.get("name") or "")).name, item.get("content_base64") or ""
        if not name or not content or not name.lower().endswith(".tgz"):
            raise LocalizedError("palette_file", name=name)
        try:
            raw = base64.b64decode(content, validate=True)
        except Exception as exc:
            raise LocalizedError("base64_invalid", name=name) from exc
        if len(raw) > PALETTE_MAX_BYTES:
            raise LocalizedError("palette_size", name=name)
    return files


def palette_details(item):
    return Path(str(item.get("name") or "")).name, base64.b64decode(item.get("content_base64") or "", validate=True)


def build_palette_preview(profile, master_url=None):
    target = node_red_base_url(master_url) + "/nodes" if master_url else "<AL15 host>:1880/nodes"
    rows = []
    for item in validate_palette_files(profile):
        filename, raw = palette_details(item)
        rows.append({"section": "node_red_palettes", "label": "Node-RED Palette Install: " + filename, "adr": "/nodes",
                     "data": {"filename": filename, "sizeBytes": len(raw), "target": target}, "auth_mode": "Node-RED token or none"})
    return rows


def palette_package_metadata(filename, raw):
    fallback = Path(filename).name[:-4] if str(filename).lower().endswith(".tgz") else Path(filename).name
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            package_json = json.loads(archive.extractfile("package/package.json").read().decode("utf-8"))
            return str(package_json.get("name") or fallback), str(package_json.get("version") or "")
    except Exception:
        return fallback, ""


def node_modules_from_response(data):
    """Sammelt (name, version) aller Module aus der Antwort von GET /nodes."""
    found = set()

    def walk(value):
        if isinstance(value, dict):
            name = value.get("name") or value.get("module")
            version = value.get("version") or value.get("local")
            if isinstance(name, str):
                found.add((name.lower(), str(version or "")))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)
    return found


def verify_node_red_palette(base_url, name, version="", token=None, attempts=3, interval=1):
    headers = _api_headers(token)
    last = {}
    for attempt in range(1, attempts + 1):
        try:
            r = requests.get(base_url.rstrip("/") + "/nodes", headers=headers, timeout=PALETTE_VERIFY_TIMEOUT, verify=False)
            last = {"attempt": attempt, "http_status": r.status_code}
            if r.status_code == 200:
                for found_name, found_version in node_modules_from_response(r.json()):
                    if found_name == name.lower() and (not version or not found_version or found_version == version):
                        return True, {"attempt": attempt, "installed_version": found_version}
        except Exception as exc:
            last = {"attempt": attempt, "error": str(exc)}
        if attempt < attempts:
            time.sleep(interval)
    return False, last


def install_node_red_palette(master_url, username, password, item):
    filename, raw = palette_details(item)
    name, version = palette_package_metadata(filename, raw)
    base = node_red_base_url(master_url)
    token = None
    try:
        token = get_node_red_token(base, username, password)
    except Exception:
        pass
    headers = _api_headers(token)
    # Zurücklesen: gleiche Palette in gleicher Version bereits installiert -> nicht erneut installieren.
    if version:
        already, detail = verify_node_red_palette(base, name, version, token, attempts=1, interval=0)
        if already and str(detail.get("installed_version") or "") == version:
            return {"code": 200, "skipped": True, "verification": "already_installed", "package": name, "version": version,
                    "message": "Palette already installed.", "verification_detail": detail}
    status, error = None, None
    try:
        r = requests.post(base.rstrip("/") + "/nodes", headers=headers, files={"tarball": (filename, raw, "application/x-compressed")},
                          timeout=PALETTE_UPLOAD_TIMEOUT, verify=False)
        status = r.status_code
        if status not in (200, 201, 204):
            error = r.text[:2000]
    except Exception as exc:
        error = str(exc)
    ok = status in (200, 201, 204)
    attempts = PALETTE_FAST_VERIFY_ATTEMPTS if ok else PALETTE_RECOVERY_VERIFY_ATTEMPTS
    interval = PALETTE_FAST_VERIFY_INTERVAL if ok else PALETTE_RECOVERY_VERIFY_INTERVAL
    installed, detail = verify_node_red_palette(base, name, version, token, attempts, interval)
    if installed or ok:
        return {"code": 200, "http_status": status, "verification": "verified" if installed else "upload_confirmed", "package": name,
                "version": version, "message": "Palette installed.", "verification_detail": detail, "upload_error": error}
    return {"code": status or 500, "http_status": status, "verification": "not_found", "package": name, "version": version,
            "message": error or "Palette not found by GET /nodes.", "verification_detail": detail}


# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------
def normalize_flow_document(value, filename):
    if isinstance(value, list):
        nodes = value
    elif isinstance(value, dict) and isinstance(value.get("flows"), list):
        nodes = value["flows"]
    else:
        raise LocalizedError("flow_structure", name=filename)
    if not all(isinstance(node, dict) for node in nodes):
        raise LocalizedError("flow_nodes", name=filename)
    return nodes


def validate_flow_files(profile):
    files = (profile.get("node_red_flows") or {}).get("files") or []
    if not isinstance(files, list):
        raise LocalizedError("flow_list")
    all_ids = set()
    for item in files:
        if not isinstance(item, dict):
            raise LocalizedError("flow_entry")
        filename = Path(str(item.get("name") or "")).name
        if not filename.lower().endswith(".json"):
            raise LocalizedError("flow_type", name=filename)
        content = item.get("content_json")
        encoded = json.dumps(content, ensure_ascii=False).encode("utf-8")
        if len(encoded) > FLOW_MAX_BYTES:
            raise LocalizedError("flow_size", name=filename)
        for node in normalize_flow_document(content, filename):
            node_id = node.get("id")
            if node_id:
                if node_id in all_ids:
                    raise LocalizedError("flow_duplicate_id", node_id=node_id)
                all_ids.add(node_id)
    return files


def merged_flows(profile):
    merged = []
    for item in validate_flow_files(profile):
        merged.extend(normalize_flow_document(item.get("content_json"), item.get("name") or "flow.json"))
    return merged


def canonical_flows(value):
    """Vergleichsform für Flows: Knotenliste (v1-Array oder v2-Objekt) nach id sortiert."""
    nodes = value.get("flows") if isinstance(value, dict) else value
    if not isinstance(nodes, list):
        return None
    return sorted(json.dumps(n, sort_keys=True, ensure_ascii=False) for n in nodes if isinstance(n, dict))


def publish_node_red_flows(master_url, username, password, profile):
    flows = merged_flows(profile)
    if not flows:
        return {"code": 200, "message": "No Node-RED flow selected."}
    base_url = node_red_base_url(master_url)
    token, auth_error = None, None
    try:
        token = get_node_red_token(base_url, username, password)
    except Exception as exc:
        auth_error = str(exc)
    headers = {"Content-Type": "application/json; charset=utf-8", "Node-RED-Deployment-Type": NODERED_DEPLOYMENT_TYPE}
    if token:
        headers["Authorization"] = "Bearer " + token
    # Zurücklesen: identische Flows nicht erneut deployen (ein Deploy startet die Flows neu).
    try:
        current = requests.get(base_url.rstrip("/") + "/flows", headers={k: v for k, v in headers.items() if k == "Authorization"},
                               timeout=PALETTE_VERIFY_TIMEOUT, verify=False)
        if current.status_code == 200 and canonical_flows(current.json()) == canonical_flows(flows):
            return {"code": 200, "skipped": True, "message": "Node-RED flows already identical.", "node_count": len(flows),
                    "auth": "token" if token else "none"}
    except Exception:
        pass
    response = requests.post(base_url.rstrip("/") + "/flows", headers=headers, json=flows, timeout=NODERED_TIMEOUT, verify=False)
    if response.status_code in (200, 204):
        return {"code": 200, "http_status": response.status_code, "message": "Node-RED flow deployed successfully.",
                "node_count": len(flows), "auth": "token" if token else "none"}
    detail = response.text[:1000]
    if auth_error and not token:
        detail = f"Authentication attempt: {auth_error}; deployment response: {detail}"
    return {"code": response.status_code, "http_status": response.status_code, "message": detail}


def _read_node_red(master_url, username, password, path):
    """GET auf die Node-RED-Admin-API (mit Token, falls Zugangsdaten vorhanden)."""
    base_url = node_red_base_url(master_url)
    token = None
    try:
        token = get_node_red_token(base_url, username, password)
    except Exception:
        pass
    headers = {"Accept": "application/json", **_api_headers(token)}
    response = requests.get(base_url.rstrip("/") + path, headers=headers, timeout=NODERED_TIMEOUT, verify=False)
    response.raise_for_status()
    return response.json()


def read_node_red_flows(master_url, username, password):
    """Aktive Flows (Geräte-Backup). Antwort v2: {"rev", "flows": [...]}."""
    return _read_node_red(master_url, username, password, "/flows")


def read_node_red_nodes(master_url, username, password):
    """Installierte Node-Module (GET /nodes, Geräte-Backup)."""
    return _read_node_red(master_url, username, password, "/nodes")


def build_flow_preview(profile, master_url=None):
    files = validate_flow_files(profile)
    if not files:
        return []
    nodes = merged_flows(profile)
    names = [Path(str(item.get("name") or "")).name for item in files]
    target = node_red_base_url(master_url) + "/flows" if master_url else "<AL15 host>:1880/flows"
    return [{"section": "node_red_flows", "label": f"Node-RED Flow Import ({len(files)} file(s))", "adr": "/flows",
             "data": {"files": names, "nodeCount": len(nodes), "deploymentType": NODERED_DEPLOYMENT_TYPE, "target": target},
             "auth_mode": "Node-RED token or none"}]
