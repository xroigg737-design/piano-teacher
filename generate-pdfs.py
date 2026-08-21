#!/usr/bin/env python3
"""
Genera PDFs professionals amb portada, sketchnote i transcripció
justificada amb Platypus per cada vídeo de Raquel García Piano.
"""
import os, json, re, sys
from collections import Counter

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Frame, PageTemplate, BaseDocTemplate,
    NextPageTemplate, FrameBreak
)
from reportlab.lib.utils import simpleSplit

DIR = "/home/xroig/piano-teacher/transcriptions"
OUT = "/home/xroig/piano-teacher/pdfs"
os.makedirs(OUT, exist_ok=True)

W, H = A4

# Fonts
pdfmetrics.registerFont(TTFont('Serif',       '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Serif-Bold',   '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'))
pdfmetrics.registerFont(TTFont('Serif-It',     '/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf'))
pdfmetrics.registerFont(TTFont('Serif-BoldIt', '/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf'))
pdfmetrics.registerFont(TTFont('Sans',         '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Sans-Bold',    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('Sans-It',      '/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf'))

# Colors
CHARCOAL   = HexColor('#2c2c2c')
DARK_TEXT   = HexColor('#333333')
MID_TEXT    = HexColor('#555555')
LIGHT_TEXT  = HexColor('#888888')
VERY_LIGHT  = HexColor('#cccccc')
CREAM       = HexColor('#faf8f5')
WARM_WHITE  = HexColor('#fefefe')
GOLD        = HexColor('#c8962e')
GOLD_LIGHT  = HexColor('#e8c87a')
GOLD_BG     = HexColor('#f9f3e6')
TEAL        = HexColor('#2a7b7b')
TEAL_LIGHT  = HexColor('#e6f2f2')
RUST        = HexColor('#b85c38')
RUST_LIGHT  = HexColor('#f5e8e2')
NAVY        = HexColor('#1e3a5f')
NAVY_LIGHT  = HexColor('#e8eef5')
SAGE        = HexColor('#5a7a5a')
SAGE_LIGHT  = HexColor('#eaf0ea')
LINE_COLOR  = HexColor('#ddd5ca')
PAGE_BG     = HexColor('#fffefa')

SECTION_COLORS = [
    (TEAL, TEAL_LIGHT), (RUST, RUST_LIGHT),
    (NAVY, NAVY_LIGHT), (SAGE, SAGE_LIGHT),
    (GOLD, GOLD_BG),
]

STOPWORDS = set("""
de la el en y que es un una los las del al por con no se su para como más
pero si lo todo esta ya hay le me te nos les muy bien ser ir hacer puede
todo esta este esta esto eso así son fue ser ha han sido también entre
tiene muy ya todo sus porque donde cuando sin ese esa esos esas algo
poco cada nos otro otra otros todas como hasta desde donde cada
sobre entre ellos ellas ella usted ustedes cual quien cuyo aquí
ahí entonces después antes durante siempre nunca nada nadie
tan casi mismo yo tu el ella nosotros vosotros mis tus
a o u e i las uno dos tres cuatro cinco seis siete ocho nueve diez
ver tener decir dar saber querer llegar pasar deber poner volver creer
llevar dejar seguir encontrar llamar venir pensar salir conocer vivir
tipo digamos momento bueno pues vale verdad vamos entonces mira claro
cosa cosas forma manera parte vez veces tiempo punto hecho idea caso
demás estas estos aquella aquel porque además según
aunque mientras tanto hacia mediante cualquier sido estar siendo estado
estaba estaban poder podemos pueden podría
haber había hay hemos tenemos tienen tenía
incluso sino embargo cuanto siendo realmente
""".split())


def merge_into_paragraphs(text):
    """Join Whisper's fragmented lines into proper flowing paragraphs."""
    lines = text.split('\n')
    paragraphs = []
    current = []

    for line in lines:
        line = line.strip()
        if not line:
            if current:
                paragraphs.append(' '.join(current))
                current = []
            continue

        current.append(line)

        if re.search(r'[.!?…»"][\s)*]*$', line):
            paragraphs.append(' '.join(current))
            current = []

    if current:
        paragraphs.append(' '.join(current))

    # Split overly long paragraphs (>600 chars) at sentence boundaries
    final = []
    for para in paragraphs:
        if len(para) <= 600:
            final.append(para)
            continue
        sents = re.split(r'(?<=[.!?])\s+', para)
        chunk = []
        chunk_len = 0
        for s in sents:
            chunk.append(s)
            chunk_len += len(s)
            if chunk_len > 400:
                final.append(' '.join(chunk))
                chunk = []
                chunk_len = 0
        if chunk:
            final.append(' '.join(chunk))

    return [p.strip() for p in final if p.strip()]


def extract_insights(text, n_ideas=6, n_tips=5, n_quotes=3):
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 25]
    words = re.findall(r'[a-záéíóúñü]{4,}', text.lower())
    freq = Counter(w for w in words if w not in STOPWORDS)
    top = [w for w, _ in freq.most_common(25)]

    scored = []
    for s in sentences:
        sl = s.lower()
        sc = sum(1 for w in top[:12] if w in sl)
        if any(k in sl for k in ['importante', 'clave', 'fundamental', 'esencial']): sc += 4
        if any(k in sl for k in ['consejo', 'recomiendo', 'sugiero', 'truco']): sc += 3
        if any(k in sl for k in ['nunca', 'siempre', 'error', 'cuidado', 'evita']): sc += 2
        if any(k in sl for k in ['técnica', 'ejercicio', 'práctica', 'estudiar', 'método']): sc += 1
        if len(s) > 300: sc -= 2
        if len(s) < 30: sc -= 1
        scored.append((s, sc))
    scored.sort(key=lambda x: -x[1])

    ideas, tips, quotes = [], [], []
    seen = set()
    tip_kw = ['hay que', 'debes', 'tienes que', 'es importante', 'recomiendo',
              'consejo', 'intenta', 'practica', 'evita', 'asegúrate', 'recuerda', 'no hagas']
    for s, sc in scored:
        key = s[:25].lower()
        if key in seen or sc <= 0: continue
        seen.add(key)
        t = s[:140] + '...' if len(s) > 140 else s
        sl = s.lower()
        if any(k in sl for k in tip_kw):
            if len(tips) < n_tips: tips.append(t); continue
        if len(ideas) < n_ideas: ideas.append(t)
        elif 50 < len(s) < 180 and len(quotes) < n_quotes: quotes.append(s[:160])

    return {'ideas': ideas, 'tips': tips, 'quotes': quotes, 'themes': top[:10]}


