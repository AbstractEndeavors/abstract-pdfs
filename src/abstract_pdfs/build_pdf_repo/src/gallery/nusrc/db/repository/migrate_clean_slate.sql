-- ============================================================
-- CLEAN SLATE MIGRATION
-- ============================================================
-- Drops everything in dependency order, then recreates.
-- Run once. After this, schema.sql and schema_seo.sql are your source of truth.
-- ============================================================

BEGIN;

-- ---------- drop in reverse dependency order ----------

DROP TRIGGER IF EXISTS trg_documents_updated_at ON documents;
DROP TRIGGER IF EXISTS trg_document_seo_updated_at ON document_seo;

DROP FUNCTION IF EXISTS relocate_document(UUID, TEXT, TEXT);
DROP FUNCTION IF EXISTS set_updated_at();

DROP TABLE IF EXISTS document_tags        CASCADE;
DROP TABLE IF EXISTS tags                 CASCADE;
DROP TABLE IF EXISTS pipeline_runs        CASCADE;
DROP TABLE IF EXISTS page_analysis        CASCADE;
DROP TABLE IF EXISTS document_seo         CASCADE;
DROP TABLE IF EXISTS analysis_types       CASCADE;
DROP TABLE IF EXISTS pages                CASCADE;
DROP TABLE IF EXISTS documents            CASCADE;
DROP TABLE IF EXISTS tenants              CASCADE;

DROP TYPE IF EXISTS processing_status;


-- ---------- extensions ----------

CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ---------- tenants ----------

CREATE TABLE tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ---------- documents ----------

CREATE TYPE processing_status AS ENUM (
    'pending',
    'ingesting',
    'analyzing',
    'complete',
    'failed'
);

CREATE TABLE documents (
    id              SERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    doc_id          TEXT NOT NULL,
    slug            TEXT NOT NULL,
    base_path       TEXT NOT NULL,
    pdf_path        TEXT NOT NULL,
    status          processing_status NOT NULL DEFAULT 'pending',
    page_count      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (tenant_id, doc_id)
);

CREATE INDEX idx_documents_tenant   ON documents (tenant_id);
CREATE INDEX idx_documents_status   ON documents (status);
CREATE INDEX idx_documents_slug     ON documents (tenant_id, slug);


-- ---------- pages ----------

CREATE TABLE pages (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number     INTEGER NOT NULL,
    image_path      TEXT,
    text_path       TEXT,
    info_path       TEXT,
    metadata_path   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (document_id, page_number)
);

CREATE INDEX idx_pages_document ON pages (document_id);


-- ---------- analysis type registry ----------

CREATE TABLE analysis_types (
    slug        TEXT PRIMARY KEY,
    label       TEXT NOT NULL,
    description TEXT
);

INSERT INTO analysis_types (slug, label, description) VALUES
    ('keywords',       'Keyword Extraction',   'spaCy + KeyBERT combined keyword output'),
    ('density',        'Keyword Density',       'Per-keyword density scores and stuffing flags'),
    ('summary',        'Page Summary',          'Extractive or abstractive page summary'),
    ('seo_keywords',   'SEO Keywords',          'Filtered keywords with primary/secondary/hashtag classification'),
    ('ocr',            'OCR Output',            'Raw OCR text extraction'),
    ('layout',         'Layout Analysis',       'Structural layout detection');


-- ---------- page-level analysis ----------

CREATE TABLE page_analysis (
    id              SERIAL PRIMARY KEY,
    page_id         INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    analysis_type   TEXT NOT NULL REFERENCES analysis_types(slug),
    payload         JSONB NOT NULL DEFAULT '{}',
    model_version   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (page_id, analysis_type)
);

CREATE INDEX idx_page_analysis_type    ON page_analysis (analysis_type);
CREATE INDEX idx_page_analysis_payload ON page_analysis USING gin (payload);


-- ---------- pipeline runs ----------

CREATE TABLE pipeline_runs (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    status          processing_status NOT NULL,
    stage           TEXT NOT NULL,
    error_message   TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,

    CONSTRAINT finished_requires_terminal CHECK (
        (status IN ('complete', 'failed')) = (finished_at IS NOT NULL)
    )
);

CREATE INDEX idx_pipeline_runs_doc    ON pipeline_runs (document_id);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs (status) WHERE status = 'failed';


-- ---------- tags ----------

CREATE TABLE tags (
    id      SERIAL PRIMARY KEY,
    slug    TEXT NOT NULL UNIQUE,
    label   TEXT NOT NULL
);

CREATE TABLE document_tags (
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tag_id      INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (document_id, tag_id)
);


-- ---------- document-level SEO metadata ----------

CREATE TABLE document_seo (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    keywords        TEXT NOT NULL DEFAULT '',
    canonical_url   TEXT,
    thumbnail_url   TEXT,
    og              JSONB NOT NULL DEFAULT '{}',
    twitter         JSONB NOT NULL DEFAULT '{}',
    meta_other      JSONB NOT NULL DEFAULT '{}',
    robots          TEXT NOT NULL DEFAULT 'index, follow',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (document_id)
);

CREATE INDEX idx_document_seo_doc ON document_seo (document_id);


-- ---------- functions ----------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION relocate_document(
    p_tenant_id     UUID,
    p_doc_id        TEXT,
    p_new_base_path TEXT
)
RETURNS INTEGER AS $$
DECLARE
    v_document_id INTEGER;
    v_old_base    TEXT;
BEGIN
    SELECT id, base_path
      INTO v_document_id, v_old_base
      FROM documents
     WHERE tenant_id = p_tenant_id
       AND doc_id    = p_doc_id
       FOR UPDATE;

    IF v_document_id IS NULL THEN
        RAISE EXCEPTION 'document not found: tenant=%, doc_id=%', p_tenant_id, p_doc_id;
    END IF;

    UPDATE documents
       SET base_path   = p_new_base_path,
           pdf_path    = replace(pdf_path,    v_old_base, p_new_base_path),
           updated_at  = now()
     WHERE id = v_document_id;

    UPDATE pages
       SET image_path    = replace(image_path,    v_old_base, p_new_base_path),
           text_path     = replace(text_path,     v_old_base, p_new_base_path),
           info_path     = replace(info_path,     v_old_base, p_new_base_path),
           metadata_path = replace(metadata_path, v_old_base, p_new_base_path)
     WHERE document_id = v_document_id;

    RETURN v_document_id;
END;
$$ LANGUAGE plpgsql;


-- ---------- triggers ----------

CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_document_seo_updated_at
    BEFORE UPDATE ON document_seo
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


COMMIT;
