import os
import httpx

BOT = os.environ["TELEGRAM_BOT_TOKEN"]
PAT = os.environ["GH_PAT"]
REPO = os.environ["GITHUB_REPOSITORY"]

# Prototype: Telegram offset is kept in a repository variable.
# The first run can therefore be started manually and subsequent runs continue.
GH = "https://api.github.com"
TG = f"https://api.telegram.org/bot{BOT}"

def gh_headers():
    return {
        "Authorization": f"Bearer {PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def main():
    with httpx.Client(timeout=60) as client:
        # Read offset from repository variables.
        vr = client.get(f"{GH}/repos/{REPO}/actions/variables/TELEGRAM_OFFSET", headers=gh_headers())
        offset = 0
        if vr.status_code == 200:
            offset = int(vr.json()["value"])

        r = client.get(f"{TG}/getUpdates", params={"offset": offset, "timeout": 1})
        r.raise_for_status()
        updates = r.json().get("result", [])

        for update in updates:
            new_offset = update["update_id"] + 1
            msg = update.get("message") or {}
            text = (msg.get("text") or "").strip()
            chat_id = msg.get("chat", {}).get("id")

            if not text or not chat_id:
                offset = new_offset
                continue

            if text.startswith("/start"):
                send(client, chat_id, "🤖 جاهز. اكتب لي وش الأداة اللي تبي أسويها.")
            elif text.startswith("/help"):
                send(client, chat_id, "اكتب طلبك مباشرة، وسأرسله إلى GitHub + DeepSeek ثم أبني المشروع.")
            else:
                dispatch(client, text, str(chat_id))
                send(client, chat_id, "🚀 تم إرسال الطلب إلى GitHub. سأبدأ إنشاء المشروع والبناء.")

            offset = new_offset

        # GitHub variables are immutable via create, so use update when present.
        payload = {"name": "TELEGRAM_OFFSET", "value": str(offset)}
        ur = client.patch(
            f"{GH}/repos/{REPO}/actions/variables/TELEGRAM_OFFSET",
            headers=gh_headers(),
            json={"value": str(offset)},
        )
        if ur.status_code == 404:
            client.post(
                f"{GH}/repos/{REPO}/actions/variables",
                headers=gh_headers(),
                json=payload,
            )

def dispatch(client, request, chat_id):
    r = client.post(
        f"{GH}/repos/{REPO}/actions/workflows/build-tweak.yml/dispatches",
        headers=gh_headers(),
        json={
            "ref": "main",
            "inputs": {"request": request[:4000], "chat_id": chat_id},
        },
    )
    r.raise_for_status()

def send(client, chat_id, text):
    r = client.post(
        f"{TG}/sendMessage",
        json={"chat_id": chat_id, "text": text},
    )
    r.raise_for_status()

if __name__ == "__main__":
    main()
