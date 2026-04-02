import logging
import os

from fpdf import FPDF

logger = logging.getLogger(__name__)

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

    target_dir = os.path.dirname(os.path.abspath(filename))
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    try:
        pdf.output(filename)
    except (OSError, IOError) as exc:
        message = f"Failed to write PDF to '{filename}': {exc}"
        logger.exception(message)
        raise RuntimeError(message) from exc
    except Exception as exc:
        message = f"Unexpected error while writing PDF to '{filename}': {exc}"
        logger.exception(message)
        raise RuntimeError(message) from exc

if __name__ == "__main__":
    # The drive link must be provided via environment variable to avoid committing secrets or ephemeral links.
    drive_link = os.environ.get('DRIVE_LINK')
    if not drive_link:
        raise RuntimeError(
            "Missing required environment variable DRIVE_LINK. "
            "Set DRIVE_LINK before running generate_pdf.py."
        )

    output_filename = "Submission_Link.pdf"
    create_pdf(drive_link, output_filename)
    print(f"PDF generated: {output_filename}")
