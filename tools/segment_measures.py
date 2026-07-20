#!/usr/bin/env python3
"""
segment_measures — recorta UMA foto por compasso e dá palpite de alturas.

Detecta pautas + barras de compasso em cada página (300 dpi) e:
  - salva measures/mNNN.png : recorte ampliado de cada compasso (na ordem de leitura)
  - measures.json : lista ordenada {idx, page, system, seg, x0,x1, pitches[], n_heads}
'pitches' é o palpite (cabeças cheias, aplica armadura). Compassos sem cabeça
detectada saem com pitches=[] (pausa / multi-pausa / notas abertas — inspecione a foto).

Uso: python3 segment_measures.py <render_out_dir> --sharps 4   (ou --flats 1)
"""
import argparse, os, glob, json
import numpy as np

DIA = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

def acc_map(sharps, flats):
    if sharps:
        return {n: '#' for n in ['F', 'C', 'G', 'D', 'A', 'E', 'B'][:sharps]}
    if flats:
        return {n: '-' for n in ['B', 'E', 'A', 'D', 'G', 'C', 'F'][:flats]}
    return {}

def pitch_from(cy, lines, accs):
    ytop = lines[0]; half = (lines[-1]-lines[0])/8.0
    steps = round((ytop-cy)/half); base = 5*7+DIA.index('F'); idx = base+steps
    name = DIA[idx % 7]
    return f"{name}{accs.get(name,'')}{idx//7}"

def staff_groups(im, W):
    bw = (im < 128).astype(np.uint8); rs = bw.sum(axis=1); th = 0.4*W
    lines = [y for y in range(im.shape[0]) if rs[y] > th]
    g = []; cur = [lines[0]] if lines else []
    for y in lines[1:]:
        if y-cur[-1] <= 3: cur.append(y)
        else: g.append(int(np.mean(cur))); cur = [y]
    if cur: g.append(int(np.mean(cur)))
    return [g[i:i+5] for i in range(0, len(g), 5)]

def _longest_run(mask):
    best = cur = 0
    for v in mask:
        cur = cur+1 if v else 0
        best = max(best, cur)
    return best

def find_barlines(im, lines, W, heads):
    """Barra = coluna com run vertical CONTÍNUO cobrindo ~toda a altura da pauta,
    e sem cabeça de nota colada (evita confundir com hastes)."""
    y0, y1 = lines[0]-2, lines[-1]+2
    h = y1-y0
    seg = im[y0:y1, :] < 128
    head_x = [cx for cx, cy in heads if lines[0]-95 < cy < lines[-1]+95]
    cols = []
    for x in range(W):
        if seg[:, x].sum() >= h*0.9 and _longest_run(seg[:, x]) >= h*0.9:
            # rejeita se houver cabeça de nota bem colada (haste)
            if not any(abs(x-hx) < 10 for hx in head_x):
                cols.append(x)
    groups = []; cur = [cols[0]] if cols else []
    for x in cols[1:]:
        if x-cur[-1] <= 25: cur.append(x)     # une barras duplas/repetição
        else: groups.append(int(np.mean(cur))); cur = [x]
    if cur: groups.append(int(np.mean(cur)))
    return groups

def staff_extent(im, lines, W):
    # horizontal extent of the staff lines
    y = lines[2]
    row = im[y-1:y+2, :].min(axis=0) < 128
    xs = np.where(row)[0]
    return (int(xs[0]), int(xs[-1])) if len(xs) else (0, W)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('render_dir')
    ap.add_argument('--sharps', type=int, default=0)
    ap.add_argument('--flats', type=int, default=0)
    ap.add_argument('--out', default='measures', help='subpasta de saída dos recortes')
    ap.add_argument('--clef-pad', type=int, default=330,
                    help='px após início da pauta p/ pular clave+armadura no 1o compasso do sistema')
    a = ap.parse_args()
    import cv2
    from PIL import Image
    accs = acc_map(a.sharps, a.flats)
    out_dir = os.path.join(a.render_dir, a.out)
    os.makedirs(out_dir, exist_ok=True)
    for f in glob.glob(os.path.join(out_dir, '*.png')):
        try:
            os.remove(f)
        except OSError:
            pass
    measures = []
    idx = 0
    for pg in sorted(glob.glob(os.path.join(a.render_dir, 'page*.png'))):
        page_no = int(''.join(c for c in os.path.basename(pg) if c.isdigit()) or 1)
        im = cv2.imread(pg, cv2.IMREAD_GRAYSCALE); H, W = im.shape
        bw = (im < 128).astype(np.uint8)
        filled = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 13)))
        n, lab, st, ct = cv2.connectedComponentsWithStats(filled, 8)
        heads = [(ct[i][0], ct[i][1]) for i in range(1, n)
                 if 120 < st[i][4] < 650 and 12 <= st[i][2] <= 32 and 10 <= st[i][3] <= 27]
        pil = Image.open(pg)
        systems = staff_groups(im, W)
        for si, lines in enumerate(systems):
            bl = find_barlines(im, lines, W, heads)
            left, right = staff_extent(im, lines, W)
            content_start = left + a.clef_pad
            # boundaries: content_start + barlines (barlines already include system-end)
            bnds = [content_start] + [b for b in bl if b > content_start]
            for j in range(len(bnds)-1):
                x0, x1 = bnds[j], bnds[j+1]
                if x1-x0 < 40:
                    continue
                idx += 1
                hs = sorted((cx, cy) for cx, cy in heads if x0 < cx < x1 and lines[0]-95 < cy < lines[-1]+95)
                pitches = [pitch_from(cy, lines, accs) for cx, cy in hs]
                # crop with a little vertical + left context
                cy0 = max(0, lines[0]-105); cy1 = min(H, lines[-1]+105)
                crop = pil.crop((max(0, x0-15), cy0, min(W, x1+15), cy1))
                crop = crop.resize((int(crop.width*2.4), int(crop.height*2.4)))
                fn = os.path.join(out_dir, f'm{idx:03d}.png')
                crop.save(fn)
                measures.append({"idx": idx, "page": page_no, "system": si, "seg": j,
                                 "x0": x0, "x1": x1, "pitches": pitches, "n_heads": len(hs),
                                 "crop": os.path.relpath(fn, a.render_dir)})
    json.dump(measures, open(os.path.join(a.render_dir, 'measures.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print(f"{idx} compassos recortados em {out_dir}")
    print("resumo (idx: n_cabeças | palpite):")
    for m in measures:
        print(f"  m{m['idx']:03d}: {m['n_heads']:2d} | {' '.join(m['pitches'])}")

if __name__ == '__main__':
    main()
