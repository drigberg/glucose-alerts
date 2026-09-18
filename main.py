import json
import os
import typing
import uuid
from datetime import datetime
from dotenv import load_dotenv
from email_client import EmailClient
from enum import Enum

from pylibrelinkup import PyLibreLinkUp

MIN_SECONDS_SINCE_LAST_DATA_FOR_FETCH = 50.0

class AlertLevel(Enum):
    TARGET = 3
    LOW = 2
    WARNING = 1
    EMERGENCY = 0

ALERT_LEVEL_THRESHOLDS = {
    AlertLevel.TARGET: 15.0,
    AlertLevel.LOW: 10.0,
    AlertLevel.WARNING: 7.5,
    AlertLevel.EMERGENCY: 5.0,
}

def log(message: str):
    print(f"[glucose-alerts] [{datetime.now().isoformat()}] - {message}")

class GlucoseMonitor:
    email_client: EmailClient
    libre_client: PyLibreLinkUp
    data: typing.Any
    alerts: typing.Any

    def __init__(self, injected_data=None, injected_alerts=None):
        load_dotenv()
        self.email_client = EmailClient(sender=os.getenv("EMAIL_SENDER"))
        self.libre_client = PyLibreLinkUp(email=os.getenv("LIBRE_USERNAME"), password=os.getenv("LIBRE_PASSWORD"))
        self.data = injected_data if injected_data is not None else self.load_data()
        self.alerts = injected_alerts if injected_alerts is not None else self.load_alerts()

    def load_alerts(self):
        os.makedirs('data', exist_ok=True)
        try:
            with open('data/alerts.json') as f:
                content = f.read().strip()
                return json.loads(content) if content else []
        except FileNotFoundError:
            return []
    
    def save_alerts(self):
        with open('data/alerts.json', 'w') as f:
            json.dump(self.alerts, f)

    def load_data(self):
        os.makedirs('data', exist_ok=True)
        try:
            with open('data/glucose-data.json') as f:
                content = f.read().strip()
                return json.loads(content) if content else []
        except FileNotFoundError:
            return []
    
    def save_data(self):
        with open('data/glucose-data.json', 'w') as f:
            json.dump(self.data, f)

    def authenticate(self):
        log("Authenticating...")
        self.libre_client.authenticate()
    
    @property
    def latest_stored_value(self):
        return self.data[-1] if len(self.data) > 0 else { "timestamp":"2026-01-01T12:00:00", "value":27.8 }

    @property
    def latest_alert(self):
        return self.alerts[-1] if len(self.alerts) > 0 else {"timestamp":"2026-01-01T12:00:00", "type":"RECOVERY", "level":"TARGET",}

    def get_seconds_since_latest_stored_value(self):
        latest_datetime = datetime.fromisoformat(self.latest_stored_value["timestamp"]) 
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

        response_json = self.libre_client._get_graph_data_json(uuid.UUID("01a00a94-f06c-742d-b3ce-631da9d29cc1"))

        try:
            glucose_measurement = response_json["data"]["connection"]["glucoseMeasurement"]
        except Exception as e:
            log("Error parsing response!")
            print("Response:", response_json)
            raise e

        timestamp_iso = datetime.strptime(glucose_measurement["Timestamp"], "%m/%d/%Y %I:%M:%S %p").isoformat()
        if self.latest_stored_value["timestamp"] == timestamp_iso:
            log("No new data since last fetch")
            return None

        # We only use the current reading because the graph_data contains smoothed values with 5-minute granularity.
        self.data.append({
            "timestamp": timestamp_iso,
            "value": glucose_measurement["Value"]
        })
        self.save_data()
        return self.latest_stored_value
    
    def get_current_alert_level(self) -> typing.Optional[AlertLevel]:
        if self.latest_stored_value["value"] <= ALERT_LEVEL_THRESHOLDS[AlertLevel.EMERGENCY]:
            return AlertLevel.EMERGENCY
        if self.latest_stored_value["value"] <= ALERT_LEVEL_THRESHOLDS[AlertLevel.WARNING]:
            return AlertLevel.WARNING
        if self.latest_stored_value["value"] <= ALERT_LEVEL_THRESHOLDS[AlertLevel.LOW]:
            return AlertLevel.LOW
        if self.latest_stored_value["value"] <= ALERT_LEVEL_THRESHOLDS[AlertLevel.TARGET]:
            return AlertLevel.TARGET
        return None

    
    def should_send_alert(self) -> typing.Optional[dict]:
        latest_alert_level = AlertLevel[self.latest_alert["level"]]
        latest_alert_type = self.latest_alert["type"]
        current_alert_level = self.get_current_alert_level()

        if current_alert_level is None:
            # No alert level -- do nothing
            return None
        if current_alert_level == latest_alert_level:
            # No change -- do nothing, regardless of last alert's type
            return None
        if current_alert_level.value > latest_alert_level.value:
            # Recovery -- only send if the most recent 3 values are all above the last alert level's threshold
            threshold = ALERT_LEVEL_THRESHOLDS[latest_alert_level]
            recent_values = [d["value"] for d in self.data[-3:]]
            if len(recent_values) < 3 or not all(v >= threshold for v in recent_values):
                return None
            return {"level": current_alert_level, "type": "RECOVERY"}
        # Alert
        return {"level": current_alert_level, "type": "ALERT"}

    def send_alert(self, alert: dict):
        log(f"Sending alert {alert["level"].name}-{alert["type"]}")

        # Send from sender to sender for now
        self.email_client.send(
            recipients=[os.getenv("EMAIL_SENDER")],
            subject="Chips Glucose Alert!",
            body=f"Value: {self.latest_stored_value["value"]}\nLevel: {alert["level"].name}\nType: {alert["type"]}")

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