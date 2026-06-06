-- ============================================================
-- Schema Extension: SEO metadata + analysis type registry
-- Run after schema.sql
-- ============================================================


-- ---------- analysis type registry ----------
-- Instead of free-text analysis_type strings scattered across inserts,
-- register them. Typos become constraint violations, not silent garbage.

CREATE TABLE analysis_types (
    slug        TEXT PRIMARY KEY,              -- 'keywords', 'density', 'summary', 'layout', 'ocr'
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

-- Add FK to page_analysis so only registered types are allowed
ALTER TABLE page_analysis
    ADD CONSTRAINT fk_analysis_type
    FOREIGN KEY (analysis_type) REFERENCES analysis_types(slug);


-- ---------- document-level SEO metadata ----------
-- One row per document. The full og/twitter/meta blob lives here.
-- JSONB because the shape varies (player cards, app cards, geo, hreflang).

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

    UNIQUE (document_id)                                -- one SEO record per document
);

CREATE INDEX idx_document_seo_doc ON document_seo (document_id);

CREATE TRIGGER trg_document_seo_updated_at
    BEFORE UPDATE ON document_seo
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
