def create_manifest(pdf_path,data):
      data["summary"] = get_full_text_summary(pdf_path)
      data["keywords"] = get_full_text_keywords(pdf_path)
      data["category"] = "General"
      data["page_count"] = len(os.listdir(thumb_dir))
      data["pages"] = []
      return data
def create_info_json(page_dir,thumbnail_html_url,page_data,text_summary,text_page_text):
    # info.json — one per thumbnail image
    info_json = {
        "page_url":     thumbnail_html_url,
        "alt":          page_data["alt"],
        "caption":      page_data["caption"],
        "title":        page_data["title"],
        "description":  page_data["description"],
        "keywords_str": page_data["keywords_str"],
        "longdesc":     text_page_text,
        "text":         text_page_text,
        # schema.url must be the IMAGE url — cards_from_subdirs uses this for the card thumbnail
        "schema": {
            **meta.get("og", {}),
            "url":         thumbnail_page_url,   # ← image URL, not page URL
            "contentUrl":  thumbnail_page_url,
            "site_name":   "thedailydialectics.com",
        },
        # social_meta must use og: prefixed keys — that's what cards_from_subdirs looks for
        "social_meta": {
            "og:image":      thumbnail_page_url,
            "og:image:alt":  page_data["alt"],
            "og:title":      page_data["title"],
            "og:description": page_data["description"][:300],
            "twitter:image": thumbnail_page_url,
            "twitter:card":  "summary_large_image",
        },
    }
    write_atomic(
        json_path,
        json.dumps(info_json, indent=2, ensure_ascii=False),
    )
    # HTML — one per thumbnail image
    html = build_image_html(meta, thumbnail_page_url, page_data['title'])
    stem = os.path.splitext(os.path.basename(thumbnail_page_path))[0]
    write_atomic(
        os.path.join(page_dir, f"{stem}.html"),
        html,
    )
    logger.info("Wrote page %d → %s", i, page_dir)
