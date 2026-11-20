"""HTTP-/HTTPS-Server und erweiterte MQTT-Parameter: Requests, Prüfungen, Zurücklesen, Maskierung, Code 230."""
import unittest

from _helpers import APP, FIXTURES, default_profile
from messages import LocalizedError
from readback import DeviceReader, plan_requests
from service_definitions import build_certificate_key_pem, build_https_requests, pem_certificate_list

HTTPS = "/connections/httpserver1/httpserver"
MQTT = "/connections/mqttclient/mqttsetup"
MQTTCC = "/connections/mqttcommandchannel/mqttcmdchannel/mqttcmdchannelsetup"


def pem(name):
    return (FIXTURES / "https" / name).read_text(encoding="utf-8")


def pair(cert="server_cert.pem", key="server_key.pem", password=None):
    return {"certificate": {"name": cert, "pem": pem(cert)}, "private_key": {"name": key, "pem": pem(key)}, "password": password}


def reader_for(values):
    return DeviceReader(lambda adr: {"code": 200, "data": {"value": values[adr]}} if adr in values else {"code": 404})


class HttpsRequests(unittest.TestCase):
    def test_full_https_section(self):
        reqs = build_https_requests({"port": "8443", "secure": 1, "certificate": pair(),
                                     "trustedclientcertificates": pem("client_cert.pem") + "\n" + pem("server_cert.pem"),
                                     "validate_client_certificate": 0})
        adrs = [r.adr for r in reqs]
        self.assertEqual(adrs, [HTTPS + "/port/setdata", HTTPS + "/securesetup/secure/setdata",
                                HTTPS + "/securesetup/certificate_key_pem/setdata",
                                HTTPS + "/securesetup/trustedclientcertificates/setdata",
                                HTTPS + "/securesetup/validateclientcertificate/setdata"])
        self.assertEqual(reqs[0].data, {"newvalue": 8443})
        value = reqs[2].data["newvalue"]
        self.assertEqual(set(value), {"certificate", "key"})
        self.assertTrue(value["certificate"].startswith("-----BEGIN CERTIFICATE-----"))
        self.assertEqual(len(reqs[3].data["newvalue"]), 2)  # eine Liste einzelner PEM-Zertifikate

    def test_http_port_without_action(self):
        # Fehler gefunden beim Live-Test 2026-11-20: Aktion "Keine Aktion" verwarf den Port.
        p = default_profile(); p["connections_http"]["port"] = 8080
        reqs = APP.compile_requests(p)
        self.assertEqual([(r["adr"], r["data"]) for r in reqs], [("/connections/httpserver0/httpserver/port/setdata", {"newvalue": 8080})])

    def test_no_action_creates_nothing(self):
        self.assertEqual(build_https_requests({}), [])
        self.assertEqual([r for r in APP.compile_requests(default_profile())], [])

    def test_validation(self):
        for data, key in (({"port": 70000}, "https_port"), ({"secure": 2}, "https_secure"),
                          ({"validate_client_certificate": 3}, "https_validate"),
                          ({"trustedclientcertificates": "kein PEM"}, "https_trusted_pem")):
            with self.assertRaises(LocalizedError) as ctx:
                build_https_requests(data)
            self.assertEqual(ctx.exception.key, key)

    def test_server_certificate_needs_tls_server_eku(self):
        # Das OPC-UA-Testzertifikat hat keine EKU "TLS Server" -> das Gerät würde mit 422 ablehnen.
        opc = {"certificate": {"name": "cert.pem", "pem": (FIXTURES / "opcua" / "cert.pem").read_text()},
               "private_key": {"name": "key.pem", "pem": (FIXTURES / "opcua" / "key.pem").read_text()}}
        with self.assertRaises(LocalizedError) as ctx:
            build_https_requests({"certificate": opc})
        self.assertEqual(ctx.exception.key, "https_cert_eku")
        # Für MQTT-Client-Zertifikate gilt die Prüfung nicht.
        self.assertIsNotNone(build_certificate_key_pem(opc, "MQTT Client"))

    def test_pem_pair_errors(self):
        with self.assertRaises(LocalizedError) as ctx:
            build_certificate_key_pem({"certificate": {"pem": pem("server_cert.pem")}}, "HTTPS")
        self.assertEqual(ctx.exception.key, "pem_pair_key_missing")
        with self.assertRaises(LocalizedError) as ctx:
            build_certificate_key_pem(pair("client_cert.pem", "encrypted_key.pem"), "MQTT Client")
        self.assertEqual(ctx.exception.key, "pem_pair_key_password")
        value = build_certificate_key_pem(pair("client_cert.pem", "encrypted_key.pem", "Test1234"), "MQTT Client")
        self.assertEqual(value["password"], "Test1234")
        with self.assertRaises(LocalizedError) as ctx:
            build_certificate_key_pem(pair("server_cert.pem", "server_cert.pem"), "HTTPS")
        self.assertEqual(ctx.exception.key, "pem_pair_key_invalid")

    def test_pem_list_normalizes_chains(self):
        chain = [pem("server_cert.pem").strip() + ",\n" + pem("client_cert.pem").strip()]
        self.assertEqual(len(pem_certificate_list(chain)), 2)
        self.assertIsNone(pem_certificate_list(""))


