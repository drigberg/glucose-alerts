import boto3
import os

from dotenv import load_dotenv

class EmailClient:
    sender: str

    def __init__(self, sender):
        self.sender = sender

    def send(self, recipients, subject, body_text, body_html=None):
        ses = boto3.client(
            "ses",
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_account_id=os.getenv("AWS_ACCOUNT_ID"))
        body = {
            "Text": {
                "Data": body_text,
            }
        }
        if body_html:
            body["Html"] = {
                "Data": body_html,
            }
        response = ses.send_email(
            Source=self.sender,
            Destination={
                "ToAddresses": recipients
            },
            Message={
                "Subject": {
                    "Data": subject,
                },
                "Body": body,
            },
        )
        return response

if __name__ == "__main__":
    load_dotenv()
    email_client = EmailClient(os.getenv("EMAIL_SENDER"))
    email_client.send(["daniel.rigberg@gmail.com"], "Hello", "Peril")