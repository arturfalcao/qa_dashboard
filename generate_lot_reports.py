#!/usr/bin/env python3
"""
Generate PDF reports for Cordeiro Campos lot CC-SS25-T001
"""

import boto3
from botocore.client import Config
import psycopg2
from datetime import datetime, timedelta
import uuid
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# DigitalOcean Spaces Configuration
SPACES_REGION = 'lon1'
SPACES_ENDPOINT = f'https://{SPACES_REGION}.digitaloceanspaces.com'
SPACES_ACCESS_KEY = 'DO004MPHJC2PFZVQE23M'
SPACES_SECRET_KEY = 'WFoe83+YGGJkV/wQmtSJcxStddXp4pexdT7/0xXyvGQ'
SPACES_BUCKET = 'pp-reports'

# Database Configuration
DB_CONFIG = {
    'host': 'db-postgresql-lon1-48038-do-user-23540354-0.h.db.ondigitalocean.com',
    'port': 25060,
    'user': 'doadmin',
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': 'defaultdb',
    'sslmode': 'require'
}

LOT_ID = '0ac8675e-414c-42cb-afd4-8139dd229f40'
TENANT_ID = '254226e3-a316-413e-aa05-d0dd47c8f855'
USER_ID = 'e3e2c5fe-ac80-4522-8309-5fb6eb447cd0'

def get_s3_client():
    session = boto3.session.Session()
    return session.client('s3',
                         region_name=SPACES_REGION,
                         endpoint_url=SPACES_ENDPOINT,
                         aws_access_key_id=SPACES_ACCESS_KEY,
                         aws_secret_access_key=SPACES_SECRET_KEY,
                         config=Config(signature_version='s3v4'))

def upload_pdf_to_s3(pdf_buffer, filename):
    """Upload PDF to S3 and return the key"""
    client = get_s3_client()
    s3_key = f"reports/{TENANT_ID}/{filename}"

    client.put_object(
        Bucket=SPACES_BUCKET,
        Key=s3_key,
        Body=pdf_buffer.getvalue(),
        ContentType='application/pdf',
        ACL='private'
    )

    return s3_key

