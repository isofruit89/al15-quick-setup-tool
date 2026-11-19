"""Ist-/Soll-Vergleich vor dem Schreiben (readback.py)."""
import unittest

import _helpers  # noqa: F401  (setzt sys.path)
from readback import DeviceReader, opcua_settings_equal, plan_requests, values_equal
from service_definitions import normalize_mqtt_trusted_server_certificates as norm

CERT_A = "-----BEGIN CERTIFICATE-----\nAAA\nBBB\n-----END CERTIFICATE-----"
CERT_B = "-----BEGIN CERTIFICATE-----\nCCC\n-----END CERTIFICATE-----"
MQTT_CERTS = "/connections/mqttclient/mqttsetup/securesetup/trustedservercertificates/setdata"
OPCUA = "/connections/opcua_server"


def reader_for(values):
    """DeviceReader mit festen Gerätewerten; unbekannte Pfade antworten 401."""
    return DeviceReader(lambda adr: {"code": 200, "data": {"value": values[adr]}} if adr in values else {"code": 401})


class ValuesEqual(unittest.TestCase):
    def test_certificate_chain_as_sent(self):
        self.assertTrue(values_equal(MQTT_CERTS, [CERT_A + ",\n" + CERT_B], norm(CERT_A + "\r\n\r\n" + CERT_B)))

    def test_certificate_chain_differs(self):
        self.assertFalse(values_equal(MQTT_CERTS, [CERT_A], norm(CERT_A + "\n" + CERT_B)))
        self.assertFalse(values_equal(MQTT_CERTS, None, norm(CERT_A)))

    def test_scalar_formats(self):
        self.assertTrue(values_equal("/x/setdata", None, ""))
        self.assertTrue(values_equal("/x/setdata", "1", 1))
        self.assertFalse(values_equal("/x/setdata", 1, True))
        self.assertTrue(values_equal("/x/setdata", "Prüfstand Ä €", "Prüfstand Ä €"))

    def test_opcua_profiles_order_independent(self):
        current = {"port": 4843, "security_profiles": [{"name": "None", "enabled": False}, {"name": "Basic256Sha256", "enabled": True}]}
        target = {"security_profiles": [{"name": "Basic256Sha256", "enabled": True}, {"name": "None", "enabled": False}]}
        self.assertTrue(opcua_settings_equal(current, target)[0])
        self.assertTrue(opcua_settings_equal({"port": 4843, "enable_anonymous": True}, {"port": 4843})[0])
        self.assertFalse(opcua_settings_equal({"port": 4843}, {"port": 4844})[0])


class PlanRequests(unittest.TestCase):
    def test_mixed_plan(self):
        reader = reader_for({
            "/network/br0/ipv4/mode/getdata": 1, "/network/br0/ipv4/gateway/getdata": "0.0.0.0",
            "/network/br0/ipv4/address0/address/getdata": "192.168.0.10",
            "/network/br0/ipv4/address0/subnetmask/getdata": "255.255.255.0",
            "/network/br0/ipv4/staticdnsservers/getdata": [],
            "/connections/mqttcommandchannel/status/getdata": "irgendwas",
        })
        net = {"adr": "/network/br0/ipv4/setnetwork", "label": "Network",
               "data": {"mode": 1, "gateway": "", "address": [{"Address": "192.168.0.10", "Subnetmask": "255.255.255.0"}]}}
        plan = plan_requests(reader, [
            net,
            {"adr": "/connections/mqttcommandchannel/status/start", "label": "MQTTCC Start"},
            {"adr": "/devicetag/functiontag/setdata", "label": "F", "data": {"newvalue": "x"}},
            {"adr": "/connections/mqttcommandchannel/mqttcmdchannel/mqttcmdchannelsetup/password/setdata", "label": "PW", "data": {"newvalue": "x"}},
        ])
        self.assertEqual([d["decision"] for _, d in plan], ["skip", "unverified", "unverified", "unverified"])

    def test_dhcp_needs_gateway_mode(self):
        values = {"/network/br0/ipv4/mode/getdata": 2, "/network/br0/ipv4/gateway/getdata": "0.0.0.0",
                  "/network/br0/ipv4/address0/address/getdata": "169.254.6.224",
                  "/network/br0/ipv4/address0/subnetmask/getdata": "255.255.0.0",
                  "/network/br0/ipv4/staticdnsservers/getdata": [],
                  "/network/br0/ipv4/gateway_mode/getdata": 1, "/network/br0/ipv4/dns_mode/getdata": 3}
        req = {"adr": "/network/br0/ipv4/setnetwork", "label": "Network",
               "data": {"mode": 2, "gateway": "", "address": [], "gateway_mode": 1, "dns_mode": 3}}
        self.assertEqual(plan_requests(reader_for(values), [req])[0][1]["decision"], "skip")
        values["/network/br0/ipv4/gateway_mode/getdata"] = 0
        self.assertEqual(plan_requests(reader_for(values), [req])[0][1]["decision"], "write")

    def test_opcua_group_unchanged_keeps_stopped(self):
        reader = reader_for({OPCUA + "/status/getdata": "stopped", OPCUA + "/settings/getdata": {"port": 4843}})
        group = [{"adr": OPCUA + "/status/stop", "label": "OPC UA Stop (conditional)"},
                 {"adr": OPCUA + "/settings/setdata", "label": "OPC UA Settings", "data": {"value": {"port": 4843}}},
                 {"adr": OPCUA + "/status/start", "label": "OPC UA Start (nach Settings)"}]
        self.assertEqual([d["decision"] for _, d in plan_requests(reader, group)], ["skip", "skip", "skip"])

    def test_opcua_group_change_restarts_running_server(self):
        reader = reader_for({OPCUA + "/status/getdata": "running", OPCUA + "/settings/getdata": {"port": 4843}})
        group = [{"adr": OPCUA + "/status/stop", "label": "OPC UA Stop (conditional)"},
                 {"adr": OPCUA + "/settings/setdata", "label": "OPC UA Settings", "data": {"value": {"port": 4844}}},
                 {"adr": OPCUA + "/status/start", "label": "OPC UA Start (nach Settings)"}]
        self.assertEqual([d["decision"] for _, d in plan_requests(reader, group)], ["write", "write", "write"])


if __name__ == "__main__":
    unittest.main()
