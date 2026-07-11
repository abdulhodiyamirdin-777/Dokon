import base64
import json
import requests

GITHUB_TOKEN = "ghp_Jw8yZxht8h0rrozobBqE4ahzAm8ZwW42rOAc"
REPO = "abdulhodiyamirdin-777/Dokon"
API_BASE = f"https://api.github.com/repos/{REPO}/contents/"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


def get_file(path):
    """Faylni o'qiydi. Qaytaradi: (matn_kontenti, sha) yoki (None, None) agar topilmasa."""
    r = requests.get(API_BASE + path, headers=HEADERS)
    if r.status_code != 200:
        return None, None
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def update_file(path, new_content, message):
    """Faylni yangi kontent bilan yozadi (commit qiladi)."""
    _, sha = get_file(path)
    payload = {
        "message": message,
        "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(API_BASE + path, headers=HEADERS, json=payload)
    return r.status_code in (200, 201)


def get_products():
    content, _ = get_file("products.json")
    if content is None:
        return []
    return json.loads(content)


def save_products(products, message="Mahsulotlar yangilandi"):
    content = json.dumps(products, ensure_ascii=False, indent=2)
    return update_file("products.json", content, message)


def get_stats():
    content, _ = get_file("stats.json")
    if content is None:
        return {"orders": 0, "revenue": 0}
    return json.loads(content)


def save_stats(stats, message="Statistika yangilandi"):
    content = json.dumps(stats, ensure_ascii=False, indent=2)
    return update_file("stats.json", content, message)
