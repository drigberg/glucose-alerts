import json
import os
import typing
from pylibrelinkup import PyLibreLinkUp, GraphResponse
from dotenv import load_dotenv
from datetime import datetime
from enum import Enum
import uuid

class AlertLevel(Enum):
    NONE = 0
    SOFT = 1
    WARNING = 2
    EMERGENCY = 3

def log(message: str):
    print(f"[glucose-alerts] [{datetime.now().isoformat()}] - {message}")

SOFT_THRESHOLD = 10.0
WARNING_THRESHOLD = 7.5
EMERGENCY_THRESHOLD = 5.0

class GlucoseMonitor:
    client: PyLibreLinkUp
    data: typing.Any
    alerts: typing.Any

    def __init__(self, injected_data, injected_alerts):
        load_dotenv()
        self.client = PyLibreLinkUp(email=os.getenv("USERNAME"), password=os.getenv("PASSWORD"))
        self.data = injected_data or self.load_data()
        self.alerts = injected_alerts or self.load_alerts()

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
        with open('data/data.json', 'w') as f:
            json.dump(self.data, f)

    def authenticate(self):
        log("Authenticating...")
        self.client.authenticate()
    
    def get_seconds_since_latest_stored_value(self):
        latest_stored_value = self.data[-1]
        latest_datetime = datetime.fromisoformat(latest_stored_value["timestamp"]) 
        return (datetime.now() - latest_datetime).total_seconds()

    def fetch_latest_value(self) -> typing.Optional[dict]:
        seconds_since_last_stored_value = self.get_seconds_since_latest_stored_value()
        if seconds_since_last_stored_value < 60.0:
            log(f"Last ran {seconds_since_last_stored_value} seconds ago -- try again in {60 - seconds_since_last_stored_value} seconds")
            return None

        log("Fetching and parsing data...")

        response_json = self.client._get_graph_data_json(uuid.UUID("01a00a94-f06c-742d-b3ce-631da9d29cc1"))
        parsed = GraphResponse.model_validate(response_json)
        current = parsed.current
        if self.data[-1]["timestamp"] == current.timestamp.isoformat():
            log("No new data since last fetch")
            return None

        print(self.data[-1]["timestamp"], current.timestamp.isoformat())
        # We only use GraphResponse.current because GraphResponse.graph_data contains smoothed
        # data with 5-minute granularity.
        self.data.append({
            "timestamp": parsed.current.timestamp.isoformat(),
            "value": current.value
        })
        self.save_data()
        return self.data[-1]
    
    def get_alert_level(self) -> AlertLevel:
        if self.data[-1]["value"] <= EMERGENCY_THRESHOLD:
            return AlertLevel.EMERGENCY
        if self.data[-1]["value"] <= WARNING_THRESHOLD:
            return AlertLevel.WARNING
        if self.data[-1]["value"] <= SOFT_THRESHOLD:
            return AlertLevel.SOFT
        return AlertLevel.NONE

    def send_alert(self):
        if self.is_glucose_below_emergency_threshold:
            return 

    
def main():
    log("Running script!")

    monitor = GlucoseMonitor()
    monitor.authenticate()

    latest_value = monitor.fetch_latest_value()
    if latest_value is None:
        return

    log(f"Latest value: {latest_value["value"]} at {latest_value["timestamp"]}")


if __name__ == "__main__":
    main()