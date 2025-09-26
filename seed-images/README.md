# Seed Images

This directory contains the curated garment renders that power the demo seed data and the live mock generator.

## Included Images

### Normal Garment Images
- `garment-1.png` – Studio render of a pastel technical tee
- `garment-2.png` – Heather grey performance hoodie
- `garment-3.png` – Indigo denim trousers with contrast stitching
- `garment-4.png` – Camel polo with placket detailing
- `garment-5.png` – Midnight field jacket with metal trims
- `garment-6.png` – Garnet ribbed knitwear
- `garment-7.png` – Olive raglan crewneck
- `garment-8.png` – Heritage trench silhouette

### Defect Reference Images
- `defect-stain.png` – Visible stain across front torso
- `defect-stitching.png` – Irregular seam tension and broken thread
- `defect-misprint.png` – Offset screen print on chest graphic
- `defect-measurement.png` – Measurement tape showing variance
- `defect-other.png` – Fabric tear along seam intersection

All files are lossless PNG renders sized 512×512px so the detail cards can zoom without artifacts. They were generated locally with the helper script in `scripts/generate_seed_images.py`:

```bash
pnpm ts-node --skip-project scripts/generate_seed_images.py  # or python scripts/generate_seed_images.py
```

## How the Mock Services Use These Assets

1. The database seed populates MinIO with these renders and links them to inspection photos, annotations, and approvals.
2. The live inspection generator reuses the same catalog so every randomly created inspection has a realistic visual.
3. If the files are missing the services fall back to a simple placeholder buffer, but the real demo experience relies on the images above.