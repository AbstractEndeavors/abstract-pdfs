from .imports import *
def slice_pdf(
        pdf_path:         str,
        out_root:         Optional[str] = None,
        engines                         = "layout_ocr",
        engine_directory: bool          = False,
        visualize:        bool          = None,
        root_url                        = None,
        media_root                      = None,
        pdfs_public_url                 = None,
        image_strategies = None,
    ):
    out_root = os.path.dirname(pdf_path)
    data = {"pdf_path":pdf_path,
                    "out_root":out_root,
                    "engines":engines,
                    "engine_directory":engine_directory,
                    "visualize":visualize,
                    "root_url":ROOT_URL,
                    "media_root":MEDIA_ROOT,
                    "pdfs_public_url":PDFS_PUBLIC_URL,
                    "image_strategies":image_strategies
                }
    return postRequest('https://clownworld.biz/ocr/pdfs/manifest/process',data=data)
