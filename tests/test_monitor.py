"""Service Monitor (/monitor): Requests, Prüfungen, Gerätename, Zurücklesen, Entfernen, Maskierung, Backup."""
import unittest

from _helpers import APP, default_profile
from backup import DeviceBackup
from messages import LocalizedError
from readback import DeviceReader, plan_requests
from service_definitions import (
    build_monitor_requests, mask_recipient, parse_monitor_recipient, relative_data_point,
)

DEV = "ifm-AL1590-000251100049"
ITEM = {"id": 7, "data_points": ["/devicestatus/temperature/cpu", f"{DEV}/iolinkmaster/port[1]/iolinkdevice/pdin"],
        "sample_interval": 1000, "notify_interval": 5000, "data_changed": True, "description": "Temperatur",
        "persist": True, "recipient": {"scheme": "mqtts", "host": "broker.local", "port": 8883, "topic": "al15/temp",
                                       "user": "u1", "password": "geheim"}}


def device(items):
    return DeviceReader(lambda adr: {"code": 200, "data": {"items": items}} if adr == "/monitor/getitems" else {"code": 404})


def bound(data):
    reqs = APP.bind_monitor_requests([dict(r.__dict__, section="service_monitor") for r in build_monitor_requests(data)], DEV)
    return reqs


class Requests(unittest.TestCase):
    def test_payload(self):
        req = build_monitor_requests({"items": [ITEM]})[0]
        self.assertEqual(req.adr, "/monitor/add")
        self.assertEqual(req.data["data_points"], ["/devicestatus/temperature/cpu", "/iolinkmaster/port[1]/iolinkdevice/pdin"])
        self.assertEqual(req.data["recipient"], "mqtts://u1:geheim@broker.local:8883/al15/temp")
        self.assertEqual((req.data["id"], req.data["data_changed"], req.data["persist"], req.data["description"]), (7, True, True, "Temperatur"))

    def test_defaults_and_text_input(self):
        item = {"data_points": "/a/b\n/c/d", "sample_interval": "500", "notify_interval": 500,
                "recipient": {"scheme": "mqtt", "host": "10.0.0.1", "topic": "/x"}}
        data = build_monitor_requests({"items": [item]})[0].data
        self.assertEqual(data["data_points"], ["/a/b", "/c/d"])
        self.assertEqual(data["recipient"], "mqtt://10.0.0.1:1883/x")  # Standardport, ohne Zugangsdaten
        self.assertNotIn("id", data)
        self.assertTrue(data["persist"])

    def test_validation(self):
        cases = [({"data_points": []}, "monitor_datapoints"), ({"sample_interval": 0}, "monitor_interval"),
                 ({"recipient": dict(ITEM["recipient"], scheme="http")}, "monitor_scheme"),
                 ({"recipient": dict(ITEM["recipient"], host="")}, "monitor_host"),
                 ({"recipient": dict(ITEM["recipient"], topic="")}, "monitor_topic"),
                 ({"recipient": dict(ITEM["recipient"], port=70000)}, "monitor_port"),
                 ({"recipient": dict(ITEM["recipient"], password="a@b")}, "monitor_credentials")]
        for change, key in cases:
            with self.assertRaises(LocalizedError) as ctx:
                build_monitor_requests({"items": [dict(ITEM, **change)]})
            self.assertEqual(ctx.exception.key, key)
        with self.assertRaises(LocalizedError) as ctx:
            build_monitor_requests({"items": [ITEM, ITEM]})
        self.assertEqual(ctx.exception.key, "monitor_id_duplicate")

    def test_recipient_helpers(self):
        parsed = parse_monitor_recipient("mqtt://user:pw@192.168.0.2:1883/test/monitor")
        self.assertEqual((parsed["host"], parsed["port"], parsed["topic"], parsed["user"], parsed["password"]),
                         ("192.168.0.2", 1883, "test/monitor", "user", "pw"))
        self.assertEqual(mask_recipient("mqtt://user:pw@h:1/t"), "mqtt://user:***@h:1/t")
        self.assertEqual(relative_data_point(f"{DEV}/devicestatus/x"), "/devicestatus/x")

    def test_order_before_https_and_network(self):
        p = default_profile()
        p["service_monitor"]["items"] = [ITEM]
        p["connections_https"]["port"] = 443
        p["connections_mqtt_command_channel"]["qos"] = 1
        sections = [r["section"] for r in APP.compile_requests(p)]
        self.assertEqual(sections, ["connections_mqtt_command_channel", "service_monitor", "connections_https"])


