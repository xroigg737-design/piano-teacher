#!/bin/bash
# Transcriu tots els mp3 del canal de Raquel Garcia amb Whisper large
# Genera fitxers .txt amb la transcripció de cada vídeo

DIR="/home/xroig/piano-teacher/transcriptions"
MODEL="large"
LANG="es"
DONE=0
TOTAL=$(ls "$DIR"/*.mp3 2>/dev/null | wc -l)

echo "=== Transcripció Whisper ($MODEL) ==="
echo "Total fitxers: $TOTAL"
echo ""

for mp3 in "$DIR"/*.mp3; do
    id=$(basename "$mp3" .mp3)
    txt="$DIR/${id}.txt"

    if [ -f "$txt" ]; then
        DONE=$((DONE + 1))
        echo "[$DONE/$TOTAL] SKIP (ja transcrit): $id"
        continue
    fi

    DONE=$((DONE + 1))

    # Get title from info.json if available
    title=""
    if [ -f "$DIR/${id}.info.json" ]; then
        title=$(python3 -c "import json; print(json.load(open('$DIR/${id}.info.json'))['title'])" 2>/dev/null)
    fi

    echo "[$DONE/$TOTAL] Transcrivint: $id ${title:+($title)}"

    whisper "$mp3" \
        --model "$MODEL" \
        --language "$LANG" \
        --output_format txt \
        --output_dir "$DIR" \
        2>/dev/null

    if [ -f "$txt" ]; then
        echo "  -> OK ($(wc -w < "$txt") paraules)"
    else
        echo "  -> ERROR transcrivint $id"
    fi
done

echo ""
echo "=== COMPLETAT ==="
echo "Transcrits: $(ls "$DIR"/*.txt 2>/dev/null | wc -l) / $TOTAL"
