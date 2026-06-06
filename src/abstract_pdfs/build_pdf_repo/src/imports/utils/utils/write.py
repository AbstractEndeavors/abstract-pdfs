import os
from .imports import *
def save_info(data,file_path):
    if data:
        safe_dump_to_json(data=data,file_path=file_path)
def write_atomic(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    write_to_file(file_path = tmp,contents=content)
    os.replace(tmp, path)


def truncate_to_word_limit(text, max_words=5_000):
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])

def humanize(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").title()

def getPath(path):
    if path and isinstance(path,str):
        path = Path(path)
    return path
def safe_load_json(path):
    """Load JSON from path, return {} on any failure."""
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def safe_write_json(path, data):
    """Write JSON to path, creating parent dirs."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def safe_read_text(path):
    """Read text file, return '' on failure."""
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def safe_write_text(path, content):
    """Write text to path, creating parent dirs."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
