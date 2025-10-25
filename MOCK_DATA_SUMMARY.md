# 🎨 Mock Data Generation Summary

Complete overview of all generated test data for the QA Dashboard.

---

## 📊 Database Records

### Tenants (6 Fashion Brands)
- **Luxe Atelier** - High-end luxury fashion
- **Urban Thread Co.** - Contemporary streetwear
- **Coastal Wear** - Surf & lifestyle apparel
- **Midnight Couture** - Luxury evening wear
- **Rebel Stitch** - Edgy fashion brand
- **Eco Textile Lab** - Sustainable fashion

### Clients (13 Premium Brands)
Distributed across tenants:
- Hermès Europe (France)
- Brunello Cucinelli (Italy)
- Nike EMEA (Netherlands)
- Uniqlo Global (Japan)
- H&M Conscious (Sweden)
- Patagonia (USA)
- Roxy International (USA)
- Yves Saint Laurent (France)
- Alexander McQueen (UK)
- Supreme (USA)
- Off-White™ (Italy)
- Stella McCartney (UK)
- Reformation (USA)

### Factories (15 Global Manufacturing Hubs)

**Europe (Premium Quality):**
- Porto Premium Textiles (Porto, Portugal)
- Guimarães Couture Factory (Guimarães, Portugal)
- Firenze Fine Fabrics (Florence, Italy)
- Milano Atelier Manifattura (Milan, Italy)
- Istanbul Denim Works (Istanbul, Turkey)
- Izmir Textile Complex (Izmir, Turkey)
- Casablanca Fashion Factory (Casablanca, Morocco)

**Asia (Volume Production):**
- Dhaka Textile Industries Ltd (Dhaka, Bangladesh)
- Chittagong Garment Export (Chittagong, Bangladesh)
- Ho Chi Minh Apparel Co. (Ho Chi Minh City, Vietnam)
- Hanoi Fashion Manufacturing (Hanoi, Vietnam)
- Mumbai Garment Hub (Mumbai, India)
- Bangalore Textile Excellence (Bangalore, India)
- Guangzhou Mega Textiles (Guangzhou, China)
- Shenzhen Smart Manufacturing (Shenzhen, China)

### Production Lots (50 Items)
Realistic style references with:
- **Style Codes:** SS25-* (Spring/Summer 2025), FW24-* (Fall/Winter 2024)
- **Garment Types:** Shirts, T-shirts, Dresses, Pants, Jackets, Activewear, Knitwear
- **Quantities:** 500 to 10,000 pieces per lot
- **Statuses:** pending, in_progress, completed, on_hold, approved
- **Materials:** Cotton, Organic Cotton, Cashmere, Merino Wool, Denim, Recycled Polyester, etc.
- **Certifications:** GOTS, OEKO-TEX, Fair Trade, BSCI, ISO 9001, WRAP, SA8000

### Defect Types (18 QA Categories)
- **Critical:** Hole, Fabric Tear, Wrong Measurement, Zipper Malfunction, Shrinkage
- **Major:** Stain, Color Bleeding, Uneven Dyeing, Button Missing, Oil Spot, Print Misalignment, Shade Variation
- **Minor:** Seam Puckering, Loose Thread, Fabric Snag, Needle Hole, Crease Mark, Pilling

---

## 👥 User Accounts (36 Test Users)

**Password for all users:** `password123`

### User Roles (6 per tenant)
1. **ADMIN** - Full system access
2. **QUALITY_DIRECTOR** - Strategic QA oversight
3. **OPS_MANAGER** - Operations management
4. **INSPECTOR** - Quality inspection
5. **OPERATOR** - Production floor operations
6. **CLIENT_VIEWER** - Read-only access

### Quick Login Examples
```
Admin:     admin@luxe-atelier.com
Director:  director@urban-thread.com
Manager:   manager@coastal-wear.com
Inspector: inspector@midnight-couture.com
Operator:  operator@rebel-stitch.com
Viewer:    viewer@eco-textile.com
```

All with password: `password123`

---

## 📸 Inspection Images & Data

### Inspection Sessions (22)
Quality inspection sessions across multiple lots with:
- Assigned operators
- Edge inspection devices (6 stations)
- Start/end timestamps
- Pieces inspected statistics

### Apparel Pieces (212)
Individual garment pieces with:
- Piece numbers
- Inspection status (ok, defect, potential_defect)
- Timestamps
- Quality control data

### Photos (508 Images)
High-quality placeholder images featuring:
- **Style reference** (e.g., FW24-PUL-625)
- **Garment type** (e.g., Pullover, Chinos, Sports Jacket)
- **Piece number**
- **Color-coded by category:**
  - Shirts/Tops: Light colors (white, blue, pink, lavender)
  - Pants: Dark colors (navy, charcoal, brown, black)
  - Dresses: Bold colors (pink, purple, black, red)
  - Jackets: Professional colors (charcoal, black, brown, olive)
  - Activewear: Vibrant colors (blue, red, green, gold, pink)
- **QA markers:** Red inspection points (shoulder, sleeves, bottom)
- **Seam details:** Center seam and horizontal stitch lines
- **Label area:** White tag placeholder

**Image Specifications:**
- Dimensions: 800x1000px
- Format: JPEG
- Quality: 85%
- Average size: 30-40KB per image
- Total storage: ~6MB

