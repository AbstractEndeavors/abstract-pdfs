from .imports import *
def get_meta_info(analyzed_data,page_dir,metadata_path):
    image_path = analyzed_data.get("image_path")
    summary = analyzed_data.get("summary", "")
    keywords = analyzed_data.get("keywords", {})
    dirname = os.path.dirname(page_dir)
    dirbase = os.path.basename(dirname)
    parent_dirname = os.path.dirname(dirname)
    parent_dirbase = os.path.basename(parent_dirname)
    pdf_title = parent_dirbase.replace('_','-').replace('_','-').replace('--','-')
    page_title = f"{pdf_title}-{dirbase}"
    alt = f"{pdf_title}-{dirbase} pdf Image"
    capt = summary[:67] if len(summary) >67 else summary
    caption = f"{alt} {capt}..." 
    
    href = path_to_url(image_path)
    meta_info = get_page_data(page_title,
                href,
                summary,
                keywords,
                href,
                alt=alt,
                caption=caption)
    safe_dump_to_json(file_path=str(metadata_path), data=meta_info)
    return meta_info
