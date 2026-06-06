from abstract_utilities import *
PDF_DIRECTORY = directory = PDFS_ROOT
input(PDFS_ROOT)
dirs,ALL_PDFS = get_files_and_dirs(PDF_DIRECTORY,allowed_exts=".pdf")


pdf_dirname = os.path.dirname(pdf_path)
pages_dir = os.path.join(pdf_dirname,'pages')

render_pdf_pages(
    pdf_path: Path(pdf_path),
    output_dir: Path(pages_dir),
    dpi= 200,
    fmt= "png",
)


for page in os.listdir(pages_dir):
    page_image_path = os.path.join(pages_dir,page,'image.png')
    page_text = image_to_text(
        image_path=page_image_path
        )
    page_text_path = os.path.join(pages_dir,page,'text.txt')
    write_to_file(file_path=page_text_path,contents=page_text)
    analyzed_data = analyze_page(text_path = page_text_path)
    page_info_path = os.path.join(pages_dir,page,'info.json')
    safe_dump_to_json(file_path=page_info_path,data=analyzed_data)
    analyzed_data['image_path']=page_image_path
    meta_info = get_meta_info(analyzed_data)

