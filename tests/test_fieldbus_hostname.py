"""Feldbus-Umschaltung (PROFINET/EtherNet/IP) und Hostname: Requests, Prüfungen, Zurücklesen, Reihenfolge, Backup."""
import unittest

from _helpers import APP, default_profile
from backup import DeviceBackup
from messages import LocalizedError
from readback import DeviceReader, plan_requests
from service_definitions import build_fieldbus_type_requests, build_hostname_requests


class FieldbusType(unittest.TestCase):
    def test_requests(self):
        self.assertEqual([r.adr for r in build_fieldbus_type_requests({"type": 0})], ["/devicesettings/fieldbustype/Profinet/enable"])
        self.assertEqual([r.adr for r in build_fieldbus_type_requests({"type": "2"})], ["/devicesettings/fieldbustype/EtherNetIP/enable"])
        self.assertEqual(build_fieldbus_type_requests({"type": None}), [])
        self.assertIsNone(build_fieldbus_type_requests({"type": 2})[0].data)  # enable ohne Daten

    def test_invalid_type(self):
        with self.assertRaises(LocalizedError) as ctx:
            build_fieldbus_type_requests({"type": 1})
        self.assertEqual(ctx.exception.key, "fieldbus_type")

    def test_readback(self):
        reqs = [dict(r.__dict__, section="fieldbus_type") for r in build_fieldbus_type_requests({"type": 0})]
        status = lambda v: DeviceReader(lambda adr: {"code": 200, "data": {"value": v}}
                                        if adr == "/devicesettings/fieldbustype/status/getdata" else {"code": 404})
        self.assertEqual(plan_requests(status(0), reqs)[0][1]["decision"], "skip")
        decision = plan_requests(status(2), reqs)[0][1]
        self.assertEqual((decision["decision"], decision["current"], decision["target"]), ("write", "EtherNet/IP", "PROFINET"))

    def test_factory_profile_keeps_section_inactive(self):
        from profile_schema import FACTORY_PROFILE
        self.assertEqual(FACTORY_PROFILE["fieldbus_type"], {"apply": False, "type": 2})
        self.assertNotIn("fieldbus_type", {r["section"] for r in APP.compile_requests(dict(FACTORY_PROFILE, name="w"))})

    def test_backup(self):
        reader = DeviceReader(lambda adr: {"code": 200, "data": {"value": 0}}
                              if adr == "/devicesettings/fieldbustype/status/getdata" else {"code": 404})
        job = DeviceBackup(reader, "t")
        list(job.rows())
        self.assertEqual(job.profile["fieldbus_type"], {"apply": True, "type": 0})


class Hostname(unittest.TestCase):
    def test_valid_names(self):
        for name in ("ifm-AL1590-000251100049", "Ab-C1", "a.b", "a" * 63):
            self.assertEqual(build_hostname_requests({"hostname": name})[0].data, {"newvalue": name})
        self.assertEqual(build_hostname_requests({"hostname": "  "}), [])
        self.assertEqual(build_hostname_requests({"hostname": None}), [])

    def test_invalid_names_match_device(self):
        # Vom AL1590 mit 422 abgelehnt (live geprüft 2026-11-20)
        for name in ("a" * 64, "-abc", "abc-", "1abc", "abc_d", "a.", "a-.b", "bad name"):
            with self.assertRaises(LocalizedError) as ctx:
                build_hostname_requests({"hostname": name})
            self.assertEqual(ctx.exception.key, "hostname_invalid")

    def test_order_hostname_before_network(self):
        p = default_profile()
        p["hostname"]["hostname"] = "al15-test"
        p["fieldbus_type"]["type"] = 0
        p["port_configuration"]["ports"][0]["pin4"] = 3
        p["connections_https"]["port"] = 443
        p["network"].update({"mode": "dhcp"})
        sections = [r["section"] for r in APP.compile_requests(p)]
        self.assertEqual(sections, ["port_configuration", "fieldbus_type", "connections_https", "hostname", "network"])


class Backup(unittest.TestCase):
    def test_hostname_is_stored_without_action(self):
        reader = DeviceReader(lambda adr: {"code": 200, "data": {"value": "geraet-1"}}
                              if adr == "/network/br0/hostname/getdata" else {"code": 404})
        job = DeviceBackup(reader, "t")
        rows = [r for r in job.rows() if r["section"] == "hostname"]
        self.assertEqual(job.profile["hostname"], {"apply": False, "hostname": "geraet-1"})
        self.assertEqual(rows[-1]["note"], "hostname_no_action")


if __name__ == "__main__":
    unittest.main()
