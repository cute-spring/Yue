import os
import tempfile
from docx import Document
import markdown

class ExportService:
    @staticmethod
    def export_to_txt(content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    @staticmethod
    def export_to_docx(content: str) -> str:
        doc = Document()
        # For a simple implementation, we just add the markdown content as a paragraph.
        # A more robust implementation might parse the markdown and map to docx styles.
        for line in content.split('\n'):
            if line.strip():
                doc.add_paragraph(line)
        
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        doc.save(path)
        return path

    @staticmethod
    def export_to_pdf(content: str) -> str:
        html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
        styled_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: sans-serif; line-height: 1.6; padding: 2em; color: #333; }}
                pre {{ background: #f4f4f4; padding: 1em; border-radius: 4px; white-space: pre-wrap; }}
                code {{ font-family: monospace; background: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; }}
                h1, h2, h3, h4 {{ color: #111; margin-top: 1.5em; }}
                blockquote {{ border-left: 4px solid #ccc; margin-left: 0; padding-left: 1em; color: #666; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f4f4f4; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
        try:
            from weasyprint import HTML
            HTML(string=styled_html).write_pdf(path)
        except Exception as e:
            # Fallback or raise a descriptive error
            raise RuntimeError(f"PDF generation requires WeasyPrint system dependencies (e.g. pango, cairo). Error: {str(e)}")
            
        return path
