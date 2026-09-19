import base64
import json
import os
import traceback
import typing
import uuid
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv
from email_client import EmailClient
from enum import Enum
from signal_client import SignalClient
from string import Template

from playwright.sync_api import sync_playwright
from pylibrelinkup import PyLibreLinkUp

MIN_SECONDS_SINCE_LAST_DATA_FOR_FETCH = 50.0

class AlertLevel(Enum):
    TEST = 5
    SILENT = 4
    GOOD = 3
    TARGET = 2
    WARNING = 1
    EMERGENCY = 0

ALERT_LEVEL_COLORS = {
    AlertLevel.TEST: "#8e24aa",
    AlertLevel.SILENT: "#8e24aa",
    AlertLevel.GOOD: "#039be5",
    AlertLevel.TARGET: "#43a047",
    AlertLevel.WARNING: "#f9a825",
    AlertLevel.EMERGENCY: "#c62828",
}

ALERT_LEVEL_THRESHOLDS = {
    AlertLevel.TEST: 100.0,
    AlertLevel.SILENT: 27.8,
    AlertLevel.GOOD: 15.0,
    AlertLevel.TARGET: 10.0,
    AlertLevel.WARNING: 7.5,
    AlertLevel.EMERGENCY: 5.0,
}

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

def load_template(name: str) -> Template:
    with open(os.path.join(TEMPLATES_DIR, name)) as f:
        return Template(f.read())

def log(message: str):
    print(f"[glucose-alerts] [{datetime.now().isoformat(timespec='milliseconds')}] - {message}")

@dataclass
class Config:
    libre_username: str
    libre_password: str
    email_sender: str
    signal_api_url: str
    signal_sender: str
    signal_recipient: str
    force_send_test: bool

