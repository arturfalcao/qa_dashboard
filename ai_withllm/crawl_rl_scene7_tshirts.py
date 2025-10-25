import re, os, json, time, hashlib
from urllib.parse import urljoin, urlencode
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ----------------------- CONFIG -----------------------
OUT_DIR = "rl_tshirts_flatlay"
CSV_PATH = os.path.join(OUT_DIR, "images.csv")
TARGET_MIN = 320                # recolher pelo menos isto (pára quando >= 300 válidas)
WID = 2000                      # largura do JPG final
TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RL-collector/1.0)"}

# Páginas de categoria (men/men-t-shirts etc.). Adiciona quantas quiseres.
CATEGORY_URLS = [
    "https://www.ralphlauren.com/men-clothing-t-shirts",           # Men T-Shirts
    "https://www.ralphlauren.com/women-clothing-t-shirts",         # Women T-Shirts
]

# Palavras-chave para flat-lay em Scene7 (ajusta se precisares)
ALLOW_INFIX = [
    "product", "prod", "front", "flat", "lay", "still", "studio", "catalog"
]
DENY_INFIX = [
    "lifestyle", "detail", "swatch", "video", "back", "angle", "model"
]
# ------------------------------------------------------


def scene7_url(asset_id:str, wid:int=WID) -> str:
    params = {"fmt":"jpg", "wid": str(wid)}
    return f"https://dtcralphlauren.scene7.com/is/image/PoloGSI/{asset_id}?{urlencode(params)}"

def sha1(b:bytes)->str:
    return hashlib.sha1(b).hexdigest()

def ensure_out():
    os.makedirs(OUT_DIR, exist_ok=True)

def fetch(url):
    return requests.get(url, headers=HEADERS, timeout=TIMEOUT)

def looks_like_flat(name:str) -> bool:
    n = name.lower()
    if any(x in n for x in DENY_INFIX): return False
    if any(x in n for x in ALLOW_INFIX): return True
    # fallback: muitos assets são tipo s7-1412709_product / _imageX
    return "_product" in n or "_image" in n

def find_scene7_ids_in_html(html:str):
    """
    Extrai possíveis IDs Scene7 (ex.: 's7-1412709_product', 's7-*******') a partir de:
    - <img src=".../is/image/PoloGSI/<ID>?...">
    - blobs JSON com 'image'/'assets'/'scene7' etc.
    """
    ids = set()

    # 1) URLs diretas <img src=...is/image/PoloGSI/ID?...>
    for m in re.finditer(r"/is/image/PoloGSI/([a-zA-Z0-9_\-]+)\?", html):
        ids.add(m.group(1))

    # 2) JSON embutido (data-state, window.__INITIAL_STATE__, etc.)
    for m in re.finditer(r">\s*({.*?})\s*<", html, flags=re.DOTALL):
        block = m.group(1)
        if "scene7" in block.lower() or "is/image" in block:
            try:
                data = json.loads(block)
                # procura recursivamente strings com .../is/image/PoloGSI/<ID>?
                rec = json.dumps(data)
                for mm in re.finditer(r"/is/image/PoloGSI/([a-zA-Z0-9_\-]+)\?", rec):
                    ids.add(mm.group(1))
            except Exception:
                pass

    return sorted(ids)

def collect_product_links(category_url:str):
    """Recolhe links de produto a partir da página de categoria (paginada)."""
    links = set()
    url = category_url
    for _ in range(1, 20):  # até ~20 páginas por categoria (ajusta)
        r = fetch(url)
        if r.status_code != 200: break
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.select("a[href]"):
            href = a["href"]
            if "/p/" in href or "/product/" in href:
                links.add(urljoin(url, href.split("?")[0]))
        # tenta encontrar next-page
        next_a = soup.select_one('a[aria-label*="Next"], a.pagination__next, a[rel="next"]')
        if not next_a: break
        url = urljoin(url, next_a.get("href"))
        time.sleep(0.7)
    return sorted(links)

def download_and_validate(session, url, out_name):
    try:
        with session.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True) as r:
            if r.status_code != 200 or "image" not in r.headers.get("Content-Type",""):
                return None
            content = r.content
        # valida fundo branco (heurística simples)
        import PIL.Image as PILImage, io, numpy as np
        im = PILImage.open(io.BytesIO(content)).convert("RGB")
        w, h = im.size
        if min(w, h) < 800:  # exige resolução mínima
            return None
        arr = np.array(im)
        border = np.concatenate([arr[0,:,:], arr[-1,:,:], arr[:,0,:], arr[:,-1,:]], axis=0)
        # proporção de pixels claros no bordo
        border_bright = (border.mean(axis=1) > 235).mean()
        if border_bright < 0.6:
            return None
        fn = os.path.join(OUT_DIR, out_name)
        with open(fn, "wb") as f:
            f.write(content)
        return (fn, w, h, sha1(content))
    except Exception:
        return None

def main():
    ensure_out()
    session = requests.Session()
    seen_assets = set()
    rows = []
    total = 0

    # 1) Links de produto por categoria
    prod_links = []
    for cat in CATEGORY_URLS:
        prod_links += collect_product_links(cat)
    prod_links = sorted(set(prod_links))

    # 2) Para cada produto, extrai IDs Scene7 e baixa as flat-lays
    for pl in tqdm(prod_links, desc="Produtos"):
        if total >= TARGET_MIN:
            break
        r = fetch(pl)
        if r.status_code != 200:
            continue
        ids = find_scene7_ids_in_html(r.text)
        for asset in ids:
            if total >= TARGET_MIN:
                break
            if asset in seen_assets:
                continue
            if not looks_like_flat(asset):
                continue
            img_url = scene7_url(asset, wid=WID)
            res = download_and_validate(session, img_url, f"{asset}.jpg")
            if res:
                fn, w, h, digest = res
                rows.append({"brand":"Ralph Lauren","url":img_url,"file":fn,"width":w,"height":h,"sha1":digest})
                seen_assets.add(asset)
                total += 1
        time.sleep(0.5)

    # 3) Guarda CSV
    import csv
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        wtr = csv.DictWriter(f, fieldnames=["brand","url","file","width","height","sha1"])
        wtr.writeheader()
        for row in rows:
            wtr.writerow(row)

    print(f"Done. Saved {len(rows)} images in {OUT_DIR} and CSV at {CSV_PATH}")

if __name__ == "__main__":
    main()
