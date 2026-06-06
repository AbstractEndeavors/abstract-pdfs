from abstract_security import *
from abstract_database import get_db_connection,get_db_vars,get_db_env_value,get_db_vars_from_kwargs

def get_conn():
    env_values = get_db_env_value(dbname='tdd_docs',
                                  user='putkoff',
                                  )

    return get_db_connection(**env_values)
def normalize_keyword(k: str) -> str:
    return k.lower().replace("/", "_").strip()

def document_exists_by_path(base_path: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT 1 FROM documents
        WHERE base_path = %s
        LIMIT 1
    """, (base_path,))

    exists = cur.fetchone() is not None

    cur.close()
    conn.close()

    return exists
def insert_document(data: dict) -> int:
    conn = get_conn()
    cur = conn.cursor()

    from pathlib import Path

    slug = Path(data.get("base_path", "document")).name.lower().replace(" ", "-")

    cur.execute("""
        INSERT INTO documents (
            doc_id,
            slug,
            base_path,
            pdf_path
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (doc_id) DO NOTHING
        RETURNING id
    """, (
        data.get("doc_id"),
        slug,
        data.get("base_path"),
        data.get("pdf_path"),
    ))

    row = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return row[0] if row else None
def insert_pages(cur, doc_id: int, pages: list):
    for p in pages:
        cur.execute("""
            INSERT INTO document_pages (
                document_id,
                page_number,
                page_path,
                image_path,
                html_path,
                text_path,
                info_path,
                has_image,
                has_html,
                has_text,
                has_info
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (document_id, page_number)
            DO UPDATE SET
                page_path = EXCLUDED.page_path,
                image_path = EXCLUDED.image_path,
                html_path = EXCLUDED.html_path,
                text_path = EXCLUDED.text_path,
                info_path = EXCLUDED.info_path,
                has_image = EXCLUDED.has_image,
                has_html = EXCLUDED.has_html,
                has_text = EXCLUDED.has_text,
                has_info = EXCLUDED.has_info
        """, (
            doc_id,
            p["page_number"],
            p["page_path"],
            p["image_path"],
            p["html_path"],
            p["text_path"],
            p["info_path"],
            p["has_image"],
            p["has_html"],
            p["has_text"],
            p["has_info"],
        ))
##
##def insert_keywords(cur, doc_id, kw):
##    density = kw.get("density") or {}
##    density_flags = kw.get("density_flags") or {}
##
##    for k, value in density.items():
##        cur.execute("""
##            INSERT INTO keywords (
##                document_id, keyword, normalized_keyword,
##                density, density_flag,
##                is_primary, is_secondary, is_dropped
##            )
##            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
##            ON CONFLICT DO NOTHING
##        """, (
##            doc_id,
##            k,
##            normalize_keyword(k),
##            value,
##            density_flags.get(k),
##            k in (kw.get("primary") or []),
##            k in (kw.get("secondary") or []),
##            k in (kw.get("dropped") or [])
##        ))
def insert_page_analysis(doc_id, page_dir, analysis):
    page_number = int(page_dir.name.replace("page_", ""))

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO page_analysis (
            document_id,
            page_number,
            summary,
            keywords,
            raw
        )
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (document_id, page_number)
        DO UPDATE SET
            summary = EXCLUDED.summary,
            keywords = EXCLUDED.keywords,
            raw = EXCLUDED.raw
    """, (
        doc_id,
        page_number,
        analysis.get("summary"),
        json.dumps(analysis.get("keywords")),
        json.dumps(analysis)
    ))

    conn.commit()
    cur.close()
    conn.close()
def register_document(base_dir: Path):
    payload = build_document_payload(base_dir, page_analysis={})

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO documents (
            doc_id,
            slug,
            base_path,
            pdf_path
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (doc_id) DO NOTHING
        RETURNING id
    """, (
        payload["doc_id"],
        payload["slug"],
        payload["base_path"],
        payload["pdf_path"],
    ))

    row = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return row[0] if row else None

##def insert_sources(cur, doc_id, raw):
##    raw = raw or {}
##
##    for k in raw.get("keywords_spacy", []):
##        cur.execute("""
##            INSERT INTO keyword_sources (document_id, source, keyword)
##            VALUES (%s,%s,%s)
##            ON CONFLICT DO NOTHING
##        """, (doc_id, "spacy", k))
##
##    for k, score in raw.get("keywords_keybert", []):
##        cur.execute("""
##            INSERT INTO keyword_sources (document_id, source, keyword, score)
##            VALUES (%s,%s,%s,%s)
##            ON CONFLICT DO NOTHING
##        """, (doc_id, "keybert", k, score))


##def insert_meta(cur, doc_id, kw):
##    cur.execute("""
##        INSERT INTO keyword_meta (document_id, meta_keywords, preset_used)
##        VALUES (%s,%s,%s)
##        ON CONFLICT (document_id)
##        DO UPDATE SET
##            meta_keywords = EXCLUDED.meta_keywords,
##            preset_used = EXCLUDED.preset_used
##    """, (
##        doc_id,
##        kw.get("meta_keywords"),
##        kw.get("preset_used")
####    ))
##
##
##def insert_hashtags(cur, doc_id, hashtags):
##    for tag in hashtags:
##        cur.execute("""
##            INSERT INTO hashtags (document_id, hashtag)
##            VALUES (%s,%s)
##            ON CONFLICT DO NOTHING
##        """, (doc_id, tag))
