#!/usr/bin/env python3
"""
Edge Service Measurement Integration
Automatically measures garments when photos are taken
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
import cv2
import numpy as np
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import hashlib
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

# Import measurement system
from garment_measurement_intelligent import IntelligentGarmentMeasurement
from garment_measurement_proper import ProperGarmentMeasurer

class EdgeMeasurementService:
    """Service to automatically measure garments from edge service photos"""

    def __init__(self, config_path: str = "edge_config.json"):
        """Initialize the edge measurement service"""

        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize measurement system with correct scale
        self.measurement_system = IntelligentGarmentMeasurement(
            ruler_length_cm=self.config.get('ruler_length_cm', 31.0),
            manual_scale=self.config.get('manual_scale', 34.32),  # Use correct scale
            debug=False
        )

        # Track processed pieces
        self.processed_pieces = set()
        self.processing = set()

        # Upload endpoint
        self.upload_url = self.config.get('upload_url', 'http://localhost:3000/api/measurements')
        self.api_key = self.config.get('api_key', '')

        print(f"🤖 Edge Measurement Service Started")
        print(f"   Ruler: {self.config.get('ruler_length_cm', 31.0)}cm")
        print(f"   Scale: {self.config.get('manual_scale', 34.32)} pixels/cm")
        print(f"   Upload URL: {self.upload_url}")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file"""
        if Path(config_path).exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            # Default configuration
            return {
                'ruler_length_cm': 31.0,
                'manual_scale': 34.32,
                'watch_directory': '../test_images_mesurements',
                'output_directory': './measurement_results',
                'upload_url': 'http://localhost:3000/api/measurements',
                'api_key': '',
                'process_interval': 5
            }

    async def process_new_photo(self, photo_path: str, piece_id: str, lot_id: str = None):
        """Process a new photo for measurement"""

        # Check if this piece has been processed
        if piece_id in self.processed_pieces or piece_id in self.processing:
            print(f"⏭️ Piece {piece_id} already processed/processing")
            return None

        self.processing.add(piece_id)

        try:
            print(f"\n📸 Processing first photo for piece: {piece_id}")
            print(f"   Photo: {photo_path}")

            # Run measurement
            result = self.measurement_system.measure(photo_path)

            if result:
                # Add metadata
                result['piece_id'] = piece_id
                result['lot_id'] = lot_id
                result['photo_path'] = photo_path
                result['processed_at'] = datetime.now().isoformat()

                # Save results locally
                output_dir = Path(self.config.get('output_directory', './measurement_results'))
                output_dir.mkdir(parents=True, exist_ok=True)

                # Save measurement JSON
                result_file = output_dir / f"measurement_{piece_id}.json"
                with open(result_file, 'w') as f:
                    json.dump(result, f, indent=2)

                print(f"✅ Measurements saved: {result_file}")

                # Upload results
                await self._upload_results(result, photo_path)

                # Mark as processed
                self.processed_pieces.add(piece_id)

                return result

        except Exception as e:
            print(f"❌ Error processing piece {piece_id}: {e}")

        finally:
            self.processing.discard(piece_id)

        return None

    async def _upload_results(self, measurements: Dict, photo_path: str):
        """Upload measurement results and annotated image"""

        try:
            print(f"📤 Uploading results...")

            # Prepare upload data
            upload_data = {
                'piece_id': measurements.get('piece_id'),
                'lot_id': measurements.get('lot_id'),
                'garment_type': measurements.get('garment_type'),
                'measurements': measurements.get('measurements', {}),
                'confidence': measurements.get('confidence', 0),
                'size_estimate': measurements.get('size_estimate', 'unknown'),
                'timestamp': measurements.get('processed_at')
            }

            # Check for annotated image
            stem = Path(photo_path).stem
            annotated_path = f"clean_annotated_{stem}.png"

            if Path(annotated_path).exists():
                # Upload with image
                async with aiohttp.ClientSession() as session:
                    with open(annotated_path, 'rb') as f:
                        files = {
                            'data': json.dumps(upload_data),
                            'image': f
                        }

                        headers = {}
                        if self.api_key:
                            headers['Authorization'] = f"Bearer {self.api_key}"

                        async with session.post(
                            self.upload_url,
                            data=files,
                            headers=headers
                        ) as response:
                            if response.status == 200:
                                print(f"✅ Results uploaded successfully")
                            else:
                                print(f"⚠️ Upload failed: {response.status}")
            else:
                # Upload without image
                async with aiohttp.ClientSession() as session:
                    headers = {'Content-Type': 'application/json'}
                    if self.api_key:
                        headers['Authorization'] = f"Bearer {self.api_key}"

                    async with session.post(
                        self.upload_url,
                        json=upload_data,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            print(f"✅ Results uploaded successfully")
                        else:
                            print(f"⚠️ Upload failed: {response.status}")

        except Exception as e:
            print(f"❌ Upload error: {e}")

    def extract_piece_id(self, filename: str) -> Optional[str]:
        """Extract piece ID from filename"""

        # Expected format: lot_id_piece_id_photo_number.jpg
        # Or: piece_id_timestamp.jpg
        # Or just use the filename as piece_id if no pattern matches

        stem = Path(filename).stem

        # Try different patterns
        parts = stem.split('_')

        if len(parts) >= 3:
            # Assume format: lot_piece_photo
            return f"{parts[0]}_{parts[1]}"
        elif len(parts) >= 2:
            # Assume format: piece_timestamp
            return parts[0]
        else:
            # Use whole stem as piece_id
            return stem


class PhotoWatcher(FileSystemEventHandler):
    """Watch for new photos from edge service"""

    def __init__(self, measurement_service: EdgeMeasurementService):
        self.service = measurement_service
        self.loop = asyncio.new_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=2)

    def on_created(self, event):
        """Handle new photo file"""
        if not event.is_directory:
            file_path = event.src_path

            # Check if it's an image
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                print(f"\n🆕 New photo detected: {file_path}")

                # Extract piece ID
                piece_id = self.service.extract_piece_id(Path(file_path).name)

                # Process asynchronously
                asyncio.run_coroutine_threadsafe(
                    self.service.process_new_photo(file_path, piece_id),
                    self.loop
                )


