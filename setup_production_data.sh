#!/bin/bash

# Production Data Setup Script
# Runs migrations and populates database with demo data
# Uploads images to S3/MinIO

set -e  # Exit on error

echo "=========================================="
echo "Production Data Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f "apps/api/.env" ]; then
    echo -e "${RED}✗ Error: apps/api/.env file not found${NC}"
    echo "Please create the .env file with database and MinIO credentials"
    exit 1
fi

echo -e "${GREEN}Step 1: Building API${NC}"
echo "--------------------------------------"
npm run build:api
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ API built successfully${NC}"
echo ""

echo -e "${GREEN}Step 2: Running Database Migrations${NC}"
echo "--------------------------------------"
cd apps/api
npm run migration:run
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Migrations failed${NC}"
    exit 1
fi
cd ../..
echo -e "${GREEN}✓ Migrations completed${NC}"
echo ""

echo -e "${GREEN}Step 3: Installing Python Dependencies${NC}"
echo "--------------------------------------"
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠ pip3 not found, skipping dependency installation${NC}"
else
    pip3 install psycopg2-binary Pillow minio --quiet
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
fi
echo ""

echo -e "${GREEN}Step 4: Generating Mock Data${NC}"
echo "--------------------------------------"
python3 generate_mock_data.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Mock data generation failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Mock data generated${NC}"
echo ""

echo -e "${GREEN}Step 5: Creating Test Users${NC}"
echo "--------------------------------------"
python3 create_test_users.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ User creation failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Test users created${NC}"
echo ""

echo -e "${GREEN}Step 6: Generating Lot Images${NC}"
echo "--------------------------------------"
python3 generate_lot_images.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Image generation failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Lot images generated${NC}"
echo ""

echo -e "${GREEN}Step 7: Uploading Images to S3/MinIO${NC}"
echo "--------------------------------------"
python3 upload_mock_images_to_s3.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ S3 upload failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Images uploaded to S3${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Start the API: npm run start:prod (in apps/api)"
echo "  2. Start the Web: npm run start (in apps/web)"
echo "  3. Login with test credentials from TEST_CREDENTIALS.md"
echo ""
echo "Default test user:"
echo "  Email: admin@luxe-atelier.com"
echo "  Password: password123"
echo ""
