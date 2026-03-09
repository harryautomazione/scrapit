import csv
from datetime import datetime
from pathlib import Path
from scraper.config import OUTPUT_DIR


def save(data: dict, name: str, *, output_dir: str | None = None) -> str:
    base = Path(output_dir) if output_dir else OUTPUT_DIR
    base.mkdir(parents=True, exist_ok=True)
    out_file = base / f"{name}.csv"
    file_exists = out_file.exists()

    flat = {k: str(v) for k, v in data.items()}

    with open(out_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=flat.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(flat)

    return str(out_file)


def read(name: str, *, output_dir: str | None = None) -> list[dict]:
    """Read records from a CSV output file."""
    base = Path(output_dir) if output_dir else OUTPUT_DIR
    out_file = base / f"{name}.csv"
    if not out_file.exists():
        return []
    with open(out_file, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
