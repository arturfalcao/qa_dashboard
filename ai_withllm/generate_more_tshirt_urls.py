#!/usr/bin/env python3
"""
Generate even more t-shirt URLs with expanded ranges and strategies.
"""

def generate_comprehensive_urls(num_urls=2000):
    """Generate comprehensive t-shirt URLs from multiple sources."""
    urls = set()

    # Strategy 1: Expanded product code ranges
    # Based on Uniqlo's known t-shirt product patterns
    tshirt_ranges = [
        # Classic/Basic tees
        (410000, 430000, 25),   # Earlier products
        (430000, 450000, 20),   # Mid-range
        (450000, 470000, 15),   # Recent releases
        (470000, 475000, 10),   # Latest

        # UT Collection (graphic tees) - typically higher codes
        (436000, 439000, 10),
        (446000, 449000, 10),
        (456000, 459000, 10),
        (466000, 469000, 10),

        # Women's t-shirts (different range)
        (415000, 425000, 30),
        (435000, 445000, 30),
        (445000, 455000, 30),

        # Kids t-shirts
        (405000, 415000, 50),
    ]

    # All possible color codes
    all_colors = [
        '00', '01', '02', '03', '04', '05', '06', '07', '08', '09',
        '10', '11', '30', '31', '32', '33', '34', '35', '36', '37',
        '56', '57', '58', '59', '60', '61', '62', '63', '64', '65',
        '66', '67', '68', '69'
    ]

    print("Generating URLs from product code ranges...")
    for start, end, step in tshirt_ranges:
        for code in range(start, end, step):
            for color in all_colors:
                url = f"https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/{code}/item/goods_{color}_{code}.jpg"
                urls.add(url)

                if len(urls) >= num_urls:
                    return list(urls)

    # Strategy 2: Add specific known product lines
    known_lines = [
        'AIRism', 'Supima', 'Dry-EX', 'Heattech'
    ]

    # Generate more variations
    print(f"Generated {len(urls)} URLs")
    return list(urls)

if __name__ == '__main__':
    urls = generate_comprehensive_urls(num_urls=2000)
    print(f"Total generated: {len(urls)} URLs")

    with open('comprehensive_tshirt_urls.txt', 'w') as f:
        for url in urls:
            f.write(url + '\n')

    print("Saved to comprehensive_tshirt_urls.txt")
