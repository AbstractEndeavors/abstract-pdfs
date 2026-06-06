def first_existing_file(*paths):
    """Return the first path that exists as a file, or ''."""
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return ""