class GlucoseMonitor:
    email_client: EmailClient
    signal_client: SignalClient
    libre_client: PyLibreLinkUp
    data: typing.Any
    alerts: typing.Any
    force_send_test: bool

    def __init__(self, config: Config, injected_data=None, injected_alerts=None):
        self.email_client = EmailClient(sender=config.email_sender)
        self.signal_client = SignalClient(
            api_url=config.signal_api_url,
            sender=config.signal_sender,
            recipient=config.signal_recipient,
        )
        self.libre_client = PyLibreLinkUp(email=config.libre_username, password=config.libre_password)
        self.data = injected_data if injected_data is not None else self.load_data()
        self.alerts = injected_alerts if injected_alerts is not None else self.load_alerts()
        self.force_send_test = config.force_send_test

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
        return self.alerts[-1] if len(self.alerts) > 0 else {"timestamp":"2026-01-01T12:00:00", "type":"RECOVERY", "level":"SILENT",}

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

        timestamp_iso = datetime.strptime(glucose_measurement["FactoryTimestamp"], "%m/%d/%Y %I:%M:%S %p").isoformat()
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
        if self.latest_stored_value["value"] <= ALERT_LEVEL_THRESHOLDS[AlertLevel.SILENT]:
            return AlertLevel.SILENT
        return None

    
    def should_send_alert(self) -> typing.Optional[dict]:
        latest_alert_level = AlertLevel[self.latest_alert["level"]]
        latest_alert_type = self.latest_alert["type"]
        current_alert_level = self.get_current_alert_level()

        log(f"Latest alert: {latest_alert_level.name} ({latest_alert_type}) at {self.latest_alert["timestamp"]}")
        log(f"Current alert level: {current_alert_level.name if current_alert_level is not None else 'None'}")
        
        if self.force_send_test is True:
            return {"level": AlertLevel.TEST, "type": "ALERT"}

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
            if level == AlertLevel.TEST:
                return "This is just a test! Chips is probably doing just fine right now. He's a good boyo!"
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
        status_color = ALERT_LEVEL_COLORS[alert["level"]]
        advice = self.get_advice(alert)

        alerts_html = ""
        todays_alerts = self.get_todays_alerts()[-5:]
        if todays_alerts:
            row_template = load_template("email_alert_row.template")
            rows = ""
            for a in todays_alerts:
                timestamp = datetime.fromisoformat(a["timestamp"]).strftime("%H:%M")
                row_color = ALERT_LEVEL_COLORS.get(AlertLevel[a["level"]], "#555")
                rows += row_template.substitute(timestamp=timestamp, row_color=row_color, level=a["level"], type=a["type"])
            section_template = load_template("email_alerts_section.template")
            alerts_html = section_template.substitute(rows=rows)

        body_template = load_template("email_body.template")
        return body_template.substitute(
            status_color=status_color,
            emoji=emoji,
            alert_type_title=alert_type.title(),
            value=value,
            level_name=level_name,
            advice=advice,
            alerts_html=alerts_html,
        )

    def format_signal_message(self, alert: dict) -> str:
        value = self.latest_stored_value["value"]
        level_name = alert["level"].name
        alert_type = alert["type"]
        emoji = "⬆️" if alert_type == "RECOVERY" else "🌈" if level_name == AlertLevel.TEST.name else "⬇️"
        advice = self.get_advice(alert)
        return f"{emoji} Chips Glucose {alert_type.title()}\n\nReading: {value} mmol/L — {level_name}\n\n{advice}"

    def render_html_to_image(self, html: str) -> bytes:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 520, "height": 1})
            page.set_content(html, wait_until="networkidle")
            png_bytes = page.screenshot(full_page=True)
            browser.close()
        return png_bytes

    def send_alert(self, alert: dict):
        if alert["level"] != AlertLevel.SILENT:
            log(f"Sending alert {alert["level"].name}-{alert["type"]}")

            try:
                self.email_client.send(
                    recipients=[os.getenv("EMAIL_SENDER")],
                    subject=self.format_email_subject(alert),
                    body_text=self.format_email_body_text(alert),
                    body_html=self.format_email_body_html(alert))
                log(f"Successfully sent email!")
            except Exception as e:
                log(f"Error sending email!")
                template = "Error type: {0}\n Arguments:\n{1!r}"
                message = template.format(type(e).__name__, e.args)
                print(message)
                print(traceback.format_exc())

            try:
                html = self.format_email_body_html(alert)
                png_bytes = self.render_html_to_image(html)
                png_b64 = base64.b64encode(png_bytes).decode("ascii")
                attachment = f"data:image/png;base64,{png_b64}"

                log(f"Sending Signal message... (attachment size: {len(png_bytes)} bytes)")
                self.signal_client.send(
                    self.format_signal_message(alert),
                    base64_attachments=[attachment],
                )
                log(f"Successfully sent Signal message!")
            except Exception as e:
                log(f"Error sending Signal message!")
                print("Error:", e)
                message = template.format(type(e).__name__, e.args)
                print(message)
                print(traceback.format_exc())

        # Only TEST alerts are unsaved! SILENT recoveries need to be saved so that we can send a GOOD alert
        # when his glucose drops again.
        if alert["level"] != AlertLevel.TEST:
            self.alerts.append({ 
                "timestamp": datetime.now().isoformat(),
                "level": alert["level"].name,
                "type": alert["type"],
            })
            self.save_alerts()
    
def main():
    log("Running script!")

    load_dotenv()
    config = Config(
        email_sender=os.getenv("EMAIL_SENDER", ""),
        signal_api_url=os.getenv("SIGNAL_API_URL", ""),
        signal_sender=os.getenv("SIGNAL_SENDER", ""),
        signal_recipient=os.getenv("SIGNAL_RECIPIENT", ""),
        libre_username=os.getenv("LIBRE_USERNAME", ""),
        libre_password=os.getenv("LIBRE_PASSWORD", ""),
        force_send_test=(os.getenv("FORCE_SEND_TEST") == "true"))

    monitor = GlucoseMonitor(config)

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