"""Geräte-Backup (backup.py): Umwandlung der Gerätewerte und Rundlauf Backup -> Übertragung."""
import json
import re
import unittest
import uuid

import messages
from _helpers import APP, ROOT
from backup import DeviceBackup, NOT_BACKED_UP, NOT_READABLE, READ, summary, user_modules
from readback import DeviceReader, plan_requests

CERT_A = "-----BEGIN CERTIFICATE-----\nAAA\n-----END CERTIFICATE-----"
CERT_B = "-----BEGIN CERTIFICATE-----\nBBB\n-----END CERTIFICATE-----"
MQTT = "/connections/mqttclient/mqttsetup"
MQTTCC = "/connections/mqttcommandchannel/mqttcmdchannel/mqttcmdchannelsetup"

# Werte wie am AL1590 (FW 1.7.0.2) am 2026-11-20 gelesen, ergänzt um Zertifikate und Ports.
DEVICE = {
    "/devicetag/applicationtag/getdata": "Test123",
    "/devicetag/functiontag/getdata": None,
    "/devicetag/locationtag/getdata": "Prüfstand Ä",
    "/network/br0/ipv4/mode/getdata": 1,
    "/network/br0/ipv4/address0/address/getdata": "192.168.0.77",
    "/network/br0/ipv4/address0/subnetmask/getdata": "255.255.255.0",
    "/network/br0/ipv4/gateway/getdata": "",
    "/network/br0/ipv4/staticdnsservers/getdata": [],
    "/network/br0/ipv4/gateway_mode/getdata": 1,
    "/network/br0/ipv4/dns_mode/getdata": 3,
    "/application/ntp/settings/serverlist/getdata": ["0.pool.ntp.org", "1.pool.ntp.org"],
    "/application/ntp/status/getdata": "running",
    "/application/node-red/status/getdata": "running",
    "/security/authentication_enabled/getdata": False,
    "/connections/httpserver0/httpserver/allowed_services/getdata": 0,
    "/connections/opcua_server/settings/getdata": {
        "port": 4843, "enable_anonymous": True,
        "security_profiles": [{"name": "Basic256Sha256", "enabled": False}, {"name": "Aes128Sha256RsaOaep", "enabled": False},
                              {"name": "Aes256Sha256RsaPss", "enabled": False}, {"name": "None", "enabled": True}]},
    "/connections/opcua_server/status/getdata": "running",
    MQTT + "/qos/getdata": 0,
    MQTT + "/clientid/getdata": "",
    MQTT + "/securesetup/validateservercertificate/getdata": 0,
    MQTT + "/securesetup/trustedservercertificates/getdata": [CERT_A + ",\n" + CERT_B],
    "/connections/mqttclient/status/getdata": "stopped",
    MQTTCC + "/brokerip/getdata": "",
    MQTTCC + "/brokerport/getdata": 1883,
    MQTTCC + "/qos/getdata": 0,
    MQTTCC + "/cmdtopic/getdata": "iotcore-request",
    MQTTCC + "/defaultreplytopic/getdata": "iotcore-response",
    MQTTCC + "/clientid/getdata": "",
    MQTTCC + "/securesetup/secure/getdata": 0,
    MQTTCC + "/securesetup/validateservercertificate/getdata": 0,
    MQTTCC + "/securesetup/trustedservercertificates/getdata": None,
    MQTTCC + "/user/getdata": None,
    "/connections/mqttcommandchannel/status/getdata": "stopped",
    # HTTP/HTTPS-Server und neue MQTT-Parameter (am 2026-11-20 gelesen)
    "/connections/httpserver0/httpserver/port/getdata": 80,
    "/connections/httpserver1/httpserver/port/getdata": 443,
    "/connections/httpserver1/httpserver/securesetup/secure/getdata": 0,
    "/connections/httpserver1/httpserver/securesetup/validateclientcertificate/getdata": 0,
    "/connections/httpserver1/httpserver/securesetup/trustedclientcertificates/getdata": [],
    "/connections/httpserver1/httpserver/securesetup/certificate_key_pem/getdata": {"certificate": CERT_A, "key": None, "password": None},
    MQTT + "/version/getdata": 1, MQTT + "/keepalive/getdata": 15, MQTT + "/willtopic/getdata": None,
    MQTT + "/willmessage/getdata": "", MQTT + "/retain/getdata": False,
    MQTT + "/securesetup/certificate_key_pem/getdata": {"certificate": None, "key": None, "password": None},
    MQTTCC + "/version/getdata": 1, MQTTCC + "/keepalive/getdata": 15, MQTTCC + "/willtopic/getdata": None,
    MQTTCC + "/willmessage/getdata": None,
    MQTTCC + "/securesetup/certificate_key_pem/getdata": {"certificate": None, "key": None, "password": None},
}
for _port in range(1, 9):
    DEVICE[f"/iolinkmaster/port[{_port}]/mode/getdata"] = 3 if _port != 2 else 1
    if _port <= 4:
        DEVICE[f"/iolinkmaster/port[{_port}]/powercontrol/mode_ua/getdata"] = 0 if _port != 3 else 2
