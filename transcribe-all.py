#!/usr/bin/env python3
import os, json, sys, time

os.environ['LD_LIBRARY_PATH'] = '/home/xroig/.local/lib/python3.12/site-packages/nvidia/cublas/lib:' + os.environ.get('LD_LIBRARY_PATH', '')

DIR = "/home/xroig/piano-teacher/transcriptions"
MODEL = "medium"

print(f"Carregant model Whisper {MODEL} (GPU float16)...")
sys.stdout.flush()

from faster_whisper import WhisperModel
model = WhisperModel(MODEL, device="cuda", compute_type="float16")

print("Model carregat!")
sys.stdout.flush()

mp3s = sorted([f for f in os.listdir(DIR) if f.endswith('.mp3')])
total = len(mp3s)
done = 0
skipped = 0
total_words = 0
t_start = time.time()

print(f"Total fitxers: {total}")
sys.stdout.flush()

for mp3 in mp3s:
    vid_id = mp3.replace('.mp3', '')
    txt_path = os.path.join(DIR, vid_id + '.txt')

    if os.path.exists(txt_path) and os.path.getsize(txt_path) > 0:
        done += 1
        skipped += 1
        total_words += len(open(txt_path).read().split())
        print(f"[{done}/{total}] SKIP: {vid_id}")
        sys.stdout.flush()
        continue

    done += 1
    title = vid_id
    info_path = os.path.join(DIR, vid_id + '.info.json')
    if os.path.exists(info_path):
        try:
            with open(info_path) as f:
                info = json.load(f)
                title = info.get('title', vid_id)
        except:
            pass

    print(f"[{done}/{total}] Transcrivint: {title}")
    sys.stdout.flush()

    t0 = time.time()
    try:
        mp3_path = os.path.join(DIR, mp3)
        segments, info = model.transcribe(mp3_path, language="es", beam_size=5)

        text_lines = []
        for segment in segments:
            text_lines.append(segment.text.strip())

        full_text = "\n".join(text_lines)

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(full_text)

        elapsed = time.time() - t0
        word_count = len(full_text.split())
        total_words += word_count
        print(f"  -> OK ({word_count} paraules, {elapsed:.0f}s)")
        sys.stdout.flush()
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  -> ERROR ({elapsed:.0f}s): {e}")
        sys.stdout.flush()

total_time = time.time() - t_start
print(f"\n=== COMPLETAT ===")
print(f"Transcrits: {done - skipped} nous, {skipped} ja existents, {total} total")
print(f"Total paraules: {total_words}")
print(f"Temps total: {total_time/60:.0f} minuts")
txts = len([f for f in os.listdir(DIR) if f.endswith('.txt')])
print(f"Fitxers .txt: {txts}")
sys.stdout.flush()
