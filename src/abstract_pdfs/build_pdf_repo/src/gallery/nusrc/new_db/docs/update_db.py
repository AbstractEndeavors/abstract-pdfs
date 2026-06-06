def process_page(repo: Repository, document_id: int, page_number: int, page_dir: str):
    """
    Process a single page: extract text, analyze, generate metadata, save to DB.
    
    Args:
        repo: Repository instance (injected)
        document_id: Document ID from DB
        page_number: Page number (1-indexed)
        page_dir: Directory path containing page assets
    """
    
    # 1. Create/upsert page record with file paths
    image_path = os.path.join(page_dir, "image.png")
    text_path = os.path.join(page_dir, "text.txt")
    info_path = os.path.join(page_dir, "info.json")
    metadata_path = os.path.join(page_dir, "metadata.json")
    
    page = repo.upsert_page(
        document_id=document_id,
        page_number=page_number,
        image_path=image_path,
        text_path=text_path,
        info_path=info_path,
        metadata_path=metadata_path
    )
    
    # 2. Extract text
    if not os.path.isfile(text_path):
        text_content = extract_single_pdf_page_text(pdf_path, page_number)
        write_to_file(file_path=text_path, contents=text_content)
    else:
        text_content = read_from_file(text_path)
    
    # 3. Analyze page
    if not os.path.isfile(info_path):
        analysis = analyze_page(text_content)
        safe_dump_to_json(file_path=info_path, data=analysis)
    else:
        analysis = safe_load_from_json(info_path)
    
    # 4. Generate metadata
    if not os.path.isfile(metadata_path):
        metadata = generate_metadata(analysis, page_number, document_id)
        safe_dump_to_json(file_path=metadata_path, data=metadata)
    else:
        metadata = safe_load_from_json(metadata_path)
    
    # 5. Save everything to DB
    repo.save_page_content(
        page_id=page.id,
        text_content=text_content,
        analysis=analysis,
        metadata=metadata
    )
    
    print(f"Processed page {page_number}")

def analyze_page(text_content: str) -> dict:
    """Analyze page text, return analysis dict."""
    data = {
        "text": text_content,
        "scope": "page",
        "summary_preset": "brief",
        "keyword_preset": "seo",
        "input_policy": "allow"
    }
    return postRequest('https://clownworld.biz/hugpy/analyze/text', data=data)

def generate_metadata(analysis: dict, page_number: int, document_id: int) -> dict:
    """Generate metadata from analysis."""
    data = {"info": analysis}
    return postRequest('https://clownworld.biz/metadata/get/info', data=data)

# Main workflow
if __name__ == "__main__":
    conn = psycopg.connect(DATABASE_URL, autocommit=True)
    repo = Repository(conn)
    
    try:
        # Get pending documents
        pending_docs = repo.list_documents(TENANT_ID, status=Status.PENDING)
        
        for doc in pending_docs:
            print(f"Processing {doc.slug}...")
            pages_dir = os.path.join(doc.base_path, 'pages')
            
            if not os.path.isdir(pages_dir):
                print(f"  No pages directory")
                continue
            
            # Process each page
            for i in range(1, doc.page_count + 1):
                page_str = f"{i:04d}"
                page_dir = os.path.join(pages_dir, page_str)
                
                if not os.path.isdir(page_dir):
                    continue
                
                process_page(repo, doc.id, i, page_dir)
            
            # Mark document complete
            repo.update_document_status(doc.id, Status.COMPLETE)
    
    finally:
        conn.close()
