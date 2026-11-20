"""Werkseinstellungen als Vorbelegung des Editors (FACTORY_PROFILE)."""
import json
import unittest
from pathlib import Path

from _helpers import APP
from profile_schema import DEFAULT_PROFILE, FACTORY_PROFILE, migrate_profile

FACTORY_BACKUP = Path(__file__).resolve().parent / "fixtures" / "werkszustand_AL1590_fw1702.json"


class FactoryProfile(unittest.TestCase):
    def test_compiles_without_errors(self):
        p = dict(FACTORY_PROFILE, name="werk")
        sections = {r["section"] for r in APP.compile_requests(p)}
        self.assertNotIn("network", sections)  # Netzwerk bleibt unangetastet
        self.assertIn("connections_mqtt_client", sections)

    def test_start_stop_and_device_specific_values_are_not_prefilled(self):
        for section, data in FACTORY_PROFILE.items():
            if isinstance(data, dict) and "action" in data:
                self.assertEqual(data["action"], "none", section)
        self.assertIsNone(FACTORY_PROFILE["device_tags"]["application_tag"])
        self.assertIsNone(FACTORY_PROFILE["connections_mqtt_client"]["clientid"])
        self.assertIsNone(FACTORY_PROFILE["network"]["mode"])

    def test_old_profiles_are_not_filled_with_factory_values(self):
        old = {"schema_version": 2, "name": "alt", "connections_http": {"apply": True, "action": "start"}}
        self.assertIsNone(migrate_profile(old)["connections_http"]["port"])
        self.assertIsNone(DEFAULT_PROFILE["connections_mqtt_client"]["keepalive"])

    @unittest.skipUnless(FACTORY_BACKUP.exists(), "Werks-Backup nicht vorhanden")
    def test_matches_values_read_after_factory_reset(self):
        read = json.loads(FACTORY_BACKUP.read_text(encoding="utf-8"))
        for section, data in FACTORY_PROFILE.items():
            if not isinstance(data, dict) or section in ("network", "system_security"):
                continue
            for key, value in data.items():
                if key in ("apply", "action") or value is None:
                    continue
                self.assertEqual(value, read[section][key], f"{section}.{key}")


if __name__ == "__main__":
    unittest.main()