class EdgeServiceAPI:
    """API integration for edge service"""

    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.session = requests.Session()

    def get_pending_pieces(self) -> list:
        """Get list of pieces pending measurement"""
        try:
            response = self.session.get(f"{self.base_url}/api/pieces/pending-measurement")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error fetching pending pieces: {e}")
        return []

    def mark_piece_measured(self, piece_id: str, measurements: Dict):
        """Mark piece as measured"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/pieces/{piece_id}/measurements",
                json=measurements
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error marking piece as measured: {e}")
            return False


def run_service():
    """Main service runner"""

    # Initialize service
    service = EdgeMeasurementService()

    # Set up file watcher
    watch_dir = service.config.get('watch_directory', '../test_images_mesurements')

    if not Path(watch_dir).exists():
        Path(watch_dir).mkdir(parents=True, exist_ok=True)

    print(f"👀 Watching directory: {watch_dir}")

    event_handler = PhotoWatcher(service)
    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=True)
    observer.start()

    # Also check for existing photos periodically
    api = EdgeServiceAPI(service.config.get('api_base_url', 'http://localhost:3000'))

    try:
        print("✅ Service running. Press Ctrl+C to stop.")

        while True:
            # Check for pending pieces every minute
            time.sleep(60)

            pending = api.get_pending_pieces()
            if pending:
                print(f"📋 Found {len(pending)} pending pieces")

                for piece in pending:
                    piece_id = piece.get('id')
                    photo_path = piece.get('photo_path')

                    if photo_path and Path(photo_path).exists():
                        asyncio.run(service.process_new_photo(
                            photo_path,
                            piece_id,
                            piece.get('lot_id')
                        ))

    except KeyboardInterrupt:
        observer.stop()
        print("\n🛑 Service stopped")

    observer.join()


if __name__ == "__main__":
    # Create default config if not exists
    config_path = "edge_config.json"
    if not Path(config_path).exists():
        default_config = {
            "ruler_length_cm": 31.0,
            "manual_scale": 34.32,
            "watch_directory": "../test_images_mesurements",
            "output_directory": "./measurement_results",
            "upload_url": "http://localhost:3000/api/measurements",
            "api_base_url": "http://localhost:3000",
            "api_key": "",
            "process_interval": 5
        }

        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)

        print(f"📝 Created default config: {config_path}")
        print("   Please update with your settings")

    run_service()