def esc(text):
    """Escape XML entities for Paragraph."""
    return (text.replace('&', '&amp;').replace('<', '&lt;')
                .replace('>', '&gt;').replace('"', '&quot;'))


# ============================================================
#  COVER PAGE (drawn on canvas)
# ============================================================
def draw_cover(c, title, duration, word_count, vid_id, category):
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Top gold band
    c.setFillColor(GOLD)
    c.rect(0, H - 8, W, 8, fill=1, stroke=0)

    # Left vertical accent
    c.setStrokeColor(GOLD); c.setLineWidth(2.5)
    c.line(50, H - 60, 50, 180)

    # Series label
    c.setFont('Sans', 8); c.setFillColor(GOLD)
    c.drawString(68, H - 80, 'RAQUEL GARCÍA PIANO  ·  CANAL YOUTUBE')
    c.setStrokeColor(LINE_COLOR); c.setLineWidth(0.3)
    c.line(68, H - 88, W - 80, H - 88)

    # Category
    if category:
        c.setFont('Sans-It', 10); c.setFillColor(TEAL)
        c.drawString(68, H - 115, category)

    # Title
    c.setFont('Serif-Bold', 26); c.setFillColor(CHARCOAL)
    lines = simpleSplit(title, 'Serif-Bold', 26, W - 150)
    ty = H - 160
    for line in lines[:3]:
        c.drawString(68, ty, line)
        ty -= 36

    # Rule under title
    c.setStrokeColor(GOLD); c.setLineWidth(1.2)
    c.line(68, ty - 5, 200, ty - 5)
    c.setStrokeColor(LINE_COLOR); c.setLineWidth(0.3)
    c.line(200, ty - 5, W - 80, ty - 5)

    # Metadata
    my = ty - 45
    for label, value in [
        ('Durada', duration),
        ('Paraules', f'{word_count:,}'.replace(',', '.')),
        ('Font', 'YouTube — @Raquelgarciapiano'),
        ('Contingut', 'Sketchnote + Transcripció completa'),
    ]:
        c.setFont('Sans-Bold', 8); c.setFillColor(LIGHT_TEXT)
        c.drawString(68, my, label.upper())
        c.setFont('Serif', 10.5); c.setFillColor(DARK_TEXT)
        c.drawString(160, my, value)
        my -= 22

    # Bottom band
    c.setFillColor(CHARCOAL); c.rect(0, 0, W, 100, fill=1, stroke=0)
    c.setFillColor(GOLD); c.rect(0, 100, W, 2, fill=1, stroke=0)
    c.setFont('Sans-Bold', 11); c.setFillColor(GOLD_LIGHT)
    c.drawString(50, 68, 'PIANO TEACHER')
    c.setFont('Sans', 8); c.setFillColor(HexColor('#999999'))
    c.drawString(50, 50, 'Assessor professional per dominar el piano')
    c.setFont('Sans', 7.5); c.setFillColor(HexColor('#777777'))
    c.drawRightString(W - 50, 50, f'youtube.com/watch?v={vid_id}')


