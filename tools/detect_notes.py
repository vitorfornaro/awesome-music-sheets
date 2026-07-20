#!/usr/bin/env python3
"""
detect_notes — assistente de alturas por visão computacional.

Detecta as pautas, cabeças de nota (cheias) e barras de compasso de cada
página (300 dpi) e imprime as alturas ESCRITAS por compasso, aplicando a
armadura. Serve de apoio à transcrição (o ritmo você lê nos recortes de
render_pages). Não detecta bem cabeças abertas (mínimas/semibreves).

Uso: python3 detect_notes.py <out_dir_do_render_pages> --sharps 4
     (use --flats N para bemóis)
"""
import argparse, os, glob
import numpy as np

DIA = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

def acc_map(sharps, flats):
    if sharps:
        order = ['F', 'C', 'G', 'D', 'A', 'E', 'B']
        return {n: '#' for n in order[:sharps]}
    if flats:
        order = ['B', 'E', 'A', 'D', 'G', 'C', 'F']
        return {n: '-' for n in order[:flats]}
    return {}

def pitch_from(cy, lines, accs):
    ytop = lines[0]; half = (lines[-1]-lines[0])/8.0
    steps = round((ytop-cy)/half); base = 5*7+DIA.index('F'); idx = base+steps
    name = DIA[idx % 7]; a = accs.get(name, '')
    return f"{name}{a}{idx//7}"

def staff_rows(im, W):
    bw = (im < 128).astype(np.uint8); rs = bw.sum(axis=1); th = 0.4*W
    lines = [y for y in range(im.shape[0]) if rs[y] > th]
    g = []; cur = [lines[0]] if lines else []
    for y in lines[1:]:
        if y-cur[-1] <= 3: cur.append(y)
        else: g.append(int(np.mean(cur))); cur = [y]
    if cur: g.append(int(np.mean(cur)))
    return g

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out_dir')
    ap.add_argument('--sharps', type=int, default=0)
    ap.add_argument('--flats', type=int, default=0)
    a = ap.parse_args()
    import cv2
    accs = acc_map(a.sharps, a.flats)
    for pg in sorted(glob.glob(os.path.join(a.out_dir, 'page*.png'))):
        im = cv2.imread(pg, cv2.IMREAD_GRAYSCALE); H, W = im.shape
        bw = (im < 128).astype(np.uint8)
        rows = staff_rows(im, W); systems = [rows[i:i+5] for i in range(0, len(rows), 5)]
        filled = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 13)))
        n, lab, st, ct = cv2.connectedComponentsWithStats(filled, 8)
        heads = [(ct[i][0], ct[i][1]) for i in range(1, n)
                 if 120 < st[i][4] < 650 and 12 <= st[i][2] <= 32 and 10 <= st[i][3] <= 27]
        def bars(lines):
            y0, y1 = lines[0]-2, lines[-1]+2; col = (im[y0:y1, :] < 128).sum(axis=0)
            hc = col >= (y1-y0)*0.85; xs = [x for x in range(W) if hc[x]]
            g = []; cur = [xs[0]] if xs else []
            for x in xs[1:]:
                if x-cur[-1] <= 6: cur.append(x)
                else: g.append(int(np.mean(cur))); cur = [x]
            if cur: g.append(int(np.mean(cur)))
            return [b for b in g if b > 360]
        print(f"\n===== {os.path.basename(pg)} — {len(systems)} sistemas =====")
        for si, lines in enumerate(systems):
            hs = sorted((cx, cy) for cx, cy in heads if lines[0]-95 < cy < lines[-1]+95 and cx > 360)
            bl = bars(lines); edges = [360]+bl+[W]
            print(f"-- sistema {si} (barras x={bl})")
            for j in range(len(edges)-1):
                seq = [pitch_from(y, lines, accs) for x, y in hs if edges[j] < x < edges[j+1]]
                if seq: print(f"   compasso~{j}: {' '.join(seq)}")

if __name__ == '__main__':
    main()
