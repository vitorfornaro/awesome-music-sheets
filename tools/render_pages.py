#!/usr/bin/env python3
"""
render_pages — prepara imagens de um PDF para leitura/transcrição.

Gera em <out>/:
  page-<n>.png     (300 dpi, para detecção)
  low-<n>.png      (150 dpi, visão geral)
  sys-<n>-<i>.png  (recorte de cada sistema, ampliado, para ler o ritmo)

Uso: python3 render_pages.py <pdf> <out_dir>
"""
import sys, os, subprocess
import numpy as np

def staff_rows(png):
    import cv2
    im = cv2.imread(png, cv2.IMREAD_GRAYSCALE); H, W = im.shape
    bw = (im < 128).astype(np.uint8); rs = bw.sum(axis=1); th = 0.4*W
    lines = [y for y in range(H) if rs[y] > th]
    g = []; cur = [lines[0]] if lines else []
    for y in lines[1:]:
        if y-cur[-1] <= 3: cur.append(y)
        else: g.append(int(np.mean(cur))); cur = [y]
    if cur: g.append(int(np.mean(cur)))
    return g

def main():
    pdf, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    subprocess.run(['pdftoppm', '-r', '300', '-png', pdf, os.path.join(out, 'page')], check=True)
    subprocess.run(['pdftoppm', '-r', '150', '-png', pdf, os.path.join(out, 'low')], check=True)
    from PIL import Image
    pages = sorted(f for f in os.listdir(out) if f.startswith('page') and f.endswith('.png'))
    for pi, pg in enumerate(pages, 1):
        rows = staff_rows(os.path.join(out, pg))
        tops = rows[0::5]
        im = Image.open(os.path.join(out, pg)); W, H = im.size
        for i, t in enumerate(tops):
            y0 = max(0, t-100); y1 = min(H, t+195)
            c = im.crop((80, y0, W-30, y1)); c = c.resize((int(c.width*1.4), int(c.height*1.4)))
            c.save(os.path.join(out, f'sys-{pi}-{i}.png'))
        print(f"page {pi}: {len(tops)} sistemas, staff rows={len(rows)}")
    print("OK ->", out)

if __name__ == '__main__':
    main()