# ============================================================
#  SKETCHNOTE PAGE (drawn on canvas)
# ============================================================
def rounded_rect(c, x, y, w, h, r, **kw):
    p = c.beginPath()
    p.moveTo(x+r, y); p.lineTo(x+w-r, y)
    p.arcTo(x+w-r, y, x+w, y+r, r)
    p.lineTo(x+w, y+h-r); p.arcTo(x+w, y+h-r, x+w-r, y+h, r)
    p.lineTo(x+r, y+h); p.arcTo(x+r, y+h, x, y+h-r, r)
    p.lineTo(x, y+r); p.arcTo(x, y+r, x+r, y, r)
    p.close()
    fill = kw.get('fill'); stroke = kw.get('stroke')
    if fill: c.setFillColor(fill)
    if stroke: c.setStrokeColor(stroke); c.setLineWidth(kw.get('sw', 0.5))
    c.drawPath(p, fill=1 if fill else 0, stroke=1 if stroke else 0)


def draw_sketchnote(c, title, duration, word_count, vid_id, data):
    c.showPage()
    c.setFillColor(PAGE_BG); c.rect(0, 0, W, H, fill=1, stroke=0)

    margin = 50
    usable = W - 2 * margin

    # Header bar
    c.setFillColor(CHARCOAL); c.rect(0, H - 55, W, 55, fill=1, stroke=0)
    c.setFont('Sans-Bold', 9); c.setFillColor(GOLD)
    c.drawString(margin, H - 25, 'SKETCHNOTE')
    c.setFont('Sans', 7.5); c.setFillColor(HexColor('#aaa'))
    c.drawRightString(W - margin, H - 25, f'{duration}  ·  {word_count:,} paraules'.replace(',', '.'))
    c.setFont('Sans-Bold', 11); c.setFillColor(white)
    tlines = simpleSplit(title, 'Sans-Bold', 11, usable)
    c.drawString(margin, H - 44, tlines[0] if tlines else title[:60])

    cy = H - 75
    col_w = (usable - 20) / 2
    left_x = margin
    right_x = margin + col_w + 20

    ideas = data['ideas']
    tips = data['tips']
    quotes = data['quotes']
    themes = data['themes']

    # LEFT: IDEAS CLAU
    ly = cy
    c.setFont('Sans-Bold', 10); c.setFillColor(NAVY)
    c.drawString(left_x, ly, 'IDEAS CLAU')
    c.setStrokeColor(NAVY); c.setLineWidth(1.5)
    c.line(left_x, ly - 4, left_x + 75, ly - 4)
    ly -= 22

    for i, idea in enumerate(ideas[:6]):
        accent, bg = SECTION_COLORS[i % len(SECTION_COLORS)]
        lines = simpleSplit(idea, 'Serif', 8.5, col_w - 28)
        box_h = max(28, len(lines) * 12.5 + 12)
        box_y = ly - box_h
        rounded_rect(c, left_x, box_y, col_w, box_h, 5, fill=WARM_WHITE, stroke=LINE_COLOR)
        c.setFillColor(accent)
        c.rect(left_x, box_y, 4, box_h, fill=1, stroke=0)
        c.setFont('Sans-Bold', 14); c.setFillColor(accent)
        c.drawString(left_x + 10, box_y + box_h - 17, str(i + 1))
        c.setFont('Serif', 8.5); c.setFillColor(DARK_TEXT)
        ty = box_y + box_h - 15
        for line in lines[:4]:
            c.drawString(left_x + 28, ty, line); ty -= 12.5
        ly = box_y - 8

    # RIGHT: CONSELLS + CITES
    ry = cy
    if tips:
        c.setFont('Sans-Bold', 10); c.setFillColor(SAGE)
        c.drawString(right_x, ry, 'CONSELLS PRÀCTICS')
        c.setStrokeColor(SAGE); c.setLineWidth(1.5)
        c.line(right_x, ry - 4, right_x + 118, ry - 4)
        ry -= 22
        for tip in tips[:5]:
            lines = simpleSplit(tip, 'Serif', 8.2, col_w - 22)
            box_h = max(24, len(lines) * 11.5 + 10)
            box_y = ry - box_h
            rounded_rect(c, right_x, box_y, col_w, box_h, 4, fill=SAGE_LIGHT)
            c.setFillColor(SAGE)
            c.rect(right_x, box_y, 4, box_h, fill=1, stroke=0)
            c.setFont('Sans-Bold', 9); c.setFillColor(SAGE)
            c.drawString(right_x + 10, box_y + box_h - 14, '>')
            c.setFont('Serif', 8.2); c.setFillColor(DARK_TEXT)
            ty = box_y + box_h - 14
            for line in lines[:3]:
                c.drawString(right_x + 20, ty, line); ty -= 11.5
            ry = box_y - 6

    if quotes:
        ry -= 12
        c.setFont('Sans-Bold', 10); c.setFillColor(RUST)
        c.drawString(right_x, ry, 'CITES DESTACADES')
        c.setStrokeColor(RUST); c.setLineWidth(1.5)
        c.line(right_x, ry - 4, right_x + 110, ry - 4)
        ry -= 22
        for quote in quotes[:3]:
            lines = simpleSplit(quote, 'Serif-It', 8.2, col_w - 30)
            box_h = max(26, len(lines) * 11.5 + 14)
            box_y = ry - box_h
            rounded_rect(c, right_x, box_y, col_w, box_h, 4, fill=RUST_LIGHT)
            c.setFont('Serif-Bold', 22); c.setFillColor(RUST)
            c.drawString(right_x + 6, box_y + box_h - 18, '“')
            c.setFont('Serif-It', 8.2); c.setFillColor(MID_TEXT)
            ty = box_y + box_h - 16
            for line in lines[:3]:
                c.drawString(right_x + 22, ty, line); ty -= 11.5
            ry = box_y - 6

    # BOTTOM: THEMES
    bar_y = 45
    c.setStrokeColor(LINE_COLOR); c.setLineWidth(0.3)
    c.line(margin, bar_y + 40, W - margin, bar_y + 40)
    c.setFont('Sans-Bold', 7.5); c.setFillColor(LIGHT_TEXT)
    c.drawString(margin, bar_y + 27, 'TEMES PRINCIPALS')
    tx = margin
    for i, theme in enumerate(themes[:10]):
        pill_w = c.stringWidth(theme, 'Sans', 7.5) + 14
        if tx + pill_w > W - margin: break
        accent = SECTION_COLORS[i % len(SECTION_COLORS)][0]
        rounded_rect(c, tx, bar_y, pill_w, 18, 9, fill=accent)
        c.setFont('Sans', 7.5); c.setFillColor(white)
        c.drawString(tx + 7, bar_y + 5, theme)
        tx += pill_w + 5

    c.setFont('Sans', 6); c.setFillColor(VERY_LIGHT)
    c.drawString(margin, 28, 'Piano Teacher · Sketchnote generat automàticament')


