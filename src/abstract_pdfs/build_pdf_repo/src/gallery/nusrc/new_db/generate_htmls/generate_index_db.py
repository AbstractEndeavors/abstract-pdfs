#!/usr/bin/env python3
from src import *
"""
generate_index_db.py — Static HTML generation from the document registry DB.

Walks the filesystem tree for directory structure, queries the DB for content,
and renders through Jinja2 templates. Every directory gets an index.html:
  - Leaf dirs matching a DB document → viewer page
  - Leaf dirs with info.json (no DB match) → image page
  - Branch dirs with children → gallery index

Design:
  - Filesystem provides structure (which directories exist).
  - DB provides content (titles, descriptions, SEO, page data).
  - Jinja2 templates own all HTML. No f-string markup in Python.
  - Templates are loaded from a registry, not discovered at runtime.
  - All config is explicit. No smart defaults.

Usage:
    python generate_index_db.py \\
        --dsn           "postgresql://user:pass@localhost:5432/tdd_docs" \\
        --tenant-slug   default \\
        --root          /srv/media/thedailydialectics/pdfs \\
        --media-root    /srv/media/thedailydialectics \\
        --base-url      https://thedailydialectics.com/pdfs \\
        --site-root     https://thedailydialectics.com

    # Single directory:
    python generate_index_db.py \\
        --dsn           "postgresql://user:pass@localhost:5432/tdd_docs" \\
        --tenant-slug   default \\
        --root          /srv/media/thedailydialectics/pdfs/wipow/a197278 \\
        --media-root    /srv/media/thedailydialectics \\
        --base-url      https://thedailydialectics.com/pdfs/wipow/a197278 \\
        --site-root     https://thedailydialectics.com \\
        --no-recurse --dry-run
"""










