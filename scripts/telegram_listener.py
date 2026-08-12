import os
import time
import httpx

BOT = os.environ["TELEGRAM_BOT_TOKEN"]
PAT = os.environ["GH_PAT"]
REPO = os.environ["GITHUB_REPOSITORY"]

GH = "https://api.github.com"
TG = f"https://api.telegram.org/bot{BOT}"

def gh_headers():
    return {
        "Authorization": f"Bearer {PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def get_offset(client):
    r = client.get(f"{GH}/repos/{REPO}/actions/variables/TELEGRAM_OFFSET",
                   headers=gh_headers())
    if r.status_code == 200:
        try:
            return int(r.json()["value"])
        except (ValueError, TypeError):
            pass
    return 0

def set_offset(client, offset):
    h = gh_headers()
    r = client.patch(
        f"{GH}/repos/{REPO}/actions/variables/TELEGRAM_OFFSET",
        headers=h, json={"value": str(offset)}
    )
    if r.status_code == 404:
        r = client.post(
            f"{GH}/repos/{REPO}/actions/variables",
            headers=h,
            json={"name": "TELEGRAM_OFFSET", "value": str(offset)}
        )
    r.raise_for_status()

def send(client, chat_id, text):
    r = client.post(f"{TG}/sendMessage",
                    json={"chat_id": chat_id, "text": text})
    r.raise_for_status()

def dispatch_build(client, request, chat_id):
    r = client.post(
        f"{GH}/repos/{REPO}/actions/workflows/build-tweak.yml/dispatches",
        headers=gh_headers(),
        json={
            "ref": "main",
            "inputs": {
                "request": request[:4000],
                "chat_id": str(chat_id)
            }
        }
    )
    r.raise_for_status()

def main():
    with httpx.Client(timeout=70) as client:
        offset = get_offset(client)
        started = time.time()
        max_runtime = 5 * 60 * 60

        while time.time() - started < max_runtime:
            try:
                r = client.get(
                    f"{TG}/getUpdates",
                    params={
                        "offset": offset,
                        "timeout": 30,
                        "allowed_updates": '["message"]'
                    }
                )
                r.raise_for_status()

                for update in r.json().get("result", []):
                    offset = max(offset, update["update_id"] + 1)
                    set_offset(client, offset)

                    msg = update.get("message") or {}
                    text = (msg.get("text") or "").strip()
                    chat_id = msg.get("chat", {}).get("id")

                    if not text or not chat_id:
                        continue

                    if text.startswith("/start"):
                        send(client, chat_id,
                             "🤖 جاهز. اكتب لي الأداة اللي تبي أسويها.")
                    elif text.startswith("/help"):
                        send(client, chat_id,
                             "اكتب طلبك مباشرة، وسأرسله إلى GitHub + DeepSeek ثم أبني المشروع.")
                    elif text.startswith("/status"):
                        send(client, chat_id,
                             "🟢 البوت متصل ويستمع للطلبات.")
                    else:
                        send(client, chat_id,
                             "🚀 استلمت طلبك. جاري إرساله إلى GitHub...")
                        try:
                            dispatch_build(client, text, chat_id)
                        except Exception as exc:
                            send(client, chat_id,
                                 f"❌ تعذر تشغيل البناء: {type(exc).__name__}")
            except Exception:
                time.sleep(5)

if __name__ == "__main__":
    main()