# ============================================================
#  TRANSCRIPTION (Platypus — justified, full-width paragraphs)
# ============================================================
def build_transcription_story(title, text, duration, word_count, vid_id):
    """Build Platypus flowables for the transcription pages."""
    paragraphs = merge_into_paragraphs(text)

    # Styles
    s_title = ParagraphStyle(
        'Title', fontName='Serif-Bold', fontSize=18, leading=24,
        textColor=CHARCOAL, spaceAfter=6, alignment=TA_LEFT,
    )
    s_label = ParagraphStyle(
        'Label', fontName='Sans-Bold', fontSize=7.5, leading=10,
        textColor=GOLD, spaceAfter=2, spaceBefore=0,
    )
    s_meta = ParagraphStyle(
        'Meta', fontName='Sans', fontSize=8, leading=11,
        textColor=LIGHT_TEXT, spaceAfter=4,
    )
    s_body = ParagraphStyle(
        'Body', fontName='Serif', fontSize=10.5, leading=16,
        textColor=DARK_TEXT, alignment=TA_JUSTIFY,
        firstLineIndent=20, spaceBefore=0, spaceAfter=8,
    )
    s_body_first = ParagraphStyle(
        'BodyFirst', parent=s_body,
        firstLineIndent=0, spaceAfter=8,
    )
    s_rule = ParagraphStyle(
        'Rule', fontName='Sans', fontSize=2, leading=4,
        spaceBefore=4, spaceAfter=14,
    )

    story = []

    # Header block
    story.append(Paragraph('TRANSCRIPCIÓ COMPLETA', s_label))
    story.append(Paragraph(esc(title), s_title))
    meta = f'Raquel García Piano &nbsp;·&nbsp; {esc(duration)} &nbsp;·&nbsp; {word_count:,} paraules'.replace(',', '.')
    story.append(Paragraph(meta, s_meta))

    # Decorative rule (using a table as a horizontal line)
    rule_table = Table([['']], colWidths=[W - 130], rowHeights=[1])
    rule_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.8, GOLD),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(rule_table)
    story.append(Spacer(1, 14))

    # Body paragraphs
    for i, para in enumerate(paragraphs):
        style = s_body_first if i == 0 else s_body
        story.append(Paragraph(esc(para), style))

    return story


