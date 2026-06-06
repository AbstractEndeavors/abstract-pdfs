-- ============================================================
-- Document Registry Schema
-- ============================================================
-- Tenancy flows top-down: tenant -> document -> page -> asset
-- Processing is a separate axis: pipeline_runs track state per document
-- Tags are a registry, not free-text columns
-- ============================================================

-- ---------- extensions ----------

CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()


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
    doc_id          TEXT NOT NULL,                       -- sha256 identity hash
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
    image_path      TEXT,                                -- page render: image.png
    text_path       TEXT,                                -- extracted text: text.txt
    info_path       TEXT,                                -- structural info: info.json
    metadata_path   TEXT,                                -- analysis output: metadata.json
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (document_id, page_number)
);

CREATE INDEX idx_pages_document ON pages (document_id);


-- ---------- page-level analysis ----------
-- Structured output from your analysis pipeline.
-- JSONB so you can query into it without schema migrations
-- every time the analysis evolves.

CREATE TABLE page_analysis (
    id              SERIAL PRIMARY KEY,
    page_id         INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    analysis_type   TEXT NOT NULL,                       -- e.g. 'ocr', 'layout', 'classification'
    payload         JSONB NOT NULL DEFAULT '{}',
    model_version   TEXT,                                -- which model/version produced this
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (page_id, analysis_type)
);

CREATE INDEX idx_page_analysis_type ON page_analysis (analysis_type);
CREATE INDEX idx_page_analysis_payload ON page_analysis USING gin (payload);


-- ---------- pipeline runs ----------
-- Immutable log of processing attempts.
-- Documents have a current `status`; this table tells you *why*.

CREATE TABLE pipeline_runs (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    status          processing_status NOT NULL,
    stage           TEXT NOT NULL,                       -- e.g. 'ingest', 'ocr', 'analyze'
    error_message   TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,

    CONSTRAINT finished_requires_terminal CHECK (
        (status IN ('complete', 'failed')) = (finished_at IS NOT NULL)
    )
);

CREATE INDEX idx_pipeline_runs_doc    ON pipeline_runs (document_id);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs (status) WHERE status = 'failed';


-- ---------- tags (registry, not free-text) ----------

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


-- ---------- path relocation ----------
-- When a document moves on disk, update all paths in one transaction.

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
       FOR UPDATE;                                      -- row lock

    IF v_document_id IS NULL THEN
        RAISE EXCEPTION 'document not found: tenant=%, doc_id=%', p_tenant_id, p_doc_id;
    END IF;

    -- rewrite document-level paths
    UPDATE documents
       SET base_path   = p_new_base_path,
           pdf_path    = replace(pdf_path,    v_old_base, p_new_base_path),
           updated_at  = now()
     WHERE id = v_document_id;

    -- rewrite every page-level path
    UPDATE pages
       SET image_path    = replace(image_path,    v_old_base, p_new_base_path),
           text_path     = replace(text_path,     v_old_base, p_new_base_path),
           info_path     = replace(info_path,     v_old_base, p_new_base_path),
           metadata_path = replace(metadata_path, v_old_base, p_new_base_path)
     WHERE document_id = v_document_id;

    RETURN v_document_id;
END;
$$ LANGUAGE plpgsql;


-- ---------- updated_at trigger ----------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
