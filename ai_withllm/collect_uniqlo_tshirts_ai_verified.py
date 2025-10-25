#!/usr/bin/env python3
"""
Coleta 300+ t-shirts flat-lay do Uniqlo com VERIFICAÇÃO AI.
Usa CLIP para garantir que cada imagem é realmente uma t-shirt.
"""

import os
import csv
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from PIL import Image
import numpy as np
from tqdm import tqdm
import io
import torch
from transformers import CLIPProcessor, CLIPModel

# ----------------------- CONFIG -----------------------
OUT_DIR = "uniqlo_tshirts_ai_verified"
CSV_PATH = os.path.join(OUT_DIR, "images.csv")
TARGET_MIN = 320                # Objetivo: 320 imagens
WIDTH = 2000                    # Resolução da imagem
TIMEOUT = 10
MAX_WORKERS = 8                 # Menos threads (CLIP é pesado)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Códigos VERIFICADOS de t-shirts
VERIFIED_CODES = [
    410025, 410225, 410250, 410275, 410300, 410375, 410425, 410450, 410550, 410575,
    410625, 410675, 410700, 410750, 410825, 410900, 410925, 410950, 410975, 411075,
    411225, 411250, 411275, 411325, 411350, 411375, 411400, 411425,
    422700, 423600, 425000, 425500, 425700, 425900, 426400, 426700, 427400, 428500,
    440600, 444300, 444900, 450600, 452200, 453900, 457200, 458100, 458300, 459700,
    460500, 460900, 461200, 461600, 463500, 463600, 464200, 464300, 464500
]

SEARCH_RADIUS = 25

COLOR_CODES = [
    '00', '01', '02', '03', '04', '05', '06', '07', '08', '09',
    '10', '30', '31', '32', '56', '57', '58', '69'
]

# CLIP labels for classification
TSHIRT_LABELS = [
    "a t-shirt on white background",
    "a short sleeve shirt on white background",
    "a tee shirt product photo"
]

NON_TSHIRT_LABELS = [
    "pants on white background",
    "jeans on white background",
    "jacket on white background",
    "dress on white background",
    "shorts on white background",
    "sweater on white background",
    "hoodie on white background"
]
# ------------------------------------------------------


class TShirtVerifier:
    """Verifica se imagem é t-shirt usando CLIP."""

    def __init__(self):
        print("Carregando modelo CLIP...")
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.model.eval()
        print("✓ CLIP carregado")

    def is_tshirt(self, image: Image.Image, threshold: float = 0.6) -> bool:
        """
        Verifica se imagem é t-shirt usando CLIP.
        Retorna True se a imagem for classificada como t-shirt.
        """
        try:
            # Prepara labels
            all_labels = TSHIRT_LABELS + NON_TSHIRT_LABELS

            # Processa imagem e texto
            inputs = self.processor(
                text=all_labels,
                images=image,
                return_tensors="pt",
                padding=True
            )

            # Inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)[0]

            # Soma probabilidades de t-shirt vs não-t-shirt
            tshirt_prob = probs[:len(TSHIRT_LABELS)].sum().item()
            non_tshirt_prob = probs[len(TSHIRT_LABELS):].sum().item()

            return tshirt_prob > threshold

        except Exception as e:
            print(f"Erro ao classificar: {e}")
            return False


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
    """
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


def download_and_validate(url: str, product_code: int, color_code: str, verifier: TShirtVerifier) -> dict:
    """
    Baixa, valida e classifica uma imagem.
    Retorna dict com metadados se válida, None se inválida.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)

        if response.status_code != 200:
            return None

        if "image" not in response.headers.get("Content-Type", ""):
            return None

        content = response.content

        # 1. Valida flat-lay
        if not is_valid_flatlay(content):
            return None

        # 2. Abre imagem
        img = Image.open(io.BytesIO(content)).convert("RGB")
        w, h = img.size

        # 3. VERIFICA SE É T-SHIRT COM CLIP
        if not verifier.is_tshirt(img):
            return None

        # 4. Salva imagem
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


def generate_product_urls():
    """Gera URLs para códigos verificados + códigos próximos."""
    urls = []
    seen_codes = set()

    for base_code in VERIFIED_CODES:
        for offset in range(-SEARCH_RADIUS, SEARCH_RADIUS + 1):
            code = base_code + offset
            if code in seen_codes:
                continue
            seen_codes.add(code)

            for color in COLOR_CODES:
                urls.append((code, color, uniqlo_url(code, color)))

    return urls


def main():
    print("="*60)
    print("UNIQLO T-SHIRT COLLECTOR - AI VERIFIED (CLIP)")
    print("="*60)

    ensure_out()

    # Carrega CLIP
    verifier = TShirtVerifier()

    # Gera URLs
    print("\n[1/3] Gerando URLs de produto...")
    product_urls = generate_product_urls()
    print(f"  → Geradas {len(product_urls)} URLs para testar")
    print(f"  → Verificação AI: CLIP para garantir t-shirts")

    # Download paralelo
    print(f"\n[2/3] Baixando e validando com AI ({MAX_WORKERS} workers)...")
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(download_and_validate, url, code, color, verifier): (code, color)
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

    print(f"\n  ✓ Coletadas {len(results)} t-shirts VERIFICADAS com AI")

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
    print(f"T-shirts coletadas (AI verified): {len(results)}")
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

    print(f"\n✅ Concluído! T-shirts em: {OUT_DIR}/")
    print("="*60)


if __name__ == "__main__":
    main()
