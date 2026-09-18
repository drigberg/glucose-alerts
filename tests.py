import unittest
from main import GlucoseMonitor, AlertLevel

class TestGlucoseMonitor(unittest.TestCase):
    def test_get_current_alert_level_no_history(self):
        monitor = GlucoseMonitor(
            injected_data=[],
            injected_alerts=[])
        self.assertEqual(monitor.get_current_alert_level(), None)

    def test_get_current_alert_level(self):
        param_list = [
            (27.8, None),
            (20.0, None),
            (15.1, None),
            (15.0, AlertLevel.TARGET),
            (10.1, AlertLevel.TARGET),
            (10.0, AlertLevel.LOW),
            (7.6, AlertLevel.LOW),
            (7.5, AlertLevel.WARNING),
            (5.1, AlertLevel.WARNING),
            (5.0, AlertLevel.EMERGENCY),
            (4.0, AlertLevel.EMERGENCY),
        ]
        for latest_value, expected_alert_level in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[])
                self.assertEqual(monitor.get_current_alert_level(), expected_alert_level)
    def test_should_send_alert_no_history(self):
        param_list = [
            (9.0, AlertLevel.LOW, "ALERT"),
            (7.0, AlertLevel.WARNING, "ALERT"),
            (5.0, AlertLevel.EMERGENCY, "ALERT"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)
    def test_should_not_send_alert_no_history(self):
        param_list = [
            (15.1),
            (20.0),
            (27.8),
        ]
        for latest_value in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[])
                alert = monitor.should_send_alert()
                self.assertEqual(alert, None)

    def test_should_send_alert_after_target_recovery(self):
        param_list = [
            (9.0, AlertLevel.LOW, "ALERT"),
            (7.0, AlertLevel.WARNING, "ALERT"),
            (5.0, AlertLevel.EMERGENCY, "ALERT"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"level":"LOW", "type": "ALERT"},
                        {"level":"TARGET", "type": "RECOVERY"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)

    def test_should_send_alert_after_low_recovery(self):
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
                        {"level":"LOW", "type": "RECOVERY"}
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
                        {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
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
            (11.0, AlertLevel.TARGET, "RECOVERY"),
            (9.0, AlertLevel.LOW, "RECOVERY"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": latest_value},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value},
                        {"timestamp": "2026-09-17T12:02:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"level":"EMERGENCY", "type": "ALERT"},
                        {"level":"WARNING", "type": "RECOVERY"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)
    def test_should_send_recovery_after_low_recovery(self):
        param_list = [
            (11.0, AlertLevel.TARGET, "RECOVERY"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": latest_value},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value},
                        {"timestamp": "2026-09-17T12:02:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"level":"WARNING", "type": "ALERT"},
                        {"level":"LOW", "type": "RECOVERY"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)

    def test_should_not_send_recovery_without_three_consecutive_values(self):
        """Recovery alerts should be suppressed if fewer than 3 recent values are above the threshold."""
        # Only 2 data points
        monitor = GlucoseMonitor(
            injected_data=[
                {"timestamp": "2026-09-17T12:00:00", "value": 11.0},
                {"timestamp": "2026-09-17T12:01:00", "value": 11.0}
            ],
            injected_alerts=[
                {"level":"WARNING", "type": "ALERT"}
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert, None)

    def test_should_not_send_recovery_if_recent_value_below_threshold(self):
        """Recovery should be suppressed if any of the last 3 values is below the last alert level's threshold."""
        monitor = GlucoseMonitor(
            injected_data=[
                {"timestamp": "2026-09-17T12:00:00", "value": 11.0},
                {"timestamp": "2026-09-17T12:01:00", "value": 7.0},
                {"timestamp": "2026-09-17T12:02:00", "value": 11.0}
            ],
            injected_alerts=[
                {"level":"WARNING", "type": "ALERT"}
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert, None)

    def test_should_send_alert_no_change(self):
        param_list = [
            (9.0, AlertLevel.LOW),
            (6.0, AlertLevel.WARNING),
            (4.0, AlertLevel.EMERGENCY),
        ]
        for latest_value, alert_level in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
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