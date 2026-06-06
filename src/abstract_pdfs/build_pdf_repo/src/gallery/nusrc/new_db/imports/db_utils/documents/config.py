from  .imports import *
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
CONN_MGR = connectionManager(    dbName="tdd_docs",
    user="putkoff",
    env_path='/home/solcatcher/.env.d/database.env')
DATABASE_URL = CONN_MGR.dburl
TENANT_ID = "c16c16fd-e86e-4727-952c-dcb569c52f0d"
# ── Config ───────────────────────────────────────────────────
PDF_MEDIA_ROOT = "/var/www/ABSTRACT_ENDEAVORS/media/TDD/pdfs"
PDFS_ROOT = os.environ.get("PDFS_ROOT", PDF_MEDIA_ROOT)
TENANT_SLUG = os.environ.get("TENANT_SLUG", "thedailydialectics")
TENANT_NAME = os.environ.get("TENANT_NAME", "The Daily Dialectics")
DPI = int(os.environ.get("RENDER_DPI", "200"))
FORCE = os.environ.get("FORCE_REPROCESS", "").lower() in ("1", "true", "yes")