# ============================================================
#  FULL PDF GENERATION
# ============================================================
def generate_pdf(vid_id, title, duration, text, category=''):
    word_count = len(text.split())
    data = extract_insights(text)
    pdf_path = os.path.join(OUT, f'{vid_id}.pdf')

    # Phase 1: cover + sketchnote on raw canvas
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setTitle(title)
    c.setAuthor('Piano Teacher — Raquel García Piano')
    draw_cover(c, title, duration, word_count, vid_id, category)
    draw_sketchnote(c, title, duration, word_count, vid_id, data)
    c.save()

    # Phase 2: transcription pages with Platypus (appended)
    from io import BytesIO

    # Build transcription PDF in memory
    buf = BytesIO()
    margin_l, margin_r, margin_top, margin_bot = 65, 60, 55, 60

    short_title = title[:50] + ('...' if len(title) > 50 else '')

    def header_footer(canvas_obj, doc):
        canvas_obj.saveState()
        # Background
        canvas_obj.setFillColor(PAGE_BG)
        canvas_obj.rect(0, 0, W, H, fill=1, stroke=0)
        # Header line
        canvas_obj.setStrokeColor(LINE_COLOR); canvas_obj.setLineWidth(0.3)
        canvas_obj.line(margin_l, H - 38, W - margin_r, H - 38)
        canvas_obj.setFont('Sans', 6.5); canvas_obj.setFillColor(LIGHT_TEXT)
        canvas_obj.drawString(margin_l, H - 34, 'PIANO TEACHER  ·  RAQUEL GARCÍA PIANO')
        canvas_obj.drawRightString(W - margin_r, H - 34, duration)
        # Footer
        canvas_obj.setStrokeColor(LINE_COLOR); canvas_obj.setLineWidth(0.3)
        canvas_obj.line(margin_l, margin_bot - 15, W - margin_r, margin_bot - 15)
        canvas_obj.setFont('Sans', 6.5); canvas_obj.setFillColor(LIGHT_TEXT)
        canvas_obj.drawString(margin_l, margin_bot - 28, short_title)
        canvas_obj.drawRightString(W - margin_r, margin_bot - 28, str(doc.page + 2))
        canvas_obj.restoreState()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin_l, rightMargin=margin_r,
        topMargin=margin_top, bottomMargin=margin_bot,
        title=title, author='Piano Teacher',
    )
    doc.build(
        build_transcription_story(title, text, duration, word_count, vid_id),
        onFirstPage=header_footer,
        onLaterPages=header_footer,
    )

    # Merge: cover+sketchnote + transcription pages
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()
    # Add cover + sketchnote
    reader1 = PdfReader(pdf_path)
    for page in reader1.pages:
        writer.add_page(page)
    # Add transcription
    buf.seek(0)
    reader2 = PdfReader(buf)
    for page in reader2.pages:
        writer.add_page(page)
    # Write final
    with open(pdf_path, 'wb') as f:
        writer.write(f)

    return pdf_path


