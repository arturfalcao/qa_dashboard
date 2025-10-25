#!/usr/bin/env python3
"""
Coleta 300+ t-shirts flat-lay de alta resolução do Uniqlo (2000x2000px).
Gera URLs diretas do CDN, valida fundo branco, e salva em CSV.
"""

import os
import csv
import hashlib
import time
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
import requests
from PIL import Image
import numpy as np
from tqdm import tqdm

# ----------------------- CONFIG -----------------------
OUT_DIR = "uniqlo_tshirts_300"
CSV_PATH = os.path.join(OUT_DIR, "images.csv")
TARGET_MIN = 320                # Objetivo: 320 imagens (para garantir 300+)
WIDTH = 2000                    # Resolução da imagem
TIMEOUT = 10
MAX_WORKERS = 20                # Threads paralelas
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Ranges de códigos de produto Uniqlo para t-shirts
# Baseado em análise de padrões: 410000-475000
PRODUCT_RANGES = [
    # Men's t-shirts
    (410000, 412000, 25),   # Classic crew neck
    (415000, 418000, 25),   # Premium cotton
    (420000, 425000, 50),   # Supima/AIRism
    (425000, 430000, 50),   # Graphic tees (UT)
    (430000, 435000, 75),   # Seasonal
    (440000, 445000, 100),  # Recent releases
    (450000, 455000, 100),  # Latest
    (455000, 460000, 100),  # Current season
    (460000, 465000, 100),  # New arrivals
    (465000, 470000, 150),  # Latest collections
]

# Códigos de cor mais comuns no Uniqlo
COLOR_CODES = [
    '00',  # White
    '01',  # Off-white
    '02',  # Light gray
    '03',  # Gray
    '04',  # Dark gray
    '05',  # Navy
    '06',  # Blue
    '07',  # Light blue
    '08',  # Green
    '09',  # Black
    '10',  # Brown
    '30',  # Red
    '31',  # Pink
    '32',  # Orange
    '56',  # Yellow
    '57',  # Light green
    '58',  # Olive
    '69',  # Purple
]
# ------------------------------------------------------


def uniqlo_url(product_code: int, color_code: str, width: int = WIDTH) -> str:
    """Gera URL direta do CDN Uniqlo."""
    return f"https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/{product_code}/item/goods_{color_code}_{product_code}.jpg?width={width}"


def sha1(b: bytes) -> str:
    """Hash SHA1 do conteúdo."""
    return hashlib.sha1(b).hexdigest()


def ensure_out():
    """Cria diretório de saída."""
    os.makedirs(OUT_DIR, exist_ok=True)


def is_valid_flatlay(image_bytes: bytes, min_size: int = 800) -> bool:
    """
    Valida se a imagem é flat-lay (fundo branco, alta resolução).

    Critérios:
    - Resolução mínima: 800x800px
    - Borda da imagem deve ser >60% pixels claros (>235 RGB)
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size

        # Verifica resolução mínima
        if min(w, h) < min_size:
            return False

        # Verifica fundo branco nas bordas
        arr = np.array(img)

        # Concatena pixels das 4 bordas
        border = np.concatenate([
            arr[0, :, :],      # Top
            arr[-1, :, :],     # Bottom
            arr[:, 0, :],      # Left
            arr[:, -1, :]      # Right
        ], axis=0)

        # Calcula proporção de pixels claros (média RGB > 235)
        border_brightness = (border.mean(axis=1) > 235).mean()

        return border_brightness > 0.6

    except Exception:
        return False


def download_and_validate(url: str, product_code: int, color_code: str) -> dict:
    """
    Baixa e valida uma imagem.
    Retorna dict com metadados se válida, None se inválida.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)

        if response.status_code != 200:
            return None

        if "image" not in response.headers.get("Content-Type", ""):
            return None

        content = response.content

        # Valida se é flat-lay
        if not is_valid_flatlay(content):
            return None

        # Abre imagem para pegar dimensões
        img = Image.open(io.BytesIO(content))
        w, h = img.size

        # Salva imagem
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

    except Exception as e:
        return None


def generate_product_urls():
    """Gera todas as URLs de produto possíveis."""
    urls = []

    for start, end, step in PRODUCT_RANGES:
        for code in range(start, end, step):
            for color in COLOR_CODES:
                urls.append((code, color, uniqlo_url(code, color)))

    return urls


def main():
    print("="*60)
    print("UNIQLO T-SHIRT COLLECTOR - 300+ HIGH-RES IMAGES")
    print("="*60)

    ensure_out()

    # Gera URLs
    print("\n[1/3] Gerando URLs de produto...")
    product_urls = generate_product_urls()
    print(f"  → Geradas {len(product_urls)} URLs para testar")

    # Download paralelo
    print(f"\n[2/3] Baixando e validando imagens ({MAX_WORKERS} workers)...")
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submete todas as tarefas
        futures = {
            executor.submit(download_and_validate, url, code, color): (code, color)
            for code, color, url in product_urls
        }

        # Processa resultados conforme completam
        with tqdm(total=len(futures), desc="Processando") as pbar:
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
                    pbar.set_postfix({"válidas": len(results)})

                pbar.update(1)

                # Para quando atingir objetivo
                if len(results) >= TARGET_MIN:
                    # Cancela tasks pendentes
                    for f in futures:
                        f.cancel()
                    break

    print(f"\n  ✓ Coletadas {len(results)} imagens válidas")

    # Salva CSV
    print("\n[3/3] Salvando metadados em CSV...")
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    print(f"  ✓ CSV salvo em: {CSV_PATH}")

    # Estatísticas finais
    print("\n" + "="*60)
    print("RESUMO")
    print("="*60)
    print(f"Imagens coletadas: {len(results)}")
    if results:
        total_size = sum(r["size_bytes"] for r in results) / (1024**2)
        avg_size = total_size / len(results)
        resolutions = {}
        for r in results:
            res = f'{r["width"]}x{r["height"]}'
            resolutions[res] = resolutions.get(res, 0) + 1

        print(f"Tamanho total: {total_size:.1f} MB")
        print(f"Tamanho médio: {avg_size:.2f} MB/imagem")
        print(f"\nResoluções:")
        for res, count in sorted(resolutions.items(), key=lambda x: -x[1]):
            print(f"  {res}: {count} imagens ({count/len(results)*100:.1f}%)")

    print(f"\n✅ Concluído! Imagens em: {OUT_DIR}/")
    print("="*60)


if __name__ == "__main__":
    main()
