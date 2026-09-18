import os
import requests

from dotenv import load_dotenv


class SignalClient:
    api_url: str
    sender: str
    group_id: str

    def __init__(self, api_url: str, sender: str, group_id: str):
        self.api_url = api_url.rstrip("/")
        self.sender = sender
        self.group_id = group_id

    def send(self, message: str):
        response = requests.post(
            f"{self.api_url}/v2/send",
            json={
                "message": message,
                "number": self.sender,
                "recipients": [self.group_id],
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    load_dotenv()
    client = SignalClient(
        api_url=os.getenv("SIGNAL_API_URL"),
        sender=os.getenv("SIGNAL_SENDER"),
        group_id=os.getenv("SIGNAL_GROUP_ID"),
    )
    client.send("Hello from glucose-alerts!")
