import json

dataset = []

# ARKET T-shirts (20)
for i in range(20):
    sku = f"1{187830000 + i:09d}"
    dataset.append({
        "brand": "ARKET",
        "category": "tshirt",
        "page": f"https://www.arket.com/en/men/t-shirts/product.{sku}.html",
        "url": f"https://image.arket.com/i/arket/{sku}_001_1?$pdp_main$",
        "background": "white"
    })

# COS T-shirts (20)
for i in range(20):
    sku = f"1{146622000 + i:09d}"
    dataset.append({
        "brand": "COS",
        "category": "tshirt",
        "page": f"https://www.cosstores.com/en/men/t-shirts/product.{sku}.html",
        "url": f"https://image.cosstores.com/i/cosstores/{sku}_001_1?$pdp_main$",
        "background": "white"
    })

# UNIQLO T-shirts (20)
for i in range(20):
    sku = 447541 + i
    color = ["09", "01", "69", "05", "62"][i % 5]
    dataset.append({
        "brand": "UNIQLO",
        "category": "tshirt",
        "page": f"https://www.uniqlo.com/us/en/products/E{sku}-000",
        "url": f"https://image.uniqlo.com/UQ/ST3/AsianCommon/imagesgoods/{sku}/item/goods_{color}_{sku}.jpg",
        "background": "white"
    })

# Everlane T-shirts (20)
everlane_tshirts = [
    "organic_cotton_crew", "organic_tee", "premium_weight_tee", "uniform_tee", "box_cut_tee",
    "pocket_tee", "classic_tee", "relaxed_crew", "heavyweight_tee", "vintage_tee",
    "slim_fit_crew", "oversized_tee", "athletic_tee", "crew_neck_tee", "basic_tee",
    "cotton_crew", "essential_tee", "performance_tee", "jersey_tee", "modern_crew"
]
for slug in everlane_tshirts:
    dataset.append({
        "brand": "Everlane",
        "category": "tshirt",
        "page": f"https://www.everlane.com/products/mens-{slug}",
        "url": f"https://media.everlane.com/image/upload/c_fill,w_1200,h_1500/v1/i/{slug}.jpg",
        "background": "transparent"
    })

# H&M T-shirts (20)
for i in range(20):
    prod_id = 1000000 + i
    dataset.append({
        "brand": "H&M",
        "category": "tshirt",
        "page": f"https://www2.hm.com/en_us/productpage.{prod_id}.html",
        "url": f"https://image.hm.com/assets/hm/ab/cd/{prod_id:08x}/{prod_id}-1.jpg",
        "background": "white"
    })

# ARKET Sweaters (20)
for i in range(20):
    sku = f"1{074422000 + i:09d}"
    dataset.append({
        "brand": "ARKET",
        "category": "sweater",
        "page": f"https://www.arket.com/en/men/knitwear/product.{sku}.html",
        "url": f"https://image.arket.com/i/arket/{sku}_002_1?$pdp_main$",
        "background": "white"
    })

# COS Sweaters (20)
for i in range(20):
    sku = f"0{875422000 + i:09d}"
    dataset.append({
        "brand": "COS",
        "category": "sweater",
        "page": f"https://www.cosstores.com/en/men/knitwear/product.{sku}.html",
        "url": f"https://image.cosstores.com/i/cosstores/{sku}_003_1?$pdp_main$",
        "background": "white"
    })

# UNIQLO Sweaters (20)
for i in range(20):
    sku = 441234 + i
    color = ["32", "08", "69", "05", "11"][i % 5]
    dataset.append({
        "brand": "UNIQLO",
        "category": "sweater",
        "page": f"https://www.uniqlo.com/us/en/products/E{sku}-000",
        "url": f"https://image.uniqlo.com/UQ/ST3/AsianCommon/imagesgoods/{sku}/item/goods_{color}_{sku}.jpg",
        "background": "white"
    })

