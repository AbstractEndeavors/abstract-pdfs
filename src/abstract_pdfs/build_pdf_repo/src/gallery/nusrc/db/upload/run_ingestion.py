from pathlib import Path
from .upload_document import upload_document
from .imports import *
from .upload_to_db import *
ROOT = Path("/srv/staging/pdfs")


def get_text_for_document(base_dir: Path):
    for txt in base_dir.rglob("text.txt"):
        return txt
    return None


def ingest_all():
    for pages_dir in ROOT.rglob("pages"):
        base_dir = pages_dir.parent

       
        print(f"📄 Processing: {base_dir}")

        base_path = str(base_dir)

        # ✅ Skip if already exists
        if document_exists_by_path(base_path):
            print("⏭️ Skipping (already exists)")
            continue

        # ✅ Step 1: insert document + pages ONLY
        doc_id = upload_document(base_dir)

        if not doc_id:
            print("⏭️ Skipped (already exists)")
            continue

        print(f"🧱 Inserted document {doc_id}")

        # ✅ Step 2: process pages independently
        process_pages(base_dir, doc_id)
        
        print(f"✅ Completed {doc_id}")

##        except Exception as e:
##            print(f"❌ Failed: {base_dir}")
##            print(e)
##            input(e)