class MqttRequests(unittest.TestCase):
    def test_new_mqtt_fields(self):
        p = default_profile()
        p["connections_mqtt_client"].update({"version": 2, "keepalive": "30", "willtopic": "al15/state", "willmessage": "",
                                             "retain": True, "client_certificate": pair()})
        p["connections_mqtt_command_channel"].update({"version": 1, "keepalive": 60, "willtopic": "", "client_certificate": pair()})
        reqs = {r["adr"]: r for r in APP.compile_requests(p)}
        self.assertEqual(reqs[MQTT + "/version/setdata"]["data"], {"newvalue": 2})
        self.assertEqual(reqs[MQTT + "/keepalive/setdata"]["data"], {"newvalue": 30})
        self.assertEqual(reqs[MQTT + "/willmessage/setdata"]["data"], {"newvalue": ""})
        self.assertEqual(reqs[MQTT + "/retain/setdata"]["data"], {"newvalue": True})
        self.assertIn(MQTT + "/securesetup/certificate_key_pem/setdata", reqs)
        self.assertIn(MQTTCC + "/version/setdata", reqs)
        self.assertIn(MQTTCC + "/securesetup/certificate_key_pem/setdata", reqs)
        self.assertNotIn(MQTTCC + "/retain/setdata", reqs)

    def test_mqtt_validation(self):
        p = default_profile(); p["connections_mqtt_client"]["version"] = 5
        with self.assertRaises(LocalizedError):
            APP.compile_requests(p)
        p = default_profile(); p["connections_mqtt_command_channel"]["keepalive"] = -1
        with self.assertRaises(LocalizedError):
            APP.compile_requests(p)

    def test_https_before_network_and_after_mqtt(self):
        p = default_profile()
        p["connections_https"]["port"] = 443
        p["connections_mqtt_client"]["qos"] = 1
        p["network"]["mode"] = "dhcp"
        sections = [r["section"] for r in APP.compile_requests(p)]
        self.assertEqual(sections, ["connections_mqtt_client", "connections_https", "network"])


class Readback(unittest.TestCase):
    def test_certificate_compare_ignores_unreadable_key(self):
        reqs = [r.__dict__ for r in build_https_requests({"certificate": pair()})]
        same = {HTTPS + "/securesetup/certificate_key_pem/getdata": {"certificate": pem("server_cert.pem").replace("\n", "\r\n"), "key": None, "password": None}}
        decision = plan_requests(reader_for(same), reqs)[0][1]
        self.assertEqual(decision["decision"], "skip")
        self.assertNotIn("BEGIN", str(decision))  # nur Fingerabdrücke, kein PEM und kein Key
        other = {HTTPS + "/securesetup/certificate_key_pem/getdata": {"certificate": None, "key": None, "password": None}}
        self.assertEqual(plan_requests(reader_for(other), reqs)[0][1]["decision"], "write")

    def test_trusted_client_certificates_compare(self):
        reqs = [r.__dict__ for r in build_https_requests({"trustedclientcertificates": pem("client_cert.pem")})]
        adr = HTTPS + "/securesetup/trustedclientcertificates/getdata"
        self.assertEqual(plan_requests(reader_for({adr: [pem("client_cert.pem")]}), reqs)[0][1]["decision"], "skip")
        self.assertEqual(plan_requests(reader_for({adr: []}), reqs)[0][1]["decision"], "write")

    def test_empty_will_topic_equals_null(self):
        p = default_profile(); p["connections_mqtt_client"]["willtopic"] = ""
        reqs = APP.compile_requests(p)
        self.assertEqual(plan_requests(reader_for({MQTT + "/willtopic/getdata": None}), reqs)[0][1]["decision"], "skip")


class MaskingAndReboot(unittest.TestCase):
    def test_key_is_masked_in_preview(self):
        p = default_profile(); p["connections_https"]["certificate"] = pair()
        rows = APP.app.test_client().post("/preview", json=p).get_json()["requests"]
        text = str(rows)
        self.assertNotIn("PRIVATE KEY", text)
        self.assertIn("certificate_sha256", text)

    def test_code_230_is_success_with_reboot_hint(self):
        self.assertTrue(APP.is_success_code("230", HTTPS + "/port/setdata"))
        self.assertTrue(APP.needs_reboot([{"code": 230}]))
        self.assertEqual(APP.row_status({"code": 230}, "en"), "OK (reboot required)")
        self.assertEqual(APP.row_status({"code": 422}, "de"), "Fehler")


if __name__ == "__main__":
    unittest.main()
