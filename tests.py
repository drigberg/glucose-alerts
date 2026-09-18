import unittest
from main import GlucoseMonitor, AlertLevel, Config


test_config = Config(
    email_sender="test@example.com",
    signal_api_url="http://localhost:8080",
    signal_sender="+1234567890",
    signal_recipient="group.fake",
    libre_username="test@example.com",
    libre_password="test",
    force_send_test=False,
)

class TestGlucoseMonitor(unittest.TestCase):
    def test_get_current_alert_level_no_history(self):
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[],
            injected_alerts=[])
        self.assertEqual(monitor.get_current_alert_level(), None)

    def test_get_current_alert_level(self):
        param_list = [
            (27.8, None),
            (20.0, None),
            (15.1, None),
            (15.0, AlertLevel.GOOD),
            (10.1, AlertLevel.GOOD),
            (10.0, AlertLevel.TARGET),
            (7.6, AlertLevel.TARGET),
            (7.5, AlertLevel.WARNING),
            (5.1, AlertLevel.WARNING),
            (5.0, AlertLevel.EMERGENCY),
            (4.0, AlertLevel.EMERGENCY),
        ]
        for latest_value, expected_alert_level in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    config=test_config,
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[])
                self.assertEqual(monitor.get_current_alert_level(), expected_alert_level)
    def test_should_send_alert_no_history(self):
        param_list = [
            (9.0, AlertLevel.TARGET, "ALERT"),
            (7.0, AlertLevel.WARNING, "ALERT"),
            (5.0, AlertLevel.EMERGENCY, "ALERT"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    config=test_config,
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
                    config=test_config,
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[])
                alert = monitor.should_send_alert()
                self.assertEqual(alert, None)

    def test_should_send_alert_after_good_recovery(self):
        param_list = [
            (9.0, AlertLevel.TARGET, "ALERT"),
            (7.0, AlertLevel.WARNING, "ALERT"),
            (5.0, AlertLevel.EMERGENCY, "ALERT"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    config=test_config,
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"timestamp": "2026-09-17T12:00:00", "level":"TARGET", "type": "ALERT"},
                        {"timestamp": "2026-09-17T12:01:00", "level":"GOOD", "type": "RECOVERY"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)

    def test_should_send_alert_after_great_recovery(self):
        param_list = [
            (7.0, AlertLevel.WARNING, "ALERT"),
            (5.0, AlertLevel.EMERGENCY, "ALERT"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    config=test_config,
                    injected_data=[
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"timestamp": "2026-09-17T12:00:00", "level":"WARNING", "type": "ALERT"},
                        {"timestamp": "2026-09-17T12:01:00", "level":"TARGET", "type": "RECOVERY"}
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
                    config=test_config,
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"timestamp": "2026-09-17T11:00:00", "level":"EMERGENCY", "type": "ALERT"},
                        {"timestamp": "2026-09-17T11:01:00", "level":"WARNING", "type": "RECOVERY"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)

    def test_should_send_recovery_after_warning_recovery(self):
        param_list = [
            (11.0, AlertLevel.GOOD, "RECOVERY"),
            (9.0, AlertLevel.TARGET, "RECOVERY"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    config=test_config,
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": latest_value},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value},
                        {"timestamp": "2026-09-17T12:02:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"timestamp": "2026-09-17T11:00:00", "level":"EMERGENCY", "type": "ALERT"},
                        {"timestamp": "2026-09-17T11:01:00", "level":"WARNING", "type": "RECOVERY"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)
    def test_should_send_recovery_after_low_recovery(self):
        param_list = [
            (11.0, AlertLevel.GOOD, "RECOVERY"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    config=test_config,
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": latest_value},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value},
                        {"timestamp": "2026-09-17T12:02:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"timestamp": "2026-09-17T12:00:00", "level":"WARNING", "type": "ALERT"},
                        {"timestamp": "2026-09-17T12:01:00", "level":"TARGET", "type": "RECOVERY"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)

    def test_should_not_send_recovery_without_three_consecutive_values(self):
        """Recovery alerts should be suppressed if fewer than 3 recent values are above the threshold."""
        # Only 2 data points
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:00:00", "value": 11.0},
                {"timestamp": "2026-09-17T12:01:00", "value": 11.0}
            ],
            injected_alerts=[
                {"timestamp": "2026-09-17T12:00:00", "level":"WARNING", "type": "ALERT"}
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert, None)

    def test_should_not_send_recovery_if_recent_value_below_threshold(self):
        """Recovery should be suppressed if any of the last 3 values is below the last alert level's threshold."""
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:00:00", "value": 11.0},
                {"timestamp": "2026-09-17T12:01:00", "value": 7.0},
                {"timestamp": "2026-09-17T12:02:00", "value": 11.0}
            ],
            injected_alerts=[
                {"timestamp": "2026-09-17T12:01:00", "level":"WARNING", "type": "ALERT"}
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert, None)

    def test_should_send_alert_no_change(self):
        param_list = [
            (9.0, AlertLevel.TARGET),
            (6.0, AlertLevel.WARNING),
            (4.0, AlertLevel.EMERGENCY),
        ]
        for latest_value, alert_level in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    config=test_config,
                    injected_data=[
                        {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
                        {"timestamp": "2026-09-17T12:01:00", "value": latest_value}
                    ],
                    injected_alerts=[
                        {"timestamp": "2026-09-17T12:00:00", "level":"WARNING", "type": "ALERT"},
                        {"timestamp": "2026-09-17T12:01:00", "level": alert_level.name, "type": "ALERT"}
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert, None)

    def test_get_advice_alert(self):
        cases = [
            (AlertLevel.GOOD, "ALERT", "dropped to the upper half of his target range"),
            (AlertLevel.TARGET, "ALERT", "is in the perfect range"),
            (AlertLevel.WARNING, "ALERT", "trending a little low"),
            (AlertLevel.EMERGENCY, "ALERT", "dangerously low"),
        ]
        for level, alert_type, expected_snippet in cases:
            with self.subTest(f"{level.name}-{alert_type}"):
                monitor = GlucoseMonitor(config=test_config, injected_data=[], injected_alerts=[])
                advice = monitor.get_advice({"level": level, "type": alert_type})
                self.assertIn(expected_snippet, advice)

    def test_get_advice_recovery(self):
        cases = [
            (AlertLevel.GOOD, "RECOVERY", "still in a good place"),
            (AlertLevel.TARGET, "RECOVERY", "back into his target range"),
            (AlertLevel.WARNING, "RECOVERY", "recovering slightly"),
        ]
        for level, alert_type, expected_snippet in cases:
            with self.subTest(f"{level.name}-{alert_type}"):
                monitor = GlucoseMonitor(config=test_config, injected_data=[], injected_alerts=[])
                advice = monitor.get_advice({"level": level, "type": alert_type})
                self.assertIn(expected_snippet, advice)

    def test_get_todays_alerts(self):
        from datetime import datetime
        today = datetime.now().isoformat()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[],
            injected_alerts=[
                {"level": "WARNING", "type": "ALERT", "timestamp": "2025-01-01T12:00:00"},
                {"level": "TARGET", "type": "ALERT", "timestamp": today},
                {"level": "GOOD", "type": "RECOVERY", "timestamp": today},
            ])
        todays = monitor.get_todays_alerts()
        self.assertEqual(len(todays), 2)
        self.assertEqual(todays[0]["level"], "TARGET")
        self.assertEqual(todays[1]["level"], "GOOD")

    def test_format_email_body_text_contains_key_info(self):
        from datetime import datetime
        today = datetime.now().isoformat()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 4.5}
            ],
            injected_alerts=[
                {"level": "WARNING", "type": "ALERT", "timestamp": today},
            ])
        alert = {"level": AlertLevel.EMERGENCY, "type": "ALERT"}
        body = monitor.format_email_body_text(alert)
        self.assertIn("4.5", body)
        self.assertIn("ALERT", body)
        self.assertIn("EMERGENCY", body)
        self.assertIn("dangerously low", body)
        self.assertIn("Recent alerts today", body)

    def test_format_email_body_text_recovery(self):
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 12.0}
            ],
            injected_alerts=[])
        alert = {"level": AlertLevel.GOOD, "type": "RECOVERY"}
        body = monitor.format_email_body_text(alert)
        self.assertIn("12.0", body)
        self.assertIn("RECOVERY", body)
        self.assertIn("out of his target range, but still in a good place", body)

    def test_format_email_body_text_no_todays_alerts(self):
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 7.0}
            ],
            injected_alerts=[
                {"level": "WARNING", "type": "ALERT", "timestamp": "2025-01-01T12:00:00"},
            ])
        alert = {"level": AlertLevel.WARNING, "type": "ALERT"}
        body = monitor.format_email_body_text(alert)
        self.assertNotIn("Recent alerts today", body)

    def test_format_email_body_text_limits_to_five_alerts(self):
        from datetime import datetime
        today = datetime.now().isoformat()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 7.0}
            ],
            injected_alerts=[
                {"level": "WARNING", "type": "ALERT", "timestamp": today},
                {"level": "TARGET", "type": "RECOVERY", "timestamp": today},
                {"level": "WARNING", "type": "ALERT", "timestamp": today},
                {"level": "TARGET", "type": "RECOVERY", "timestamp": today},
                {"level": "WARNING", "type": "ALERT", "timestamp": today},
                {"level": "TARGET", "type": "RECOVERY", "timestamp": today},
                {"level": "EMERGENCY", "type": "ALERT", "timestamp": today},
            ])
        alert = {"level": AlertLevel.EMERGENCY, "type": "ALERT"}
        body = monitor.format_email_body_text(alert)
        alert_lines = [l for l in body.split("\n") if l.strip().startswith("—", 6)]
        self.assertEqual(len(alert_lines), 5)

    def test_format_email_body_html_contains_key_info(self):
        from datetime import datetime
        today = datetime.now().isoformat()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 4.5}
            ],
            injected_alerts=[
                {"level": "WARNING", "type": "ALERT", "timestamp": today},
            ])
        alert = {"level": AlertLevel.EMERGENCY, "type": "ALERT"}
        html = monitor.format_email_body_html(alert)
        self.assertIn("4.5", html)
        self.assertIn("EMERGENCY", html)
        self.assertIn("dangerously low", html)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Recent Alerts Today", html)
        self.assertIn("WARNING (ALERT)", html)

    def test_format_email_body_html_recovery(self):
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 12.0}
            ],
            injected_alerts=[])
        alert = {"level": AlertLevel.GOOD, "type": "RECOVERY"}
        html = monitor.format_email_body_html(alert)
        self.assertIn("12.0", html)
        self.assertIn("Recovery", html)
        self.assertIn("#039be5", html)

    def test_format_email_body_html_no_todays_alerts(self):
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 7.0}
            ],
            injected_alerts=[
                {"level": "WARNING", "type": "ALERT", "timestamp": "2025-01-01T12:00:00"},
            ])
        alert = {"level": AlertLevel.WARNING, "type": "ALERT"}
        html = monitor.format_email_body_html(alert)
        self.assertNotIn("Recent Alerts Today", html)

    def test_format_email_body_html_alert_uses_red(self):
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 4.5}
            ],
            injected_alerts=[])
        alert = {"level": AlertLevel.EMERGENCY, "type": "ALERT"}
        html = monitor.format_email_body_html(alert)
        self.assertIn("#c62828", html)

    def test_format_signal_message_alert(self):
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 4.5}
            ],
            injected_alerts=[])
        alert = {"level": AlertLevel.EMERGENCY, "type": "ALERT"}
        message = monitor.format_signal_message(alert)
        self.assertIn("4.5", message)
        self.assertIn("EMERGENCY", message)
        self.assertIn("⬇️", message)
        self.assertIn("dangerously low", message)

    def test_format_signal_message_recovery(self):
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 12.0}
            ],
            injected_alerts=[])
        alert = {"level": AlertLevel.GOOD, "type": "RECOVERY"}
        message = monitor.format_signal_message(alert)
        self.assertIn("12.0", message)
        self.assertIn("⬆️", message)
        self.assertIn("Recovery", message)

    def test_force_send_test_returns_test_alert(self):
        monitor = GlucoseMonitor(
            config=Config(
                email_sender="test@example.com",
                signal_api_url="http://localhost:8080",
                signal_sender="+31630645264",
                signal_recipient="group.YkpJNzZNME1mSlFiNW9qTU5QUnRWdFRGV2dhUzVkNjd3c2JVWjduMXNMOD0=",
                libre_username="test@example.com",
                libre_password="test",
                force_send_test=True),
            injected_data=[
                {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
            ],
            injected_alerts=[])
        alert = monitor.should_send_alert()
        self.assertEqual(alert["level"], AlertLevel.TEST)
        self.assertEqual(alert["type"], "ALERT")

    def test_force_send_test_ignores_current_level(self):
        """force_send_test should return a TEST alert regardless of the current glucose value."""
        monitor = GlucoseMonitor(
            config=Config(
                email_sender="test@example.com",
                signal_api_url="http://localhost:8080",
                signal_sender="+31630645264",
                signal_recipient="group.YkpJNzZNME1mSlFiNW9qTU5QUnRWdFRGV2dhUzVkNjd3c2JVWjduMXNMOD0=",
                libre_username="test@example.com",
                libre_password="test",
                force_send_test=True),
            injected_data=[
                {"timestamp": "2026-09-17T12:00:00", "value": 4.0},
            ],
            injected_alerts=[
                {"timestamp": "2026-09-17T11:55:00", "level": "EMERGENCY", "type": "ALERT"},
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert["level"], AlertLevel.TEST)
        self.assertEqual(alert["type"], "ALERT")

    def test_get_advice_test_alert(self):
        monitor = GlucoseMonitor(config=test_config, injected_data=[], injected_alerts=[])
        advice = monitor.get_advice({"level": AlertLevel.TEST, "type": "ALERT"})
        self.assertIn("test", advice.lower())

    def test_format_email_body_html_test_uses_violet(self):
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 20.0}
            ],
            injected_alerts=[])
        alert = {"level": AlertLevel.TEST, "type": "ALERT"}
        html = monitor.format_email_body_html(alert)
        self.assertIn("#8e24aa", html)
        self.assertIn("TEST", html)

    def test_format_signal_message_test(self):
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 20.0}
            ],
            injected_alerts=[])
        alert = {"level": AlertLevel.TEST, "type": "ALERT"}
        message = monitor.format_signal_message(alert)
        self.assertIn("20.0", message)
        self.assertIn("TEST", message)
        self.assertIn("test", message.lower())

if __name__ == '__main__':
    unittest.main()