DEVICE.update({"/network/br0/hostname/getdata": "ifm-AL1590-000251100049", "/devicesettings/fieldbustype/status/getdata": 2})


MONITOR_ITEMS = [{"id": 1, "data_points": ["ifm-AL1590-000251100049/devicestatus/temperature/cpu"], "sample_interval": 1000,
                  "notify_interval": 1000, "data_changed": False, "recipient": "mqtt://192.168.0.2:1883/test/monitor",
                  "description": "test", "persist": True}]


def reader_for(values, monitor=MONITOR_ITEMS):
    def read(adr):
        if adr == "/monitor/getitems":
            return {"code": 200, "data": {"items": monitor}}
        return {"code": 200, "data": {"value": values[adr]}} if adr in values else {"code": 404}
    return DeviceReader(read)


def run_backup(values=DEVICE, **kwargs):
    job = DeviceBackup(reader_for(values), "backup_test", **kwargs)
    rows = list(job.rows())
    return job.profile, rows


class Conversion(unittest.TestCase):
    def test_values(self):
        p, _ = run_backup()
        self.assertEqual(p["device_tags"], {"apply": True, "application_tag": "Test123", "function_tag": "", "location_tag": "Prüfstand Ä"})
        self.assertEqual(p["network"]["mode"], "static")
        self.assertEqual((p["network"]["address"], p["network"]["subnetmask"], p["network"]["gateway"]), ("192.168.0.77", "255.255.255.0", ""))
        self.assertFalse(p["network"]["apply"])  # Netzwerk bewusst "Keine Aktion"
        self.assertEqual(p["port_configuration"]["ports"][1], {"port": 2, "pin4": 1, "pin2": 0})
        self.assertEqual(p["port_configuration"]["ports"][2]["pin2"], 2)
        self.assertNotIn("pin2", p["port_configuration"]["ports"][5])
        self.assertEqual(p["system_ntp"], {"apply": True, "servers": ["0.pool.ntp.org", "1.pool.ntp.org"], "action": "start"})
        self.assertEqual(p["system_security"]["credentials_enabled"], False)
        self.assertEqual(p["connections_http"]["action"], "start")
        self.assertEqual(p["connections_opcua"]["port"], 4843)
        self.assertTrue(p["connections_opcua"]["enable_anonymous"])
        self.assertIsNone(p["connections_opcua"]["certificate"])
        self.assertEqual(p["connections_mqtt_client"]["trustedservercertificates"], [CERT_A, CERT_B])
        self.assertEqual(p["connections_mqtt_client"]["action"], "stop")
        cc = p["connections_mqtt_command_channel"]
        self.assertEqual((cc["brokerport"], cc["cmdtopic"], cc["user"]), (1883, "iotcore-request", ""))
        self.assertIsNone(cc["password"])
        self.assertIsNone(cc["trustedservercertificates"])
        self.assertEqual((p["connections_http"]["port"], p["connections_https"]["port"], p["connections_https"]["secure"]), (80, 443, 0))
        self.assertIsNone(p["connections_https"]["trustedclientcertificates"])
        self.assertIsNone(p["connections_https"]["certificate"])
        mq = p["connections_mqtt_client"]
        self.assertEqual((mq["version"], mq["keepalive"], mq["willtopic"], mq["willmessage"], mq["retain"]), (1, 15, "", "", False))
        self.assertEqual((cc["version"], cc["keepalive"], cc["willtopic"]), (1, 15, ""))

    def test_dhcp_and_gateway_placeholder(self):
        values = dict(DEVICE)
        values["/network/br0/ipv4/mode/getdata"] = 2
        p, _ = run_backup(values)
        self.assertEqual((p["network"]["mode"], p["network"]["address"]), ("dhcp", ""))
        values.update({"/network/br0/ipv4/mode/getdata": 1, "/network/br0/ipv4/gateway/getdata": "0.0.0.0"})
        self.assertEqual(run_backup(values)[0]["network"]["gateway"], "")

    def test_unreadable_values_stay_no_action(self):
        values = {k: v for k, v in DEVICE.items() if "qos" not in k}
        values["/connections/mqttclient/status/getdata"] = "starting"
        values["/connections/httpserver0/httpserver/allowed_services/getdata"] = 7
        p, rows = run_backup(values)
        self.assertIsNone(p["connections_mqtt_client"]["qos"])
        self.assertEqual(p["connections_mqtt_client"]["action"], "none")
        self.assertEqual(p["connections_http"]["action"], "none")
        states = {r["label"]: r["state"] for r in rows}
        self.assertEqual(states["MQTT QoS"], NOT_READABLE)
        self.assertEqual(states["HTTP"], NOT_READABLE)

    def test_not_backed_up_rows(self):
        _, rows = run_backup()
        labels = {r["label"] for r in rows if r["state"] == NOT_BACKED_UP}
        self.assertTrue({"@bk_lbl_opcua_cert", "@bk_lbl_mqttcc_password", "@bk_lbl_iodd", "@bk_lbl_https_cert"} <= labels)
        self.assertNotIn("@bk_lbl_mqtt_client_cert", labels)  # kein Client-Zertifikat installiert
        self.assertEqual(summary(rows)["not_readable"], 0)

    def test_flows_and_modules(self):
        flows = {"rev": "x", "flows": [{"id": "a", "type": "tab"}, {"id": "b", "type": "inject", "z": "a"}]}
        modules = [{"module": "node-red", "user": False, "version": "4.1.4"},
                   {"module": "node-red-contrib-opcua", "user": True, "version": "0.2.355"},
                   {"module": "node-red-contrib-opcua", "user": True, "version": "0.2.355"}]
        p, rows = run_backup(flows_fn=lambda: flows, modules_fn=lambda: user_modules(modules))
        self.assertEqual(p["node_red_flows"]["files"], [{"name": "backup_test_flows.json", "content_json": flows["flows"]}])
        palette_rows = [r for r in rows if r["section"] == "node_red_palettes"]
        self.assertEqual([r["label"] for r in palette_rows], ["node-red-contrib-opcua 0.2.355"])
        p, rows = run_backup()
        self.assertEqual(p["node_red_flows"]["files"], [])


