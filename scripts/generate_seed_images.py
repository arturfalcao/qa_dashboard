import math
import os
import random
import struct
import zlib
from typing import Callable, Tuple, Dict, List

WIDTH = 512
HEIGHT = 512

Color = Tuple[int, int, int]

# Utility helpers

def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(color_a: Color, color_b: Color, t: float) -> Color:
    return (
        int(lerp(color_a[0], color_b[0], t)),
        int(lerp(color_a[1], color_b[1], t)),
        int(lerp(color_a[2], color_b[2], t)),
    )


def mix(color_a: Color, color_b: Color, amount: float) -> Color:
    return lerp_color(color_a, color_b, clamp(amount, 0.0, 1.0))


def add_noise(value: float, scale: float = 0.05) -> float:
    return value + (random.random() - 0.5) * scale


# PNG encoder based on the PNG specification

def write_png(filename: str, pixels: List[List[Color]]) -> None:
    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        return struct.pack('!I', len(data)) + chunk_type + data + struct.pack('!I', zlib.crc32(chunk_type + data) & 0xFFFFFFFF)

    raw = bytearray()
    for row in pixels:
        raw.append(0)  # filter type 0 (None)
        for r, g, b in row:
            raw.extend([r, g, b])

    compressed = zlib.compress(bytes(raw), level=9)

    header = struct.pack('!IIBBBBB', WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    png_data = bytearray()
    png_data.extend(b'\x89PNG\r\n\x1a\n')
    png_data.extend(png_chunk(b'IHDR', header))
    png_data.extend(png_chunk(b'IDAT', compressed))
    png_data.extend(png_chunk(b'IEND', b''))

    with open(filename, 'wb') as f:
        f.write(png_data)


# Garment masks -------------------------------------------------------------

def tshirt_mask(nx: float, ny: float) -> float:
    # Returns distance-like metric: negative inside, positive outside
    # Body
    if ny > 0.85 or ny < -0.95:
        return 1.0

    width_top = 0.75
    width_mid = 0.45
    width_bottom = 0.38

    if ny < -0.35:
        width = lerp(width_top, width_mid, (ny + 0.95) / 0.6)
    elif ny < 0.45:
        width = width_mid
    else:
        width = lerp(width_mid, width_bottom, (ny - 0.45) / 0.4)

    dx = abs(nx) - width
    if ny > 0.6:
        dx = abs(nx) - width_bottom

    if ny < -0.55:
        sleeve_width = 0.9
        dx = min(dx, abs(nx) - sleeve_width)

    return max(dx, ny - 0.85)


def hoodie_mask(nx: float, ny: float) -> float:
    base = tshirt_mask(nx, ny)
    # Add hood
    hood_center_y = -0.75
    hood_radius = 0.35
    hood = math.sqrt((nx) ** 2 + (ny - hood_center_y) ** 2) - hood_radius
    return min(base, hood)


def jacket_mask(nx: float, ny: float) -> float:
    base = tshirt_mask(nx, ny)
    # Slightly wider body for jacket
    extra = abs(nx) - 0.5
    return min(base, extra)


def sweater_mask(nx: float, ny: float) -> float:
    return tshirt_mask(nx * 0.95, ny)


def pants_mask(nx: float, ny: float) -> float:
    if ny < -0.2 or ny > 0.95:
        return 1.0

    if ny < 0.2:
        width = 0.35
        dx = abs(nx) - width
        return max(dx, abs(ny + 0.2) - 0.4)

    leg_width = 0.23
    gap = 0.06
    if nx < 0:
        dx = abs(nx + gap) - leg_width
    else:
        dx = abs(nx - gap) - leg_width

    return max(dx, ny - 0.95)


def long_coat_mask(nx: float, ny: float) -> float:
    if ny > 0.95 or ny < -0.95:
        return 1.0

    width_top = 0.55
    width_bottom = 0.45

    if ny < 0.5:
        width = width_top
    else:
        width = lerp(width_top, width_bottom, (ny - 0.5) / 0.45)

    dx = abs(nx) - width
    return max(dx, ny - 0.95)


MASKS: Dict[str, Callable[[float, float], float]] = {
    'tshirt': tshirt_mask,
    'hoodie': hoodie_mask,
    'jacket': jacket_mask,
    'sweater': sweater_mask,
    'pants': pants_mask,
    'long_coat': long_coat_mask,
}


# Pattern helpers -----------------------------------------------------------

def apply_pattern(base: Color, nx: float, ny: float, pattern: str, accent: Color) -> Color:
    if pattern == 'stripes':
        stripe = (math.sin((ny + 0.5) * math.pi * 6) + 1) / 2
        amount = 0.2 if stripe > 0.5 else -0.1
        return mix(base, accent, 0.2 if stripe > 0.55 else 0.0)
    if pattern == 'heather':
        noise = (math.sin(nx * 25) + math.cos(ny * 35)) * 0.5
        return mix(base, (min(base[0] + 30, 255), min(base[1] + 30, 255), min(base[2] + 30, 255)), 0.25 * (noise + 1) / 2)
    if pattern == 'polo':
        if abs(nx) < 0.08 and ny < -0.1:
            return mix(base, accent, 0.35)
        if abs(nx) < 0.01 and ny > -0.1:
            return mix(base, (240, 240, 240), 0.25)
    if pattern == 'zipper':
        if abs(nx) < 0.015:
            return mix(base, (220, 220, 220), 0.4)
    if pattern == 'denim':
        seam = abs(nx) < 0.02 or abs(abs(nx) - 0.25) < 0.015
        if seam:
            return mix(base, (235, 200, 140), 0.35)
        stitches = math.sin((ny + nx) * 35)
        return mix(base, (base[0] + 20, base[1] + 20, base[2] + 20), 0.1 if stitches > 0.5 else 0)
    if pattern == 'ribbed':
        rib = (math.sin(nx * math.pi * 12) + 1) / 2
        return mix(base, (base[0] - 20, base[1] - 20, base[2] - 20), 0.2 if rib > 0.5 else 0)
    if pattern == 'contrast_sleeves':
        if ny < -0.3:
            sleeve_color = accent
            return mix(base, sleeve_color, 0.85)
    return base


# Defect overlays -----------------------------------------------------------

def apply_defect(color: Color, nx: float, ny: float, defect: Dict) -> Color:
    if not defect:
        return color

    d_type = defect.get('type')
    if d_type == 'stain':
        for cx, cy, radius in defect['spots']:
            dist = math.sqrt((nx - cx) ** 2 + (ny - cy) ** 2)
            if dist < radius:
                intensity = clamp(1 - dist / radius, 0, 1)
                stain_color = defect.get('color', (140, 35, 30))
                return mix(color, stain_color, 0.6 * intensity)
    elif d_type == 'stitching':
        wave = math.sin((ny + 0.2) * math.pi * 8 + nx * 6)
        if abs(nx) < 0.02 and abs(wave) > 0.75:
            return mix(color, (200, 40, 40), 0.6)
        if abs(nx) < 0.01:
            return mix(color, (230, 230, 230), 0.3)
    elif d_type == 'misprint':
        if ny < -0.1 and abs(nx) < 0.35:
            band = (ny + 0.3) / 0.25
            if 0 <= band <= 1:
                mis_color = defect.get('color', (235, 235, 235))
                return mix(color, mis_color, 0.7)
        if ny < -0.12 and abs(nx - 0.12) < 0.08:
            return mix(color, (40, 40, 40), 0.8)
    elif d_type == 'measurement':
        if abs(ny - defect.get('line_y', 0.2)) < 0.01:
            return mix(color, (220, 220, 220), 0.4)
        ticks = defect.get('ticks', [])
        for tx in ticks:
            if abs(nx - tx) < 0.008:
                return mix(color, (220, 220, 220), 0.5)
    elif d_type == 'tear':
        tear_path = math.sin(nx * 20) * 0.08
        if abs(ny - tear_path) < 0.03 and abs(nx) < 0.4:
            return mix(color, (60, 60, 60), 0.7)
    return color


def render_image(shape: str, base_color: Color, accent_color: Color, pattern: str = '', defect: Dict = None) -> List[List[Color]]:
    mask_fn = MASKS[shape]
    background_top = (235, 235, 240)
    background_bottom = (205, 205, 210)

    pixels: List[List[Color]] = []
    for y in range(HEIGHT):
        row: List[Color] = []
        for x in range(WIDTH):
            nx = (x / WIDTH) * 2 - 1
            ny = (y / HEIGHT) * 2 - 1

            background = lerp_color(background_top, background_bottom, y / HEIGHT)
            body_color = base_color

            distance = mask_fn(nx, ny)
            if distance <= 0:
                shade = clamp(0.15 + (ny + 1) / 2 * 0.55, 0.2, 0.85)
                body_color = tuple(int(channel * shade) for channel in base_color)
                body_color = apply_pattern(body_color, nx, ny, pattern, accent_color)
                if abs(nx) > 0.4 and ny < -0.3:
                    body_color = mix(body_color, tuple(int(c * 0.92) for c in body_color), 0.5)
                if defect:
                    body_color = apply_defect(body_color, nx, ny, defect)
                row.append(body_color)
            else:
                # soft shadow near edges
                shadow = clamp(1 - min(distance * 8, 1), 0, 1)
                shadow_color = mix(background, (180, 180, 185), shadow * 0.2)
                row.append(shadow_color)
        pixels.append(row)
    return pixels


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def main() -> None:
    random.seed(42)
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'seed-images')
    ensure_dir(base_dir)

    garments = [
        ('garment-1.png', 'tshirt', (190, 220, 240), (40, 120, 210), 'stripes', None),
        ('garment-2.png', 'hoodie', (180, 200, 215), (220, 230, 240), 'zipper', None),
        ('garment-3.png', 'pants', (50, 80, 120), (230, 210, 170), 'denim', None),
        ('garment-4.png', 'tshirt', (245, 210, 150), (230, 160, 70), 'polo', None),
        ('garment-5.png', 'jacket', (55, 70, 95), (215, 170, 90), 'zipper', None),
        ('garment-6.png', 'sweater', (180, 95, 100), (210, 150, 150), 'ribbed', None),
        ('garment-7.png', 'tshirt', (120, 160, 120), (240, 240, 240), 'contrast_sleeves', None),
        ('garment-8.png', 'long_coat', (160, 130, 90), (200, 190, 170), 'heather', None),
    ]

    defects = [
        ('defect-stain.png', 'tshirt', (210, 225, 230), (150, 50, 45), 'stripes', {
            'type': 'stain',
            'spots': [(-0.1, 0.1, 0.22), (0.05, 0.25, 0.18)],
            'color': (150, 40, 30),
        }),
        ('defect-stitching.png', 'hoodie', (190, 210, 220), (230, 230, 230), 'zipper', {
            'type': 'stitching',
        }),
        ('defect-misprint.png', 'tshirt', (230, 210, 150), (35, 35, 35), 'polo', {
            'type': 'misprint',
            'color': (240, 240, 240),
        }),
        ('defect-measurement.png', 'pants', (60, 85, 120), (230, 210, 170), 'denim', {
            'type': 'measurement',
            'line_y': 0.35,
            'ticks': [-0.25, -0.15, -0.05, 0.05, 0.15, 0.25],
        }),
        ('defect-other.png', 'jacket', (65, 80, 110), (220, 180, 100), 'zipper', {
            'type': 'tear',
        }),
    ]

    for filename, shape, base_color, accent, pattern, defect in garments + defects:
        pixels = render_image(shape, base_color, accent, pattern, defect)
        write_png(os.path.join(base_dir, filename), pixels)
        print(f'Generated {filename}')


if __name__ == '__main__':
    main()
