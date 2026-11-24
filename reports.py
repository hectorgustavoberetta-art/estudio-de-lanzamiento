"""Native Office exports for the market study."""
from datetime import datetime
from io import BytesIO
from pathlib import Path
import re
from zoneinfo import ZoneInfo

NAVY = "102A43"
BLUE = "245783"
GRAY = "536477"
PALE = "EDF2F6"
BRAND = "INTELIGENCIA DE MERCADO"
DOMAIN = "Sistemas Aéreos No Tripulados (UAS)"
TAGLINE = "Análisis tecnológico, comercial y estratégico."
TITLE = "ESTUDIO DE MERCADO Y LANZAMIENTO COMERCIAL"
FOOTER = "Informe generado mediante inteligencia artificial · Sujeto a revisión y validación humana"
ART = Path(__file__).with_name("fondo-drones.png")
MISSING = "Sin consignar en la ficha"


def report_metadata(name, audience, sheet):
    fields = {}
    for line in sheet.splitlines():
        label, sep, value = line.strip().replace("**", "").partition(":")
        if sep and value.strip():
            fields[label.strip(" #*|-").casefold()] = value.strip()
    date = datetime.now(ZoneInfo("America/Santiago")).date()
    model = fields.get("modelo") or fields.get("producto / modelo") or name
    market = fields.get("mercado objetivo") or fields.get("mercado de destino")
    return [
        ("Producto", name),
        ("Modelo", model),
        ("Fabricante", fields.get("fabricante", MISSING)),
        ("País de origen", fields.get("país de origen", fields.get("pais de origen", MISSING))),
        ("Mercado objetivo", market or MISSING),
        ("Público de la pieza comercial", audience),
        ("Fecha de elaboración", date.isoformat()),
    ]


def export_name(metadata, extension):
    values = dict(metadata)
    model = re.sub(r"[^\w.-]+", "_", values["Modelo"]).strip("._-")[:80] or "Modelo"
    return f"Estudio_de_Mercado_{model}_{values['Fecha de elaboración']}.{extension}"


