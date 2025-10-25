#!/usr/bin/env python3
"""
Generate more comprehensive Uniqlo product URLs.
"""

def generate_uniqlo_urls(num_urls=500):
    """Generate more Uniqlo URLs with wider range."""
    urls = set()

    # Expand product code range - Uniqlo products from recent years
    for product_code in range(420000, 475000, 50):  # Wider range, sample every 50
        for color_code in ['00', '01', '03', '04', '05', '06', '07', '08', '09',
                          '10', '30', '31', '32', '33', '34', '35', '36', '37',
                          '56', '57', '58', '59', '60', '61', '62', '63', '64',
                          '65', '66', '67', '68', '69']:
            url = f"https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/{product_code}/item/goods_{color_code}_{product_code}.jpg"
            urls.add(url)

            if len(urls) >= num_urls:
                return list(urls)

    return list(urls)

if __name__ == '__main__':
    urls = generate_uniqlo_urls(num_urls=500)
    print(f"Generated {len(urls)} URLs")

    with open('more_urls.txt', 'w') as f:
        for url in urls:
            f.write(url + '\n')

    print("Saved to more_urls.txt")
