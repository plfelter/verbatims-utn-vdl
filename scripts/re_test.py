import re
from pathlib import Path

scrap_data: Path = Path(__file__).resolve().parent / "scrap-data"

data: str = (scrap_data / "contrib-page-1.html").read_text()
re.findall('data-max="(.*?)" data-url=', data)
print("done")