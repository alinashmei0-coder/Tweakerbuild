import json
import os
from pathlib import Path
import httpx

API_KEY = os.environ["DEEPSEEK_API_KEY"]
REQUEST = os.environ["REQUEST"]

SYSTEM = r"""
You are the project generator for a Theos iOS tweak build pipeline.

Return ONLY JSON:
{
  "files": [
    {"path": "Makefile", "content": "..."},
    {"path": "control", "content": "..."},
    {"path": "Tweak.xm", "content": "..."}
  ]
}

Rules:
- Generate a minimal buildable Theos project.
- Never use absolute paths or ../.
- Do not put secrets in files.
- Do not invent proprietary classes/selectors as confirmed facts.
- If the request depends on private headers or unknown symbols, make the limitation explicit in the generated code/comments rather than fabricating APIs.
- Prefer safe, minimal implementations.
"""

payload = {
    "model": "deepseek-v4-flash",
    "temperature": 0.1,
    "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": REQUEST},
    ],
}

with httpx.Client(timeout=180) as client:
    r = client.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    r.raise_for_status()
    data = r.json()

content = data["choices"][0]["message"]["content"].strip()
if content.startswith("```"):
    content = content.split("\n", 1)[1]
    if content.endswith("```"):
        content = content[:-3]

obj = json.loads(content)
files = obj.get("files")
if not isinstance(files, list) or not files:
    raise RuntimeError("DeepSeek did not return files.")

root = Path(".").resolve()

for item in files:
    rel = Path(item["path"])
    if rel.is_absolute() or ".." in rel.parts:
        raise RuntimeError(f"Unsafe path: {rel}")
    destination = (root / rel).resolve()
    if root not in destination.parents and destination != root:
        raise RuntimeError(f"Unsafe path: {rel}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(item.get("content", ""), encoding="utf-8")

print(f"Wrote {len(files)} files.")
