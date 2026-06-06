from .imports import *
def get_incomplete_documents():
    """Get all documents that aren't complete."""
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    try:
        with conn.cursor(row_factory=rows.dict_row) as cur:
            cur.execute("""
                SELECT id, slug, status, page_count
                FROM documents
                WHERE tenant_id = %s
                AND status != 'complete'
                ORDER BY created_at DESC
            """, (TENANT_ID,))
            return cur.fetchall()
    finally:
        conn.close()

def retry_incomplete():
    """Reset incomplete documents to pending."""
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    try:
        with conn.cursor(row_factory=rows.dict_row) as cur:
            cur.execute("""
                UPDATE documents
                SET status = 'pending'
                WHERE tenant_id = %s
                AND status IN ('failed', 'ingesting')
            """, (TENANT_ID,))
            print(f"Reset {cur.rowcount} documents to pending")
    finally:
        conn.close()
def get_pending_paths():
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    try:
        with conn.cursor(row_factory=rows.dict_row) as cur:
            cur.execute("""
                SELECT base_path FROM documents
                WHERE tenant_id = %s
                AND status = 'pending'
                ORDER BY created_at DESC
            """, (TENANT_ID,))
            
            for row in cur.fetchall():
                input(row['base_path'])
    finally:
        conn.close()
def show_incomplete():
    """Show incomplete documents."""
    docs = get_incomplete_documents()
    print(f"\nIncomplete documents: {len(docs)}\n")
    for doc in docs:
        print(f"ID: {doc['id']:5d} | Status: {doc['status']:10s} | Pages: {doc['page_count']:3} | {doc['slug']}")

if __name__ == "__main__":
    get_pending_paths()
    
##    response = input("\nReset all incomplete to 'pending'? (y/n): ")
##    if response.lower() == 'y':
##        retry_incomplete()
##        print("\nRestart pipeline: sudo systemctl restart pdf_pipeline.service")
