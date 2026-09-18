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
    GOOD = 3
    TARGET = 2
    WARNING = 1
    EMERGENCY = 0

ALERT_LEVEL_THRESHOLDS = {
    AlertLevel.GOOD: 15.0,
    AlertLevel.TARGET: 10.0,
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
        return self.alerts[-1] if len(self.alerts) > 0 else {"timestamp":"2026-01-01T12:00:00", "type":"RECOVERY", "level":"GOOD",}

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
        if self.latest_stored_value["value"] <= ALERT_LEVEL_THRESHOLDS[AlertLevel.TARGET]:
            return AlertLevel.TARGET
        if self.latest_stored_value["value"] <= ALERT_LEVEL_THRESHOLDS[AlertLevel.GOOD]:
            return AlertLevel.GOOD
        return None

    
    def should_send_alert(self) -> typing.Optional[dict]:
        latest_alert_level = AlertLevel[self.latest_alert["level"]]
        latest_alert_type = self.latest_alert["type"]
        current_alert_level = self.get_current_alert_level()

        log(f"Latest alert: {latest_alert_level.name} ({latest_alert_type}) at {self.latest_alert["timestamp"]}")
        log(f"Current alert level: {current_alert_level.name if current_alert_level is not None else 'None'}")
        
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

    def format_email_subject(self, alert: dict) -> str:
        return f"Chips Glucose Alert: {alert["level"].name} ({alert["type"]})"

    def get_advice(self, alert: dict) -> str:
        level = alert["level"]
        alert_type = alert["type"]
        if alert_type == "RECOVERY":
            if level == AlertLevel.GOOD:
                return "He's out of his target range, but still in a good place! No action needed."
            if level == AlertLevel.TARGET:
                return "He's back into his target range! It's too soon to tell if he's going to drop again, so keep monitoring just to be safe."
            if level == AlertLevel.WARNING:
                return "He's recovering slightly, but his glucose is still quite low. Continue to monitor closely and be ready to intervene."
        else:
            if level == AlertLevel.GOOD:
                return "He's dropped to the upper half of his target range! That's awesome."
            if level == AlertLevel.TARGET:
                return "His glucose is in the perfect range! Just keep an eye on him in case it drops further."
            if level == AlertLevel.WARNING:
                return "His glucose is still in a good range, but trending a little low! Monitor his behavior closely, consider giving him a snack, and have honey/dextrose ready in case he drops further or shows signs of distress."
            if level == AlertLevel.EMERGENCY:
                return "His glucose is dangerously low! Monitor his behavior and rub honey/dextrose into his gums if he's showing signs of distress (quietly meowing, breathing fast, wobbling, drooling, vomiting)."
        return ""

    def get_todays_alerts(self) -> list:
        today = datetime.now().date()
        return [a for a in self.alerts if datetime.fromisoformat(a["timestamp"]).date() == today]

    def format_email_body_text(self, alert: dict) -> str:
        value = self.latest_stored_value["value"]
        level_name = alert["level"].name
        alert_type = alert["type"]

        type_description = "RECOVERY" if alert_type == "RECOVERY" else "ALERT"
        lines = [
            f"Current reading: {value} mmol/L",
            f"Status: {type_description} — {level_name}",
            "",
            self.get_advice(alert),
        ]

        todays_alerts = self.get_todays_alerts()[-5:]
        if todays_alerts:
            lines.append("")
            lines.append("--- Recent alerts today ---")
            for a in todays_alerts:
                timestamp = datetime.fromisoformat(a["timestamp"]).strftime("%H:%M")
                lines.append(f"  {timestamp} — {a['level']} ({a['type']})")

        return "\n".join(lines)

    def format_email_body_html(self, alert: dict) -> str:
        value = self.latest_stored_value["value"]
        level_name = alert["level"].name
        alert_type = alert["type"]

        emoji = "⬆️" if alert_type == "RECOVERY" else "⬇️"
        status_color = "#2e7d32" if alert_type == "RECOVERY" else "#c62828"
        advice = self.get_advice(alert)

        alerts_html = ""
        todays_alerts = self.get_todays_alerts()[-5:]
        if todays_alerts:
            rows = ""
            for a in todays_alerts:
                timestamp = datetime.fromisoformat(a["timestamp"]).strftime("%H:%M")
                row_color = "#2e7d32" if a["type"] == "RECOVERY" else "#c62828"
                rows += f'<tr><td style="padding:4px 12px 4px 0;color:#555;">{timestamp}</td><td style="padding:4px 0;color:{row_color};font-weight:600;">{a["level"]} ({a["type"]})</td></tr>'
            alerts_html = f"""
            <tr><td style="padding:24px 32px 16px;">
                <p style="margin:0 0 8px;font-size:13px;color:#888;text-transform:uppercase;letter-spacing:1px;">Recent Alerts Today</p>
                <table style="font-size:14px;">{rows}</table>
            </td></tr>"""

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f4f4f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:24px 0;">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
    <tr><td style="background:{status_color};padding:24px 32px;">
        <h1 style="margin:0;color:#ffffff;font-size:22px;">{emoji} Chips Glucose {alert_type.title()}</h1>
    </td></tr>
    <tr><td style="padding:24px 32px;">
        <table style="width:100%;font-size:15px;">
            <tr>
                <td style="padding:8px 0;color:#555;">Current Reading</td>
                <td style="padding:8px 0;text-align:right;font-size:28px;font-weight:700;color:#222;">{value} <span style="font-size:14px;color:#888;">mmol/L</span></td>
            </tr>
            <tr>
                <td style="padding:8px 0;color:#555;">Level</td>
                <td style="padding:8px 0;text-align:right;font-weight:600;color:{status_color};">{level_name}</td>
            </tr>
        </table>
    </td></tr>
    <tr><td style="padding:0 32px 24px;">
        <p style="margin:0;padding:16px;background:#f8f9fa;border-radius:6px;font-size:14px;line-height:1.5;color:#333;">{advice}</p>
    </td></tr>{alerts_html}
    <tr><td style="padding:16px 32px;border-top:1px solid #eee;">
        <p style="margin:0;font-size:11px;color:#aaa;text-align:center;">Chips Glucose Alerts</p>
    </td></tr>
</table>
</td></tr></table>
</body></html>"""

    def send_alert(self, alert: dict):
        log(f"Sending alert {alert["level"].name}-{alert["type"]}")

        # Send from sender to sender for now
        self.email_client.send(
            recipients=[os.getenv("EMAIL_SENDER")],
            subject=self.format_email_subject(alert),
            body_text=self.format_email_body_text(alert),
            body_html=self.format_email_body_html(alert))

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