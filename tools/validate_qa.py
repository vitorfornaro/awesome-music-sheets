#!/usr/bin/env python3
"""
validate_qa — QA de uma partitura transcrita.

Checks:
  [RITMO]   cada compasso fecha na fórmula de compasso            (TRAVA)
  [SYNC]    IDs de nota do SVG == IDs do timemap (verovio)        (TRAVA)
            e duração do MP3 ≈ duração do MIDI                    (aviso se > tolerância)
  [ALCANCE] notas dentro do alcance escrito do sax alto (Bb3..G6) (aviso)
  [VISUAL]  gera imagem PDF-original x transcrição p/ revisão     (sempre)

Uso:
  python3 validate_qa.py --mxml song.musicxml --mp3 song_sax.mp3 \
        --pdf original.pdf --bpm 112 --out qa_out/ [--title "Nome"]

Sai com código 0 se os checks que TRAVAM passarem; !=0 se algum travar.
"""
import argparse, os, sys, subprocess, json

# alto sax written range (concert transposition ignored — lemos o escrito)
SAX_LO, SAX_HI = 58, 91   # Bb3 .. G6 (MIDI)

def check_rhythm(mxml):
    from music21 import converter
    s = converter.parse(mxml)
    part = s.parts[0]
    bad = []
    for m in part.getElementsByClass('Measure'):
        ts = m.timeSignature or part.recurse().getElementsByClass('TimeSignature').first()
        target = ts.barDuration.quarterLength if ts else 4.0
        dur = sum(n.quarterLength for n in m.notesAndRests)
        if abs(dur - target) > 1e-6:
            bad.append((m.number, dur, target))
    return bad

def check_range(mxml):
    from music21 import converter
    s = converter.parse(mxml)
    out = []
    for n in s.parts[0].recurse().notes:
        for p in (n.pitches if hasattr(n, 'pitches') else [n.pitch]):
            if not (SAX_LO <= p.midi <= SAX_HI):
                out.append((getattr(n, 'measureNumber', '?'), str(p), p.midi))
    return out

def mp3_duration(mp3):
    try:
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                            '-of', 'default=nk=1:nw=1', mp3], capture_output=True, text=True)
        return float(r.stdout.strip())
    except Exception:
        return None

def midi_duration(mxml, bpm, out_dir):
    from music21 import converter
    midi = os.path.join(out_dir, '_qa.mid')
    converter.parse(mxml).write('midi', fp=midi)
    import pretty_midi
    return pretty_midi.PrettyMIDI(midi).get_end_time()

def check_sync(mxml, mp3, bpm, out_dir):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import saxlib
    svg, notes, _midi = saxlib.render_svg_timemap(mxml, bpm)
    missing = [i for i in notes if f'id="{i}"' not in svg]
    md = None
    ad = mp3_duration(mp3)
    tm_end = max((w[1] for wins in notes.values() for w in wins), default=0)/1000.0
    return {"note_ids": len(notes), "missing_ids": len(missing),
            "midi_dur": round(tm_end, 2),
            "mp3_dur": round(ad, 2) if ad else None,
            "timemap_end": round(tm_end, 2),
            "dur_diff": round(abs(tm_end-(ad or 0)), 2) if ad else None}

def visual_diff(mxml, pdf, bpm, out_dir, title=''):
    import verovio, cairosvg
    from PIL import Image, ImageDraw, ImageFont
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # render transcription
    tk = verovio.toolkit()
    tk.setOptions({"pageWidth": 2600, "pageHeight": 16000, "scale": 40, "adjustPageHeight": True,
                   "breaks": "auto", "footer": "none", "header": "none", "font": "Leipzig"})
    import saxlib; saxlib.inject_tempo(mxml, bpm)
    tk.loadFile(mxml); tk.redoLayout()
    mine_png = os.path.join(out_dir, '_mine.png')
    cairosvg.svg2png(bytestring=tk.renderToSVG(1).encode(), write_to=mine_png,
                     output_width=1500, background_color='white')
    # render pdf pages
    base = os.path.join(out_dir, '_orig')
    subprocess.run(['pdftoppm', '-r', '150', '-png', pdf, base], check=True)
    pages = sorted([f for f in os.listdir(out_dir) if f.startswith('_orig') and f.endswith('.png')])
    imgs = [Image.open(os.path.join(out_dir, p)).convert('RGB') for p in pages]
    mine = Image.open(mine_png).convert('RGB')
    W = 1500
    def fit(im):
        r = W/im.width; return im.resize((W, int(im.height*r)))
    imgs = [fit(i) for i in imgs]; mine = fit(mine)
    lh = 46
    total_h = lh + sum(i.height for i in imgs) + lh + mine.height + 30
    canvas = Image.new('RGB', (W, total_h), 'white'); d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
    except Exception:
        font = ImageFont.load_default()
    y = 0
    d.text((16, 8), f"PDF ORIGINAL — {title}", fill=(180, 20, 40), font=font); y = lh
    for im in imgs:
        canvas.paste(im, (0, y)); y += im.height
    d.text((16, y+8), "MINHA TRANSCRICAO (o que o player toca)", fill=(180, 20, 40), font=font); y += lh
    canvas.paste(mine, (0, y))
    out = os.path.join(out_dir, 'qa_comparacao.png')
    canvas.save(out)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mxml', required=True); ap.add_argument('--mp3', required=True)
    ap.add_argument('--pdf', required=True); ap.add_argument('--bpm', type=float, required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--title', default='')
    ap.add_argument('--dur-tol', type=float, default=1.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    report = {"blocking_ok": True, "warnings": []}

    bad = check_rhythm(a.mxml)
    report["rhythm_bad_measures"] = bad
    if bad:
        report["blocking_ok"] = False

    sync = check_sync(a.mxml, a.mp3, a.bpm, a.out)
    report["sync"] = sync
    if sync["missing_ids"] > 0:
        report["blocking_ok"] = False
    if sync["dur_diff"] is not None and sync["dur_diff"] > a.dur_tol:
        report["warnings"].append(f"MP3 x MIDI diferem {sync['dur_diff']}s")

    rng = check_range(a.mxml)
    report["out_of_range"] = rng
    if rng:
        report["warnings"].append(f"{len(rng)} nota(s) fora do alcance típico do sax alto")

    report["visual"] = visual_diff(a.mxml, a.pdf, a.bpm, a.out, a.title)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("\n=== QA ===")
    print(f"[RITMO ] {'OK' if not bad else 'FALHOU: '+str(bad)}")
    print(f"[SYNC  ] IDs {sync['note_ids']} / faltando {sync['missing_ids']} | "
          f"MP3 {sync['mp3_dur']}s vs MIDI {sync['midi_dur']}s")
    print(f"[ALCANCE] {'OK' if not rng else str(len(rng))+' fora do alcance'}")
    print(f"[VISUAL ] {report['visual']}")
    print(f"\nPUBLICAR? {'SIM (checks essenciais OK)' if report['blocking_ok'] else 'NAO — corrija o que travou'}")
    sys.exit(0 if report["blocking_ok"] else 2)

if __name__ == '__main__':
    main()