class Binding(unittest.TestCase):
    def test_device_name_is_prefixed(self):
        req = bound({"items": [dict(ITEM, sample_condition="/devicestatus/x")]})[0]
        self.assertEqual(req["data"]["data_points"][0], f"{DEV}/devicestatus/temperature/cpu")
        self.assertEqual(req["data"]["sample_condition"], f"{DEV}/devicestatus/x")


class Readback(unittest.TestCase):
    def device_item(self, **change):
        data = bound({"items": [ITEM]})[0]["data"]
        return dict(data, **change)

    def test_same_item_is_skipped(self):
        decision = plan_requests(device([self.device_item()]), bound({"items": [ITEM]}))[0][1]
        self.assertEqual(decision["decision"], "skip")
        self.assertNotIn("geheim", str(decision))  # Passwort maskiert

    def test_changed_or_missing_item_is_written(self):
        reqs = bound({"items": [ITEM]})
        self.assertEqual(plan_requests(device([self.device_item(notify_interval=1)]), reqs)[0][1]["decision"], "write")
        self.assertEqual(plan_requests(device([]), reqs)[0][1]["reason"], "monitor_new")

    def test_description_ignored_when_device_omits_it(self):
        item = self.device_item(); item.pop("description")
        self.assertEqual(plan_requests(device([item]), bound({"items": [ITEM]}))[0][1]["decision"], "skip")

    def test_item_without_id_matches_by_content(self):
        no_id = dict(ITEM); no_id.pop("id")
        existing = self.device_item(id=3)
        decision = plan_requests(device([existing]), bound({"items": [no_id]}))[0][1]
        self.assertEqual((decision["decision"], decision["reason"]), ("skip", "monitor_same_content"))

    def test_remove_unlisted(self):
        other = {"id": 1, "data_points": [f"{DEV}/devicestatus/temperature/cpu"], "sample_interval": 1000, "notify_interval": 1000,
                 "recipient": "mqtt://192.168.0.2:1883/test/monitor"}
        planned = plan_requests(device([self.device_item(), other]), bound({"items": [ITEM], "remove_unlisted": True}))
        self.assertEqual(planned[1][0]["adr"], "/monitor/remove_unlisted")
        self.assertEqual(planned[1][1]["target"], {"remove_ids": [1]})
        planned = plan_requests(device([self.device_item()]), bound({"items": [ITEM], "remove_unlisted": True}))
        self.assertEqual(planned[1][1]["decision"], "skip")

    def test_no_removal_without_option(self):
        reqs = bound({"items": [ITEM]})
        self.assertEqual([r["adr"] for r in reqs], ["/monitor/add"])


class Masking(unittest.TestCase):
    def test_preview_masks_password(self):
        p = default_profile(); p["service_monitor"]["items"] = [ITEM]
        rows = APP.app.test_client().post("/preview", json=p).get_json()["requests"]
        self.assertNotIn("geheim", str(rows))
        self.assertIn("u1:***@broker.local", str(rows))


class Backup(unittest.TestCase):
    def test_items_are_backed_up_without_device_name(self):
        item = bound({"items": [ITEM]})[0]["data"]
        reader = DeviceReader(lambda adr: {"code": 200, "data": {"items": [item]}} if adr == "/monitor/getitems" else {"code": 404})
        job = DeviceBackup(reader, "t")
        rows = [r for r in job.rows() if r["section"] == "service_monitor"]
        entry = job.profile["service_monitor"]["items"][0]
        self.assertEqual(entry["data_points"], ["/devicestatus/temperature/cpu", "/iolinkmaster/port[1]/iolinkdevice/pdin"])
        self.assertEqual(entry["recipient"]["password"], "geheim")
        self.assertEqual(rows[0]["note"], "monitor_credentials")
        self.assertNotIn("geheim", str(rows))
        # Rundlauf: Backup-Eintrag gegen dasselbe Gerät -> unverändert
        reqs = APP.bind_monitor_requests([dict(r.__dict__) for r in build_monitor_requests(job.profile["service_monitor"])], DEV)
        self.assertEqual(plan_requests(device([item]), reqs)[0][1]["decision"], "skip")


if __name__ == "__main__":
    unittest.main()
