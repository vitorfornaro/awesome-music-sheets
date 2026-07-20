#!/usr/bin/env python3
"""
qa_notecount — CHECAGEM INDEPENDENTE de contagem de notas por compasso.

Motivação: erros como "1a colcheia virou semínima e a nota final some" (Asa Branca
c10-c13) mantêm o compasso somando 4/4, então passam batido em "fecha na fórmula?"
e na comparação visual em miniatura. Esta checagem conta as CABEÇAS DE NOTA
direto dos glifos SMuFL do PDF, por compasso, e compara com o nº de notas no
spec.json. Divergência = bandeira vermelha (nota faltante/sobrando), independente
de a duração fechar.

NÃO usa a lógica de duração/autoclose do extrator (que é onde o bug nasce) — conta
os glifos crus e a segmentação por barras, igual o vector_extract segmenta.

Uso:
  python3 tools/qa_notecount.py songs/Asa_Branca          # 1 música
  python3 tools/qa_notecount.py --all                     # todas do songs.json
  python3 tools/qa_notecount.py --repertorio "Menq (junino)"
Saída: por música, os compassos onde a contagem PDF != spec (com os dois números).
Sai com código !=0 se achar qualquer divergência (útil pra gate de QA).
"""
import argparse, os, sys, json, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import fitz
from vector_extract import collect, systems_from_lines, NOTEHEADS, RESTS


def pdf_heads_per_measure(pdf):
    """Retorna lista paralela aos compassos: nº de cabeças de nota por compasso.
    Replica a segmentação por barras do vector_extract.extract (mesma ordem de
    compassos: por página, por sistema, esq->dir, pulando segmentos sem glifo)."""
    doc = fitz.open(pdf)
    out = []
    for pno in range(len(doc)):
        pg = doc[pno]
        glyphs, horiz, vert, beams, slurs = collect(pg)
        all_sys = systems_from_lines(horiz)
        centers = [(s[0] + s[-1]) / 2 for s in all_sys]
        def nearest_sys(y):
            return min(range(len(centers)), key=lambda i: abs(y - centers[i]))
        for sidx, lines in enumerate(all_sys):
            top, bot = lines[0], lines[-1]
            band = lambda g: nearest_sys(g["y"]) == sidx and top - 45 < g["y"] < bot + 45
            heads = [g for g in glyphs if g["cp"] in NOTEHEADS and band(g)]
            rests = [g for g in glyphs if g["cp"] in RESTS and band(g)]
            xs_all = [g["x"] for g in heads + rests]
            if not xs_all:
                continue
            left, right = min(xs_all) - 8, max(xs_all) + 8
            sh = bot - top
            def is_stem(v):
                for h in heads:
                    if abs(h["x"] - v["x"]) < 7 and (v["y0"] - 4 <= h["y"] <= v["y0"] + 9 or v["y1"] - 9 <= h["y"] <= v["y1"] + 4):
                        return True
                return False
            bars = sorted([v["x"] for v in vert
                           if v["y0"] <= top + 4 and v["y1"] >= bot - 4 and v["h"] >= sh * 0.95
                           and left < v["x"] < right + 40 and not is_stem(v)])
            mb = []
            for x in bars:
                if mb and x - mb[-1] < 12:
                    continue
                mb.append(x)
            bnds = [left] + mb + [right + 50]
            for j in range(len(bnds) - 1):
                lo, hi = bnds[j], bnds[j + 1]
                mh = [h for h in heads if lo <= h["x"] < hi]
                mr = [r for r in rests if lo <= r["x"] < hi]
                if not mh and not mr:
                    continue  # segmento sem glifo (borda/barra falsa) — igual ao extract
                out.append(len(mh))
    return out


def spec_notes_per_measure(spec_path):
    s = json.load(open(spec_path, encoding='utf-8'))
    return [sum(1 for t in m if not t.split(':')[0].startswith('R')) for m in s['measures']]


def check_song(sdir):
    slug = os.path.basename(sdir.rstrip('/'))
    pdf = os.path.join(sdir, 'source.pdf')
    spec = os.path.join(sdir, 'spec.json')
    if not (os.path.exists(pdf) and os.path.exists(spec)):
        return None
    pdf_counts = pdf_heads_per_measure(pdf)
    spec_counts = spec_notes_per_measure(spec)
    n = min(len(pdf_counts), len(spec_counts))
    problems = []
    for i in range(n):
        if pdf_counts[i] != spec_counts[i]:
            problems.append((i + 1, pdf_counts[i], spec_counts[i]))
    lendiff = len(pdf_counts) - len(spec_counts)
    return {"slug": slug, "pdf_measures": len(pdf_counts), "spec_measures": len(spec_counts),
            "lendiff": lendiff, "problems": problems}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('song', nargs='?', help='pasta da música (songs/<slug>)')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--repertorio', default=None)
    a = ap.parse_args()

    dirs = []
    if a.song:
        dirs = [a.song]
    else:
        S = json.load(open(os.path.join(ROOT, 'songs.json'), encoding='utf-8'))
        for s in S:
            if a.repertorio and s.get('repertorio') != a.repertorio:
                continue
            sl = s.get('slug')
            if sl:
                dirs.append(os.path.join(ROOT, 'songs', sl))

    any_problem = False
    for d in dirs:
        r = check_song(d if os.path.isabs(d) else os.path.join(ROOT, d))
        if r is None:
            continue
        tag = ""
        if r["lendiff"] != 0:
            tag = f"  [!! nº de compassos difere: PDF={r['pdf_measures']} spec={r['spec_measures']}]"
        if r["problems"] or r["lendiff"] != 0:
            any_problem = True
            print(f"\n⚠ {r['slug']}{tag}")
            for c, pc, sc in r["problems"]:
                flag = "faltando no spec" if pc > sc else "sobrando no spec"
                print(f"   c{c}: PDF tem {pc} notas, spec tem {sc}  ({abs(pc-sc)} {flag})")
        else:
            print(f"✓ {r['slug']}  ({r['spec_measures']} compassos, contagem bate)")
    sys.exit(1 if any_problem else 0)


if __name__ == '__main__':
    main()
