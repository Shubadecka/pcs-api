import os
import random
import smtplib
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv  # type: ignore

# Load environment variables from .env file
load_dotenv()

# Email configuration - replace with your email settings
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))


def generate_verification_code():
    return "".join(random.choices(string.digits, k=6))


def send_verification_email(email, code):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = email
        msg["Subject"] = f"Palmer Cloud Server Verification Code {code}"

        body = f"Your verification code is: {code}\nThis code will expire in 5 minutes."
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.connect(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()

        if not all([EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER]):
            raise ValueError("Missing email configuration. Check your .env file.")

        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        raise e
