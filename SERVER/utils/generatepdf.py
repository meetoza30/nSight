from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm

# nCircle brand color
NCIRCLE_BLUE = colors.HexColor("#0B6FA4")

# --- Styles ---
title_style = ParagraphStyle(
    'title',
    fontSize=16,
    textColor=NCIRCLE_BLUE,
    fontName='Helvetica-Bold',
    spaceAfter=8,
    spaceBefore=12
)

label_value_style = ParagraphStyle(
    'label_value',
    fontSize=10,
    textColor=colors.black,
    leading=14,
    spaceAfter=2
)

section_header_style = ParagraphStyle(
    'section_header',
    fontSize=12,
    textColor=NCIRCLE_BLUE,
    fontName='Helvetica-Bold',
    spaceAfter=6,
    spaceBefore=12
)

body_style = ParagraphStyle(
    'body',
    fontSize=10,
    textColor=colors.black,
    leading=13,
    spaceAfter=4
)

bullet_style = ParagraphStyle(
    'bullet',
    fontSize=10,
    textColor=colors.black,
    leading=13,
    leftIndent=10,
    spaceAfter=2
)

# Style for experience header labels (Company, Designation, Duration) - BIGGER font
experience_label_style = ParagraphStyle(
    'experience_label',
    fontSize=11,
    textColor=colors.black,
    leading=15,
    spaceAfter=2
)


def first_page_header(canvas, doc):
    """Draw the header with logo - ONLY on first page"""
    canvas.saveState()
    width, height = A4
    
    try:
        # Logo at top left - positioned to stay within page bounds
        # height - 20*mm positions the TOP of the logo 20mm from top of page
        logo_height = 20 * mm
        canvas.drawImage(
            "./ncircle_tech_logo.jpg", 
            20 * mm,                    # x position: 20mm from left
            height - 20 * mm,           # y position: 20mm from top (logo bottom)
            width=45*mm,                # logo width
            height=logo_height,         # logo height
            preserveAspectRatio=True,
            mask='auto'
        )
    except Exception as e:
        print(f"Logo not found: {e}")
    
    # Blue line under header
    canvas.setStrokeColor(NCIRCLE_BLUE)
    canvas.setLineWidth(1.5)
    canvas.line(20*mm, height - 25*mm, 190*mm, height - 25*mm)
    
    # Page number at bottom
    canvas.setFillColor(colors.gray)
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(195*mm, 10*mm, f"Page {doc.page}")
    
    canvas.restoreState()


def later_pages_header(canvas, doc):
    """Draw header WITHOUT logo - for pages 2 onwards"""
    canvas.saveState()
    width, height = A4
    
    # Blue line at top (no logo)
    canvas.setStrokeColor(NCIRCLE_BLUE)
    canvas.setLineWidth(1.5)
    canvas.line(20*mm, height - 15*mm, 190*mm, height - 15*mm)
    
    # Page number at bottom
    canvas.setFillColor(colors.gray)
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(195*mm, 10*mm, f"Page {doc.page}")
    
    canvas.restoreState()


def labeled_line(label, value):
    """Create a line with label in blue and value in black"""
    text = f'<font color="#0B6FA4"><b>{label}</b></font> {value}'
    return Paragraph(text, label_value_style)


def project_block(project):
    """Generate project details block"""
    elements = []
    
    # Client
    if project.get("client"):
        elements.append(labeled_line("Client:", project["client"]))
    
    # Project Name
    if project.get("project_name"):
        elements.append(labeled_line("Project:", project["project_name"]))
    
    # Project Span
    if project.get("project_span"):
        elements.append(labeled_line("Project Span:", project["project_span"]))
    
    # Technologies
    tech = project.get("technologies", [])
    if tech:
        tech_str = ",".join(tech) if isinstance(tech, list) else tech
        elements.append(labeled_line("Technologies:", tech_str))
    
    # Description
    desc = project.get("description")
    if desc:
        elements.append(labeled_line("Description:", ""))
        if isinstance(desc, list):
            for point in desc:
                elements.append(Paragraph(f'<bullet>&bull;</bullet> {point}', bullet_style))
        else:
            elements.append(Paragraph(str(desc), body_style))
    
    # Role/Responsibility
    if project.get("role_responsibility"):
        elements.append(labeled_line("Role/Responsibility:", project["role_responsibility"]))
    
    elements.append(Spacer(1, 8))
    return elements


