"""Offline-Paketierung von Node-RED-Paletten (TGZ mit gebündelten Abhängigkeiten).

Ablauf: Paket per npm installieren -> Runtime-Test mit Node.js -> fehlende Module hoisten ->
bundledDependencies setzen -> TGZ erzeugen -> TGZ entpacken und erneut testen.
"""
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from messages import LocalizedError

# Lädt jede Node-RED-Node-Datei und jede Abhängigkeit des Pakets; meldet das erste fehlende Modul.
RUNTIME_CHECK_JS = r"""
const fs=require('fs'),path=require('path');const {createRequire}=require('module');
const pj=path.resolve(process.argv[2]),root=path.dirname(pj),pkg=JSON.parse(fs.readFileSync(pj,'utf8')),req=createRequire(pj),checks=[];
for(const f of Object.values((pkg['node-red']||{}).nodes||{}))checks.push({kind:'node',name:String(f),file:path.resolve(root,String(f))});
for(const n of Object.keys(pkg.dependencies||{}))checks.push({kind:'dependency',name:n});
for(const c of checks){try{if(c.kind==='node')require(c.file);else{req.resolve(c.name);req(c.name)}}catch(e){const m=(String(e.message).match(/Cannot find module ['\"]([^'\"]+)['\"]/)||[])[1]||'';console.log(JSON.stringify({ok:false,errorCode:e.code||'RUNTIME_ERROR',missingModule:m,message:String(e.message),stack:String(e.stack||''),check:c}));process.exit(2)}}
console.log(JSON.stringify({ok:true,checks:checks.length,package:pkg.name,version:pkg.version}));
"""


def run_runtime_check(package_dir):
    checker = package_dir.parent / "al15-runtime-check.js"
    checker.write_text(RUNTIME_CHECK_JS, encoding="utf-8")
    r = subprocess.run(["node", str(checker), str(package_dir / "package.json")], cwd=package_dir.parent,
                       capture_output=True, text=True, timeout=90)
    lines = [x for x in (r.stdout or "").splitlines() if x.strip()]
    return json.loads(lines[-1]) if lines else {"ok": False, "message": (r.stderr or "Runtime check failed")[-2000:]}


def package_candidates(node_modules, missing):
    """Verschachtelte Kopien eines fehlenden Moduls ohne native Teile und ohne Install-Skripte."""
    rel = Path(*missing.split("/"))
    out = []
    for pj in node_modules.rglob("package.json"):
        if pj.parent.parts[-len(rel.parts):] != rel.parts:
            continue
        try:
            d = json.loads(pj.read_text(encoding="utf-8"))
            if d.get("name") != missing or any(pj.parent.rglob("*.node")):
                continue
            scripts = d.get("scripts") or {}
            if any(k in scripts for k in ("preinstall", "install", "postinstall")):
                continue
            out.append({"path": pj.parent, "version": str(d.get("version") or "")})
        except Exception:
            pass
    return out


def repair_runtime_resolution(package_dir, max_repairs=50):
    repairs = []
    nm = package_dir / "node_modules"
    nm.mkdir(exist_ok=True)
    for _ in range(max_repairs):
        result = run_runtime_check(package_dir)
        if result.get("ok"):
            return result, repairs
        missing = result.get("missingModule")
        if result.get("errorCode") != "MODULE_NOT_FOUND" or not missing:
            raise LocalizedError("pack_runtime_failed", detail=json.dumps(result, ensure_ascii=False))
        candidates = package_candidates(nm, missing)
        versions = {x["version"] for x in candidates}
        if not candidates or len(versions) != 1:
            raise LocalizedError("pack_dependency_ambiguous", name=missing, count=len(candidates), versions=sorted(versions))
        target = nm / Path(*missing.split("/"))
        if target.exists():
            raise LocalizedError("pack_dependency_unloadable", name=missing)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(candidates[0]["path"], target, symlinks=False)
        repairs.append({"action": "copy-and-hoist", "package": missing, "version": candidates[0]["version"],
                        "source": str(candidates[0]["path"].relative_to(package_dir)), "target": str(target.relative_to(package_dir))})
    raise LocalizedError("pack_hoisting_limit")


def top_level_packages(node_modules):
    out = set()
    if not node_modules.exists():
        return out
    for c in node_modules.iterdir():
        if c.name.startswith("@") and c.is_dir():
            out.update(f"{c.name}/{x.name}" for x in c.iterdir() if x.is_dir())
        elif c.is_dir():
            out.add(c.name)
    return out


def update_bundled_dependencies(package_dir):
    pj = package_dir / "package.json"
    d = json.loads(pj.read_text(encoding="utf-8"))
    d["bundledDependencies"] = sorted(top_level_packages(package_dir / "node_modules"))
    pj.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    return d["bundledDependencies"]


def direct_archive_name(package_dir):
    d = json.loads((package_dir / "package.json").read_text(encoding="utf-8"))
    return f"{str(d['name']).replace('@', '').replace('/', '-')}-{d['version']}.tgz"


def create_direct_archive(package_dir, output_file):
    if output_file.exists():
        output_file.unlink()
    with tarfile.open(output_file, "w:gz", dereference=True) as archive:
        archive.add(package_dir, arcname="package", recursive=True)
    return output_file


def validate_packed_archive(tgz_path, workspace_package_dir):
    work = Path(tempfile.mkdtemp(prefix="al15_tgz_test_"))
    try:
        with tarfile.open(tgz_path, "r:gz") as archive:
            root = work.resolve()
            for member in archive.getmembers():
                dest = (work / member.name).resolve()
                if dest != root and root not in dest.parents:
                    raise LocalizedError("pack_unsafe_path")
            archive.extractall(work)
        package_dir = work / "package"
        result = run_runtime_check(package_dir)
        if not result.get("ok"):
            raise LocalizedError("pack_tgz_runtime_failed", detail=json.dumps(result, ensure_ascii=False))
        missing = sorted(top_level_packages(workspace_package_dir / "node_modules") - top_level_packages(package_dir / "node_modules"))
        if missing:
            raise LocalizedError("pack_tgz_incomplete", names=", ".join(missing))
        return result
    finally:
        shutil.rmtree(work, ignore_errors=True)
