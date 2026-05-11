import os
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(46, 80, 119)
        self.cell(0, 10, 'Jira Triage Automation: Stakeholder Briefing', 0, 1, 'C')
        self.ln(5)

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(77, 161, 169)
        self.cell(0, 10, label, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 7, body)
        self.ln()

def create_pdf(input_md_path, output_pdf_path):
    pdf = PDF()
    pdf.add_page()
    
    with open(input_md_path, 'r') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        # Remove emojis for latin-1 compatibility
        line = line.encode('ascii', 'ignore').decode('ascii').strip()
        if not line:
            pdf.ln(2)
            continue
            
        if line.startswith('# '):
            # Header is already in PDF.header()
            continue
        elif line.startswith('## '):
            pdf.chapter_title(line[3:])
        elif line.startswith('* '):
            pdf.set_font('Arial', '', 11)
            pdf.set_text_color(0, 0, 0)
            text = line[2:].replace('**', '')
            pdf.cell(10) # Indent
            pdf.multi_cell(0, 7, f"- {text}")
        elif line.startswith('---'):
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
        else:
            pdf.chapter_body(line.replace('**', ''))
            
    pdf.output(output_pdf_path)
    print(f"PDF created at: {output_pdf_path}")

if __name__ == "__main__":
    input_path = "/Users/sanket_74/.gemini/antigravity/brain/18812ef9-33ba-4591-96ea-0fb051fadc3f/stakeholder_briefing.md"
    output_path = "/Users/sanket_74/Documents/Antigravity/Jira-Summarizer/Stakeholder_Briefing.pdf"
    create_pdf(input_path, output_path)
