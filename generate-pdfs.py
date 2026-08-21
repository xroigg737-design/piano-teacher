#!/usr/bin/env python3
"""
Genera PDFs professionals amb sketchnote infogràfic + transcripció
per cada vídeo del canal de Raquel García Piano.
"""
import os, json, re, math, sys
from collections import Counter

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

DIR = "/home/xroig/piano-teacher/transcriptions"
OUT = "/home/xroig/piano-teacher/pdfs"
os.makedirs(OUT, exist_ok=True)

# Fonts
pdfmetrics.registerFont(TTFont('Serif',      '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Serif-Bold',  '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'))
pdfmetrics.registerFont(TTFont('Serif-It',    '/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf'))
pdfmetrics.registerFont(TTFont('Serif-BoldIt','/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf'))
pdfmetrics.registerFont(TTFont('Sans',        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Sans-Bold',   '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('Sans-It',     '/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf'))

W, H = A4  # 595.28 x 841.89

# Professional color palette
CHARCOAL    = HexColor('#2c2c2c')
DARK_TEXT   = HexColor('#333333')
MID_TEXT    = HexColor('#555555')
LIGHT_TEXT  = HexColor('#888888')
VERY_LIGHT  = HexColor('#cccccc')
CREAM       = HexColor('#faf8f5')
WARM_WHITE  = HexColor('#fefefe')
GOLD_ACCENT = HexColor('#c8962e')
GOLD_LIGHT  = HexColor('#e8c87a')
GOLD_BG     = HexColor('#f9f3e6')
TEAL        = HexColor('#2a7b7b')
TEAL_LIGHT  = HexColor('#e6f2f2')
TEAL_BG     = HexColor('#f0f7f7')
RUST        = HexColor('#b85c38')
RUST_LIGHT  = HexColor('#f5e8e2')
NAVY        = HexColor('#1e3a5f')
NAVY_LIGHT  = HexColor('#e8eef5')
SAGE        = HexColor('#5a7a5a')
SAGE_LIGHT  = HexColor('#eaf0ea')
LINE_COLOR  = HexColor('#ddd5ca')
PAGE_BG     = HexColor('#fffefa')

SECTION_COLORS = [
    (TEAL, TEAL_LIGHT, TEAL_BG),
    (RUST, RUST_LIGHT, RUST_LIGHT),
    (NAVY, NAVY_LIGHT, NAVY_LIGHT),
    (SAGE, SAGE_LIGHT, SAGE_LIGHT),
    (GOLD_ACCENT, GOLD_BG, GOLD_BG),
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


def extract_insights(text, n_ideas=6, n_tips=5, n_quotes=3):
    sentences = [s.strip() for s in re.split(r'[.\n]+', text) if len(s.strip()) > 25]
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
    for s, sc in scored:
        key = s[:25].lower()
        if key in seen or sc <= 0: continue
        seen.add(key)
        t = s[:140] + '...' if len(s) > 140 else s
        sl = s.lower()
        if any(k in sl for k in ['hay que', 'debes', 'tienes que', 'es importante',
                                   'recomiendo', 'consejo', 'intenta', 'practica',
                                   'evita', 'asegúrate', 'recuerda', 'no hagas']):
            if len(tips) < n_tips: tips.append(t); continue
        if len(ideas) < n_ideas: ideas.append(t)
        elif 50 < len(s) < 180 and len(quotes) < n_quotes: quotes.append(s[:160])

    themes = top[:10]
    return {'ideas': ideas, 'tips': tips, 'quotes': quotes, 'themes': themes}


def rounded_rect(c, x, y, w, h, r, **kw):
    p = c.beginPath()
    p.moveTo(x+r, y); p.lineTo(x+w-r, y)
    p.arcTo(x+w-r, y, x+w, y+r, r)
    p.lineTo(x+w, y+h-r)
    p.arcTo(x+w, y+h-r, x+w-r, y+h, r)
    p.lineTo(x+r, y+h)
    p.arcTo(x+r, y+h, x, y+h-r, r)
    p.lineTo(x, y+r)
    p.arcTo(x, y+r, x+r, y, r)
    p.close()
    fill = kw.get('fill')
    stroke = kw.get('stroke')
    sw = kw.get('stroke_width', 0.5)
    if fill: c.setFillColor(fill)
    if stroke: c.setStrokeColor(stroke); c.setLineWidth(sw)
    c.drawPath(p, fill=1 if fill else 0, stroke=1 if stroke else 0)


def draw_text_block(c, text, x, y, w, font, size, color, leading=None, max_lines=99):
    if leading is None: leading = size * 1.45
    c.setFont(font, size); c.setFillColor(color)
    lines = simpleSplit(text, font, size, w)
    for line in lines[:max_lines]:
        c.drawString(x, y, line)
        y -= leading
    return y


def draw_header_footer(c, title_short, page_num, total_label=''):
    # Thin top line
    c.setStrokeColor(LINE_COLOR); c.setLineWidth(0.4)
    c.line(50, H - 38, W - 50, H - 38)
    # Header text
    c.setFont('Sans', 6.5); c.setFillColor(LIGHT_TEXT)
    c.drawString(50, H - 34, 'PIANO TEACHER  ·  RAQUEL GARCÍA PIANO')
    c.drawRightString(W - 50, H - 34, total_label)
    # Footer
    c.setStrokeColor(LINE_COLOR); c.setLineWidth(0.3)
    c.line(50, 42, W - 50, 42)
    c.setFont('Sans', 6.5); c.setFillColor(LIGHT_TEXT)
    c.drawString(50, 30, title_short[:55])
    c.drawRightString(W - 50, 30, str(page_num))


# ============================================================
#  PAGE 1: COVER
# ============================================================
def draw_cover(c, title, duration, word_count, vid_id, category):
    # Cream background
    c.setFillColor(CREAM); c.rect(0, 0, W, H, fill=1, stroke=0)

    # Top gold band
    c.setFillColor(GOLD_ACCENT); c.rect(0, H - 8, W, 8, fill=1, stroke=0)

    # Vertical accent line left
    c.setStrokeColor(GOLD_ACCENT); c.setLineWidth(2.5)
    c.line(50, H - 60, 50, 180)

    # Series label
    c.setFont('Sans', 8); c.setFillColor(GOLD_ACCENT)
    c.drawString(68, H - 80, 'RAQUEL GARCÍA PIANO  ·  CANAL YOUTUBE')

    # Thin line under label
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

    # Decorative rule under title
    c.setStrokeColor(GOLD_ACCENT); c.setLineWidth(1.2)
    c.line(68, ty - 5, 200, ty - 5)

    # Metadata block
    my = ty - 45
    meta_items = [
        ('Durada', duration),
        ('Paraules', f'{word_count:,}'.replace(',', '.')),
        ('Font', 'YouTube — @Raquelgarciapiano'),
        ('Contingut', 'Sketchnote + Transcripció completa'),
    ]
    for label, value in meta_items:
        c.setFont('Sans-Bold', 8); c.setFillColor(LIGHT_TEXT)
        c.drawString(68, my, label.upper())
        c.setFont('Serif', 10.5); c.setFillColor(DARK_TEXT)
        c.drawString(160, my, value)
        my -= 22

    # Bottom block
    c.setFillColor(CHARCOAL); c.rect(0, 0, W, 100, fill=1, stroke=0)
    c.setFillColor(GOLD_ACCENT); c.rect(0, 100, W, 2, fill=1, stroke=0)

    c.setFont('Sans-Bold', 11); c.setFillColor(GOLD_LIGHT)
    c.drawString(50, 68, 'PIANO TEACHER')
    c.setFont('Sans', 8); c.setFillColor(HexColor('#999999'))
    c.drawString(50, 50, 'Assessor professional per dominar el piano')

    c.setFont('Sans', 7.5); c.setFillColor(HexColor('#777777'))
    c.drawRightString(W - 50, 50, f'youtube.com/watch?v={vid_id}')


# ============================================================
#  PAGE 2: SKETCHNOTE INFOGRAPHIC
# ============================================================
def draw_sketchnote(c, title, duration, word_count, vid_id, data):
    c.showPage()
    # Light warm background
    c.setFillColor(PAGE_BG); c.rect(0, 0, W, H, fill=1, stroke=0)

    margin_l, margin_r = 50, 50
    usable = W - margin_l - margin_r

    # Header bar
    c.setFillColor(CHARCOAL); c.rect(0, H - 55, W, 55, fill=1, stroke=0)
    c.setFont('Sans-Bold', 9); c.setFillColor(GOLD_ACCENT)
    c.drawString(margin_l, H - 25, 'SKETCHNOTE')
    c.setFont('Sans', 7.5); c.setFillColor(HexColor('#aaaaaa'))
    c.drawRightString(W - margin_r, H - 25, f'{duration}  ·  {word_count:,} paraules'.replace(',', '.'))
    # Title in header
    c.setFont('Sans-Bold', 11); c.setFillColor(white)
    tlines = simpleSplit(title, 'Sans-Bold', 11, usable)
    c.drawString(margin_l, H - 44, tlines[0] if tlines else title[:60])

    cy = H - 75
    col_w = (usable - 20) / 2
    left_x = margin_l
    right_x = margin_l + col_w + 20

    ideas = data['ideas']
    tips = data['tips']
    quotes = data['quotes']
    themes = data['themes']

    # ---- LEFT: IDEAS CLAU ----
    ly = cy
    c.setFont('Sans-Bold', 10); c.setFillColor(NAVY)
    c.drawString(left_x, ly, 'IDEAS CLAU')
    c.setStrokeColor(NAVY); c.setLineWidth(1.5)
    c.line(left_x, ly - 4, left_x + 75, ly - 4)
    ly -= 22

    for i, idea in enumerate(ideas[:6]):
        accent, bg_line, bg_fill = SECTION_COLORS[i % len(SECTION_COLORS)]
        lines = simpleSplit(idea, 'Serif', 8.5, col_w - 28)
        box_h = max(28, len(lines) * 12.5 + 12)
        box_y = ly - box_h

        # Card background
        rounded_rect(c, left_x, box_y, col_w, box_h, 5, fill=WARM_WHITE, stroke=LINE_COLOR)
        # Left color accent bar
        c.setFillColor(accent)
        c.rect(left_x, box_y, 4, box_h, fill=1, stroke=0)

        # Number
        c.setFont('Sans-Bold', 14); c.setFillColor(accent)
        c.drawString(left_x + 10, box_y + box_h - 17, str(i + 1))

        # Text
        c.setFont('Serif', 8.5); c.setFillColor(DARK_TEXT)
        ty = box_y + box_h - 15
        for line in lines[:4]:
            c.drawString(left_x + 28, ty, line)
            ty -= 12.5

        ly = box_y - 8

    # ---- RIGHT: CONSELLS + CITES ----
    ry = cy
    if tips:
        c.setFont('Sans-Bold', 10); c.setFillColor(SAGE)
        c.drawString(right_x, ry, 'CONSELLS PRÀCTICS')
        c.setStrokeColor(SAGE); c.setLineWidth(1.5)
        c.line(right_x, ry - 4, right_x + 118, ry - 4)
        ry -= 22

        for i, tip in enumerate(tips[:5]):
            lines = simpleSplit(tip, 'Serif', 8.2, col_w - 22)
            box_h = max(24, len(lines) * 11.5 + 10)
            box_y = ry - box_h

            # Light sage background
            rounded_rect(c, right_x, box_y, col_w, box_h, 4, fill=SAGE_LIGHT)

            # Check mark
            c.setFont('Sans-Bold', 9); c.setFillColor(SAGE)
            c.drawString(right_x + 8, box_y + box_h - 14, '>')

            # Text
            c.setFont('Serif', 8.2); c.setFillColor(DARK_TEXT)
            ty = box_y + box_h - 14
            for line in lines[:3]:
                c.drawString(right_x + 20, ty, line)
                ty -= 11.5

            ry = box_y - 6

    if quotes:
        ry -= 12
        c.setFont('Sans-Bold', 10); c.setFillColor(RUST)
        c.drawString(right_x, ry, 'CITES DESTACADES')
        c.setStrokeColor(RUST); c.setLineWidth(1.5)
        c.line(right_x, ry - 4, right_x + 110, ry - 4)
        ry -= 22

        for i, quote in enumerate(quotes[:3]):
            lines = simpleSplit(quote, 'Serif-It', 8.2, col_w - 30)
            box_h = max(26, len(lines) * 11.5 + 14)
            box_y = ry - box_h

            rounded_rect(c, right_x, box_y, col_w, box_h, 4, fill=RUST_LIGHT)

            # Opening quote mark
            c.setFont('Serif-Bold', 22); c.setFillColor(RUST)
            c.drawString(right_x + 6, box_y + box_h - 18, '“')

            c.setFont('Serif-It', 8.2); c.setFillColor(MID_TEXT)
            ty = box_y + box_h - 16
            for line in lines[:3]:
                c.drawString(right_x + 22, ty, line)
                ty -= 11.5

            ry = box_y - 6

    # ---- BOTTOM: THEMES BAR ----
    bar_y = 45
    bar_h = 35
    c.setStrokeColor(LINE_COLOR); c.setLineWidth(0.3)
    c.line(margin_l, bar_y + bar_h + 5, W - margin_r, bar_y + bar_h + 5)

    c.setFont('Sans-Bold', 7.5); c.setFillColor(LIGHT_TEXT)
    c.drawString(margin_l, bar_y + bar_h - 8, 'TEMES PRINCIPALS')

    tx = margin_l
    c.setFont('Sans', 7.5)
    for i, theme in enumerate(themes[:10]):
        pill_w = c.stringWidth(theme, 'Sans', 7.5) + 14
        if tx + pill_w > W - margin_r: break
        accent = SECTION_COLORS[i % len(SECTION_COLORS)][0]
        rounded_rect(c, tx, bar_y, pill_w, 18, 9, fill=accent)
        c.setFont('Sans', 7.5); c.setFillColor(white)
        c.drawString(tx + 7, bar_y + 5, theme)
        tx += pill_w + 5

    # Footer
    c.setFont('Sans', 6); c.setFillColor(VERY_LIGHT)
    c.drawString(margin_l, 28, 'Piano Teacher · Sketchnote generat automàticament')


# ============================================================
#  PAGES 3+: TRANSCRIPTION
# ============================================================
def draw_transcription(c, title, text, duration, word_count, vid_id):
    margin_l, margin_r, margin_top, margin_bot = 65, 60, 60, 60
    usable = W - margin_l - margin_r
    font_size = 10
    leading = 15
    para_spacing = 8

    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

    # Pre-split all paragraphs into lines
    all_elements = []  # (type, content): 'line'->text, 'break'->None
    for para in paragraphs:
        lines = simpleSplit(para, 'Serif', font_size, usable)
        for line in lines:
            all_elements.append(('line', line))
        all_elements.append(('break', None))

    page_num = 2  # cover=1, sketchnote=2, first text=3
    elem_idx = 0
    first_text_page = True

    while elem_idx < len(all_elements):
        c.showPage()
        page_num += 1

        # Page background
        c.setFillColor(PAGE_BG); c.rect(0, 0, W, H, fill=1, stroke=0)

        if first_text_page:
            # Elegant section opener
            y_start = H - margin_top

            # "TRANSCRIPCIÓ" label
            c.setFont('Sans', 7.5); c.setFillColor(GOLD_ACCENT)
            c.drawString(margin_l, y_start, 'TRANSCRIPCIÓ COMPLETA')
            y_start -= 18

            # Title
            c.setFont('Serif-Bold', 16); c.setFillColor(CHARCOAL)
            tlines = simpleSplit(title, 'Serif-Bold', 16, usable)
            for tl in tlines[:2]:
                c.drawString(margin_l, y_start, tl)
                y_start -= 22

            # Metadata line
            y_start -= 4
            c.setFont('Sans', 8); c.setFillColor(LIGHT_TEXT)
            meta = f'Raquel García Piano  ·  {duration}  ·  {word_count:,} paraules'.replace(',', '.')
            c.drawString(margin_l, y_start, meta)
            y_start -= 8

            # Decorative rule
            c.setStrokeColor(GOLD_ACCENT); c.setLineWidth(0.8)
            c.line(margin_l, y_start, margin_l + 100, y_start)
            c.setStrokeColor(LINE_COLOR); c.setLineWidth(0.3)
            c.line(margin_l + 100, y_start, W - margin_r, y_start)
            y_start -= 22

            first_text_page = False
        else:
            y_start = H - margin_top
            # Running header
            draw_header_footer(c, title[:55], page_num, f'{duration}')
            y_start -= 8

        # Render text
        y = y_start
        c.setFont('Serif', font_size); c.setFillColor(DARK_TEXT)

        while elem_idx < len(all_elements) and y > margin_bot + 10:
            typ, content = all_elements[elem_idx]
            if typ == 'break':
                y -= para_spacing
                elem_idx += 1
            else:
                c.drawString(margin_l, y, content)
                y -= leading
                elem_idx += 1

        # Page footer
        c.setStrokeColor(LINE_COLOR); c.setLineWidth(0.3)
        c.line(margin_l, margin_bot - 15, W - margin_r, margin_bot - 15)
        c.setFont('Sans', 6.5); c.setFillColor(LIGHT_TEXT)
        c.drawString(margin_l, margin_bot - 28, title[:50])
        c.drawRightString(W - margin_r, margin_bot - 28, str(page_num))


# ============================================================
#  MAIN
# ============================================================
def generate_pdf(vid_id, title, duration, text, category=''):
    word_count = len(text.split())
    data = extract_insights(text)

    pdf_path = os.path.join(OUT, f'{vid_id}.pdf')
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setTitle(title)
    c.setAuthor('Piano Teacher — Raquel García Piano')
    c.setSubject(f'Sketchnote + Transcripció: {title}')

    draw_cover(c, title, duration, word_count, vid_id, category)
    draw_sketchnote(c, title, duration, word_count, vid_id, data)
    draw_transcription(c, title, text, duration, word_count, vid_id)

    c.save()
    return pdf_path


def main():
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

    print(f'Generant {total} PDFs professionals...')
    print()

    for vid_id, info in sorted(all_videos.items(), key=lambda x: x[1]['title']):
        done += 1
        txt_path = os.path.join(DIR, vid_id + '.txt')
        if not os.path.exists(txt_path):
            print(f'[{done}/{total}] SKIP: {vid_id}')
            continue
        with open(txt_path, encoding='utf-8') as f:
            text = f.read()
        if len(text.strip()) < 50:
            print(f'[{done}/{total}] SKIP (curt): {vid_id}')
            continue
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
