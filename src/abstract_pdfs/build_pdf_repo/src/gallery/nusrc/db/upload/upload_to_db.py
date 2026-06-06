from pathlib import Path
from .upload_document import upload_document
from .imports import *
import json
from abstract_utilities import get_any_value
ROOT = Path("/srv/staging/pdfs")
def check_keywords_summary(data):
    keywords = data.get("keywords")
    if not keywords:
        return False
    summary = data.get("summary")
    description = data.get("description")
    if not summary and not description:
        return False
    return True    
def get_key_value_from_data(data,key):
    value = data.get(key)
    if not value:
        values = get_any_value(data,key)
        if not values:
            return value 
        values = [value for value in values if value]
        if values:
            value = values[0]
    return value
def get_analysis_from_info(info_path):
    data_keys = {}
    info = safe_load_from_json(str(info_path))
    analysis_keys = ["alt","caption","keyword","keywords_str","summary","description","title","longdesc"]
    for key in analysis_keys:
        value = get_key_value_from_data(info,key)
        if value and key in ["summary","description"] and not data_keys.get("summary"):
            data_keys["summary"] = value
    return data_keys
def find_documents(root: Path):
    for p in root.rglob("pages"):
        yield p.parent


def get_best_text(base_dir: Path):
    """
    Pick best available text file (first found for now)
    """
    for txt in base_dir.rglob("text.txt"):
        return txt
    return None
def process_pages(base_dir: Path, doc_id: int):
    pages_dir = base_dir / "pages"

    for page_dir in sorted(pages_dir.glob("page_*")):
        text_file = page_dir / "text.txt"
        info_file = page_dir / "info.json"

        analysis = None

        # -------------------------
        # 1. Prefer existing info.json
        # -------------------------
        if info_file.exists():
##                try:
                info = get_analysis_from_info(info_file)
                if check_keywords_summary(info):
                    analysis = info
                    print(f"📦 Using existing info.json: {page_dir}")

##                except Exception as e:
##                    print(f"⚠️ Invalid info.json, falling back: {page_dir}")
##                    print(e)

        # -------------------------
        # 2. Fallback → analyze
        # -------------------------
        if analysis is None:
            if not text_file.exists():
                continue
               
            analysis = analyze_page(str(text_file))

            if not analysis:
                continue
    
            print(f"🧠 Analyzed: {page_dir}")
            
            # OPTIONAL: persist back to info.json
            try:
                with open(info_file, "w") as f:
                    json.dump(analysis, f, indent=2)
            except Exception as e:
                print(f"⚠️ Failed to write info.json: {page_dir}")
                print(e)

        # -------------------------
        # 3. Insert into DB
        # -------------------------
        insert_page_analysis(doc_id, page_dir, analysis)

##        except Exception as e:
##            print(f"❌ Page failed: {page_dir}")
##            print(e)

def process_document(base_dir: Path):
    print(f"📄 Processing: {base_dir}")

    base_path = str(base_dir)

    if document_exists_by_path(base_path):
        print("⏭️ Skipping (already exists)")
        return

    # ✅ Step 1: insert document ONLY
    doc_id = upload_document(base_dir)

    if not doc_id:
        print("⏭️ Already exists")
        return

    print(f"🧱 Document inserted: {doc_id}")

    # ✅ Step 2: insert pages (already happens inside upload_document)

    # ✅ Step 3: analyze pages (independent)
    process_pages(base_dir, doc_id)

    print(f"✅ Completed document {doc_id}")
