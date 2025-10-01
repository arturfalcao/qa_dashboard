#!/usr/bin/env python3
"""
QA Dashboard Integration for Automatic Garment Measurements
Integrates with the existing database to process piece photos
"""

import os
import json
import asyncio
import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import numpy as np
import cv2

# Import measurement system
from garment_measurement_intelligent import IntelligentGarmentMeasurement

class QADashboardMeasurementIntegration:
    """Integration with QA Dashboard for automatic measurements"""

    def __init__(self):
        """Initialize integration"""

        # Database connection
        self.db_config = {
            'host': 'localhost',
            'port': 5433,
            'database': 'qa_dashboard',
            'user': 'postgres',
            'password': 'postgres'
        }

        # Measurement system with correct scale for wooden ruler
        self.measurement_system = IntelligentGarmentMeasurement(
            ruler_length_cm=31.0,
            manual_scale=34.32,  # Correct scale for wooden ruler
            debug=False
        )

        # Track processed pieces
        self.processed_pieces = set()

        print(f"🤖 QA Dashboard Measurement Integration Started")
        print(f"   Database: {self.db_config['database']}")
        print(f"   Ruler scale: 34.32 pixels/cm")

    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def get_pending_pieces(self) -> List[Dict]:
        """Get pieces that need measurement (first photo only)"""

        query = """
            SELECT DISTINCT ON (ap.id)
                ap.id as piece_id,
                ap.piece_number,
                ap.inspection_session_id,
                pp.id as photo_id,
                pp.file_path,
                pp.s3_url,
                pp.captured_at,
                isp.lot_id,
                l.style_ref,
                l.client_id,
                c.name as client_name
            FROM apparel_pieces ap
            INNER JOIN piece_photos pp ON pp.piece_id = ap.id
            INNER JOIN inspection_sessions isp ON isp.id = ap.inspection_session_id
            INNER JOIN lots l ON l.id = isp.lot_id
            INNER JOIN clients c ON c.id = l.client_id
            WHERE NOT EXISTS (
                SELECT 1 FROM piece_measurements pm
                WHERE pm.piece_id = ap.id
            )
            AND pp.file_path IS NOT NULL
            ORDER BY ap.id, pp.captured_at ASC
            LIMIT 10;
        """

        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query)
                    pieces = cursor.fetchall()

                    print(f"📋 Found {len(pieces)} pieces pending measurement")
                    return pieces

        except Exception as e:
            print(f"❌ Database error: {e}")
            return []

    def save_measurements(self, piece_id: str, measurements: Dict) -> bool:
        """Save measurements to database"""

        # First, ensure the measurements table exists
        create_table_query = """
            CREATE TABLE IF NOT EXISTS piece_measurements (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                piece_id UUID NOT NULL REFERENCES apparel_pieces(id) ON DELETE CASCADE,
                garment_type VARCHAR(50),
                body_length_cm DECIMAL(6,2),
                chest_width_cm DECIMAL(6,2),
                chest_circumference_cm DECIMAL(6,2),
                waist_width_cm DECIMAL(6,2),
                hem_width_cm DECIMAL(6,2),
                shoulder_width_cm DECIMAL(6,2),
                hip_width_cm DECIMAL(6,2),
                inseam_cm DECIMAL(6,2),
                outseam_cm DECIMAL(6,2),
                rise_cm DECIMAL(6,2),
                thigh_width_cm DECIMAL(6,2),
                knee_width_cm DECIMAL(6,2),
                leg_opening_cm DECIMAL(6,2),
                size_estimate VARCHAR(20),
                confidence DECIMAL(3,2),
                scale_pixels_per_cm DECIMAL(6,2),
                measurement_data JSONB,
                annotated_image_path TEXT,
                measured_at TIMESTAMPTZ DEFAULT NOW(),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_piece_measurements_piece_id
            ON piece_measurements(piece_id);
        """

        insert_query = """
            INSERT INTO piece_measurements (
                piece_id, garment_type,
                body_length_cm, chest_width_cm, chest_circumference_cm,
                waist_width_cm, hem_width_cm, shoulder_width_cm,
                hip_width_cm, inseam_cm, outseam_cm, rise_cm,
                thigh_width_cm, knee_width_cm, leg_opening_cm,
                size_estimate, confidence, scale_pixels_per_cm,
                measurement_data, annotated_image_path
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (piece_id) DO NOTHING
            RETURNING id;
        """

        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Create table if not exists
                    cursor.execute(create_table_query)

                    # Extract measurements
                    m = measurements.get('measurements', {})

                    # Insert measurements
                    cursor.execute(insert_query, (
                        piece_id,
                        measurements.get('garment_type'),
                        m.get('body_length_cm'),
                        m.get('chest_width_cm'),
                        m.get('chest_circumference_cm'),
                        m.get('waist_width_cm'),
                        m.get('hem_width_cm'),
                        m.get('shoulder_width_cm'),
                        m.get('hip_width_cm'),
                        m.get('inseam_cm'),
                        m.get('outseam_cm'),
                        m.get('rise_cm'),
                        m.get('thigh_width_cm'),
                        m.get('knee_width_cm'),
                        m.get('leg_opening_cm'),
                        measurements.get('size_estimate'),
                        measurements.get('confidence'),
                        measurements.get('pixels_per_cm', 34.32),
                        json.dumps(measurements),
                        measurements.get('annotated_image_path')
                    ))

                    conn.commit()
                    result = cursor.fetchone()

                    if result:
                        print(f"✅ Measurements saved for piece {piece_id}")
                        return True

        except Exception as e:
            print(f"❌ Error saving measurements: {e}")

        return False

    async def process_piece(self, piece_data: Dict) -> Optional[Dict]:
        """Process a single piece for measurement"""

        piece_id = piece_data['piece_id']
        photo_path = piece_data['file_path']

        # Check if already processed
        if piece_id in self.processed_pieces:
            return None

        print(f"\n📸 Processing piece {piece_data['piece_number']} from lot {piece_data['style_ref']}")
        print(f"   Client: {piece_data['client_name']}")
        print(f"   Photo: {photo_path}")

        # Check if photo file exists
        if not Path(photo_path).exists():
            # Try to use S3 URL if available
            if piece_data.get('s3_url'):
                print(f"   Downloading from S3: {piece_data['s3_url']}")
                # Download image from S3
                photo_path = await self.download_s3_image(piece_data['s3_url'], piece_id)
                if not photo_path:
                    print(f"❌ Could not access photo")
                    return None
            else:
                print(f"❌ Photo file not found: {photo_path}")
                return None

        try:
            # Run measurement
            result = self.measurement_system.measure(photo_path)

            if result:
                # Add metadata
                result['piece_id'] = piece_id
                result['lot_id'] = piece_data['lot_id']
                result['style_ref'] = piece_data['style_ref']
                result['piece_number'] = piece_data['piece_number']

                # Save to database
                if self.save_measurements(piece_id, result):
                    self.processed_pieces.add(piece_id)

                    # Upload annotated image if exists
                    stem = Path(photo_path).stem
                    annotated_path = f"clean_annotated_{stem}.png"

                    if Path(annotated_path).exists():
                        await self.upload_annotated_image(piece_id, annotated_path)

                    return result

        except Exception as e:
            print(f"❌ Error processing piece {piece_id}: {e}")

        return None

    async def download_s3_image(self, s3_url: str, piece_id: str) -> Optional[str]:
        """Download image from S3"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(s3_url) as response:
                    if response.status == 200:
                        # Save to temp directory
                        temp_dir = Path("./temp_images")
                        temp_dir.mkdir(exist_ok=True)

                        temp_path = temp_dir / f"{piece_id}.jpg"
                        content = await response.read()

                        with open(temp_path, 'wb') as f:
                            f.write(content)

                        return str(temp_path)

        except Exception as e:
            print(f"Error downloading S3 image: {e}")

        return None

    async def upload_annotated_image(self, piece_id: str, image_path: str) -> bool:
        """Upload annotated image to storage"""

        try:
            # Update database with annotated image path
            update_query = """
                UPDATE piece_measurements
                SET annotated_image_path = %s
                WHERE piece_id = %s
            """

            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(update_query, (image_path, piece_id))
                    conn.commit()

            print(f"✅ Annotated image path saved for piece {piece_id}")
            return True

        except Exception as e:
            print(f"Error updating annotated image: {e}")

        return False

    async def process_all_pending(self):
        """Process all pending pieces"""

        pieces = self.get_pending_pieces()

        if not pieces:
            print("✅ No pending pieces")
            return

        # Process pieces concurrently
        tasks = []
        for piece in pieces:
            tasks.append(self.process_piece(piece))

        results = await asyncio.gather(*tasks)

        successful = [r for r in results if r is not None]
        print(f"\n📊 Processed {len(successful)}/{len(pieces)} pieces successfully")

    def get_measurement_statistics(self) -> Dict:
        """Get measurement statistics"""

        query = """
            SELECT
                COUNT(*) as total_measured,
                AVG(confidence) as avg_confidence,
                COUNT(DISTINCT garment_type) as garment_types,
                AVG(chest_width_cm) as avg_chest,
                AVG(waist_width_cm) as avg_waist,
                AVG(body_length_cm) as avg_length
            FROM piece_measurements
            WHERE measured_at > NOW() - INTERVAL '24 hours';
        """

        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query)
                    stats = cursor.fetchone()
                    return stats

        except Exception as e:
            print(f"Error getting statistics: {e}")

        return {}

async def run_continuous_processing():
    """Run continuous processing loop"""

    integration = QADashboardMeasurementIntegration()

    print("\n🔄 Starting continuous measurement processing")
    print("   Processing interval: 60 seconds")
    print("   Press Ctrl+C to stop\n")

    try:
        while True:
            # Process pending pieces
            await integration.process_all_pending()

            # Show statistics
            stats = integration.get_measurement_statistics()
            if stats:
                print(f"\n📈 Last 24h Statistics:")
                print(f"   Total measured: {stats.get('total_measured', 0)}")
                print(f"   Avg confidence: {stats.get('avg_confidence', 0):.1%}")

            # Wait before next cycle
            await asyncio.sleep(60)

    except KeyboardInterrupt:
        print("\n🛑 Processing stopped")


def main():
    """Main entry point"""

    import argparse

    parser = argparse.ArgumentParser(description='QA Dashboard Measurement Integration')
    parser.add_argument('--continuous', action='store_true',
                       help='Run in continuous mode')
    parser.add_argument('--process-once', action='store_true',
                       help='Process pending pieces once and exit')
    parser.add_argument('--piece-id', type=str,
                       help='Process specific piece by ID')

    args = parser.parse_args()

    if args.continuous:
        asyncio.run(run_continuous_processing())
    elif args.process_once:
        integration = QADashboardMeasurementIntegration()
        asyncio.run(integration.process_all_pending())
    elif args.piece_id:
        # Process specific piece
        integration = QADashboardMeasurementIntegration()
        # Fetch piece data and process
        print(f"Processing piece: {args.piece_id}")
    else:
        # Default: process once
        integration = QADashboardMeasurementIntegration()
        asyncio.run(integration.process_all_pending())


if __name__ == "__main__":
    main()