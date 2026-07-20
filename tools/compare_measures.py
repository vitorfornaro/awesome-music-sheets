#!/usr/bin/env python3
"""
compare_measures — grade de comparação compasso a compasso: ORIGINAL x TRANSCRIÇÃO.

Para cada compasso, renderiza esse compasso da minha transcrição (verovio) e
coloca ao lado do recorte do PDF original (measures.json do segment_measures).
Gera comparacao/grid_NN.png (várias páginas se necessário).

Uso:
  python3 compare_measures.py --mxml Zero.musicxml --render-dir _work/zero \
     --measures _work/zero/measures.json --out _work/zero/comparacao [--per-page 8]
"""
import argparse, os, json, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))

def render_measure_png(mxml_part_stream, ks, ts, tmpdir, i):
    """Renderiza um único compasso (music21 Measure) em PNG via verovio."""
    from music21 import stream, clef, meter, key, instrument
    import verovio, cairosvg
    sc = stream.Score(); p = stream.Part()
    p.insert(0, clef.TrebleClef()); p.insert(0, key.KeySignature(ks)); p.insert(0, meter.TimeSignature(ts))
    p.append(mxml_part_stream)
    sharp_steps = ['F', 'C', 'G', 'D', 'A', 'E', 'B'][:ks] if ks > 0 else []
    flat_steps = ['B', 'E', 'A', 'D', 'G', 'C', 'F'][:(-ks)] if ks < 0 else []
    for nn in p.recurse().notes:
        for pp in (nn.pitches if hasattr(nn, 'pitches') else [nn.pitch]):
            if pp.accidental is not None:
                if (pp.accidental.name == 'sharp' and pp.step in sharp_steps) or \
                   (pp.accidental.name == 'flat' and pp.step in flat_steps):
                    pp.accidental.displayStatus = False
    sc.append(p)
    xmlpath = os.path.join(tmpdir, f'meas_{i}.xml'); sc.write('musicxml', fp=xmlpath)
    tk = verovio.toolkit()
    tk.setOptions({"pageWidth": 1200, "pageHeight": 500, "scale": 55, "adjustPageHeight": True,
                   "footer": "none", "header": "none", "font": "Leipzig"})
    tk.loadFile(xmlpath); tk.redoLayout()
    png = os.path.join(tmpdir, f'meas_{i}.png')
    cairosvg.svg2png(bytestring=tk.renderToSVG(1).encode(), write_to=png, output_width=760, background_color='white')
    return png

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mxml', required=True); ap.add_argument('--render-dir', required=True)
    ap.add_argument('--measures', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--per-page', type=int, default=8)
    a = ap.parse_args()
    from music21 import converter
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(a.out, exist_ok=True)
    meas = json.load(open(a.measures, encoding='utf-8'))
    sc = converter.parse(a.mxml)
    part = sc.parts[0]
    ks = part.keySignature.sharps if part.keySignature else 0
    ts = part.getTimeSignatures()[0].ratioString if part.getTimeSignatures() else '4/4'
    mm = list(part.getElementsByClass('Measure'))
    n = max(len(meas), len(mm))
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    except Exception:
        font = ImageFont.load_default()
    W = 1600; rowh = 150; header = 30
    tmp = tempfile.mkdtemp()
    rows = []
    for i in range(n):
        orig = None
        if i < len(meas):
            op = os.path.join(a.render_dir, meas[i]['crop'])
            if os.path.exists(op): orig = Image.open(op).convert('RGB')
        mine = None
        if i < len(mm):
            try:
                png = render_measure_png(mm[i], ks, ts, tmp, i)
                mine = Image.open(png).convert('RGB')
            except Exception as e:
                print("render err m", i+1, e)
        row = Image.new('RGB', (W, rowh), 'white'); d = ImageDraw.Draw(row)
        d.text((8, 4), f"compasso {i+1}", fill=(180, 20, 40), font=font)
        half = (W-20)//2
        def place(im, x):
            if im is None: return
            r = min((half)/im.width, (rowh-header-6)/im.height)
            im2 = im.resize((int(im.width*r), int(im.height*r)))
            row.paste(im2, (x, header))
        d.text((10, header-2), "ORIGINAL", fill=(120, 120, 120), font=font)
        d.text((half+20, header-2), "TRANSCRICAO", fill=(120, 120, 120), font=font)
        place(orig, 10); place(mine, half+20)
        d.line([(W//2, header), (W//2, rowh)], fill=(220, 220, 220), width=1)
        rows.append(row)
    # paginate
    pg = a.per_page; pages = (len(rows)+pg-1)//pg
    for pi in range(pages):
        chunk = rows[pi*pg:(pi+1)*pg]
        canvas = Image.new('RGB', (W, rowh*len(chunk)), 'white')
        for r, im in enumerate(chunk):
            canvas.paste(im, (0, r*rowh))
        canvas.save(os.path.join(a.out, f'grid_{pi+1:02d}.png'))
    print(f"{n} compassos comparados -> {a.out} ({pages} página(s))")
    if len(meas) != len(mm):
        print(f"  ATENÇÃO: contagem difere — original={len(meas)} vs transcrição={len(mm)}")

if __name__ == '__main__':
    main()
