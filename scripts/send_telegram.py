import os
import sys
import httpx

token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["CHAT_ID"]
text = " ".join(sys.argv[1:]) or "TwaekerBuild"

url = f"https://api.telegram.org/bot{token}/sendMessage"

with httpx.Client(timeout=30) as client:
    r = client.post(url, json={"chat_id": chat_id, "text": text})
    r.raise_for_status()
