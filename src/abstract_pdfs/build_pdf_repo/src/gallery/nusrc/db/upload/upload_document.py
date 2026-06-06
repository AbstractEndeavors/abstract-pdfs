import uuid, hashlib
from pathlib import Path
from psycopg2.extras import execute_batch
from .imports import *
from ..db import (
    insert_document,

    get_conn
    
)

ROOT = Path("/srv/staging")


# -------------------------
# PATH HELPERS
# -------------------------
def rel(p: Path):
    return str(p.relative_to(ROOT))

def page_key(p: Path):
    name = p.name

    if not name.startswith("page_"):
        return None

    num = name.replace("page_", "")

    if not num.isdigit():
        return None

    return int(num)

def generate_doc_id(base_path: str):
    return hashlib.sha1(base_path.encode()).hexdigest()

def find_pdf(base_dir: Path):
    for p in Path(base_dir).glob("*.pdf"):
        return p
    return None
# -------------------------
# PAGE EXTRACTION
# -------------------------
def extract_pages(base_dir):
    pages = []
    pages_dir = Path(base_dir) / "pages"

    valid_pages = []

    for p in pages_dir.glob("page_*"):
        if not p.is_dir():
            continue

        key = page_key(p)
        if key is None:
            print(f"⚠️ Skipping invalid page dir: {p}")
            continue

        valid_pages.append((p, key))

    # sort safely
    valid_pages.sort(key=lambda x: x[1])

    for page_dir, page_number in valid_pages:
        image = page_dir / "image.png"
        html = page_dir / "index.html"
        text = page_dir / "text.txt"
        info = page_dir / "info.json"

        pages.append({
            "page_number": page_number,
            "page_path": rel(page_dir),

            "image_path": rel(image) if image.exists() else None,
            "html_path": rel(html) if html.exists() else None,
            "text_path": rel(text) if text.exists() else None,
            "info_path": rel(info) if info.exists() else None,

            "has_image": image.exists(),
            "has_html": html.exists(),
            "has_text": text.exists(),
            "has_info": info.exists(),
        })

    return pages

### -------------------------
### PAGE INSERT
### -------------------------
##def insert_pages(cur, doc_id, pages):
##    query = """
##        INSERT INTO document_pages (
##            document_id,
##            page_number,
##            page_path,
##            image_path,
##            html_path,
##            text_path,
##            info_path,
##            has_image,
##            has_html,
##            has_text,
##            has_info
##        )
##        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
##    """
##
##    data = [
##        (
##            doc_id,
##            p["page_number"],
##            p["page_path"],
##            p["image_path"],
##            p["html_path"],
##            p["text_path"],
##            p["info_path"],
##            p["has_image"],
##            p["has_html"],
##            p["has_text"],
##            p["has_info"],
##        )
##        for p in pages
##    ]
##
##    for row in data:
##        cur.execute(query, row)
##

# -------------------------
# BUILD DOCUMENT PAYLOAD
# -------------------------
def build_document_payload(base_dir):
    base_dir = Path(base_dir)

    pdf = find_pdf(base_dir)

    return {
        "doc_id": generate_doc_id(rel(base_dir)),

        # simple deterministic slug
        "slug": base_dir.name.lower().replace(" ", "-"),

        "base_path": rel(base_dir),
        "pdf_path": rel(pdf) if pdf else None,

        # 🔥 NO ANALYSIS HERE
        "pages": extract_pages(base_dir),
    }

# -------------------------
# MAIN INGEST FUNCTION
# -------------------------
def upload_document(base_dir):
    conn = get_conn()
    cur = conn.cursor()

    try:
        payload = build_document_payload(base_dir)

        doc_id = insert_document(payload)

        if not doc_id:
            print("⏭️ Skipping (already exists)")
            return None

        # 🔥 THIS is key
        insert_pages(cur, doc_id, payload["pages"])

        conn.commit()

        print(f"✅ Uploaded document {doc_id}")
        return doc_id

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()