def build_word(metadata, reviewed):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin = section.right_margin = Cm(2)
    section.top_margin, section.bottom_margin = Cm(3.4), Cm(2)
    section.header_distance, section.footer_distance = Cm(0.8), Cm(0.8)
    normal = document.styles["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(11)
    normal.font.color.rgb = RGBColor.from_string(NAVY)
    for index in (1, 2):
        document.styles[f"Heading {index}"].font.color.rgb = RGBColor.from_string(BLUE)

    header = section.header
    spacer = header.paragraphs[0].paragraph_format
    spacer.line_spacing = Pt(1)
    spacer.space_after = Pt(0)
    table = header.add_table(rows=1, cols=2, width=Cm(17))
    table.autofit = False
    for column, width in zip(table.columns, (4.4, 12.6)):
        column.width = Cm(width)
    image_cell, brand_cell = table.rows[0].cells
    image_cell.width, brand_cell.width = Cm(4.4), Cm(12.6)
    if ART.is_file():
        image_cell.paragraphs[0].add_run().add_picture(str(ART), width=Cm(4.1))
    title = brand_cell.paragraphs[0].add_run(BRAND)
    title.bold, title.font.size = True, Pt(19)
    title.font.color.rgb = RGBColor.from_string(BLUE)
    line = brand_cell.add_paragraph().add_run(DOMAIN)
    line.bold, line.font.size = True, Pt(12)
    note = brand_cell.add_paragraph().add_run(TAGLINE)
    note.font.color.rgb = RGBColor.from_string(GRAY)
    for paragraph in brand_cell.paragraphs:
        paragraph.paragraph_format.space_after = Pt(1)
    border = OxmlElement("w:tblBorders")
    bottom = OxmlElement("w:bottom")
    for key, value in (("val", "single"), ("sz", "12"), ("color", BLUE)):
        bottom.set(qn(f"w:{key}"), value)
    border.append(bottom)
    table._tbl.tblPr.append(border)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run(FOOTER + "  |  Página ")
    run.font.size, run.font.color.rgb = Pt(8), RGBColor.from_string(GRAY)
    page = OxmlElement("w:fldSimple")
    page.set(qn("w:instr"), "PAGE")
    footer._p.append(page)

    heading = document.add_paragraph(TITLE, "Title")
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    profile = document.add_table(rows=0, cols=2)
    profile.style = "Light Shading Accent 1"
    for label, value in metadata:
        left, right = profile.add_row().cells
        left.paragraphs[0].add_run(label).bold = True
        right.text = value
    document.add_heading("Informe comercial", level=1)
    for index, (claim, citation, approved, located) in enumerate(reviewed, start=1):
        document.add_heading(f"Afirmación {index} · {'Aprobada' if approved else 'Pendiente de revisión'}", level=2)
        document.add_paragraph(claim)
        if citation:
            label = "Referencia en la ficha" if located else "Referencia pendiente de cotejo"
            paragraph = document.add_paragraph()
            paragraph.add_run(f"{label} — ").bold = True
            paragraph.add_run(citation)
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def build_presentation(metadata, approved, photos=()):
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_AUTO_SIZE
    from pptx.oxml.xmlchemy import OxmlElement
    from pptx.parts.image import Image
    from pptx.util import Inches, Pt

    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    images = []
    for photo in photos:
        try:
            image = Image.from_blob(photo)
            width, height = image.size
            if width and height:
                images.append((photo, width / height))
        except (OSError, ValueError, TypeError):
            continue
    illustrative = not images
    if illustrative and ART.is_file():
        image = Image.from_file(str(ART))
        width, height = image.size
        images.append((image.blob, width / height))

    def panel(slide, x, y, width, height, opacity):
        rectangle = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(width), Inches(height)
        )
        rectangle.line.fill.background()
        rectangle.fill.solid()
        rectangle.fill.fore_color.rgb = RGBColor.from_string(NAVY)
        color = rectangle._element.spPr.solidFill.srgbClr
        alpha = OxmlElement("a:alpha")
        alpha.set("val", str(opacity))
        color.append(alpha)

    def text(slide, value, x, y, width, height, size, color="FFFFFF", bold=False):
        frame = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(height)).text_frame
        frame.word_wrap = True
        frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        run = frame.paragraphs[0].add_run()
        run.text, run.font.size, run.font.bold = value, Pt(size), bold
        run.font.name, run.font.color.rgb = "Calibri", RGBColor.from_string(color)

    def slide_with_header(title):
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string(NAVY)
        if images:
            blob, ratio = images[(len(deck.slides) - 1) % len(images)]
            picture = slide.shapes.add_picture(BytesIO(blob), 0, 0, deck.slide_width, deck.slide_height)
            target = deck.slide_width / deck.slide_height
            if ratio > target:
                picture.crop_left = picture.crop_right = (1 - target / ratio) / 2
            else:
                picture.crop_top = picture.crop_bottom = (1 - ratio / target) / 2
        panel(slide, 0, 0, 13.333, 7.5, 26000)
        panel(slide, 0, 0, 13.333, 1.94, 85000)
        panel(slide, 0, 6.88, 13.333, 0.62, 90000)
        text(slide, BRAND, 0.65, 0.29, 12, 0.46, 17, "9DDCFF", True)
        text(slide, title, 0.65, 0.82, 12, 0.94, 32, bold=True)
        image_note = " · Fondo ilustrativo" if illustrative and images else ""
        text(slide, f"{FOOTER}{image_note}  |  {len(deck.slides)}", 0.65, 7.0, 12, 0.33, 10)
        return slide

    cover = slide_with_header(TITLE)
    panel(cover, 0.55, 2.15, 8.25, 4.55, 88000)
    text(cover, DOMAIN, 0.78, 2.34, 7.8, 0.52, 23, "9DDCFF", True)
    text(cover, TAGLINE, 0.78, 2.89, 7.8, 0.44, 16)
    info = cover.shapes.add_table(len(metadata), 2, Inches(0.85), Inches(3.43), Inches(7.65), Inches(2.95)).table
    info.columns[0].width, info.columns[1].width = Inches(2.75), Inches(4.9)
    for i, pair in enumerate(metadata):
        for j, value in enumerate(pair):
            cell = info.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor.from_string(PALE if i % 2 == 0 else "FFFFFF")
            cell.text = value
            for run in cell.text_frame.paragraphs[0].runs:
                run.font.size, run.font.bold = Pt(14), j == 0
                run.font.color.rgb = RGBColor.from_string(NAVY)

    product = dict(metadata)["Producto"]
    for i, (claim, citation) in enumerate(approved, start=1):
        slide = slide_with_header(f"Síntesis ejecutiva · {product}")
        panel(slide, 0.55, 2.15, 8.25, 4.55, 88000)
        text(slide, f"Hallazgo {i} de {len(approved)}", 0.82, 2.39, 7.65, 0.46, 16, "9DDCFF", True)
        text(slide, claim, 0.82, 2.99, 7.65, 1.87, 29, bold=True)
        text(slide, "Referencia en la ficha", 0.82, 4.96, 7.65, 0.34, 14, "9DDCFF", True)
        text(slide, citation, 0.82, 5.4, 7.65, 1.05, 15)

    output = BytesIO()
    deck.save(output)
    return output.getvalue()
