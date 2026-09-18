import unittest
from main import GlucoseMonitor, AlertLevel

class TestGlucoseMonitor(unittest.TestCase):
    def test_get_current_alert_level(self):
        param_list = [
            (20.0, AlertLevel.NONE),
            (10.1, AlertLevel.NONE),
            (10.0, AlertLevel.SOFT),
            (7.6, AlertLevel.SOFT),
            (7.5, AlertLevel.WARNING),
            (5.1, AlertLevel.WARNING),
            (5.0, AlertLevel.EMERGENCY),
            (4.0, AlertLevel.EMERGENCY),
        ]
        for latest_value, expected_alert_level in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 100.0},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[])
                self.assertEqual(monitor.get_current_alert_level(), expected_alert_level)
    def test_should_send_alert_no_history(self):
        param_list = [
            (9.0, AlertLevel.SOFT, "ALERT"),
            (7.0, AlertLevel.WARNING, "ALERT"),
            (5.0, AlertLevel.EMERGENCY, "ALERT"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 100.0},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)
    def test_should_not_send_alert_no_history(self):
        param_list = [
            (10.1),
            (11.0),
            (20.0),
        ]
        for latest_value in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 100.0},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[])
                alert = monitor.should_send_alert()
                self.assertEqual(alert, None)

    def test_should_send_alert_after_none_recovery(self):
        param_list = [
            (9.0, AlertLevel.SOFT, "ALERT"),
            (7.0, AlertLevel.WARNING, "ALERT"),
            (5.0, AlertLevel.EMERGENCY, "ALERT"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 100.0},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"level":"SOFT", "type": "ALERT"},
                        {"level":"NONE", "type": "RECOVERY"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)

    def test_should_send_alert_after_soft_recovery(self):
        param_list = [
            (7.0, AlertLevel.WARNING, "ALERT"),
            (5.0, AlertLevel.EMERGENCY, "ALERT"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"level":"WARNING", "type": "ALERT"},
                        {"level":"SOFT", "type": "RECOVERY"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)

    def test_should_send_alert_after_warning_recovery(self):
        param_list = [
            (5.0, AlertLevel.EMERGENCY, "ALERT"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 100.0},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"level":"EMERGENCY", "type": "ALERT"},
                        {"level":"WARNING", "type": "RECOVERY"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)

    def test_should_send_recovery_after_warning_recovery(self):
        param_list = [
            (11.0, AlertLevel.NONE, "RECOVERY"),
            (9.0, AlertLevel.SOFT, "RECOVERY"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 100.0},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"level":"EMERGENCY", "type": "ALERT"},
                        {"level":"WARNING", "type": "RECOVERY"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)
    def test_should_send_recovery_after_soft_recovery(self):
        param_list = [
            (11.0, AlertLevel.NONE, "RECOVERY"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 100.0},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"level":"WARNING", "type": "ALERT"},
                        {"level":"SOFT", "type": "RECOVERY"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)
    def test_should_send_alert_no_change(self):
        param_list = [
            (9.0, AlertLevel.SOFT),
            (6.0, AlertLevel.WARNING),
            (4.0, AlertLevel.EMERGENCY),
        ]
        for latest_value, alert_level in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 100.0},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"level":"WARNING", "type": "ALERT"},
                        {"level": alert_level.name, "type": "ALERT"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert, None)

if __name__ == '__main__':
    unittest.main()