def create_styles():
    """Create custom styles for reports"""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a365d')
    ))

    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#2d3748')
    ))

    styles.add(ParagraphStyle(
        name='ReportBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    ))

    return styles

def generate_lot_inspection_report():
    """Generate Lot Inspection Report PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = create_styles()
    story = []

    # Title
    story.append(Paragraph("Lot Inspection Report", styles['ReportTitle']))
    story.append(Spacer(1, 20))

    # Lot Info
    story.append(Paragraph("Lot Information", styles['SectionTitle']))
    lot_data = [
        ['Style Reference:', 'CC-SS25-T001'],
        ['Garment Type:', 'T-Shirt'],
        ['Client:', 'Cordeiro Campos'],
        ['Status:', 'In Production'],
        ['Total Quantity:', '5,000 units'],
        ['Inspection Date:', datetime.now().strftime('%Y-%m-%d')],
    ]
    lot_table = Table(lot_data, colWidths=[5*cm, 10*cm])
    lot_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(lot_table)
    story.append(Spacer(1, 20))

    # Inspection Summary
    story.append(Paragraph("Inspection Summary", styles['SectionTitle']))
    summary_data = [
        ['Metric', 'Value', 'Status'],
        ['Pieces Inspected', '20', 'Complete'],
        ['Pieces OK', '18', '90%'],
        ['Pieces with Defects', '1', '5%'],
        ['Pieces Potential Defect', '1', '5%'],
        ['AQL Level', '2.5', 'PASS'],
        ['Overall Result', 'PASS', '✓'],
    ]
    summary_table = Table(summary_data, colWidths=[6*cm, 4*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # Defects Found
    story.append(Paragraph("Defects Found", styles['SectionTitle']))
    defects_data = [
        ['Piece Code', 'Defect Type', 'Description', 'Severity'],
        ['CC-T001-005', 'Stitching', 'Loose stitching on left sleeve', 'Minor'],
        ['CC-T001-012', 'Stain', 'Small oil stain near collar', 'Minor'],
    ]
    defects_table = Table(defects_data, colWidths=[3*cm, 3*cm, 6*cm, 2*cm])
    defects_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e53e3e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(defects_table)
    story.append(Spacer(1, 30))

    # Footer
    story.append(Paragraph(f"Generated by PackPolish QA Dashboard • {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Footer']))

    doc.build(story)
    return buffer

def generate_measurement_compliance_report():
    """Generate Measurement Compliance Sheet PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = create_styles()
    story = []

    story.append(Paragraph("Measurement Compliance Sheet", styles['ReportTitle']))
    story.append(Spacer(1, 20))

    # Lot Info
    story.append(Paragraph("Product Details", styles['SectionTitle']))
    story.append(Paragraph("Style: CC-SS25-T001 | Garment: T-Shirt | Material: 100% Cotton", styles['ReportBody']))
    story.append(Spacer(1, 15))

    # Measurement Table
    story.append(Paragraph("Size Measurements (cm)", styles['SectionTitle']))
    meas_data = [
        ['Size', 'Chest Width', 'Body Length', 'Tolerance', 'Status'],
        ['XS', '44', '65', '±2cm', '✓ Pass'],
        ['S', '47', '67', '±2cm', '✓ Pass'],
        ['M', '50', '69', '±2cm', '✓ Pass'],
        ['L', '53', '71', '±2cm', '✓ Pass'],
        ['XL', '56', '73', '±2cm', '✓ Pass'],
        ['XXL', '59', '75', '±2cm', '⚠ -1cm'],
    ]
    meas_table = Table(meas_data, colWidths=[2.5*cm, 3*cm, 3*cm, 3*cm, 3*cm])
    meas_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3182ce')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ebf8ff')]),
    ]))
    story.append(meas_table)
    story.append(Spacer(1, 20))

    # Compliance Summary
    story.append(Paragraph("Compliance Summary", styles['SectionTitle']))
    summary_data = [
        ['Total Samples:', '10'],
        ['Within Tolerance:', '9 (90%)'],
        ['Out of Tolerance:', '1 (10%)'],
        ['Compliance Rate:', '90%'],
        ['Overall Status:', 'ACCEPTABLE'],
    ]
    summary_table = Table(summary_data, colWidths=[5*cm, 8*cm])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 30))

    story.append(Paragraph(f"Generated by PackPolish QA Dashboard • {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Footer']))

    doc.build(story)
    return buffer

def generate_dpp_summary_report():
    """Generate DPP Summary Report PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = create_styles()
    story = []

    story.append(Paragraph("Digital Product Passport Summary", styles['ReportTitle']))
    story.append(Spacer(1, 20))

    # Product Info
    story.append(Paragraph("Product Information", styles['SectionTitle']))
    product_data = [
        ['Style Reference:', 'CC-SS25-T001'],
        ['Product Name:', 'Premium Cotton T-Shirt'],
        ['Garment Type:', 'T-Shirt'],
        ['Season:', 'Spring/Summer 2025'],
        ['Brand:', 'Cordeiro Campos'],
    ]
    product_table = Table(product_data, colWidths=[5*cm, 10*cm])
    product_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(product_table)
    story.append(Spacer(1, 15))

    # Material Composition
    story.append(Paragraph("Material Composition", styles['SectionTitle']))
    material_data = [
        ['Fiber', 'Percentage', 'Origin', 'Certification'],
        ['Cotton', '100%', 'Portugal', 'OEKO-TEX Standard 100'],
    ]
    material_table = Table(material_data, colWidths=[4*cm, 3*cm, 4*cm, 5*cm])
    material_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#38a169')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(material_table)
    story.append(Spacer(1, 15))

    # Supply Chain
    story.append(Paragraph("Supply Chain Traceability", styles['SectionTitle']))
    supply_data = [
        ['Step', 'Factory', 'Location', 'CO₂ (kg)'],
        ['1. Fiber Preparation', 'Malhas do Norte, Lda', 'Barcelos, PT', '2.50'],
        ['2. Cutting', 'Cortex - Corte Têxtil, SA', 'Guimarães, PT', '1.20'],
        ['3. Printing', 'Estamparia Moderna', 'Famalicão, PT', '3.30'],
        ['4. Sewing', 'Confeções Minho, Lda', 'Braga, PT', '2.80'],
        ['5. Packaging', 'PackStyle', 'Porto, PT', '0.90'],
        ['6. Quality Control', 'QualityCheck Portugal', 'Matosinhos, PT', '0.80'],
    ]
    supply_table = Table(supply_data, colWidths=[4*cm, 5*cm, 4*cm, 2.5*cm])
    supply_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#805ad5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#faf5ff')]),
    ]))
    story.append(supply_table)
    story.append(Spacer(1, 15))

    # Environmental Impact
    story.append(Paragraph("Environmental Impact", styles['SectionTitle']))
    env_data = [
        ['Total CO₂ Footprint:', '11.50 kg per unit'],
        ['Water Usage:', '2,700 liters per unit'],
        ['Recyclability:', '100% recyclable'],
        ['EU ESPR Compliant:', 'Yes'],
    ]
    env_table = Table(env_data, colWidths=[5*cm, 8*cm])
    env_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(env_table)
    story.append(Spacer(1, 30))

    story.append(Paragraph(f"Generated by PackPolish QA Dashboard • {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Footer']))

    doc.build(story)
    return buffer

def generate_supplier_performance_report():
    """Generate Supplier Performance Snapshot PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = create_styles()
    story = []

    story.append(Paragraph("Supplier Performance Snapshot", styles['ReportTitle']))
    story.append(Spacer(1, 20))

    story.append(Paragraph("Performance Overview", styles['SectionTitle']))
    perf_data = [
        ['Supplier', 'Quality Score', 'On-Time', 'Lead Time', 'Status'],
        ['Malhas do Norte', '96%', '100%', '2.5 days', '✓ Excellent'],
        ['Cortex Têxtil', '94%', '98%', '1.5 days', '✓ Good'],
        ['Estamparia Moderna', '92%', '100%', '2.0 days', '✓ Good'],
        ['Confeções Minho', '95%', '97%', '4.0 days', '✓ Good'],
        ['PackStyle', '98%', '100%', '1.0 day', '✓ Excellent'],
        ['QualityCheck PT', '99%', '100%', '0.5 days', '✓ Excellent'],
    ]
    perf_table = Table(perf_data, colWidths=[4*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dd6b20')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fffaf0')]),
    ]))
    story.append(perf_table)
    story.append(Spacer(1, 20))

    # Summary
    story.append(Paragraph("Summary Metrics", styles['SectionTitle']))
    summary_data = [
        ['Average Quality Score:', '95.7%'],
        ['Average On-Time Delivery:', '99.2%'],
        ['Average Lead Time:', '1.9 days'],
        ['Total Suppliers:', '6'],
        ['Rating:', 'A (Excellent)'],
    ]
    summary_table = Table(summary_data, colWidths=[5*cm, 8*cm])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 30))

    story.append(Paragraph(f"Generated by PackPolish QA Dashboard • {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Footer']))

    doc.build(story)
    return buffer

def main():
    print("=" * 60)
    print("📄 GENERATING PDF REPORTS FOR LOT CC-SS25-T001")
    print("=" * 60)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Delete existing reports for this lot
    cursor.execute("DELETE FROM reports WHERE lot_id = %s", (LOT_ID,))
    conn.commit()
    print(f"✓ Cleared existing reports")

    reports_to_generate = [
        ('LOT_INSPECTION_REPORT', generate_lot_inspection_report, 'CC-SS25-T001_Inspection_Report.pdf'),
        ('MEASUREMENT_COMPLIANCE_SHEET', generate_measurement_compliance_report, 'CC-SS25-T001_Measurement_Compliance.pdf'),
        ('DPP_SUMMARY', generate_dpp_summary_report, 'CC-SS25-T001_DPP_Summary.pdf'),
        ('SUPPLIER_PERFORMANCE_SNAPSHOT', generate_supplier_performance_report, 'CC-SS25-T001_Supplier_Performance.pdf'),
    ]

    for report_type, generator_func, filename in reports_to_generate:
        print(f"\n📝 Generating {report_type}...")

        # Generate PDF
        pdf_buffer = generator_func()
        pdf_size = len(pdf_buffer.getvalue())
        print(f"   PDF size: {pdf_size / 1024:.1f} KB")

        # Upload to S3
        s3_key = upload_pdf_to_s3(pdf_buffer, filename)
        print(f"   Uploaded to: {s3_key}")

        # Create report record
        report_id = str(uuid.uuid4())
        now = datetime.now()

        cursor.execute("""
            INSERT INTO reports (id, tenant_id, lot_id, user_id, type, status, language,
                                file_name, file_path, file_url, file_size,
                                generated_at, expires_at, generation_time_ms,
                                created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            report_id, TENANT_ID, LOT_ID, USER_ID, report_type, 'COMPLETED', 'EN',
            filename, s3_key, f'/api/reports/{report_id}/download', pdf_size,
            now, now + timedelta(days=30), 1500,
            now, now
        ))
        conn.commit()
        print(f"   ✓ Report saved: {report_id}")

    conn.close()

    print("\n" + "=" * 60)
    print("✅ ALL REPORTS GENERATED SUCCESSFULLY!")
    print("=" * 60)
    print(f"\nView at: https://app.packpolish.com/c/cordeiro-campos/lots/{LOT_ID}")

if __name__ == '__main__':
    main()
