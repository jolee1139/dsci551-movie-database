from pathlib import Path
import zipfile

import requests


DATASET_URL = "https://files.grouplens.org/datasets/movielens/ml-20m.zip"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
ZIP_PATH = RAW_DATA_DIR / "ml-20m.zip"
EXTRACTED_DIR = RAW_DATA_DIR / "ml-20m"


def download_dataset():
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if ZIP_PATH.exists():
        print("MovieLens ZIP file already exists. Skipping download.")
        return

    print("Downloading MovieLens 20M...")

    with requests.get(DATASET_URL, stream=True, timeout=60) as response:
        response.raise_for_status()

        with ZIP_PATH.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)

    print("Download complete.")


def extract_dataset():
    if EXTRACTED_DIR.exists():
        print("MovieLens dataset is already extracted.")
        return

    print("Extracting MovieLens 20M...")

    with zipfile.ZipFile(ZIP_PATH, "r") as zip_file:
        zip_file.extractall(RAW_DATA_DIR)

    print("Extraction complete.")


if __name__ == "__main__":
    download_dataset()
    extract_dataset()