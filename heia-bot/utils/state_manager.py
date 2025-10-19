import hashlib
import json
import os

STATE_FILE = "data/reminder_state.json"

os.makedirs("data", exist_ok=True)


def get_last_sent_hash():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("last_hash")
    except Exception:
        return None


def save_last_sent_hash(text: str):
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_hash": h}, f)
    return h


def has_already_sent(text: str) -> bool:
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return h == get_last_sent_hash()