def main():
    # Check PyPDF2
    try:
        import pypdf
    except ImportError:
        print("Instal·lant pypdf...")
        os.system("pip install --break-system-packages pypdf")

    with open(os.path.join(DIR, 'index.json'), encoding='utf-8') as f:
        index = json.load(f)

    vid_cat = {}
    all_videos = {}
    for cat in index['categories']:
        for v in cat['videos']:
            all_videos[v['id']] = v
            vid_cat[v['id']] = cat['name']

    total = len(all_videos)
    done = errors = 0

    print(f'Generant {total} PDFs professionals (Platypus justificat)...')
    print()

    for vid_id, info in sorted(all_videos.items(), key=lambda x: x[1]['title']):
        done += 1
        txt_path = os.path.join(DIR, vid_id + '.txt')
        if not os.path.exists(txt_path):
            print(f'[{done}/{total}] SKIP: {vid_id}'); continue
        with open(txt_path, encoding='utf-8') as f:
            text = f.read()
        if len(text.strip()) < 50:
            print(f'[{done}/{total}] SKIP (curt): {vid_id}'); continue
        try:
            pdf_path = generate_pdf(vid_id, info['title'], info.get('duration', '?'),
                                     text, vid_cat.get(vid_id, ''))
            kb = os.path.getsize(pdf_path) / 1024
            print(f'[{done}/{total}] OK: {info["title"][:55]}  ({kb:.0f}KB)')
            sys.stdout.flush()
        except Exception as e:
            errors += 1
            print(f'[{done}/{total}] ERROR: {vid_id} — {e}')
            import traceback; traceback.print_exc()
            sys.stdout.flush()

    print(f'\n=== COMPLETAT ===')
    print(f'PDFs: {done - errors}/{total}  ·  Errors: {errors}')
    sz = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.endswith('.pdf'))
    print(f'Mida total: {sz / (1024*1024):.1f}MB  ·  Directori: {OUT}')


if __name__ == '__main__':
    main()
