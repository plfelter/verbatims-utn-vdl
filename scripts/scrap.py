import urllib3
from pathlib import Path
import html
from tqdm import tqdm
import re
from datetime import datetime
import time

time.sleep(2*60*60+7*60)

contrib_base_url: str = "https://www.registre-dematerialise.fr/6058/contributions/"
scrap_data: Path = Path(__file__).resolve().parent / "scrap-data" / f"scrap-data-{datetime.now().strftime('%y%m%dT%H%M%S')}"
scrap_data.mkdir(exist_ok=True, parents=True)

# Creating a PoolManager instance for sending requests.
http = urllib3.PoolManager()


def write_html(hstr: str, p: Path):
    with p.open('w+') as fp:
        fp.write(hstr)


def get_contrib_page_data(url: str) -> str:
    # Sending a GET request and getting back response as HTTPResponse object.
    resp = http.request("GET", url)
    return html.unescape(resp.data.decode("utf-8"))


def get_last_contrib_page_number(url: str) -> int:
    first_c_page = get_contrib_page_data(url + "1")
    return int(re.findall('data-max="(.*?)" data-url=', first_c_page)[0])


for i in tqdm(range(1, get_last_contrib_page_number(contrib_base_url) + 1)):
    write_html(
        get_contrib_page_data(contrib_base_url + str(i)),
        scrap_data / f"contrib-page-{i}.html"
    )

