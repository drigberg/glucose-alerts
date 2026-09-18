import json
import os
from pylibrelinkup import PyLibreLinkUp, GraphResponse
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional

def log(message: str):
    print(f"[glucose-alerts] [{datetime.now().isoformat()}] - {message}")

class GlucoseMonitor:
    client: PyLibreLinkUp
    data: typing.Any

    def __init__(self):
        load_dotenv()
        self.client = PyLibreLinkUp(email=os.getenv("USERNAME"), password=os.getenv("PASSWORD"))
        self.data = self.load_data()

    def load_data(self):
        with open('data/data.json') as f:
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

    def fetch_latest_value(self) -> Optional[GlucoseMeasurement]:
        seconds_since_last_stored_value = self.get_seconds_since_latest_stored_value()
        if seconds_since_last_stored_value < 60.0:
            log(f"Last ran {seconds_since_last_stored_value} seconds ago -- try again in {60 - seconds_since_last_stored_value} seconds")
            return None

        log("Fetching and parsing data...")

        response_json = self.client._get_graph_data_json("01a00a94-f06c-742d-b3ce-631da9d29cc1")
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