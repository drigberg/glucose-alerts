from datetime import datetime, timedelta
import unittest
from main import GlucoseMonitor, AlertLevel, Config


test_config = Config(
    email_sender="test@example.com",
    signal_api_url="http://localhost:8080",
    signal_sender="+1234567890",
    signal_recipient="group.fake",
    signal_emergency_recipient="group2.fake",
    libre_username="test@example.com",
    libre_password="test",
    force_send_test=False,
    send_test_alerts_to_emergency_recipient=False,
)

class TestGlucoseMonitor(unittest.TestCase):
    def test_get_current_alert_level_no_history(self):
        """With no data, the default value (27.8) is at the SILENT threshold."""
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[],
            injected_alerts=[])
        self.assertEqual(monitor.get_current_alert_level(), AlertLevel.SILENT)

    def test_get_current_alert_level(self):
        param_list = [
            (27.9, None),
            (27.8, AlertLevel.SILENT),
            (20.0, AlertLevel.SILENT),
            (15.1, AlertLevel.SILENT),
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
            (27.9),
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

    def test_should_send_recovery_after_warning_alert(self):
        """After WARNING alert, 3+ values in the 30-minute window above WARNING threshold triggers recovery."""
        now = datetime.now()
        param_list = [
            (11.0, AlertLevel.GOOD, "RECOVERY"),
            (9.0, AlertLevel.TARGET, "RECOVERY"),
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    config=test_config,
                    injected_data=[
                        {"timestamp": (now - timedelta(minutes=25)).isoformat(), "value": latest_value},
                        {"timestamp": (now - timedelta(minutes=20)).isoformat(), "value": latest_value},
                        {"timestamp": (now - timedelta(minutes=15)).isoformat(), "value": latest_value}
                    ],
                    injected_alerts=[
                        {"timestamp": (now - timedelta(minutes=30)).isoformat(), "level":"WARNING", "type": "ALERT"},
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)

    def test_should_send_recovery_after_emergency_alert(self):
        """After EMERGENCY alert, 3+ values in the 3-minute window above EMERGENCY threshold triggers recovery."""
        now = datetime.now()
        param_list = [
            (11.0, AlertLevel.GOOD, "RECOVERY"),
            (9.0, AlertLevel.TARGET, "RECOVERY"),
            (7.0, AlertLevel.WARNING, "RECOVERY"),  # Above EMERGENCY (5.0), at/below WARNING (7.5)
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    config=test_config,
                    injected_data=[
                        {"timestamp": (now - timedelta(minutes=2, seconds=30)).isoformat(), "value": latest_value},
                        {"timestamp": (now - timedelta(minutes=1, seconds=30)).isoformat(), "value": latest_value},
                        {"timestamp": (now - timedelta(seconds=30)).isoformat(), "value": latest_value}
                    ],
                    injected_alerts=[
                        {"timestamp": (now - timedelta(minutes=3)).isoformat(), "level":"EMERGENCY", "type": "ALERT"},
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)

    def test_should_send_recovery_after_target_alert(self):
        now = datetime.now()
        param_list = [
            (11.0, AlertLevel.GOOD, "RECOVERY"),
            (20.5, AlertLevel.SILENT, "RECOVERY"),  # Above TARGET threshold (10.0), returns GOOD
        ]
        for latest_value, expected_alert_level, expected_alert_type in param_list:
            with self.subTest(latest_value):
                monitor = GlucoseMonitor(
                    config=test_config,
                    injected_data=[
                        {"timestamp": (now - timedelta(minutes=118)).isoformat(), "value": latest_value},
                        {"timestamp": (now - timedelta(minutes=57)).isoformat(), "value": latest_value},
                        {"timestamp": (now - timedelta(minutes=15)).isoformat(), "value": latest_value}
                    ],
                    injected_alerts=[
                        {"timestamp": (now - timedelta(minutes=121)).isoformat(), "level":"TARGET", "type": "ALERT"},
                    ])
                alert = monitor.should_send_alert()
                self.assertEqual(alert["level"], expected_alert_level)
                self.assertEqual(alert["type"], expected_alert_type)

    def test_should_send_recovery_after_good_recovery(self):
        """After a GOOD recovery, further improvement (e.g., to SILENT) should trigger recovery."""
        from datetime import datetime, timedelta
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(minutes=238)).isoformat(), "value": 20.0},
                {"timestamp": (now - timedelta(minutes=60)).isoformat(), "value": 20.0},
                {"timestamp": (now - timedelta(minutes=15)).isoformat(), "value": 20.0}
            ],
            injected_alerts=[
                {"timestamp": (now - timedelta(minutes=300)).isoformat(), "level": "TARGET", "type": "ALERT"},
                {"timestamp": (now - timedelta(minutes=239)).isoformat(), "level": "GOOD", "type": "RECOVERY"}
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert["level"], AlertLevel.SILENT)
        self.assertEqual(alert["type"], "RECOVERY")

    def test_should_send_recovery_after_target_recovery(self):
        """After a TARGET recovery, further improvement (e.g., to GOOD) should trigger recovery."""
        from datetime import datetime, timedelta
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(minutes=119)).isoformat(), "value": 12.0},
                {"timestamp": (now - timedelta(minutes=50)).isoformat(), "value": 12.0},
                {"timestamp": (now - timedelta(minutes=45)).isoformat(), "value": 12.0}
            ],
            injected_alerts=[
                {"timestamp": (now - timedelta(minutes=121)).isoformat(), "level": "WARNING", "type": "ALERT"},
                {"timestamp": (now - timedelta(minutes=119)).isoformat(), "level": "TARGET", "type": "RECOVERY"}
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert["level"], AlertLevel.GOOD)
        self.assertEqual(alert["type"], "RECOVERY")

    def test_should_send_recovery_after_warning_recovery(self):
        """After a WARNING recovery, further improvement (e.g., to TARGET) should trigger recovery."""
        from datetime import datetime, timedelta
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(minutes=25)).isoformat(), "value": 9.0},
                {"timestamp": (now - timedelta(minutes=20)).isoformat(), "value": 9.0},
                {"timestamp": (now - timedelta(minutes=15)).isoformat(), "value": 9.0}
            ],
            injected_alerts=[
                {"timestamp": (now - timedelta(minutes=3)).isoformat(), "level": "EMERGENCY", "type": "ALERT"},
                {"timestamp": (now - timedelta(minutes=2)).isoformat(), "level": "WARNING", "type": "RECOVERY"}
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert["level"], AlertLevel.TARGET)
        self.assertEqual(alert["type"], "RECOVERY")

    def test_should_not_send_recovery_without_three_consecutive_values(self):
        """Recovery alerts should be suppressed if fewer than 3 recent values are above the threshold."""
        now = datetime.now()
        # Only 2 data points
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(minutes=2)).isoformat(), "value": 11.0},
                {"timestamp": (now - timedelta(minutes=1)).isoformat(), "value": 11.0}
            ],
            injected_alerts=[
                {"timestamp": (now - timedelta(minutes=30)).isoformat(), "level":"WARNING", "type": "ALERT"}
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert, None)

    def test_should_not_send_recovery_if_recent_value_below_threshold(self):
        """Recovery should be suppressed if any value in the window is below the alert level's threshold."""
        from datetime import datetime, timedelta
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(minutes=25)).isoformat(), "value": 11.0},
                {"timestamp": (now - timedelta(minutes=15)).isoformat(), "value": 7.0},  # Below WARNING threshold
                {"timestamp": (now - timedelta(minutes=5)).isoformat(), "value": 11.0}
            ],
            injected_alerts=[
                {"timestamp": (now - timedelta(minutes=30)).isoformat(), "level":"WARNING", "type": "ALERT"}
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert, None)

    def test_should_not_send_recovery_if_outside_window(self):
        """Recovery should be suppressed if all 3+ values are outside the recovery window."""
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(minutes=35)).isoformat(), "value": 11.0},
                {"timestamp": (now - timedelta(minutes=33)).isoformat(), "value": 11.0},
                {"timestamp": (now - timedelta(minutes=31)).isoformat(), "value": 11.0}
            ],
            injected_alerts=[
                {"timestamp": (now - timedelta(minutes=40)).isoformat(), "level":"WARNING", "type": "ALERT"}
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert, None)

    def test_should_send_alert_no_change(self):
        param_list = [
            (16.0, AlertLevel.SILENT),
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

    def test_silent_recovery(self):
        """SILENT level should produce a RECOVERY alert (saved but not sent)."""
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(minutes=55)).isoformat(), "value": 16.0},
                {"timestamp": (now - timedelta(minutes=50)).isoformat(), "value": 16.0},
                {"timestamp": (now - timedelta(minutes=45)).isoformat(), "value": 16.0}
            ],
            injected_alerts=[
                {"timestamp": (now - timedelta(minutes=60)).isoformat(), "level": "TARGET", "type": "ALERT"},
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert["level"], AlertLevel.SILENT)
        self.assertEqual(alert["type"], "RECOVERY")

    def test_should_send_alert_after_silent_recovery(self):
        """After a SILENT recovery, a drop back to GOOD should send an alert."""
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:00:00", "value": 27.8},
                {"timestamp": "2026-09-17T12:01:00", "value": 12.0}
            ],
            injected_alerts=[
                {"timestamp": "2026-09-17T11:00:00", "level": "TARGET", "type": "ALERT"},
                {"timestamp": "2026-09-17T11:30:00", "level": "SILENT", "type": "RECOVERY"}
            ])
        alert = monitor.should_send_alert()
        self.assertEqual(alert["level"], AlertLevel.GOOD)
        self.assertEqual(alert["type"], "ALERT")

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
        self.assertIn("Alert", body)
        self.assertIn("Emergency", body)
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
        self.assertIn("Recovery", body)
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
        self.assertIn("Emergency", html)
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

    def test_format_graph_svg_not_enough_data(self):
        """With fewer than 2 data points, a placeholder message is shown instead of a graph."""
        monitor = GlucoseMonitor(config=test_config, injected_data=[], injected_alerts=[])
        svg = monitor.format_graph_svg()
        self.assertIn("<svg", svg)
        self.assertIn("Not enough data for graph", svg)
        self.assertNotIn("<polyline", svg)

    def test_format_graph_svg_renders_polyline_for_recent_data(self):
        """Data within the last 12 hours should be rendered as a connected polyline."""
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(hours=2)).isoformat(), "value": 10.0},
                {"timestamp": (now - timedelta(hours=1, minutes=55)).isoformat(), "value": 10.5},
                {"timestamp": (now - timedelta(hours=1, minutes=50)).isoformat(), "value": 11.0},
            ],
            injected_alerts=[])
        svg = monitor.format_graph_svg()
        self.assertIn("<svg", svg)
        self.assertIn("<polyline", svg)
        # All 3 points should be part of a single unbroken segment (only 1 polyline).
        self.assertEqual(svg.count("<polyline"), 1)

    def test_format_graph_svg_excludes_data_older_than_window(self):
        """Data older than the 12-hour window should not affect the graph."""
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(hours=20)).isoformat(), "value": 2.0},
                {"timestamp": (now - timedelta(hours=2)).isoformat(), "value": 10.0},
                {"timestamp": (now - timedelta(hours=1)).isoformat(), "value": 11.0},
            ],
            injected_alerts=[])
        recent_data = monitor.get_recent_data()
        self.assertEqual(len(recent_data), 2)

    def test_format_graph_svg_breaks_line_on_gap(self):
        """A gap larger than the threshold between consecutive readings should split the line into
        separate segments, representing missing data as a visual gap."""
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(hours=4)).isoformat(), "value": 10.0},
                {"timestamp": (now - timedelta(hours=3, minutes=55)).isoformat(), "value": 10.5},
                # Large gap here (over an hour) should break the line into a new segment.
                {"timestamp": (now - timedelta(hours=1)).isoformat(), "value": 11.0},
                {"timestamp": (now - timedelta(minutes=55)).isoformat(), "value": 11.5},
            ],
            injected_alerts=[])
        svg = monitor.format_graph_svg()
        self.assertEqual(svg.count("<polyline"), 2)

    def test_format_graph_svg_no_gap_within_threshold(self):
        """Consecutive readings within the gap threshold should remain a single segment."""
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(minutes=20)).isoformat(), "value": 10.0},
                {"timestamp": (now - timedelta(minutes=12)).isoformat(), "value": 10.5},
                {"timestamp": (now - timedelta(minutes=5)).isoformat(), "value": 11.0},
            ],
            injected_alerts=[])
        svg = monitor.format_graph_svg()
        self.assertEqual(svg.count("<polyline"), 1)

    def test_format_graph_svg_draws_isolated_reading_as_dot(self):
        """A reading with no neighbour within the gap threshold should still be visible, as a dot."""
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(hours=3)).isoformat(), "value": 10.0},
                {"timestamp": (now - timedelta(minutes=10)).isoformat(), "value": 11.0},
                {"timestamp": (now - timedelta(minutes=5)).isoformat(), "value": 12.0},
            ],
            injected_alerts=[])
        svg = monitor.format_graph_svg()
        self.assertEqual(svg.count("<circle"), 1)
        self.assertEqual(svg.count("<polyline"), 1)

    def test_format_email_body_html_uses_provided_graph_html(self):
        """Emails reference the graph as an inline cid image instead of inline SVG, which Gmail strips."""
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(minutes=10)).isoformat(), "value": 10.0},
                {"timestamp": (now - timedelta(minutes=5)).isoformat(), "value": 11.0},
            ],
            injected_alerts=[])
        alert = {"level": AlertLevel.TARGET, "type": "ALERT"}
        html = monitor.format_email_body_html(alert, graph_html='<img src="cid:glucose-graph" />')
        self.assertIn('src="cid:glucose-graph"', html)
        self.assertNotIn("<svg", html)

    def test_build_raw_message_attaches_inline_image(self):
        from email_client import EmailClient
        message = EmailClient(sender="test@example.com").build_raw_message(
            recipients=["to@example.com"],
            subject="Subject",
            body_text="text",
            body_html='<img src="cid:glucose-graph" />',
            inline_images={"glucose-graph": b"\x89PNG\r\n\x1a\nfake"})
        self.assertEqual(message.get_content_type(), "multipart/related")
        parts = message.get_payload()
        self.assertEqual(parts[0].get_content_type(), "multipart/alternative")
        self.assertEqual(parts[1].get_content_type(), "image/png")
        self.assertEqual(parts[1]["Content-ID"], "<glucose-graph>")

    def test_format_email_body_html_includes_graph(self):
        """The rendered email HTML should include the graph SVG and its section heading."""
        now = datetime.now()
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": (now - timedelta(minutes=10)).isoformat(), "value": 10.0},
                {"timestamp": (now - timedelta(minutes=5)).isoformat(), "value": 11.0},
                {"timestamp": (now - timedelta(minutes=1)).isoformat(), "value": 12.0},
            ],
            injected_alerts=[])
        alert = {"level": AlertLevel.TARGET, "type": "ALERT"}
        html = monitor.format_email_body_html(alert)
        self.assertIn("Last 12 Hours", html)
        self.assertIn("<svg", html)
        self.assertIn("<polyline", html)

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
        self.assertIn("Emergency", message)
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

    def test_format_signal_message_test_alert_emergency_recipient(self):
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 14.5}
            ],
            injected_alerts=[])
        alert = {"level": AlertLevel.TEST, "type": "ALERT"}
        message = monitor.format_signal_message(alert, to_emergency_recipient=True)
        self.assertIn("14.5", message)
        self.assertIn("Emergency Test", message)
        self.assertIn("just a test", message)

    def test_format_signal_message_test_recovery_emergency_recipient(self):
        monitor = GlucoseMonitor(
            config=test_config,
            injected_data=[
                {"timestamp": "2026-09-17T12:01:00", "value": 15.5}
            ],
            injected_alerts=[])
        alert = {"level": AlertLevel.TEST, "type": "ALERT"}
        message = monitor.format_signal_message(alert, to_emergency_recipient=True)
        self.assertIn("15.5", message)
        self.assertIn("Emergency Test", message)
        self.assertIn("just a test", message)


    def test_force_send_test_returns_test_alert(self):
        monitor = GlucoseMonitor(
            config=Config(
                email_sender="test@example.com",
                signal_api_url="http://localhost:8080",
                signal_sender="+31630645264",
                signal_recipient="group.YkpJNzZNME1mSlFiNW9qTU5QUnRWdFRGV2dhUzVkNjd3c2JVWjduMXNMOD0=",
                signal_emergency_recipient=None,
                libre_username="test@example.com",
                libre_password="test",
                force_send_test=True,
                send_test_alerts_to_emergency_recipient=False),
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
                signal_emergency_recipient=None,
                libre_username="test@example.com",
                libre_password="test",
                force_send_test=True,
                send_test_alerts_to_emergency_recipient=False),
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
        self.assertIn("Test", html)

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
        self.assertIn("Test", message)
        self.assertIn("test", message.lower())

if __name__ == '__main__':
    unittest.main()