from .imports import *
from .assembly import *
from .directory_walker import *
from .helpers import *
from .rendering import *
from .template_registry import *
# ═══════════════════════════════════════════════════════════════
# Entry point — wires everything, then walks
# ═══════════════════════════════════════════════════════════════


@dataclass
class CLIConfig:
    dsn: str
    tenant_slug: str
    root: Path
    media_root: Path
    base_url: str
    site_root: str
    template_dir: Path
    no_recurse: bool
    dry_run: bool


def run(cfg: CLIConfig) -> None:
    conn = psycopg.connect(cfg.dsn, autocommit=True)
    try:
        repo = Repository(conn)
        seo_repo = SeoRepository(conn)

        tenant = repo.get_tenant_by_slug(cfg.tenant_slug)
        if tenant is None:
            print(f"ERROR: no tenant with slug={cfg.tenant_slug!r}", file=sys.stderr)
            sys.exit(1)

        templates = TemplateRegistry(cfg.template_dir)
        resolver = PathResolver(media_root=cfg.media_root, site_root=cfg.site_root)
        doc_index = DocumentIndex(repo, seo_repo, tenant.id)

        walk_config = WalkConfig(
            site_root=cfg.site_root,
            dry_run=cfg.dry_run,
            templates=templates,
            resolver=resolver,
            doc_index=doc_index,
        )

        generate_for_directory(
            directory=cfg.root,
            base_url=cfg.base_url,
            config=walk_config,
            recurse=not cfg.no_recurse,
        )
    finally:
        conn.close()


def generate_htmls_main() -> None:
    p = argparse.ArgumentParser(
        description="Generate static HTML for every directory from the document registry DB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--dsn",
        default=os.environ.get("DATABASE_URL", ""),
        help="PostgreSQL DSN (or set DATABASE_URL env var)",
    )
    p.add_argument("--tenant-slug", required=True, dest="tenant_slug")
    p.add_argument(
        "--root", required=True,
        help="Filesystem root to walk (e.g. /srv/media/thedailydialectics/pdfs)",
    )
    p.add_argument(
        "--media-root", required=True, dest="media_root",
        help="Top-level media root for path→URL conversion",
    )
    p.add_argument(
        "--base-url", required=True, dest="base_url",
        help="Public URL for --root (e.g. https://thedailydialectics.com/pdfs)",
    )
    p.add_argument(
        "--site-root",
        default=SITE_ROOT_DEFAULT, dest="site_root",
    )
    p.add_argument(
        "--template-dir",
        default=None, dest="template_dir",
        help="Path to Jinja2 templates (default: ./templates/ next to this script)",
    )
    p.add_argument("--no-recurse", action="store_true", dest="no_recurse")
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    args = p.parse_args()

    if not args.dsn:
        print("ERROR: --dsn or DATABASE_URL required", file=sys.stderr)
        sys.exit(1)

    template_dir = Path(args.template_dir) if args.template_dir else (
        Path(__file__).resolve().parent / "templates"
    )

    cfg = CLIConfig(
        dsn=args.dsn,
        tenant_slug=args.tenant_slug,
        root=Path(args.root).resolve(),
        media_root=Path(args.media_root).resolve(),
        base_url=args.base_url.rstrip("/"),
        site_root=args.site_root.rstrip("/"),
        template_dir=template_dir,
        no_recurse=args.no_recurse,
        dry_run=args.dry_run,
    )

    if not cfg.root.is_dir():
        print(f"ERROR: {cfg.root} is not a directory", file=sys.stderr)
        sys.exit(1)

    run(cfg)
