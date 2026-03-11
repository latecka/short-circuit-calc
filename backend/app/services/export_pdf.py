"""Professional PDF report generator using ReportLab."""

from io import BytesIO
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.models import CalculationRun, Project, NetworkVersion
from app.services.network_schema import generate_network_schema

# Register DejaVu fonts for Unicode/diacritics support
pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))


def generate_calculation_report(
    run: CalculationRun,
    project: Project,
    version: NetworkVersion,
) -> BytesIO:
    """Generate professional PDF report for calculation results."""

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=25*mm,
        bottomMargin=20*mm,
    )

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=6*mm,
        alignment=TA_CENTER,
        fontName='DejaVu-Bold',
    )

    heading1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=14,
        spaceBefore=8*mm,
        spaceAfter=4*mm,
        fontName='DejaVu-Bold',
    )

    heading2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=6*mm,
        spaceAfter=3*mm,
        fontName='DejaVu-Bold',
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=3*mm,
        alignment=TA_JUSTIFY,
        fontName='DejaVu',
    )

    center_style = ParagraphStyle(
        'Center',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        fontName='DejaVu',
    )

    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.gray,
        fontName='DejaVu',
    )

    # Table style
    header_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'DejaVu-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'DejaVu'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F4F6')]),
    ])

    elements_data = version.elements or {}
    story = []

    # ========== PAGE 1: TITLE PAGE ==========
    story.append(Spacer(1, 20*mm))

    # Contractor header
    if project.contractor_name:
        story.append(Paragraph(project.contractor_name, title_style))
        if project.contractor_address:
            story.append(Paragraph(project.contractor_address, center_style))
        story.append(Spacer(1, 15*mm))

    # Project title
    story.append(Paragraph("VÝPOČET SKRATOVÝCH POMEROV", title_style))
    story.append(Paragraph("podľa IEC 60909-0", center_style))
    story.append(Spacer(1, 10*mm))

    # Project name and location
    story.append(Paragraph(f"<b>{project.name}</b>", title_style))
    if project.project_location:
        story.append(Paragraph(project.project_location, center_style))

    story.append(Spacer(1, 20*mm))

    # Info table
    info_data = []
    if project.client_name:
        info_data.append(["Objednávateľ:", project.client_name])
        if project.client_address:
            info_data.append(["", project.client_address])

    if project.contractor_name:
        info_data.append(["Zhotoviteľ:", project.contractor_name])
        if project.contractor_address:
            info_data.append(["", project.contractor_address])

    if project.project_number:
        info_data.append(["Archívne číslo:", project.project_number])

    info_data.append(["Dátum výpočtu:", run.completed_at.strftime("%d.%m.%Y") if run.completed_at else "-"])

    if project.revision:
        info_data.append(["Revízia:", project.revision])

    if project.author:
        info_data.append(["Vypracoval:", project.author])

    if project.checker:
        info_data.append(["Skontroloval:", project.checker])

    if info_data:
        info_table = Table(info_data, colWidths=[45*mm, 100*mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'DejaVu-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'DejaVu'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(info_table)

    story.append(PageBreak())

    # ========== PAGE 2: TABLE OF CONTENTS ==========
    story.append(Paragraph("OBSAH", heading1_style))
    story.append(Spacer(1, 5*mm))

    toc_data = [
        ["1.", "Úvod", "3"],
        ["2.", "Jednopólová schéma", "4"],
        ["3.", "Výsledky výpočtov", "5"],
        ["4.", "Vstupné podklady", "6"],
        ["5.", "Záver", "7"],
    ]

    toc_table = Table(toc_data, colWidths=[10*mm, 120*mm, 20*mm])
    toc_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'DejaVu'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(toc_table)

    story.append(PageBreak())

    # ========== PAGE 3: INTRODUCTION ==========
    story.append(Paragraph("1. Úvod", heading1_style))

    intro_text = f"""
    Tento dokument obsahuje výpočet skratových pomerov pre elektrickú sieť
    <b>{project.name}</b>. Výpočet bol vykonaný v súlade s normou
    <b>IEC 60909-0</b> (Výpočet skratových prúdov v trojfázových striedavých sústavách).
    """
    story.append(Paragraph(intro_text, normal_style))

    story.append(Paragraph("1.1 Rozsah výpočtu", heading2_style))

    mode_text = "Maximum (Ik max)" if run.calculation_mode.value == "max" else "Minimum (Ik min)"
    fault_types_text = ", ".join(run.fault_types)

    scope_text = f"""
    <b>Režim výpočtu:</b> {mode_text}<br/>
    <b>Typy porúch:</b> {fault_types_text}<br/>
    <b>Počet uzlov:</b> {len(run.fault_buses)}<br/>
    <b>Engine verzia:</b> {run.engine_version}
    """
    story.append(Paragraph(scope_text, normal_style))

    story.append(Paragraph("1.2 Normatívny základ", heading2_style))
    norm_text = """
    Výpočet vychádza z normy IEC 60909-0:2016, ktorá definuje metódu
    ekvivalentného zdroja napätia pre výpočet počiatočného súmerného
    skratového prúdu Ik'', nárazového skratového prúdu ip, a ďalších
    charakteristických veličín.
    """
    story.append(Paragraph(norm_text, normal_style))

    story.append(PageBreak())

    # ========== PAGE 4: NETWORK SCHEMA ==========
    story.append(Paragraph("2. Jednopólová schéma", heading1_style))

    # Generate schema
    try:
        results_for_schema = []
        for r in run.results:
            results_for_schema.append({
                'bus_id': r.bus_id,
                'fault_type': r.fault_type.value,
                'Ik': r.Ik,
                'ip': r.ip,
            })

        schema_bytes = generate_network_schema(
            elements_data,
            results=results_for_schema,
            width=10,
            height=7,
            format='png'
        )

        schema_img = Image(BytesIO(schema_bytes), width=160*mm, height=112*mm)
        story.append(schema_img)
    except Exception as e:
        story.append(Paragraph(f"Schéma nebola vygenerovaná: {str(e)}", small_style))

    story.append(PageBreak())

    # ========== PAGE 5: RESULTS ==========
    story.append(Paragraph("3. Výsledky výpočtov", heading1_style))

    # Group results by bus
    results_by_bus = {}
    for result in run.results:
        if result.bus_id not in results_by_bus:
            results_by_bus[result.bus_id] = {}
        results_by_bus[result.bus_id][result.fault_type.value] = result

    # Summary table
    story.append(Paragraph("3.1 Prehľad výsledkov", heading2_style))

    header = ["Uzol", "Un [kV]", "Ik3 [kA]", "ip3 [kA]", "Ik2 [kA]", "Ik1 [kA]"]
    table_data = [header]

    busbars_dict = {b['id']: b for b in elements_data.get('busbars', [])}

    for bus_id in sorted(results_by_bus.keys()):
        faults = results_by_bus[bus_id]
        un = busbars_dict.get(bus_id, {}).get('Un', '-')

        ik3 = faults.get('Ik3')
        ik2 = faults.get('Ik2')
        ik1 = faults.get('Ik1')

        row = [
            bus_id,
            f"{un}",
            f"{ik3.Ik:.3f}" if ik3 else "-",
            f"{ik3.ip:.3f}" if ik3 else "-",
            f"{ik2.Ik:.3f}" if ik2 else "-",
            f"{ik1.Ik:.3f}" if ik1 else "-",
        ]
        table_data.append(row)

    results_table = Table(table_data, colWidths=[35*mm, 20*mm, 25*mm, 25*mm, 25*mm, 25*mm])
    results_table.setStyle(header_table_style)
    story.append(results_table)

    # Detailed results
    story.append(Paragraph("3.2 Detailné výsledky", heading2_style))

    for bus_id in sorted(results_by_bus.keys()):
        faults = results_by_bus[bus_id]

        story.append(Paragraph(f"<b>Uzol: {bus_id}</b>", normal_style))

        detail_header = ["Parameter", "Ik3", "Ik2", "Ik1"]
        detail_data = [detail_header]

        ik3 = faults.get('Ik3')
        ik2 = faults.get('Ik2')
        ik1 = faults.get('Ik1')

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
            "R1 [Ω]",
            f"{ik3.Z1['r']:.6f}" if ik3 else "-",
            f"{ik2.Z1['r']:.6f}" if ik2 else "-",
            f"{ik1.Z1['r']:.6f}" if ik1 else "-",
        ])
        detail_data.append([
            "X1 [Ω]",
            f"{ik3.Z1['x']:.6f}" if ik3 else "-",
            f"{ik2.Z1['x']:.6f}" if ik2 else "-",
            f"{ik1.Z1['x']:.6f}" if ik1 else "-",
        ])

        detail_table = Table(detail_data, colWidths=[30*mm, 40*mm, 40*mm, 40*mm])
        detail_table.setStyle(header_table_style)
        story.append(detail_table)
        story.append(Spacer(1, 5*mm))

    story.append(PageBreak())

    # ========== PAGE 6: INPUT DATA ==========
    story.append(Paragraph("4. Vstupné podklady", heading1_style))

    # Busbars
    story.append(Paragraph("4.1 Uzly (busbary)", heading2_style))
    if elements_data.get('busbars'):
        bus_header = ["ID", "Názov", "Un [kV]"]
        bus_data = [bus_header]
        for bus in elements_data['busbars']:
            bus_data.append([bus['id'], bus.get('name', '-'), f"{bus['Un']}"])

        bus_table = Table(bus_data, colWidths=[50*mm, 60*mm, 40*mm])
        bus_table.setStyle(header_table_style)
        story.append(bus_table)

    # External grids
    story.append(Paragraph("4.2 Externé sústavy", heading2_style))
    if elements_data.get('external_grids'):
        grid_header = ["ID", "Uzol", "Sk_max [MVA]", "R/X"]
        grid_data = [grid_header]
        for grid in elements_data['external_grids']:
            grid_data.append([
                grid['id'],
                grid['bus_id'],
                f"{grid['Sk_max']}",
                f"{grid.get('rx_ratio', 0.1)}"
            ])

        grid_table = Table(grid_data, colWidths=[40*mm, 40*mm, 40*mm, 30*mm])
        grid_table.setStyle(header_table_style)
        story.append(grid_table)

    # Transformers
    story.append(Paragraph("4.3 Transformátory", heading2_style))
    if elements_data.get('transformers_2w'):
        tr_header = ["ID", "HV", "LV", "Sn [MVA]", "uk [%]"]
        tr_data = [tr_header]
        for tr in elements_data['transformers_2w']:
            tr_data.append([
                tr['id'],
                tr['bus_hv'],
                tr['bus_lv'],
                f"{tr['Sn']}",
                f"{tr['uk_percent']}"
            ])

        tr_table = Table(tr_data, colWidths=[35*mm, 35*mm, 35*mm, 25*mm, 25*mm])
        tr_table.setStyle(header_table_style)
        story.append(tr_table)

    # Generators
    if elements_data.get('generators'):
        story.append(Paragraph("4.4 Generátory", heading2_style))
        gen_header = ["ID", "Uzol", "Sn [MVA]", "Un [kV]", "Xd'' [%]"]
        gen_data = [gen_header]
        for gen in elements_data['generators']:
            gen_data.append([
                gen['id'],
                gen['bus_id'],
                f"{gen['Sn']}",
                f"{gen['Un']}",
                f"{gen['Xd_pp']}"
            ])

        gen_table = Table(gen_data, colWidths=[35*mm, 35*mm, 30*mm, 25*mm, 30*mm])
        gen_table.setStyle(header_table_style)
        story.append(gen_table)

    story.append(PageBreak())

    # ========== PAGE 7: CONCLUSION ==========
    story.append(Paragraph("5. Záver", heading1_style))

    # Find max values
    max_ik3 = max((r.Ik for r in run.results if r.fault_type.value == 'Ik3'), default=0)
    max_ip = max((r.ip for r in run.results if r.fault_type.value == 'Ik3'), default=0)

    max_ik3_bus = next((r.bus_id for r in run.results if r.fault_type.value == 'Ik3' and r.Ik == max_ik3), '-')
    max_ip_bus = next((r.bus_id for r in run.results if r.fault_type.value == 'Ik3' and r.ip == max_ip), '-')

    conclusion_text = f"""
    Výpočet skratových pomerov bol úspešne dokončený pre {len(results_by_bus)} uzlov siete.
    <br/><br/>
    <b>Maximálne hodnoty:</b><br/>
    • Najvyšší počiatočný skratový prúd Ik3'' = <b>{max_ik3:.3f} kA</b> (uzol: {max_ik3_bus})<br/>
    • Najvyšší nárazový skratový prúd ip = <b>{max_ip:.3f} kA</b> (uzol: {max_ip_bus})
    <br/><br/>
    Tieto hodnoty je potrebné porovnať so skratovou odolnosťou inštalovaných zariadení.
    """
    story.append(Paragraph(conclusion_text, normal_style))

    # Notes
    if project.notes:
        story.append(Spacer(1, 10*mm))
        story.append(Paragraph("<b>Poznámky:</b>", normal_style))
        story.append(Paragraph(project.notes, normal_style))

    # Footer info
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph(
        f"Vygenerované: {datetime.now().strftime('%d.%m.%Y %H:%M')} | Short-Circuit Calculator v{run.engine_version}",
        small_style
    ))

    # Build PDF with page numbers
    def add_page_info(canvas, doc):
        canvas.saveState()
        width, height = A4

        # Header line
        canvas.setStrokeColor(colors.lightgrey)
        canvas.line(20*mm, height - 20*mm, width - 20*mm, height - 20*mm)

        # Header text
        canvas.setFont('DejaVu', 8)
        canvas.setFillColor(colors.gray)

        if project.project_number:
            canvas.drawString(20*mm, height - 18*mm, project.project_number)

        canvas.drawRightString(width - 20*mm, height - 18*mm, project.name[:40])

        # Footer
        canvas.line(20*mm, 15*mm, width - 20*mm, 15*mm)
        canvas.drawCentredString(width / 2, 10*mm, f"Strana {doc.page}")

        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_info, onLaterPages=add_page_info)

    buffer.seek(0)
    return buffer
