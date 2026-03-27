from fpdf import FPDF

class SubmissionPDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 12)
        self.cell(0, 10, 'Submission: Google Drive Link', border=False, ln=True, align='C')
        self.ln(10)

def create_pdf(link, filename):
    pdf = SubmissionPDF()
    pdf.add_page()
    pdf.set_font('helvetica', '', 12)
    pdf.cell(0, 10, 'Link to the screen recording:', ln=True)
    pdf.set_text_color(0, 0, 255)
    pdf.cell(0, 10, link, ln=True, link=link)
    pdf.output(filename)

if __name__ == "__main__":
    drive_link = "https://drive.google.com/drive/folders/1I69CFyGUftAiL5-b0EwcsEtTrLLiacHS?usp=sharing"
    create_pdf(drive_link, "Submission_Link.pdf")
    print(f"PDF generated: Submission_Link.pdf")