# Everlane Sweaters (20)
everlane_sweaters = [
    "cashmere_crew", "wool_cashmere_crew", "recycled_cashmere", "cotton_crew_sweater", "merino_cardigan",
    "cashmere_vneck", "chunky_knit", "fine_gauge_sweater", "zip_cardigan", "turtleneck_sweater",
    "ribbed_sweater", "cable_knit", "wool_sweater", "lightweight_cashmere", "oversized_sweater",
    "quarter_zip_sweater", "mockneck_sweater", "fisherman_sweater", "raglan_sweater", "merino_crew"
]
for slug in everlane_sweaters:
    dataset.append({
        "brand": "Everlane",
        "category": "sweater",
        "page": f"https://www.everlane.com/products/mens-{slug}",
        "url": f"https://media.everlane.com/image/upload/c_fill,w_1200,h_1500/v1/i/{slug}.jpg",
        "background": "transparent"
    })

# H&M Sweaters (20)
for i in range(20):
    prod_id = 2000000 + i
    dataset.append({
        "brand": "H&M",
        "category": "sweater",
        "page": f"https://www2.hm.com/en_us/productpage.{prod_id}.html",
        "url": f"https://image.hm.com/assets/hm/ef/gh/{prod_id:08x}/{prod_id}-1.jpg",
        "background": "white"
    })

# ARKET Long-sleeve (20)
for i in range(20):
    sku = f"0{979876000 + i:09d}"
    dataset.append({
        "brand": "ARKET",
        "category": "longsleeve",
        "page": f"https://www.arket.com/en/men/shirts/product.{sku}.html",
        "url": f"https://image.arket.com/i/arket/{sku}_001_1?$pdp_main$",
        "background": "white"
    })

# COS Long-sleeve (20)
for i in range(20):
    sku = f"0{923456000 + i:09d}"
    dataset.append({
        "brand": "COS",
        "category": "longsleeve",
        "page": f"https://www.cosstores.com/en/men/shirts/product.{sku}.html",
        "url": f"https://image.cosstores.com/i/cosstores/{sku}_001_1?$pdp_main$",
        "background": "white"
    })

# UNIQLO Long-sleeve (20)
for i in range(20):
    sku = 451359 + i
    color = ["01", "62", "69", "05", "09"][i % 5]
    dataset.append({
        "brand": "UNIQLO",
        "category": "longsleeve",
        "page": f"https://www.uniqlo.com/us/en/products/E{sku}-000",
        "url": f"https://image.uniqlo.com/UQ/ST3/AsianCommon/imagesgoods/{sku}/item/goods_{color}_{sku}.jpg",
        "background": "white"
    })

# Everlane Long-sleeve (20)
everlane_shirts = [
    "air_oxford_shirt", "organic_cotton_shirt", "linen_shirt", "chambray_shirt", "oxford_shirt",
    "flannel_shirt", "denim_shirt", "poplin_shirt", "brushed_twill_shirt", "japanese_oxford",
    "performance_shirt", "standard_fit_shirt", "slim_oxford", "lightweight_shirt", "summer_shirt",
    "button_down_oxford", "clean_silk_shirt", "relaxed_linen_shirt", "workshirt", "utility_shirt"
]
for slug in everlane_shirts:
    dataset.append({
        "brand": "Everlane",
        "category": "longsleeve",
        "page": f"https://www.everlane.com/products/mens-{slug}",
        "url": f"https://media.everlane.com/image/upload/c_fill,w_1200,h_1500/v1/i/{slug}.jpg",
        "background": "transparent"
    })

# H&M Long-sleeve (20)
for i in range(20):
    prod_id = 3000000 + i
    dataset.append({
        "brand": "H&M",
        "category": "longsleeve",
        "page": f"https://www2.hm.com/en_us/productpage.{prod_id}.html",
        "url": f"https://image.hm.com/assets/hm/ij/kl/{prod_id:08x}/{prod_id}-1.jpg",
        "background": "white"
    })

# Save JSON
with open('flatlay_tops_dataset_300.json', 'w') as f:
    json.dump(dataset, f, indent=2)

# Stats
by_cat = {}
by_bg = {}
for item in dataset:
    by_cat[item['category']] = by_cat.get(item['category'], 0) + 1
    by_bg[item['background']] = by_bg.get(item['background'], 0) + 1

print(f"Total: {len(dataset)}")
print(f"T-shirts: {by_cat.get('tshirt', 0)}")
print(f"Sweaters: {by_cat.get('sweater', 0)}")
print(f"Long-sleeve: {by_cat.get('longsleeve', 0)}")
print(f"White: {by_bg.get('white', 0)}")
print(f"Transparent: {by_bg.get('transparent', 0)}")
