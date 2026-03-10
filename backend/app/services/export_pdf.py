"""PDF export service using ReportLab."""

from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from app.models import CalculationRun, Project, NetworkVersion


def generate_calculation_report(
    run: CalculationRun,
    project: Project,
    version: NetworkVersion,
) -> BytesIO:
    """Generate PDF report for calculation results."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Title2',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.gray,
        alignment=TA_CENTER,
        spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name='RightAlign',
        parent=styles['Normal'],
        alignment=TA_RIGHT,
    ))

    elements = []

    # Title
    elements.append(Paragraph("Protokol o výpočte skratových pomerov", styles['Title2']))
    elements.append(Paragraph("podľa IEC 60909-0", styles['Subtitle']))

    # Project info
    elements.append(Paragraph("Informácie o projekte", styles['SectionHeader']))

    info_data = [
        ["Projekt:", project.name],
        ["Popis:", project.description or "-"],
        ["Verzia siete:", f"v{version.version_number}"],
        ["Režim výpočtu:", "Maximum (Ik max)" if run.calculation_mode.value == "MAX" else "Minimum (Ik min)"],
        ["Typy porúch:", ", ".join(run.fault_types)],
        ["Dátum výpočtu:", run.completed_at.strftime("%d.%m.%Y %H:%M") if run.completed_at else "-"],
        ["Engine verzia:", run.engine_version],
    ]

    info_table = Table(info_data, colWidths=[45 * mm, 120 * mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10 * mm))

    # Results summary
    elements.append(Paragraph("Výsledky výpočtu", styles['SectionHeader']))

    # Group results by bus
    results_by_bus = {}
    for result in run.results:
        if result.bus_id not in results_by_bus:
            results_by_bus[result.bus_id] = {}
        results_by_bus[result.bus_id][result.fault_type.value] = result

    # Summary table
    summary_header = ["Uzol", "Ik3 [kA]", "ip3 [kA]", "Ik2 [kA]", "Ik1 [kA]"]
    summary_data = [summary_header]

    for bus_id, faults in sorted(results_by_bus.items()):
        row = [
            bus_id,
            f"{faults.get('IK3').Ik:.3f}" if faults.get('IK3') else "-",
            f"{faults.get('IK3').ip:.3f}" if faults.get('IK3') else "-",
            f"{faults.get('IK2').Ik:.3f}" if faults.get('IK2') else "-",
            f"{faults.get('IK1').Ik:.3f}" if faults.get('IK1') else "-",
        ]
        summary_data.append(row)

    summary_table = Table(summary_data, colWidths=[40 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm])
    summary_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        # Body
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (1, 1), (-1, -1), 'Courier'),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        # Alternating rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
    ]))
    elements.append(summary_table)

    # Detailed results
    elements.append(PageBreak())
    elements.append(Paragraph("Detailné výsledky", styles['SectionHeader']))

    for bus_id, faults in sorted(results_by_bus.items()):
        elements.append(Paragraph(f"Uzol: {bus_id}", styles['Heading3']))

        detail_header = ["Parameter", "Ik3", "Ik2", "Ik1"]
        detail_data = [detail_header]

        # Get fault results
        ik3 = faults.get('IK3')
        ik2 = faults.get('IK2')
        ik1 = faults.get('IK1')

        detail_data.append([
            "Ik [kA]",
            f"{ik3.Ik:.4f}" if ik3 else "-",
            f"{ik2.Ik:.4f}" if ik2 else "-",
            f"{ik1.Ik:.4f}" if ik1 else "-",
        ])
        detail_data.append([
            "ip [kA]",
            f"{ik3.ip:.4f}" if ik3 else "-",
            f"{ik2.ip:.4f}" if ik2 else "-",
            f"{ik1.ip:.4f}" if ik1 else "-",
        ])
        detail_data.append([
            "R/X",
            f"{ik3.R_X_ratio:.4f}" if ik3 else "-",
            f"{ik2.R_X_ratio:.4f}" if ik2 else "-",
            f"{ik1.R_X_ratio:.4f}" if ik1 else "-",
        ])
        detail_data.append([
            "c faktor",
            f"{ik3.c_factor:.2f}" if ik3 else "-",
            f"{ik2.c_factor:.2f}" if ik2 else "-",
            f"{ik1.c_factor:.2f}" if ik1 else "-",
        ])
        detail_data.append([
            "Z1 [Ω]",
            f"{ik3.Z1['r']:.4f}+j{ik3.Z1['x']:.4f}" if ik3 else "-",
            f"{ik2.Z1['r']:.4f}+j{ik2.Z1['x']:.4f}" if ik2 else "-",
            f"{ik1.Z1['r']:.4f}+j{ik1.Z1['x']:.4f}" if ik1 else "-",
        ])
        if any(f and f.Z0 for f in [ik3, ik2, ik1]):
            detail_data.append([
                "Z0 [Ω]",
                f"{ik3.Z0['r']:.4f}+j{ik3.Z0['x']:.4f}" if ik3 and ik3.Z0 else "-",
                f"{ik2.Z0['r']:.4f}+j{ik2.Z0['x']:.4f}" if ik2 and ik2.Z0 else "-",
                f"{ik1.Z0['r']:.4f}+j{ik1.Z0['x']:.4f}" if ik1 and ik1.Z0 else "-",
            ])

        detail_table = Table(detail_data, colWidths=[35 * mm, 45 * mm, 45 * mm, 45 * mm])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (1, 1), (-1, -1), 'Courier'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(detail_table)
        elements.append(Spacer(1, 5 * mm))

    # Footer
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        f"Vygenerované: {datetime.now().strftime('%d.%m.%Y %H:%M')} | Short-Circuit Calculator v{run.engine_version}",
        styles['Subtitle']
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
