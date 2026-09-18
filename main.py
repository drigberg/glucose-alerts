import os
from pylibrelinkup import PyLibreLinkUp, GraphResponse
from dotenv import load_dotenv
from datetime import datetime

def log(message: str):
    print(f"[glucose-alerts] [{datetime.now().isoformat()}] - {message}")

class GlucoseMonitor:
    client: PyLibreLinkUp

    def __init__(self):
        load_dotenv()
        self.client = PyLibreLinkUp(email=os.getenv("USERNAME"), password=os.getenv("PASSWORD"))

    def authenticate(self):
        log("Authenticating...")
        self.client.authenticate()

    def get_current_data(self) -> GlucoseMeasurement:
        log("Fetching and parsing data...")

        response_json = self.client._get_graph_data_json("01a00a94-f06c-742d-b3ce-631da9d29cc1")
        parsed = GraphResponse.model_validate(response_json)

        # We only use GraphResponse.current because GraphResponse.graph_data contains smoothed
        # data with 5-minute granularity.
        return parsed.current

    
def main():
    log("Running script!")

    monitor = GlucoseMonitor()
    monitor.authenticate()

    current_data = monitor.get_current_data()

    log(f"Latest value: {current_data.value} at {current_data.timestamp.isoformat()}")


if __name__ == "__main__":
    main()