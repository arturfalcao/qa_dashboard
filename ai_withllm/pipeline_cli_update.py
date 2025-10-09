# Add this to the main() function in pipeline.py

def main():
    """Command-line interface for the pipeline with ML model support."""
    import argparse

    parser = argparse.ArgumentParser(description='Garment Measurement Pipeline')

    # Existing arguments
    parser.add_argument('--calibrate', help='Calibration image with ArUco markers')
    parser.add_argument('--image', help='Garment image to process')
    parser.add_argument('--batch', help='Directory of images to process')
    parser.add_argument('--calibration', default='calibration.json',
                       help='Calibration config file')
    parser.add_argument('--type', help='Override garment type')
    parser.add_argument('--output', default='output', help='Output directory')
    parser.add_argument('--no-rectify', action='store_true', help='Skip rectification')

    # New ML model arguments
    parser.add_argument('--use_sam', action='store_true',
                       help='Enable SAM for segmentation refinement')
    parser.add_argument('--sam_checkpoint', help='Path to SAM model checkpoint')
    parser.add_argument('--use_clip', action='store_true',
                       help='Enable CLIP for zero-shot classification')
    parser.add_argument('--kp_model_path', help='Path to HRNet ONNX model for landmarks')
    parser.add_argument('--out', help='Output overlay image path')

    args = parser.parse_args()

    # Initialize pipeline with ML models
    pipeline = Pipeline(
        calibration_path=args.calibration,
        use_sam=args.use_sam,
        sam_checkpoint=args.sam_checkpoint,
        use_clip=args.use_clip,
        kp_model_path=args.kp_model_path,
        output_dir=args.output
    )

    # Rest of the function remains the same...
