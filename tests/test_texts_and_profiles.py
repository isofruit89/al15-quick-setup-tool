"""Übersetzungen, Fehlermeldungen, Umlaute und Profilverwaltung."""
import json
import re
import string
import unittest
import uuid

import messages
from _helpers import APP, ROOT, default_profile

FORMATTER = string.Formatter()


def placeholders(text):
    return {f for _, f, _, _ in FORMATTER.parse(text) if f}


class Texts(unittest.TestCase):
    def test_backend_texts_complete(self):
        de, en = messages.BACKEND_I18N["de"], messages.BACKEND_I18N["en"]
        self.assertEqual(set(de), set(en))
        for key in de:
            self.assertEqual(placeholders(de[key]), placeholders(en[key]), key)

    def test_error_catalog_consistent(self):
        for key, (de, en) in messages.ERRORS.items():
            self.assertEqual(placeholders(de), placeholders(en), key)
            self.assertFalse(re.search("[äöüÄÖÜß]", en), key)

    def test_all_raised_keys_exist(self):
        for name in ("app.py", "service_definitions.py", "nodered.py", "palette_packager.py"):
            src = (ROOT / name).read_text(encoding="utf-8")
            for key in re.findall(r'LocalizedError\(\s*f?["\']([a-z0-9_{}]+)["\']', src):
                variants = [key.replace("{slot}", s) for s in ("cert", "key")] if "{slot}" in key else [key]
                for k in variants:
                    self.assertIn(k, messages.ERRORS, f"{name}: {k}")

    def test_errors_follow_ui_language(self):
        client = APP.app.test_client()
        p = default_profile(); p["connections_opcua"]["port"] = 70000
        de = client.post("/preview?lang=de", json=dict(p, lang="de")).get_json()["error"]
        en = client.post("/preview?lang=en", json=dict(p, lang="en")).get_json()["error"]
        self.assertIn("muss zwischen", de)
        self.assertIn("must be between", en)

    def test_source_files_are_clean_utf8(self):
        for path in [*ROOT.glob("*.py"), ROOT / "static" / "app.js", ROOT / "templates" / "index.html"]:
            text = path.read_bytes().decode("utf-8")
            self.assertFalse(re.search("Ã.|â€|�", text), path.name)


class Profiles(unittest.TestCase):
    def setUp(self):
        self.client = APP.app.test_client()
        self.names = []

    def tearDown(self):
        for name in self.names:
            self.client.delete("/profiles/delete/" + name)

    def save(self, profile):
        r = self.client.post("/save", json=profile).get_json()
        self.assertTrue(r["ok"], r)
        self.names.append(r["name"])
        return r["name"]

    def test_safe_name(self):
        self.assertEqual(APP.safe_name("Größe Test  ÄÖÜ ß €"), "Größe_Test_ÄÖÜ_ß")
        self.assertEqual(APP.safe_name("../../etc"), "etc")
        self.assertEqual(APP.safe_name("CON"), "CON_")
        self.assertEqual(APP.safe_name("   "), "quick_setup_profile")

    def test_umlaut_roundtrip(self):
        special = 'Prüfstand Ä Ö Ü ß € µ ° § "Zitat" <b>&amp; ✓'
        p = default_profile()
        p["name"] = "zz_test_" + uuid.uuid4().hex[:6] + " Größe"
        p["device_tags"]["location_tag"] = special
        name = self.save(p)
        loaded = self.client.get("/profiles/load/" + name).get_json()["config"]
        self.assertEqual(loaded["device_tags"]["location_tag"], special)
        raw = (APP.PROFILE_DIR / f"{name}.json").read_text(encoding="utf-8")
        self.assertIn("Prüfstand", raw)

    def test_copy_does_not_overwrite_silently(self):
        p = default_profile(); p["name"] = "zz_test_src_" + uuid.uuid4().hex[:6]
        src = self.save(p)
        p2 = default_profile(); p2["name"] = src + "_ziel"; p2["device_tags"]["location_tag"] = "bleibt"
        dst = self.save(p2)
        r = self.client.post(f"/profiles/copy/{src}", json={"new_name": dst})
        self.assertEqual(r.status_code, 409)
        loaded = self.client.get("/profiles/load/" + dst).get_json()["config"]
        self.assertEqual(loaded["device_tags"]["location_tag"], "bleibt")
        r = self.client.post(f"/profiles/copy/{src}", json={"new_name": dst, "overwrite": True}).get_json()
        self.assertTrue(r["ok"])
        loaded = self.client.get("/profiles/load/" + dst).get_json()["config"]
        self.assertIsNone(loaded["device_tags"]["location_tag"])


if __name__ == "__main__":
    unittest.main()
