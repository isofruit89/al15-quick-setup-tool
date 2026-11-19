"""Erzeugte Requests: Profilschema v2, Migration v1, Netzwerk, OPC-UA-Zertifikat, Maskierung."""
import base64
import copy
import json
import unittest
import zlib

from _helpers import APP, FIXTURES, default_profile, fixture_file


def requests_of(profile):
    return APP.compile_requests(APP.effective_profile(APP.migrate_profile(copy.deepcopy(profile))))


class ProfileSchema(unittest.TestCase):
    def test_default_profile_sends_nothing(self):
        self.assertEqual(requests_of(default_profile()), [])

    def test_class_off_ignores_parameters(self):
        p = default_profile()
        p["device_tags"].update(apply=False, application_tag="X")
        p["port_configuration"]["ports"][0]["pin4"] = 1
        labels = [r["label"] for r in requests_of(p)]
        self.assertEqual(labels, ["Port 1 Pin 4"])

    def test_v1_migration_matches_golden_requests(self):
        golden = json.loads((FIXTURES / "migration_v1.json").read_text(encoding="utf-8"))
        for name, case in golden.items():
            with self.subTest(case=name):
                got = [{"adr": r["adr"], "data": r.get("data")} for r in requests_of(case["profile"])]
                self.assertEqual(got, case["expected"])


class Network(unittest.TestCase):
    def test_dhcp_payload(self):
        p = default_profile(); p["network"]["mode"] = "dhcp"
        data = [r for r in requests_of(p) if r["adr"] == "/network/br0/ipv4/setnetwork"][0]["data"]
        self.assertEqual(data, {"mode": 2, "gateway": "", "address": [], "gateway_mode": 1, "dns_mode": 3})

    def test_static_payload(self):
        p = default_profile()
        p["network"].update(mode="static", address="192.168.0.10", subnetmask="255.255.255.0", gateway="192.168.0.1")
        data = [r for r in requests_of(p) if r["adr"] == "/network/br0/ipv4/setnetwork"][0]["data"]
        self.assertEqual(data["mode"], 1)
        self.assertEqual(data["address"], [{"Address": "192.168.0.10", "Subnetmask": "255.255.255.0"}])

    def test_network_is_last(self):
        p = default_profile(); p["network"]["mode"] = "dhcp"; p["device_tags"]["location_tag"] = "L"
        self.assertEqual(requests_of(p)[-1]["adr"], "/network/br0/ipv4/setnetwork")


class OpcuaCertificate(unittest.TestCase):
    def profile(self, cert):
        p = default_profile(); p["connections_opcua"]["certificate"] = cert
        return p

    def test_pem_converted_to_der_with_crc(self):
        reqs = requests_of(self.profile({"certificate": fixture_file("cert.pem"), "private_key": fixture_file("key.pfx")}))
        upload = [r for r in reqs if r["adr"] == APP.OPCUA_CERT_ADR][0]["data"]
        der = (FIXTURES / "opcua" / "cert.der").read_bytes()
        self.assertEqual(base64.b64decode(upload["certificate_value"]), der)
        self.assertEqual(upload["certificate_crc32"], zlib.crc32(der))
        labels = [r["label"] for r in reqs]
        self.assertLess(labels.index("OPC UA Zertifikat"), len(labels))

    def test_rejects_invalid_combinations(self):
        client = APP.app.test_client()
        for cert in ({"certificate": fixture_file("cert.der")},
                     {"certificate": fixture_file("cert.der"), "private_key": fixture_file("key.der")},
                     {"certificate": fixture_file("key.pem"), "private_key": fixture_file("key.pfx")}):
            with self.subTest(cert=sorted(cert)):
                r = client.post("/preview", json=self.profile(cert)).get_json()
                self.assertFalse(r["ok"])

    def test_secrets_masked_in_preview(self):
        p = self.profile({"certificate": fixture_file("cert.pem"), "private_key": fixture_file("key.pfx")})
        p["connections_mqtt_command_channel"]["password"] = "geheim123"
        text = json.dumps(APP.app.test_client().post("/preview", json=p).get_json())
        self.assertNotIn("geheim123", text)
        self.assertNotIn(fixture_file("key.pfx")["content_base64"][:40], text)
        self.assertIn("*** masked ***", text)


if __name__ == "__main__":
    unittest.main()
