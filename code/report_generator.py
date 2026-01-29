from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import json
import re
from datetime import datetime
from collections import Counter

styles = {
    'Title': ParagraphStyle('Title', fontSize=36, leading=42, alignment=TA_CENTER, spaceAfter=30, textColor=colors.HexColor("#1D4ED8"), fontName='Helvetica-Bold'),
    'Subtitle': ParagraphStyle('Subtitle', fontSize=20, leading=24, alignment=TA_CENTER, spaceAfter=60, textColor=colors.HexColor("#2563EB")),
    'H1': ParagraphStyle('H1', fontSize=18, leading=22, spaceBefore=20, spaceAfter=15, textColor=colors.HexColor("#1D4ED8"), fontName='Helvetica-Bold'),
    'H2': ParagraphStyle('H2', fontSize=14, leading=18, spaceBefore=12, spaceAfter=8, fontName='Helvetica-Bold'),
    'Body': ParagraphStyle('Body', fontSize=10, leading=14, spaceAfter=10, alignment=TA_LEFT),
    'Small': ParagraphStyle('Small', fontSize=9, alignment=TA_CENTER, textColor=colors.grey),
}

def generate_coverity_style_pdf(report_data: dict, filename: str, source_file: str):
    doc = SimpleDocTemplate(filename, pagesize=LETTER, topMargin=0.8*inch, bottomMargin=0.8*inch, leftMargin=0.8*inch, rightMargin=0.8*inch)
    story = []

    # Cover Page
    story.append(Spacer(1, 2.5*inch))
    story.append(Paragraph("AudiTrailGPT", styles['Title']))
    story.append(Paragraph("Forensic Intelligence Report", styles['Subtitle']))
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph(f"Report Date: {datetime.now().strftime('%B %d, %Y')}", styles['Body']))
    story.append(Paragraph(f"Source File: {source_file}", styles['Body']))
    story.append(PageBreak())

    # Parse causal chain data
    try:
        chain_data = json.loads(report_data['causal_chain'])
        events = chain_data.get('causal_chain', [])
        summary = chain_data.get('summary', {})
    except:
        events = []
        summary = {"total_alerts": 0, "total_amount_at_risk": 0, "total_lines": 0, "unmatched_lines": 0}

    valid_events = [e for e in events if e.get('event_type') == "FINANCIAL_CRIME_ALERT"]
    total_alerts = summary.get('total_alerts', len(valid_events))
    total_amount = summary.get('total_amount_at_risk', 0)
    total_lines = summary.get('total_lines', len(events))
    unmatched = summary.get('unmatched_lines', total_lines - total_alerts)

    # Executive Summary
    story.append(Paragraph("Executive Summary", styles['H1']))
    story.append(Paragraph(f"Total log lines processed: {total_lines}", styles['Body']))
    story.append(Paragraph(f"Successfully parsed alerts: <b>{total_alerts}</b>", styles['Body']))
    story.append(Paragraph(f"Unmatched lines: {unmatched}", styles['Body']))
    story.append(Paragraph(f"Total amount at risk: <b>${total_amount:,}</b>", styles['Body']))
    story.append(Paragraph("Analysis Engine: Llama-3.3-70B + Deterministic Symbolic Parser", styles['Body']))
    if total_alerts == 0:
        story.append(Paragraph("WARNING: No alerts parsed — likely due to log format mismatch. Manual review recommended.", styles['Body']))
    story.append(PageBreak())

    # Risk Indicators Table
    if total_alerts > 0:
        story.append(Paragraph("Risk Indicators & Alert Distribution", styles['H1']))
        alert_types = [e['details']['alert_type'] for e in valid_events]
        type_count = Counter(alert_types)
        table_data = [["Alert Type", "Count", "%", "Amount per Alert", "Total Amount"]]
        for atype, count in type_count.most_common():
            sample_event = next(e for e in valid_events if e['details']['alert_type'] == atype)
            amt = sample_event['details']['amount']
            pct = f"{(count / total_alerts) * 100:.1f}%"
            table_data.append([atype, count, pct, f"${amt:,}", f"${amt * count:,}"])
        table_data.append(["TOTAL", total_alerts, "100%", "", f"${total_amount:,}"])

        table = Table(table_data, colWidths=[210, 60, 60, 100, 110])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1D4ED8")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ]))
        story.append(table)
        story.append(PageBreak())

    # Event Timeline Table
    story.append(Paragraph("Complete Event Timeline", styles['H1']))
    timeline_data = [["Date", "Case ID", "Alert Type", "Amount"]]
    for e in valid_events:
        d = e['details']
        timeline_data.append([
            e['timestamp'][:10],
            d.get('case_id', 'N/A'),
            d.get('alert_type', 'N/A'),
            f"${d.get('amount', 0):,}"
        ])

    timeline_table = Table(timeline_data, colWidths=[90, 110, 220, 100])
    timeline_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1D4ED8")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    story.append(timeline_table)
    story.append(PageBreak())

    # Detailed Forensic Narrative (Clean, Bold Rendered Properly)
    story.append(Paragraph("Detailed Forensic Analysis (Llama-3.3 Generated)", styles['H1']))
    narrative = report_data.get('narrative', 'No narrative generated.')

    # Convert **bold** to <b> tags for proper rendering
    cleaned_narrative = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', narrative)

    lines = [line.strip() for line in cleaned_narrative.split('\n') if line.strip()]
    current_para = ""

    for line in lines:
        if line.startswith('# '):
            if current_para:
                story.append(Paragraph(current_para.strip(), styles['Body']))
                current_para = ""
            story.append(Paragraph(line[2:].strip(), styles['H1']))
        elif line.startswith('## '):
            if current_para:
                story.append(Paragraph(current_para.strip(), styles['Body']))
                current_para = ""
            story.append(Paragraph(line[3:].strip(), styles['H2']))
        elif line.startswith(('- ', '* ', '• ', '1. ', '2. ', '3. ', '4. ', '5. ')):
            # Handle bullets and numbered lists
            bullet_text = line[line.find(' ')+1:].strip()
            story.append(Paragraph("• " + bullet_text, styles['Body']))
        elif line.startswith('|'):
            continue  # Skip markdown tables
        else:
            current_para += line + " "
            # Flush paragraph at sentence end or reasonable length
            if len(current_para) > 600 or (line.endswith(('.', '!', '?'))):
                story.append(Paragraph(current_para.strip(), styles['Body']))
                current_para = ""

    if current_para:
        story.append(Paragraph(current_para.strip(), styles['Body']))

    # Footer Page
    story.append(PageBreak())
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("AudiTrailGPT • Neuro-Symbolic AML Intelligence • © 2025 Group 2", styles['Small']))

    doc.build(story)
