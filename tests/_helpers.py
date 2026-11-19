"""Gemeinsame Hilfen für die Tests: Projektpfad und Testdaten."""
import base64
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as APP  # noqa: E402  (nach sys.path)


def fixture_file(name):
    """{'name', 'content_base64'} wie vom Frontend für eine Datei aus fixtures/opcua."""
    raw = (FIXTURES / "opcua" / name).read_bytes()
    return {"name": name, "content_base64": base64.b64encode(raw).decode()}


def default_profile():
    return copy.deepcopy(APP.DEFAULT_PROFILE)
