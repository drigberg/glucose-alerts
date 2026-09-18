import os
import requests

from dotenv import load_dotenv


class SignalClient:
    api_url: str
    sender: str
    recipient: str

    def __init__(self, api_url: str, sender: str, recipient: str):
        self.api_url = api_url.rstrip("/")
        self.sender = sender
        self.recipient = recipient

    def send(self, message: str, base64_attachments: list[str] | None = None):
        payload = {
            "message": message,
            "number": self.sender,
            "recipients": [self.recipient],
        }
        if base64_attachments:
            payload["base64_attachments"] = base64_attachments
        response = requests.post(
            f"{self.api_url}/v2/send",
            json=payload,
            timeout=30,
        )
        if not response.ok:
            print(f"Signal API error {response.status_code}: {response.text}")
        response.raise_for_status()
        return response.json()