def skills_section(skills):
    """Generate skills section"""
    elements = []
    elements.append(Paragraph("Skills:", section_header_style))
    
    for category, skill_list in skills.items():
        if skill_list:  # Only show categories that have skills
            skill_str = ",".join(skill_list) if isinstance(skill_list, list) else skill_list
            text = f'<bullet>&bull;</bullet> <b>{category}:</b> {skill_str}'
            elements.append(Paragraph(text, bullet_style))
    
    elements.append(Spacer(1, 8))
    return elements


def achievements_section(achievements):
    """Generate achievements section"""
    elements = []
    elements.append(Paragraph("Achievements:", section_header_style))
    
    for achievement in achievements:
        # Use circular bullet (•) instead of star (*)
        text = f'• {achievement}'
        elements.append(Paragraph(text, bullet_style))
    
    elements.append(Spacer(1, 8))
    return elements


def education_section(education_list):
    """Generate education section"""
    elements = []
    elements.append(Paragraph("Education:", section_header_style))
    
    for edu in education_list:
        degree = edu.get('degree', '')
        college = edu.get('college', '')
        year = edu.get('graduation_year', '')
        cgpa = edu.get('cgpa', '')
        
        # Format with College: and Degree: labels
        if college:
            text = f'<font color="#0B6FA4"><b>College:</b></font> {college}'
            elements.append(Paragraph(text, body_style))
        if degree:
            text = f'<font color="#0B6FA4"><b>Degree:</b></font> {degree}'
            elements.append(Paragraph(text, body_style))
        if year:
            text = f'<font color="#0B6FA4"><b>Graduation Year:</b></font> {year}'
            elements.append(Paragraph(text, body_style))
        if cgpa:
            text = f'<font color="#0B6FA4"><b>CGPA:</b></font> {cgpa}'
            elements.append(Paragraph(text, body_style))
        
        elements.append(Spacer(1, 6))
    
    return elements


def generate_resume_pdf(data, output_file):
    """Generate the resume PDF in nCircle format"""
    
    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=35*mm,
        bottomMargin=15*mm
    )
    
    story = []
    
    # --- Title: Name of Resource ---
    candidate_name = data.get('Name', 'Name Of Resource')
    story.append(Paragraph(candidate_name, title_style))
    story.append(Spacer(1, 4))
    
    # --- Total Experience ---
    total_exp = data.get('Experience', {}).get('total_experience_years', 0)
    story.append(labeled_line("Total Experience:", f"{total_exp} Years"))
    story.append(Spacer(1, 8))
    
    # --- Experience Blocks ---
    experiences = data.get('Experience', {}).get('experiences', [])
    
    for exp in experiences:
        # Company info - use BIGGER font for experience header labels
        text = f'<font color="#0B6FA4"><b>Company:</b></font> {exp.get("company", "")}'
        story.append(Paragraph(text, experience_label_style))
        text = f'<font color="#0B6FA4"><b>Designation:</b></font> {exp.get("designation", "")}'
        story.append(Paragraph(text, experience_label_style))
        text = f'<font color="#0B6FA4"><b>Duration:</b></font> {exp.get("duration", "")}'
        story.append(Paragraph(text, experience_label_style))
        story.append(Spacer(1, 6))
        
        # Projects under this company
        for proj in exp.get("projects", []):
            story.extend(project_block(proj))
    
    # --- Skills Section ---
    if data.get("Skills"):
        story.extend(skills_section(data["Skills"]))
    
    # --- Achievements Section ---
    if data.get("Achievements"):
        story.extend(achievements_section(data["Achievements"]))
    
    # --- Education Section ---
    if data.get("Education"):
        story.extend(education_section(data["Education"]))
    
    # Build the PDF - use different headers for first page vs later pages
    doc.build(story, onFirstPage=first_page_header, onLaterPages=later_pages_header)
    print(f"PDF generated in generatepdf.py: {output_file}")



