import unittest
from main import GlucoseMonitor, AlertLevel

class TestGlucoseMonitor(unittest.TestCase):
    def test_alert_level_none(self):
        monitor = GlucoseMonitor(
            injected_data=[
                {"timestamp": "2026-09-17T12:00:00", "value": 5.0},
                {"timestamp": "2026-09-17T12:00:00", "value": 20.0}
            ],
            injected_alerts=[])
        self.assertEqual(monitor.get_alert_level(), AlertLevel.NONE)
    def test_alert_level_soft(self):
        monitor = GlucoseMonitor(
            injected_data=[
                {"timestamp": "2026-09-17T12:00:00", "value": 1.0},
                {"timestamp": "2026-09-17T12:00:00", "value": 9.0}
            ],
            injected_alerts=[])
        self.assertEqual(monitor.get_alert_level(), AlertLevel.SOFT)
    def test_alert_level_warning(self):
        monitor = GlucoseMonitor(
            injected_data=[
                {"timestamp": "2026-09-17T12:00:00", "value": 1.0},
                {"timestamp": "2026-09-17T12:00:00", "value": 6.0}
            ],
            injected_alerts=[])
        self.assertEqual(monitor.get_alert_level(), AlertLevel.WARNING)
    def test_alert_level_emergency(self):
        monitor = GlucoseMonitor(
            injected_data=[
                {"timestamp": "2026-09-17T12:00:00", "value": 9.0},
                {"timestamp": "2026-09-17T12:00:00", "value": 1.0}
            ],
            injected_alerts=[])
        self.assertEqual(monitor.get_alert_level(), AlertLevel.EMERGENCY)
if __name__ == '__main__':
    unittest.main()