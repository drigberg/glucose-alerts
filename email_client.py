import boto3
import os

from dotenv import load_dotenv
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class EmailClient:
    sender: str

    def __init__(self, sender):
        self.sender = sender

    def build_raw_message(self, recipients, subject, body_text, body_html, inline_images) -> MIMEMultipart:
        message = MIMEMultipart("related")
        message["Subject"] = subject
        message["From"] = self.sender
        message["To"] = ", ".join(recipients)

        alternative = MIMEMultipart("alternative")
        alternative.attach(MIMEText(body_text, "plain", "utf-8"))
        alternative.attach(MIMEText(body_html, "html", "utf-8"))
        message.attach(alternative)

        for content_id, png_bytes in inline_images.items():
            image = MIMEImage(png_bytes, "png")
            image.add_header("Content-ID", f"<{content_id}>")
            image.add_header("Content-Disposition", "inline", filename=f"{content_id}.png")
            message.attach(image)
        return message

    def send(self, recipients, subject, body_text, body_html=None, inline_images=None):
        ses = boto3.client(
            "ses",
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_account_id=os.getenv("AWS_ACCOUNT_ID"))
        if body_html and inline_images:
            message = self.build_raw_message(recipients, subject, body_text, body_html, inline_images)
            return ses.send_raw_email(
                Source=self.sender,
                Destinations=recipients,
                RawMessage={"Data": message.as_bytes()},
            )
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