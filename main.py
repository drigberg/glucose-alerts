import json
import os
import typing
from pylibrelinkup import PyLibreLinkUp, GraphResponse
from dotenv import load_dotenv
from datetime import datetime
from enum import Enum
import uuid

MIN_SECONDS_SINCE_LAST_DATA_FOR_FETCH = 50.0

SOFT_THRESHOLD = 10.0
WARNING_THRESHOLD = 7.5
EMERGENCY_THRESHOLD = 5.0

class AlertLevel(Enum):
    NONE = 3
    SOFT = 2
    WARNING = 1
    EMERGENCY = 0

def log(message: str):
    print(f"[glucose-alerts] [{datetime.now().isoformat()}] - {message}")

class GlucoseMonitor:
    client: PyLibreLinkUp
    data: typing.Any
    alerts: typing.Any

    def __init__(self, injected_data=None, injected_alerts=None):
        load_dotenv()
        self.client = PyLibreLinkUp(email=os.getenv("USERNAME"), password=os.getenv("PASSWORD"))
        self.data = injected_data if injected_data is not None else self.load_data()
        self.alerts = injected_alerts if injected_alerts is not None else self.load_alerts()

    def load_alerts(self):
        with open('data/alerts.json') as f:
            return json.load(f)
    
    def save_alerts(self):
        with open('data/alerts.json', 'w') as f:
            json.dump(self.alerts, f)

    def load_data(self):
        with open('data/glucose-data.json') as f:
            return json.load(f)
    
    def save_data(self):
        with open('data/glucose-data.json', 'w') as f:
            json.dump(self.data, f)

    def authenticate(self):
        log("Authenticating...")
        self.client.authenticate()
    
    def get_seconds_since_latest_stored_value(self):
        latest_stored_value = self.data[-1] if len(self.data) > 0 else { "timestamp":"2026-01-01T12:00:00", "value":20.0 }
        latest_datetime = datetime.fromisoformat(latest_stored_value["timestamp"]) 
        return (datetime.now() - latest_datetime).total_seconds()

    def should_wait(self):
        seconds_since_last = round(self.get_seconds_since_latest_stored_value())
        if seconds_since_last < MIN_SECONDS_SINCE_LAST_DATA_FOR_FETCH:
            wait_until = round(MIN_SECONDS_SINCE_LAST_DATA_FOR_FETCH - seconds_since_last)
            log(f"Last ran {seconds_since_last} seconds ago -- try again in {wait_until} seconds")
            return True
        return False

    def fetch_latest_value(self) -> typing.Optional[dict]:
        log("Fetching and parsing data...")

        response_json = self.client._get_graph_data_json(uuid.UUID("01a00a94-f06c-742d-b3ce-631da9d29cc1"))
        parsed = GraphResponse.model_validate(response_json)
        current = parsed.current
        if self.data[-1]["timestamp"] == current.timestamp.isoformat():
            log("No new data since last fetch")
            return None

        # We only use GraphResponse.current because GraphResponse.graph_data contains smoothed
        # data with 5-minute granularity.
        self.data.append({
            "timestamp": parsed.current.timestamp.isoformat(),
            "value": current.value
        })
        self.save_data()
        return self.data[-1]
    
    def get_current_alert_level(self) -> AlertLevel:
        if self.data[-1]["value"] <= EMERGENCY_THRESHOLD:
            return AlertLevel.EMERGENCY
        if self.data[-1]["value"] <= WARNING_THRESHOLD:
            return AlertLevel.WARNING
        if self.data[-1]["value"] <= SOFT_THRESHOLD:
            return AlertLevel.SOFT
        return AlertLevel.NONE

    def should_send_alert(self) -> typing.Optional[dict]:
        latest_alert = self.alerts[-1] if len(self.alerts) > 0 else {"type":"RECOVERY", "level":"NONE"}
        latest_alert_level = AlertLevel[latest_alert["level"]]
        latest_alert_type = latest_alert["type"]
        current_alert_level = self.get_current_alert_level()

        if current_alert_level == latest_alert_level:
            # No change -- do nothing, regardless of last alert's type
            return None
        if current_alert_level.value > latest_alert_level.value:
            # Recovery
            return {"level": current_alert_level, "type": "RECOVERY"}
        # Alert
        return {"level": current_alert_level, "type": "ALERT"}

    def send_alert(self, alert: dict):
        log(f"Sending alert {alert["level"].name}-{alert["type"]}")
        self.alerts.append({ 
            "timestamp": datetime.now().isoformat(),
            "level": alert["level"].name,
            "type": alert["type"],
        })
        self.save_alerts()
    
def main():
    log("Running script!")

    monitor = GlucoseMonitor()

    should_wait = monitor.should_wait()
    if should_wait:
        return

    monitor.authenticate()

    latest_value = monitor.fetch_latest_value()
    if latest_value is None:
        return
    
    log(f"Latest value: {latest_value["value"]} at {latest_value["timestamp"]}")

    alert = monitor.should_send_alert()

    if alert is None:
        return

    monitor.send_alert(alert)


if __name__ == "__main__":
    main()