from .db_utils import *
##TABLE_NAMES = get_all_table_names()
##TENANTS = fetch_any_combo(tableName='tenants')
##DOCUMENTS = fetch_any_combo(tableName='documents')
##PAGES = fetch_any_combo(tableName='pages')
##DOCUMENT_SEO = fetch_any_combo(tableName="document_seo")
##ANALYSIS_TYPES = fetch_any_combo(tableName="analysis_types")
##PAGE_ANALYSIS = fetch_any_combo(tableName="page_analysis")
##DOCUMENT_TAGS = fetch_any_combo(tableName="document_tags")
##TAGS = fetch_any_combo(tableName="tags")
##ANALYSIS_STRING = ""
##for ANALYSIS_TYPE in ANALYSIS_TYPES:
##    ANALYSIS_STRING+=str(ANALYSIS_TYPE)+'\n'
##STATS = f"""
##tables: {TABLE_NAMES}
##
##tenants: {TENANTS}
##
##analysis_types: {ANALYSIS_STRING}
##
##pages: {len(PAGES)}
##page_analysis: {len(PAGE_ANALYSIS)}
##SAMPLE: {PAGE_ANALYSIS[0]}
##documents: {len(DOCUMENTS)}
##document_seo: {len(DOCUMENT_SEO)}
##SAMPLE: {DOCUMENT_SEO[0]}
##
##tags: {TAGS}
##document_tags: {len(DOCUMENT_TAGS)}
##"""
##print(STATS)