class RoundTrip(unittest.TestCase):
    def test_restore_to_same_device_changes_nothing(self):
        """Backup -> compile_requests -> Zurücklesen gegen dasselbe Gerät: alles unverändert."""
        profile, _ = run_backup()
        profile["network"]["apply"] = True  # auch das Netzwerk muss unverändert sein
        requests = APP.compile_requests(profile)
        self.assertTrue(requests)
        requests = APP.bind_monitor_requests(requests, "ifm-AL1590-000251100049")
        self.assertTrue(any(r["adr"] == "/monitor/add" for r in requests))
        planned = plan_requests(reader_for(DEVICE), requests)
        changed = [(r["label"], d) for r, d in planned if d["decision"] != "skip"]
        self.assertEqual(changed, [])


class Texts(unittest.TestCase):
    def test_all_backup_keys_exist(self):
        de = messages.BACKEND_I18N["de"]
        src = (ROOT / "backup.py").read_text(encoding="utf-8")
        for key in re.findall(r'"@([a-z0-9_]+)"', src):
            self.assertIn(key, de)
        for note in set(re.findall(r'note="([a-z_]+)"', src)):
            self.assertIn("bk_note_" + note, de)
        for state in ("read", "not_readable", "not_backed_up", "info"):
            self.assertIn("bk_state_" + state, de)
        from backup import SECTION_ORDER
        for section in SECTION_ORDER:
            self.assertIn("bk_sec_" + section, de)

    def test_frontend_backup_keys_in_both_languages(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        blocks = re.findall(r"Object\.assign\(I18N\.(de|en), \{(backupHome:.*?)\}\);", js, re.S)
        keys = {lang: set(re.findall(r"(\w+):'", body)) for lang, body in blocks}
        self.assertEqual(keys["de"], keys["en"])
        used = set(re.findall(r"t\('(backup\w+)'\)", js))
        self.assertTrue(used <= keys["de"], used - keys["de"])


class Routes(unittest.TestCase):
    def test_download_missing(self):
        client = APP.app.test_client()
        resp = client.get(f"/backup/download/nicht_da_{uuid.uuid4().hex[:6]}?kind=raw&lang=en")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(json.loads(resp.data)["error"], "Backup file not found.")


if __name__ == "__main__":
    unittest.main()
