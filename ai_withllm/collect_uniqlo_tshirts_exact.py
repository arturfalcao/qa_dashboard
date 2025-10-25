#!/usr/bin/env python3
"""
Coleta t-shirts do Uniqlo usando APENAS códigos EXATOS verificados.
NÃO busca códigos próximos - APENAS os códigos que sabemos serem t-shirts.
"""

import os
import csv
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from PIL import Image
import numpy as np
from tqdm import tqdm
import io

# ----------------------- CONFIG -----------------------
OUT_DIR = "uniqlo_tshirts_exact"
CSV_PATH = os.path.join(OUT_DIR, "images.csv")
TARGET_MIN = 320
WIDTH = 2000
TIMEOUT = 10
MAX_WORKERS = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# APENAS códigos EXATOS do dataset verificado
EXACT_TSHIRT_CODES = [
    410025, 410225, 410250, 410275, 410300, 410375, 410425, 410450, 410550, 410575,
    410625, 410675, 410700, 410750, 410825, 410900, 410925, 410950, 410975, 411075,
    411225, 411250, 411275, 411325, 411350, 411375, 411400, 411425,
    422700, 423600, 425000, 425500, 425700, 425900, 426400, 426700, 427400, 428500,
    440600, 444300, 444900, 450600, 452200, 453900, 457200, 458100, 458300, 459700,
    460500, 460900, 461200, 461600, 463500, 463600, 464200, 464300, 464500
]

# Todos os códigos de cor do Uniqlo (expandido)
COLOR_CODES = [
    '00', '01', '02', '03', '04', '05', '06', '07', '08', '09',
    '10', '11', '12', '13', '14', '15', '16', '17', '18', '19',
    '20', '21', '22', '23', '24', '25', '26', '27', '28', '29',
    '30', '31', '32', '33', '34', '35', '36', '37', '38', '39',
    '40', '41', '42', '43', '44', '45', '46', '47', '48', '49',
    '50', '51', '52', '53', '54', '55', '56', '57', '58', '59',
    '60', '61', '62', '63', '64', '65', '66', '67', '68', '69',
    '70', '71', '72', '73', '74', '75', '76', '77', '78', '79',
    '80', '81', '82', '83', '84', '85', '86', '87', '88', '89',
    '90', '91', '92', '93', '94', '95', '96', '97', '98', '99'
]
# ------------------------------------------------------


def uniqlo_url(product_code: int, color_code: str, width: int = WIDTH) -> str:
    return f"https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/{product_code}/item/goods_{color_code}_{product_code}.jpg?width={width}"


def sha1(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def ensure_out():
    os.makedirs(OUT_DIR, exist_ok=True)


def is_valid_flatlay(image_bytes: bytes, min_size: int = 800) -> bool:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size

        if min(w, h) < min_size:
            return False

        arr = np.array(img)
        border = np.concatenate([
            arr[0, :, :],
            arr[-1, :, :],
            arr[:, 0, :],
            arr[:, -1, :]
        ], axis=0)

        border_brightness = (border.mean(axis=1) > 235).mean()
        return border_brightness > 0.6

    except Exception:
        return False


def download_and_validate(url: str, product_code: int, color_code: str) -> dict:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)

        if response.status_code != 200:
            return None

        if "image" not in response.headers.get("Content-Type", ""):
            return None

        content = response.content

        if not is_valid_flatlay(content):
            return None

        img = Image.open(io.BytesIO(content))
        w, h = img.size

        filename = f"uniqlo_{product_code}_{color_code}.jpg"
        filepath = os.path.join(OUT_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(content)

        return {
            "brand": "Uniqlo",
            "product_code": product_code,
            "color_code": color_code,
            "url": url,
            "file": filename,
            "width": w,
            "height": h,
            "size_bytes": len(content),
            "sha1": sha1(content)
        }

    except Exception:
        return None


def main():
    print("="*60)
    print("UNIQLO T-SHIRT COLLECTOR - EXACT CODES ONLY")
    print("="*60)

    ensure_out()

    # Gera URLs APENAS para códigos exatos
    print("\n[1/3] Gerando URLs (APENAS códigos verificados)...")
    product_urls = []
    for code in EXACT_TSHIRT_CODES:
        for color in COLOR_CODES:
            product_urls.append((code, color, uniqlo_url(code, color)))

    print(f"  → {len(EXACT_TSHIRT_CODES)} códigos de produto EXATOS")
    print(f"  → {len(COLOR_CODES)} variações de cor")
    print(f"  → {len(product_urls)} URLs totais para testar")
    print(f"  → SEM busca de códigos próximos - APENAS t-shirts verificadas")

    # Download paralelo
    print(f"\n[2/3] Baixando e validando ({MAX_WORKERS} workers)...")
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(download_and_validate, url, code, color): (code, color)
            for code, color, url in product_urls
        }

        with tqdm(total=len(futures), desc="Processando") as pbar:
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
                    pbar.set_postfix({"válidas": len(results)})

                pbar.update(1)

                if len(results) >= TARGET_MIN:
                    for f in futures:
                        f.cancel()
                    break

    print(f"\n  ✓ Coletadas {len(results)} t-shirts")

    # Salva CSV
    print("\n[3/3] Salvando metadados...")
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    print(f"  ✓ CSV: {CSV_PATH}")

    # Estatísticas
    print("\n" + "="*60)
    print("RESUMO")
    print("="*60)
    print(f"T-shirts coletadas: {len(results)}")
    if results:
        total_size = sum(r["size_bytes"] for r in results) / (1024**2)
        resolutions = {}
        for r in results:
            res = f'{r["width"]}x{r["height"]}'
            resolutions[res] = resolutions.get(res, 0) + 1

        print(f"Tamanho total: {total_size:.1f} MB")
        print(f"Tamanho médio: {total_size/len(results):.2f} MB/img")
        print(f"\nResoluções:")
        for res, count in sorted(resolutions.items(), key=lambda x: -x[1])[:5]:
            print(f"  {res}: {count} ({count/len(results)*100:.1f}%)")

    print(f"\n✅ Concluído! Apenas T-SHIRTS em: {OUT_DIR}/")
    print("="*60)


if __name__ == "__main__":
    main()
