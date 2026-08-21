#!/usr/bin/env python3
"""
Genera PDFs amb sketchnote visual + transcripció formatejada
per cada vídeo transcrit del canal de Raquel García Piano.
"""
import os, json, re, math, textwrap, sys
from collections import Counter

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, Color, white, black
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

DIR = "/home/xroig/piano-teacher/transcriptions"
OUT = "/home/xroig/piano-teacher/pdfs"
os.makedirs(OUT, exist_ok=True)

# Register fonts
pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('DejaVu-Oblique', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf'))

W, H = A4  # 595 x 842 points

# Colors
DARK_BG = HexColor('#1a1a2e')
GOLD = HexColor('#ffaa00')
GOLD_DARK = HexColor('#d4920a')
GOLD_LIGHT = HexColor('#ffd080')
RED_YT = HexColor('#ff4444')
SOFT_WHITE = HexColor('#f0f0f0')
LIGHT_GRAY = HexColor('#e0e0e0')
MID_GRAY = HexColor('#888888')
BUBBLE_COLORS = [
    HexColor('#2d4a7a'), HexColor('#4a2d6b'), HexColor('#6b4a2d'),
    HexColor('#2d6b4a'), HexColor('#6b2d4a'), HexColor('#4a6b2d'),
    HexColor('#3d5a8a'), HexColor('#5a3d7b'),
]
ACCENT_COLORS = [
    HexColor('#4fc3f7'), HexColor('#ab47bc'), HexColor('#ff7043'),
    HexColor('#66bb6a'), HexColor('#ef5350'), HexColor('#ffa726'),
    HexColor('#26c6da'), HexColor('#ec407a'),
]

# Spanish stopwords
STOPWORDS = set("""
de la el en y que es un una los las del al por con no se su para como más
pero si lo todo esta ya hay le me te nos les muy bien ser ir hacer puede
todo esta este esta esto eso así son fue ser ha han sido también entre
tiene muy ya todo sus porque donde cuando sin ese esa esos esas algo
poco cada nos otro otra otros todas como hasta desde donde cada
sobre entre ellos ellas ella usted ustedes cual quien cuyo cuyos aquí
ahí entonces después antes durante siempre nunca nada nadie
tan casi mismo yo tu el ella nosotros vosotros ellos mis tus mis
a o u e i las uno dos tres cuatro cinco seis siete ocho nueve diez
ver tener decir dar saber querer llegar pasar deber poner volver creer
llevar dejar seguir encontrar llamar venir pensar salir conocer vivir
tipo digamos momento bueno pues vale verdad vamos entonces mira claro
cosa cosas forma manera parte vez veces tiempo punto hecho idea caso
demás estas estos aquella aquel aquellas aquellos porque además según
aunque mientras tanto hacia mediante cualquier sido estar siendo estado
estaba estaban esté estén poder podemos pueden podría podido
haber había habían hay hemos tenemos tienen tenía tenían
incluso aunque sino embargo cuanto cuantos cuántos siendo
""".split())

def extract_key_concepts(text, title='', n_concepts=6, n_quotes=3, n_tips=4):
    """Extract key concepts, quotes and tips from transcription text."""
    sentences = re.split(r'[.\n]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    # Word frequency (TF)
    words = re.findall(r'[a-záéíóúñü]{4,}', text.lower())
    word_freq = Counter(w for w in words if w not in STOPWORDS)
    top_words = [w for w, _ in word_freq.most_common(30)]

    # Score sentences by keyword density
    scored = []
    for sent in sentences:
        sent_lower = sent.lower()
        score = sum(1 for w in top_words[:15] if w in sent_lower)
        if any(kw in sent_lower for kw in ['importante', 'clave', 'fundamental', 'esencial', 'básico']):
            score += 3
        if any(kw in sent_lower for kw in ['consejo', 'truco', 'tip', 'recomiendo', 'sugiero']):
            score += 2
        if any(kw in sent_lower for kw in ['nunca', 'siempre', 'error', 'problema', 'cuidado']):
            score += 2
        if any(kw in sent_lower for kw in ['técnica', 'método', 'ejercicio', 'práctica', 'estudiar']):
            score += 1
        if len(sent) > 300:
            score -= 1
        scored.append((sent, score))

    scored.sort(key=lambda x: -x[1])

    # Key concepts (top scored unique sentences, shortened)
    concepts = []
    seen_starts = set()
    for sent, score in scored:
        start = sent[:30].lower()
        if start not in seen_starts and score > 0:
            seen_starts.add(start)
            if len(sent) > 120:
                sent = sent[:117] + '...'
            concepts.append(sent)
            if len(concepts) >= n_concepts:
                break

    # Tips - sentences with advice patterns
    tips = []
    tip_patterns = ['hay que', 'debemos', 'debes', 'tienes que', 'es importante',
                    'recomiendo', 'consejo', 'intenta', 'practica', 'no hagas',
                    'evita', 'asegúrate', 'recuerda', 'clave es']
    for sent, _ in scored:
        if any(p in sent.lower() for p in tip_patterns) and sent not in concepts:
            if len(sent) > 100:
                sent = sent[:97] + '...'
            tips.append(sent)
            if len(tips) >= n_tips:
                break

    # Quotes - longer, meaningful sentences
    quotes = []
    for sent, score in scored:
        if 40 < len(sent) < 200 and sent not in concepts and sent not in tips:
            quotes.append(sent)
            if len(quotes) >= n_quotes:
                break

    # Main themes from top words
    themes = top_words[:8]

    return {
        'concepts': concepts,
        'tips': tips,
        'quotes': quotes,
        'themes': themes,
        'top_words': top_words[:20]
    }


def draw_rounded_rect(c, x, y, w, h, r, fill=None, stroke=None, stroke_width=1):
    """Draw a rounded rectangle."""
    p = c.beginPath()
    p.moveTo(x + r, y)
    p.lineTo(x + w - r, y)
    p.arcTo(x + w - r, y, x + w, y + r, r)
    p.lineTo(x + w, y + h - r)
    p.arcTo(x + w, y + h - r, x + w - r, y + h, r)
    p.lineTo(x + r, y + h)
    p.arcTo(x + r, y + h, x, y + h - r, r)
    p.lineTo(x, y + r)
    p.arcTo(x, y + r, x + r, y, r)
    p.close()
    if fill:
        c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(stroke_width)
    if fill and stroke:
        c.drawPath(p, fill=1, stroke=1)
    elif fill:
        c.drawPath(p, fill=1, stroke=0)
    elif stroke:
        c.drawPath(p, fill=0, stroke=1)


def draw_bubble(c, x, y, w, h, text, color, font_size=9):
    """Draw a concept bubble with text."""
    # Shadow
    draw_rounded_rect(c, x+2, y-2, w, h, 8, fill=HexColor('#00000033'))
    # Bubble
    draw_rounded_rect(c, x, y, w, h, 8, fill=color, stroke=HexColor('#ffffff22'), stroke_width=0.5)
    # Text
    c.setFillColor(white)
    c.setFont('DejaVu', font_size)
    lines = simpleSplit(text, 'DejaVu', font_size, w - 16)
    ty = y + h - 14
    for line in lines[:int(h/14)]:
        c.drawString(x + 8, ty, line)
        ty -= font_size + 3


def draw_icon_circle(c, x, y, r, emoji_text, bg_color):
    """Draw a circle with centered text (icon)."""
    c.setFillColor(bg_color)
    c.circle(x, y, r, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont('DejaVu-Bold', r * 0.9)
    c.drawCentredString(x, y - r * 0.3, emoji_text)


def draw_arrow(c, x1, y1, x2, y2, color=GOLD):
    """Draw a decorative arrow."""
    c.setStrokeColor(color)
    c.setLineWidth(1.5)
    c.setDash([4, 3])
    c.line(x1, y1, x2, y2)
    c.setDash([])
    # Arrowhead
    angle = math.atan2(y2 - y1, x2 - x1)
    c.setFillColor(color)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2 - 8 * math.cos(angle - 0.4), y2 - 8 * math.sin(angle - 0.4))
    p.lineTo(x2 - 8 * math.cos(angle + 0.4), y2 - 8 * math.sin(angle + 0.4))
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def draw_sketchnote_page(c, title, duration, words, vid_id, data):
    """Draw the sketchnote summary page."""
    margin = 30
    usable_w = W - 2 * margin

    # Background
    c.setFillColor(DARK_BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Decorative top stripe
    c.setFillColor(GOLD_DARK)
    c.rect(0, H - 6, W, 6, fill=1, stroke=0)

    # Title banner
    banner_h = 70
    banner_y = H - margin - banner_h - 10
    draw_rounded_rect(c, margin, banner_y, usable_w, banner_h, 12,
                       fill=HexColor('#0f0c29'), stroke=GOLD, stroke_width=2)

    # "SKETCHNOTE" label
    c.setFillColor(GOLD)
    c.setFont('DejaVu-Bold', 8)
    c.drawString(margin + 12, banner_y + banner_h - 15, 'SKETCHNOTE')

    # Video title
    c.setFillColor(GOLD_LIGHT)
    c.setFont('DejaVu-Bold', 14)
    title_lines = simpleSplit(title, 'DejaVu-Bold', 14, usable_w - 24)
    ty = banner_y + banner_h - 32
    for line in title_lines[:2]:
        c.drawString(margin + 12, ty, line)
        ty -= 18

    # Meta info bar
    meta_y = banner_y - 22
    c.setFillColor(MID_GRAY)
    c.setFont('DejaVu', 8)
    meta = f"Durada: {duration}  |  {words:,} paraules  |  youtube.com/watch?v={vid_id}"
    c.drawString(margin + 4, meta_y, meta.replace(',', '.'))

    # Decorative line
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.5)
    c.setDash([2, 4])
    c.line(margin, meta_y - 8, W - margin, meta_y - 8)
    c.setDash([])

    concepts = data['concepts']
    tips = data['tips']
    quotes = data['quotes']
    themes = data['themes']

    # Layout zones
    content_top = meta_y - 20
    left_x = margin
    right_x = W / 2 + 10
    col_w = usable_w / 2 - 15

    # ============ LEFT COLUMN: KEY CONCEPTS ============
    cy = content_top

    # Section header: IDEAS CLAU
    c.setFillColor(GOLD)
    c.setFont('DejaVu-Bold', 11)
    c.drawString(left_x + 4, cy, '✨ IDEAS CLAU')
    cy -= 8

    # Concept bubbles
    for i, concept in enumerate(concepts[:5]):
        color = BUBBLE_COLORS[i % len(BUBBLE_COLORS)]
        bubble_h = max(36, min(60, 12 + len(concept) // 3))
        cy -= bubble_h + 8
        draw_bubble(c, left_x, cy, col_w, bubble_h, concept, color, font_size=8)

        # Number badge
        c.setFillColor(ACCENT_COLORS[i % len(ACCENT_COLORS)])
        c.circle(left_x + 12, cy + bubble_h - 6, 9, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont('DejaVu-Bold', 9)
        c.drawCentredString(left_x + 12, cy + bubble_h - 9, str(i + 1))

    # ============ RIGHT COLUMN: TIPS + QUOTES ============
    ry = content_top

    if tips:
        # Section header: CONSELLS
        c.setFillColor(HexColor('#66bb6a'))
        c.setFont('DejaVu-Bold', 11)
        c.drawString(right_x + 4, ry, '✅ CONSELLS PRÀCTICS')
        ry -= 12

        for i, tip in enumerate(tips[:4]):
            tip_lines = simpleSplit(tip, 'DejaVu', 8, col_w - 30)
            tip_h = max(24, len(tip_lines) * 12 + 10)
            ry -= tip_h + 6

            # Tip box with left accent
            draw_rounded_rect(c, right_x, ry, col_w, tip_h, 6,
                               fill=HexColor('#1e3a1e'), stroke=HexColor('#66bb6a55'), stroke_width=0.5)
            c.setFillColor(HexColor('#66bb6a'))
            c.rect(right_x, ry, 4, tip_h, fill=1, stroke=0)

            # Checkmark
            c.setFont('DejaVu-Bold', 9)
            c.drawString(right_x + 10, ry + tip_h - 13, '▶')

            # Text
            c.setFillColor(SOFT_WHITE)
            c.setFont('DejaVu', 8)
            tty = ry + tip_h - 14
            for line in tip_lines[:3]:
                c.drawString(right_x + 22, tty, line)
                tty -= 12

    if quotes:
        ry -= 16
        # Section header: CITES
        c.setFillColor(HexColor('#ab47bc'))
        c.setFont('DejaVu-Bold', 11)
        c.drawString(right_x + 4, ry, '“ CITES DESTACADES')
        ry -= 12

        for i, quote in enumerate(quotes[:2]):
            q_lines = simpleSplit(quote, 'DejaVu-Oblique', 8, col_w - 24)
            q_h = max(30, len(q_lines) * 12 + 14)
            ry -= q_h + 6

            draw_rounded_rect(c, right_x, ry, col_w, q_h, 6,
                               fill=HexColor('#2a1a3a'), stroke=HexColor('#ab47bc44'), stroke_width=0.5)

            c.setFillColor(HexColor('#ab47bc'))
            c.setFont('DejaVu-Bold', 16)
            c.drawString(right_x + 8, ry + q_h - 16, '“')

            c.setFillColor(HexColor('#d4a0e8'))
            c.setFont('DejaVu-Oblique', 8)
            qty = ry + q_h - 16
            for line in q_lines[:3]:
                c.drawString(right_x + 22, qty, line)
                qty -= 12

    # ============ BOTTOM: THEMES BAR ============
    themes_y = 60
    # Background bar
    draw_rounded_rect(c, margin, themes_y, usable_w, 44, 10,
                       fill=HexColor('#0f0c29'), stroke=HexColor('#ffffff15'), stroke_width=0.5)

    c.setFillColor(GOLD)
    c.setFont('DejaVu-Bold', 8)
    c.drawString(margin + 12, themes_y + 30, 'TEMES PRINCIPALS:')

    # Theme pills
    tx = margin + 12
    c.setFont('DejaVu', 8)
    for i, theme in enumerate(themes[:8]):
        pill_w = c.stringWidth(theme, 'DejaVu', 8) + 16
        if tx + pill_w > W - margin - 12:
            break
        color = ACCENT_COLORS[i % len(ACCENT_COLORS)]
        draw_rounded_rect(c, tx, themes_y + 6, pill_w, 18, 9, fill=color)
        c.setFillColor(white)
        c.setFont('DejaVu', 8)
        c.drawString(tx + 8, themes_y + 11, theme)
        tx += pill_w + 6

    # Decorative connectors between columns
    if concepts and tips:
        mid_x = W / 2 - 2
        c.setStrokeColor(HexColor('#ffffff15'))
        c.setLineWidth(0.5)
        c.setDash([3, 6])
        c.line(mid_x, content_top - 5, mid_x, themes_y + 50)
        c.setDash([])

    # Footer
    c.setFillColor(HexColor('#333355'))
    c.setFont('DejaVu', 6)
    c.drawString(margin, 30, 'Piano Teacher · Raquel García Piano · Sketchnote generat automàticament')
    c.drawRightString(W - margin, 30, f'youtube.com/watch?v={vid_id}')

    # Gold bottom stripe
    c.setFillColor(GOLD_DARK)
    c.rect(0, 0, W, 4, fill=1, stroke=0)


def draw_transcription_pages(c, title, text, duration, words, vid_id):
    """Draw formatted transcription pages."""
    margin = 50
    usable_w = W - 2 * margin
    line_height = 13
    font_size = 9.5
    header_h = 70

    paragraphs = text.split('\n')
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    # Prepare all lines
    all_lines = []
    for para in paragraphs:
        lines = simpleSplit(para, 'DejaVu', font_size, usable_w)
        all_lines.extend(lines)
        all_lines.append('')  # paragraph break

    page_num = 1
    line_idx = 0
    lines_per_page_first = int((H - margin - header_h - 40 - margin) / line_height)
    lines_per_page = int((H - margin - 40 - margin) / line_height)

    while line_idx < len(all_lines):
        c.showPage()

        # White background for readability
        c.setFillColor(white)
        c.rect(0, 0, W, H, fill=1, stroke=0)

        if page_num == 1:
            # Header on first transcription page
            c.setFillColor(DARK_BG)
            c.rect(0, H - header_h - 10, W, header_h + 10, fill=1, stroke=0)
            c.setFillColor(GOLD_DARK)
            c.rect(0, H - header_h - 10, W, 3, fill=1, stroke=0)

            c.setFillColor(GOLD)
            c.setFont('DejaVu-Bold', 7)
            c.drawString(margin, H - 22, 'TRANSCRIPCIÓ COMPLETA')

            c.setFillColor(white)
            c.setFont('DejaVu-Bold', 12)
            t_lines = simpleSplit(title, 'DejaVu-Bold', 12, usable_w)
            ty = H - 40
            for tl in t_lines[:2]:
                c.drawString(margin, ty, tl)
                ty -= 16

            c.setFillColor(GOLD_LIGHT)
            c.setFont('DejaVu', 8)
            c.drawString(margin, H - header_h - 2, f'{duration}  ·  {words:,} paraules  ·  Raquel García Piano'.replace(',', '.'))

            y_start = H - header_h - 30
            max_lines = lines_per_page_first
        else:
            # Simple header on continuation pages
            c.setFillColor(LIGHT_GRAY)
            c.rect(0, H - 28, W, 28, fill=1, stroke=0)
            c.setFillColor(MID_GRAY)
            c.setFont('DejaVu', 7)
            short_title = title[:60] + ('...' if len(title) > 60 else '')
            c.drawString(margin, H - 20, short_title)
            c.drawRightString(W - margin, H - 20, f'Pàgina {page_num + 1}')

            y_start = H - 50
            max_lines = lines_per_page

        # Draw text lines
        c.setFillColor(HexColor('#222222'))
        c.setFont('DejaVu', font_size)
        y = y_start
        count = 0
        while line_idx < len(all_lines) and count < max_lines:
            line = all_lines[line_idx]
            if line == '':
                y -= line_height * 0.6
            else:
                c.drawString(margin, y, line)
                y -= line_height
            line_idx += 1
            count += 1

        # Footer
        c.setStrokeColor(LIGHT_GRAY)
        c.setLineWidth(0.5)
        c.line(margin, margin - 10, W - margin, margin - 10)
        c.setFillColor(MID_GRAY)
        c.setFont('DejaVu', 6)
        c.drawString(margin, margin - 22, 'Piano Teacher · Raquel García Piano')
        c.drawRightString(W - margin, margin - 22, f'Pàg. {page_num + 1}')

        page_num += 1


def generate_pdf(vid_id, title, duration, text):
    """Generate complete PDF for a video."""
    words = len(text.split())
    data = extract_key_concepts(text, title)

    pdf_path = os.path.join(OUT, f'{vid_id}.pdf')
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setTitle(title)
    c.setAuthor('Piano Teacher - Raquel García Piano')
    c.setSubject(f'Sketchnote + Transcripció: {title}')

    # Page 1: Sketchnote
    draw_sketchnote_page(c, title, duration, words, vid_id, data)

    # Pages 2+: Formatted transcription
    draw_transcription_pages(c, title, text, duration, words, vid_id)

    c.save()
    return pdf_path


def main():
    # Load index for metadata
    with open(os.path.join(DIR, 'index.json'), encoding='utf-8') as f:
        index = json.load(f)

    # Build video lookup
    all_videos = {}
    for cat in index['categories']:
        for v in cat['videos']:
            all_videos[v['id']] = v

    total = len(all_videos)
    done = 0
    errors = 0

    print(f'Generant {total} PDFs amb sketchnotes...')
    print()

    for vid_id, info in sorted(all_videos.items(), key=lambda x: x[1]['title']):
        done += 1
        txt_path = os.path.join(DIR, vid_id + '.txt')
        if not os.path.exists(txt_path):
            print(f'[{done}/{total}] SKIP (no .txt): {vid_id}')
            continue

        with open(txt_path, encoding='utf-8') as f:
            text = f.read()

        if len(text.strip()) < 50:
            print(f'[{done}/{total}] SKIP (text massa curt): {vid_id}')
            continue

        try:
            title = info['title']
            duration = info.get('duration', '?')
            pdf_path = generate_pdf(vid_id, title, duration, text)
            size_kb = os.path.getsize(pdf_path) / 1024
            print(f'[{done}/{total}] OK: {title[:60]}  ({size_kb:.0f}KB)')
            sys.stdout.flush()
        except Exception as e:
            errors += 1
            print(f'[{done}/{total}] ERROR: {vid_id} - {e}')
            import traceback
            traceback.print_exc()
            sys.stdout.flush()

    print(f'\n=== COMPLETAT ===')
    print(f'PDFs generats: {done - errors}/{total}')
    print(f'Errors: {errors}')
    print(f'Directori: {OUT}')
    total_size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.endswith('.pdf'))
    print(f'Mida total: {total_size/(1024*1024):.1f}MB')


if __name__ == '__main__':
    main()
