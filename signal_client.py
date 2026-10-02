import os
import requests
import typing

from dotenv import load_dotenv


class SignalClient:
    api_url: str
    sender: str
    recipient: str
    emergency_recipient: typing.Optional[str]

    def __init__(self, api_url: str, sender: str, recipient: str, emergency_recipient: typing.Optional[str]):
        self.api_url = api_url.rstrip("/")
        self.sender = sender
        self.recipient = recipient
        self.emergency_recipient = emergency_recipient
    
    def send(self, message: str, base64_attachments: list[str] | None = None, send_to_emergency_recipient: bool = False):
        if send_to_emergency_recipient and self.emergency_recipient is None:
            raise ValueError("Emergency recipient is not set")

        payload = {
            "message": message,
            "number": self.sender,
            # The Signal API doesn't allow sending to multiple groups at once, we have to send this to one group at a time!
            "recipients": [self.emergency_recipient] if send_to_emergency_recipient else [self.recipient]
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
