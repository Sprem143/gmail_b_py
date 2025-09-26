from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import smtplib
from email.mime.text import MIMEText
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

# === MongoDB Setup ===
# client = AsyncIOMotorClient('mongodb://127.0.0.1:27017/gmail')
mongo_uri = os.environ.get('MONGO_URI')
if not mongo_uri:
    raise RuntimeError("MONGO_URI not found in .env file")
client = AsyncIOMotorClient(mongo_uri)
db = client["test"]
sender_collection = db["senders"]


# === FastAPI App with CORS ===
app = FastAPI(title="Email Sender API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Models ===
class Sender(BaseModel):
    email: EmailStr
    appPassword: str

class EmailRequest(BaseModel):
    email:str
    appPassword:str
    subject: str
    newmessage: str
    receivers: List[EmailStr]

# === Helper ===
def create_transporter(email, app_password):
    return smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10), email, app_password


@app.post("/sendemails")
async def send_emails(data:EmailRequest):
    user = data.email
    user = data.email
    password = data.appPassword

    # Create SMTP transporter
    try:
        transporter = smtplib.SMTP("smtp.gmail.com", 587)
        transporter.starttls()
        transporter.login(user, password)
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid sender credentials")

    sent = 0
    failed = 0

    for to in data.receivers:
        msg = MIMEText(data.newmessage, "html")
        msg["Subject"] = data.subject
        msg["From"] = user
        msg["To"] = to

        try:
            transporter.sendmail(user, to, msg.as_string())
            sent += 1
        except Exception as e:
            print(f"Failed to send to {to}: {e}")
            failed += 1

        await asyncio.sleep(1)  # delay between sends

    transporter.quit()
    return {"sent": sent, "failed": failed}
