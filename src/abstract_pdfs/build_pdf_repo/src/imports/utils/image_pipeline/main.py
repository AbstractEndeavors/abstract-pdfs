from src import get_needed_texts


if __name__ == "__main__":
    get_needed_texts(threaded=True, max_workers=MAX_WORKERS)
