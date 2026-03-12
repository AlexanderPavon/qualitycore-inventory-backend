"""
Utilidad para generación de PDFs con ReportLab.
Encapsula la configuración repetida de documentos, estilos, logo y tablas
que antes estaba duplicada en las 3 tareas Celery de tasks.py.
"""
import os
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


class PDFBuilder:
    """
    Constructor fluido de PDFs con ReportLab.

    Uso básico:
        builder = PDFBuilder(PDFBuilder.make_output_path(filename))
        builder.add_style('MyTitle', fontSize=20, alignment=1)
        builder.add_logo()
        builder.add_paragraph("Título", 'MyTitle')
        builder.add_table(data, col_widths=[...])
        builder.build()
    """

    def __init__(self, filepath: str) -> None:
        self.doc = SimpleDocTemplate(filepath, pagesize=letter)
        self.styles = getSampleStyleSheet()
        self.elements: list = []

    # ── Estilos ──────────────────────────────────────────────────────────────

    def add_style(self, name: str, **kwargs) -> None:
        """
        Registra un ParagraphStyle adicional en la hoja de estilos.
        Si textColor es un string hexadecimal (p.ej. '#256029'), lo convierte automáticamente.
        """
        if isinstance(kwargs.get('textColor'), str):
            tc = kwargs['textColor']
            kwargs['textColor'] = colors.HexColor(tc) if tc.startswith('#') else getattr(colors, tc)
        self.styles.add(ParagraphStyle(name=name, **kwargs))

    # ── Elementos ────────────────────────────────────────────────────────────

    def add_logo(self) -> None:
        """Inserta el logo de la empresa alineado a la derecha (si existe)."""
        logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo.png")
        if os.path.exists(logo_path):
            img = Image(logo_path, width=90, height=40)
            img.hAlign = 'RIGHT'
            self.elements.append(img)

    def add_paragraph(self, text: str, style: str = "Normal") -> None:
        """Añade un párrafo con el estilo indicado."""
        self.elements.append(Paragraph(text, self.styles[style]))

    def add_spacer(self, height: int = 8) -> None:
        """Añade un espacio vertical (en puntos)."""
        self.elements.append(Spacer(1, height))

    def add_hr(self) -> None:
        """Añade una línea horizontal decorativa (#cccccc)."""
        self.elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))

    def add_table(
        self,
        data: list,
        col_widths: list,
        header_color: str = "#10b981",
        font_size: int = 10,
        extra_styles: list | None = None,
    ) -> None:
        """
        Añade una tabla con estilo corporativo estándar.

        Args:
            data: Filas de la tabla; la primera fila es la cabecera.
            col_widths: Ancho de cada columna (en puntos).
            header_color: Color hexadecimal del fondo de la cabecera.
            font_size: Tamaño de fuente para todas las celdas.
            extra_styles: Directivas TableStyle adicionales (lista de tuplas).
        """
        base_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ]
        if extra_styles:
            base_styles.extend(extra_styles)

        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle(base_styles))
        self.elements.append(table)

    # ── Finalización ─────────────────────────────────────────────────────────

    def build(self) -> None:
        """Genera el archivo PDF con todos los elementos añadidos."""
        self.doc.build(self.elements)

    # ── Utilidad estática ────────────────────────────────────────────────────

    @staticmethod
    def make_output_path(filename: str) -> str:
        """
        Crea el directorio MEDIA_ROOT/reports/ si no existe y devuelve
        la ruta completa del archivo.
        """
        out_dir = os.path.join(settings.MEDIA_ROOT, "reports")
        os.makedirs(out_dir, exist_ok=True)
        return os.path.join(out_dir, filename)