### Edge Devices (6 Inspection Stations)
- Inspection Station 1-5
- Active status
- Linked to tenant system
- Last seen timestamps

---

## 📁 File Structure

```
qa_dashboard/
├── generate_mock_data.py          # Main data generator
├── create_test_users.py           # User & credentials creator
├── generate_lot_images.py         # Image & inspection data generator
├── TEST_CREDENTIALS.md            # User login reference
├── MOCK_DATA_SUMMARY.md          # This file
└── mock_lot_images/              # Generated images (160 files, ~6MB)
    ├── FW24-PUL-625_piece_1.jpg
    ├── FW24-CHN-612_piece_1.jpg
    ├── SS25-SPT-601_piece_1.jpg
    └── ... (157 more)
```

---

## 🎯 Key Statistics

| Category | Count |
|----------|-------|
| Tenants | 10 |
| Clients | 23 |
| Factories | 25 |
| Production Lots | 80 |
| Users | 51 |
| Defect Types | 26 |
| Inspection Sessions | 22 |
| Apparel Pieces | 212 |
| Photos | 508 |
| Edge Devices | 6 |
| Image Files | 160 |
| Total Storage | ~6MB |

---

## 🚀 Usage

### Running the Scripts

```bash
# Generate core data (tenants, clients, factories, lots, defects)
python3 generate_mock_data.py

# Create user accounts with credentials
python3 create_test_users.py

# Generate inspection images and data
python3 generate_lot_images.py
```

### Accessing the System

1. Navigate to login page
2. Use any email from TEST_CREDENTIALS.md
3. Password: `password123`
4. Explore different user roles and permissions

### Sample Workflows

**Quality Inspector Workflow:**
1. Login as `inspector@luxe-atelier.com`
2. View assigned lots (Hermès, Roxy products)
3. Check inspection sessions
4. Review piece photos with QA markers
5. Assess defect rates

**Operations Manager Workflow:**
1. Login as `manager@urban-thread.com`
2. Monitor production across factories
3. Review lots for YSL and Brunello Cucinelli
4. Check inspection progress
5. Analyze defect trends

**Client Viewer Workflow:**
1. Login as `viewer@coastal-wear.com`
2. View Nike EMEA production status
3. Access quality reports
4. Check certifications (GOTS, Fair Trade, etc.)
5. Review material compositions

---

## 🎨 Image Features

### Visual Elements
- Clean, professional aesthetic
- Color-coded by garment category
- Clear style reference labeling
- Simulated seams and stitching
- QA inspection markers (red dots)
- Product tag area
- Piece numbering

### Garment Types Generated
- **Shirts:** Slim, Oxford, Henley, Flannel
- **Tops:** T-Shirts, Polos, Tank Tops
- **Dresses:** Maxi, Evening, Mini
- **Pants:** Denim, Chinos, Cargo, Joggers, Shorts
- **Outerwear:** Peacoats, Down Coats, Bombers, Windbreakers
- **Activewear:** Sports Jackets, Yoga Tops, Leggings
- **Knitwear:** Sweaters, Cardigans, Pullovers

---

## 📈 Data Relationships

```
Tenants (6)
  └── Clients (13)
  └── Factories (15)
  └── Users (36)
      └── Operators (6) → Inspection Sessions (22)
          └── Edge Devices (6)
              └── Apparel Pieces (212)
                  └── Piece Photos (508)
                      └── Image Files (160)
  └── Lots (50)
      └── Material Compositions
      └── Certifications
      └── Defect Rates
          └── Defect Types (18)
```

---

## 🔧 Technical Details

### Database Tables Populated
- `tenants`
- `clients`
- `factories`
- `lots`
- `defect_types`
- `users`
- `user_roles`
- `roles`
- `edge_devices`
- `inspection_sessions`
- `apparel_pieces`
- `piece_photos`

### Image Generation
- **Library:** Pillow (PIL)
- **Font:** DejaVu Sans
- **Format:** JPEG with 85% quality
- **Dimensions:** 800x1000px (4:5 ratio)
- **Color Space:** RGB

### Password Hashing
- **Algorithm:** bcrypt
- **Salt Rounds:** Auto-generated
- **Compatibility:** Matches NestJS backend

---

## 🎁 What You Can Test

✅ Multi-tenant isolation
✅ Role-based access control (6 different roles)
✅ Production lot management
✅ Quality inspection workflows
✅ Defect tracking & categorization
✅ Factory-client relationships
✅ Material composition & certifications
✅ Edge device integration
✅ Apparel piece inspection
✅ Photo management & storage
✅ User authentication & authorization
✅ Dashboard analytics with real data
✅ International factory network
✅ Fashion industry use cases

---

## 📝 Notes

- All data is realistic and follows fashion industry standards
- Style codes follow SS (Spring/Summer) and FW (Fall/Winter) conventions
- Factory locations represent actual global manufacturing hubs
- Client brands are real luxury and fashion companies
- Material compositions are industry-standard
- Certifications are authentic sustainability/quality standards
- Images include QA inspection markers for measurement validation
- Database relationships maintain referential integrity
- All timestamps are realistic (within last 6 months)

---

*Last updated: 2025-10-24*
*Total generation time: ~3 minutes*
*Scripts: Python 3.12 + PostgreSQL 15*
