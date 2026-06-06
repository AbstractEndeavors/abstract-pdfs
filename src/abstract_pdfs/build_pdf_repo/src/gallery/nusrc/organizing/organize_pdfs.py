from abstract_database import *

def find_pdf_in_all_pdfs(pdf_path,all_pdfs):
    basename = os.path.basename(pdf_path)
    for pdf in all_pdfs:
        if pdf.endswith(basename):
            print(f"found {pdf_path}")
            if os.path.isfile(pdf):
                return pdf
def find_and_copy_pdf_in_all_pdfs(pdf_path,all_pdfs):
    basename = os.path.basename(pdf_path)
    for pdf in all_pdfs:
        if pdf.endswith(basename):
            print(f"found {pdf_path}")
            if os.path.isfile(pdf) and not os.path.isfile(pdf_path):
                shutil.copy2(pdf, pdf_path)
                return True
    return False
get_db_connection(
        name="tdd_docs",
        user="putkoff",
        env_path='/home/solcatcher/.env.d/database.env'
    )
TABLE_NAMES = get_all_table_names()
input(get_caller_dir())
DB_DATA_DIR  = os.path.join(get_caller_dir(),'dbData')
PDF_NEEDS_PATH = os.path.join(DB_DATA_DIR,'needed.json')
ALL_PDF_FILE_PATHS_PATH = os.path.join(DB_DATA_DIR,"all_pdf_paths.json")
DB_DOCUMENTS_PATH = os.path.join(DB_DATA_DIR,"documents.json")
PDF_DIRECTORY = directory = "/var/www/ABSTRACT_ENDEAVORS/media/TDD/pdfs"
os.makedirs(DB_DATA_DIR,exist_ok=True)

dirs,ALL_PDFS = get_files_and_dirs(PDF_DIRECTORY,allowed_exts=".pdf")


safe_dump_to_json(data=ALL_PDFS,file_path=ALL_PDF_FILE_PATHS_PATH)



NEEDS = []

for table_name in TABLE_NAMES:
    data = fetch_any_combo(tableName=table_name)
    for dat in data:
        dat["created_at"] = str(dat["created_at"])
    file_path = os.path.join(DB_DATA_DIR,f"{table_name}.json")
    safe_dump_to_json(data=data,file_path=file_path)
    input(table_name)
documents = safe_load_from_json(DB_DOCUMENTS_PATH)

for values in documents:
    base_path = values.get('base_path')
    pdf_rel_path = values.get('pdf_path')
    if not pdf_rel_path or not base_path:
        NEEDS.append(values)
        print(f"{values}\n\n NO GOOD")
        continue

            
    try:        
        
        
        basename= os.path.basename(pdf_rel_path)
        for pdf in ALL_PDFS:
            if pdf.endswith(basename):
                input(pdf)
        if result == False:
            NEEDS.append(values)
            print(f"need {pdf_path}")
    except Exception as e:
        print(f"{values}\n\n{e}")
safe_dump_to_json(data=NEEDS,file_path=PDF_NEEDS_PATH)
