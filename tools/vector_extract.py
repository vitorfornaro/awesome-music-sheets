#!/usr/bin/env python3
"""
vector_extract — OMR a partir do VETOR de um PDF de MuseScore (fontes Leland/Bravura).

Extrai glifos SMuFL (cabeças, pausas, pontos, acidentes) + traços (hastes, beams,
barras) e reconstrói, por compasso: altura, duração, acidente, ponto, beam-group.
Muito mais fiel que ler a imagem (pega o desenho do arranjador).

Uso (exploração): python3 vector_extract.py <pdf> --sharps 4 [--page 1]
"""
import argparse, sys, re
import fitz

# SMuFL codepoints
NOTEHEADS = {0xE0A2: 4.0, 0xE0A3: 2.0, 0xE0A4: 1.0}   # whole, half, black(base quarter)
RESTS = {0xE4E3: 4.0, 0xE4E4: 2.0, 0xE4E5: 1.0, 0xE4E6: 0.5, 0xE4E7: 0.25, 0xE4E8: 0.125}
DOT = 0xE1E7
ACC = {0xE260: 'flat', 0xE261: 'natural', 0xE262: 'sharp', 0xE263: 'double-sharp', 0xE264: 'double-flat'}
FLAGS = {0xE240, 0xE241, 0xE242, 0xE243, 0xE244, 0xE245, 0xE246, 0xE247, 0xE248, 0xE249}
DIA = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
EMIT_SLURS = True   # ligaduras reativadas (detecção de posição validada)

def key_accs(sharps):
    if sharps > 0:
        return {n: '#' for n in ['F', 'C', 'G', 'D', 'A', 'E', 'B'][:sharps]}
    if sharps < 0:
        return {n: '-' for n in ['B', 'E', 'A', 'D', 'G', 'C', 'F'][:(-sharps)]}
    return {}

def collect(pg):
    glyphs = []
    d = pg.get_text("rawdict")
    for b in d["blocks"]:
        for l in b.get("lines", []):
            for s in l.get("spans", []):
                fn = s.get("font", "")
                if fn not in ("Leland", "Bravura", "BravuraText", "LelandText"):
                    continue
                for ch in s.get("chars", []):
                    cp = ord(ch["c"]); bb = ch["bbox"]
                    glyphs.append({"cp": cp, "x": (bb[0]+bb[2])/2, "y": (bb[1]+bb[3])/2,
                                   "x0": bb[0], "x1": bb[2], "y0": bb[1], "y1": bb[3]})
    horiz, vert, beams, slurs = [], [], [], []
    for p in pg.get_drawings():
        r = p["rect"]
        has_curve = any(it[0] == "c" for it in p["items"])
        # slur/ligadura = arco CURVO (tem Bézier), largura de nota, longe da clave
        if has_curve and 13 <= r.width <= 120 and 2 <= r.height <= 16 and r.x0 > 70:
            slurs.append({"x0": r.x0, "x1": r.x1, "y": (r.y0+r.y1)/2, "w": r.width})
            continue
        # beam = path preenchido reto (SEM curva), curto e largo
        if p.get("fill") is not None and not has_curve and 1.5 <= r.height <= 9 and 3 <= r.width <= 140:
            beams.append({"x0": r.x0, "x1": r.x1, "y": (r.y0+r.y1)/2, "w": r.width})
            continue
        for it in p["items"]:
            if it[0] != "l":
                continue
            p1, p2 = it[1], it[2]
            if abs(p1.y-p2.y) < 1 and abs(p2.x-p1.x) > 40:   # pauta pode vir quebrada por compasso
                horiz.append((p1.y, min(p1.x, p2.x), max(p1.x, p2.x)))
            elif abs(p1.x-p2.x) < 1.2 and abs(p2.y-p1.y) > 4:
                vert.append({"x": p1.x, "y0": min(p1.y, p2.y), "y1": max(p1.y, p2.y), "h": abs(p2.y-p1.y)})
    return glyphs, horiz, vert, beams, slurs

def systems_from_lines(horiz):
    ys = sorted(y for y, x0, x1 in horiz)
    # 1) dedup linhas coincidentes (mesma linha desenhada em pedaços)
    uniq = []
    for v in ys:
        if uniq and v-uniq[-1][-1] < 2.5:
            uniq[-1].append(v)
        else:
            uniq.append([v])
    lines_all = [round(sum(c)/len(c), 1) for c in uniq]
    # 2) agrupa em pautas: linhas de um staff ficam ~5pt entre si; entre staves há gap grande.
    #    Usa limiar apertado p/ ignorar linhas espúrias (hairpins/ties horizontais entre sistemas).
    groups = []; cur = [lines_all[0]]
    for v in lines_all[1:]:
        if v-cur[-1] < 10:
            cur.append(v)
        else:
            groups.append(cur); cur = [v]
    groups.append(cur)
    # 3) só grupos com ~5 linhas são pautas; descarta linhas espúrias isoladas
    return [g[:5] for g in groups if len(g) >= 5]

_ACC_SYM = {0xE260: '-', 0xE261: 'n', 0xE262: '#', 0xE263: '##', 0xE264: '--'}

def pitch_of(cy, lines, accs, head=None, accgs=None):
    ytop = lines[0]; span = lines[-1]-lines[0]; half = span/8.0
    steps = round((ytop-cy)/half)
    base = 5*7+DIA.index('F'); idx = base+steps
    name = DIA[idx % 7]; octv = idx//7
    # acidente explícito à esquerda da cabeça (sustenido/bemol/bequadro) sobrepõe a armadura
    if head is not None and accgs:
        near = [a for a in accgs if 2 < head["x0"]-a["x"] < 22 and abs(a["y"]-cy) < 6]
        if near:
            sym = _ACC_SYM.get(min(near, key=lambda a: head["x0"]-a["x"])["cp"], '')
            if sym == 'n':      # bequadro cancela a armadura
                return f"{name}{octv}"
            return f"{name}{sym}{octv}"
    return f"{name}{accs.get(name,'')}{octv}"

def note_duration(h, stem, beams, glyphs, dotted):
    dur = NOTEHEADS[h["cp"]]; nb = 0
    if h["cp"] == 0xE0A4 and stem:
        # beams cruzam a haste em qualquer ponto ao longo dela (não só na ponta)
        y_lo, y_hi = stem["y0"]-3, stem["y1"]+3
        # tolerância apertada: o beam precisa realmente cobrir a haste (stub de 16avo não vaza p/ vizinha)
        bh = [b for b in beams if b["x0"]-1.5 <= stem["x"] <= b["x1"]+1.5 and y_lo <= b["y"] <= y_hi]
        # conta níveis de beam empilhados (colcheia=1, semicolcheia=2)
        ys = sorted(b["y"] for b in bh)
        nb = 1 if ys else 0
        for i in range(1, len(ys)):
            if ys[i]-ys[i-1] > 1.5:
                nb += 1
        if nb == 0:
            up = stem["y0"] < h["y"]; bend = stem["y0"] if up else stem["y1"]
            fl = [g for g in glyphs if g["cp"] in FLAGS and abs(g["x"]-stem["x"]) < 13 and abs(g["y"]-bend) < 24]
            if fl: nb = 1
        if nb >= 1:
            dur = 0.5/(2**(nb-1))
    if id(h) in dotted:
        dur *= 1.5
    return dur, nb

def extract(pdf, sharps, debug=False, crops_dir=None):
    accs = key_accs(sharps)
    doc = fitz.open(pdf)
    measures = []
    repeats = []          # paralelo a measures: "", "start", "end" ou "both"
    endings = []          # paralelo a measures: "", "1", "2", ... (casa 1a/2a)
    crops_meta = []
    ZOOM = 3.0
    if crops_dir:
        import os
        os.makedirs(crops_dir, exist_ok=True)
    from fractions import Fraction
    for pno in range(len(doc)):
        pg = doc[pno]
        pix = pg.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM)) if crops_dir else None
        glyphs, horiz, vert, beams, slurs = collect(pg)
        # marcadores de TERCINA: "3" isolado em fonte de texto (Edwin), fora da margem (nº de compasso)
        tuplets3 = []
        for b in pg.get_text("rawdict")["blocks"]:
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    if s.get("font", "").startswith("Edwin"):
                        txt = ''.join(ch['c'] for ch in s.get("chars", []))
                        if txt == "3" and s['bbox'][0] > 75:
                            tuplets3.append(((s['bbox'][0]+s['bbox'][2])/2, (s['bbox'][1]+s['bbox'][3])/2))
        # marcadores de CASA (1a/2a volta): "1."/"2." em Edwin-Bold, acima da pauta
        end_labels = []   # (x_center, y_center, num)
        for b in pg.get_text("rawdict")["blocks"]:
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    if "Bold" in s.get("font", "") and "Edwin" in s.get("font", ""):
                        txt = ''.join(ch['c'] for ch in s.get("chars", [])).strip()
                        mm = re.match(r'^([1-9])\.?$', txt)
                        if mm:
                            end_labels.append(((s['bbox'][0]+s['bbox'][2])/2,
                                               (s['bbox'][1]+s['bbox'][3])/2, int(mm.group(1))))
        all_sys = systems_from_lines(horiz)
        centers = [(s[0]+s[-1])/2 for s in all_sys]
        def nearest_sys(y):
            return min(range(len(centers)), key=lambda i: abs(y-centers[i]))
        for sidx, lines in enumerate(all_sys):
            top, bot = lines[0], lines[-1]
            # nota pertence a ESTE sistema só se for o mais próximo (evita roubar de vizinhos)
            band = lambda g: nearest_sys(g["y"]) == sidx and top-45 < g["y"] < bot+45
            heads = [g for g in glyphs if g["cp"] in NOTEHEADS and band(g)]
            rests = [g for g in glyphs if g["cp"] in RESTS and band(g)]
            dots = [g for g in glyphs if g["cp"] == DOT and band(g)]
            accgs = [g for g in glyphs if g["cp"] in ACC and band(g)]
            # exclui os acidentes da ARMADURA (os |sharps| primeiros antes da 1a nota do sistema)
            if heads:
                fnx = min(hh["x"] for hh in heads)
                presig = sorted([a for a in accgs if a["x"] < fnx], key=lambda a: a["x"])
                ksig = {id(a) for a in presig[:abs(sharps)]}
                accgs = [a for a in accgs if id(a) not in ksig]
            xs_all = [g["x"] for g in heads+rests]
            if not xs_all:
                continue
            left, right = min(xs_all)-8, max(xs_all)+8
            sh = bot-top
            def is_stem(v):
                # haste tem cabeça de nota numa das pontas; barra não
                for h in heads:
                    if abs(h["x"]-v["x"]) < 7 and (v["y0"]-4 <= h["y"] <= v["y0"]+9 or v["y1"]-9 <= h["y"] <= v["y1"]+4):
                        return True
                return False
            bars = sorted([v["x"] for v in vert
                           if v["y0"] <= top+4 and v["y1"] >= bot-4 and v["h"] >= sh*0.95
                           and left < v["x"] < right+40 and not is_stem(v)])
            mb = []
            for x in bars:
                if mb and x-mb[-1] < 12: continue
                mb.append(x)
            bnds = [left] + mb + [right+50]
            # CASAS: colchetes horizontais logo acima deste sistema (y em [top-34, top-2])
            sys_brackets = []   # (x0, x1, num)
            for hy, hx0, hx1 in horiz:
                if top-34 < hy < top-2 and (hx1-hx0) > 15:
                    num = ''
                    for lx, ly, ln in end_labels:
                        if hx0-10 <= lx <= hx0+45 and abs(ly-hy) < 22:
                            num = ln; break
                    sys_brackets.append((hx0, hx1, num))
            # barras de repetição: dots (E044) à direita da barra = início; à esquerda = fim
            rdots = [g["x"] for g in glyphs if g["cp"] == 0xE044 and band(g)]
            def rep_start_at(x):
                return any(1 < rd-x < 17 for rd in rdots)
            def rep_end_at(x):
                return any(1 < x-rd < 17 for rd in rdots)
            # build events
            # cada ponto de aumento pertence a UMA nota (a mais próxima à esquerda)
            dotted = set()
            for d in dots:
                cand = [h for h in heads if 2 < d["x"]-h["x1"] < 22 and abs(d["y"]-h["y"]) < 5]
                if cand:
                    dotted.add(id(min(cand, key=lambda h: d["x"]-h["x1"])))
            evs = []
            for h in heads:
                cands = [v for v in vert if h["x0"]-3 <= v["x"] <= h["x1"]+3 and v["h"] > 6
                         and v["y0"]-12 <= h["y"] <= v["y1"]+12]   # haste no MESMO sistema (casa Y)
                stem = min(cands, key=lambda v: abs(v["x"]-h["x"])) if cands else None
                dur, nb = note_duration(h, stem, beams, glyphs, dotted)
                stemx = stem["x"] if stem else h["x"]
                evs.append({"x": h["x"], "stemx": stemx, "kind": "n",
                            "pitch": pitch_of(h["y"], lines, accs, head=h, accgs=accgs), "dur": dur, "nb": nb})
            for r in rests:
                evs.append({"x": r["x"], "kind": "r", "dur": RESTS[r["cp"]]})
            evs.sort(key=lambda e: e["x"])
            for e in evs:
                e["beam"] = None
                e["slur"] = None
                e["tie"] = None
            # curvas: TIE (mesma altura, notas adjacentes) vs SLUR (fraseado). Liga nota do x0 à do x1.
            notes_only = [e for e in evs if e["kind"] == "n"]
            sys_slurs = [s for s in slurs if nearest_sys(s["y"]) == sidx and top-45 < s["y"] < bot+55]
            for s in sys_slurs:
                if len(notes_only) < 2:
                    break
                st = min(notes_only, key=lambda e: abs(e["x"]-s["x0"]))
                en = min(notes_only, key=lambda e: abs(e["x"]-s["x1"]))
                if st is en or en["x"] <= st["x"]:
                    continue
                between = [e for e in notes_only if st["x"] < e["x"] < en["x"]]
                if st["pitch"] == en["pitch"] and not between:
                    if st["tie"] is None and en["tie"] is None:
                        st["tie"] = "start"; en["tie"] = "stop"
                elif st["slur"] is None and en["slur"] != "start":
                    st["slur"] = "start"; en["slur"] = "stop"
            # assign to measures
            def save_crop(lo, hi):
                if not crops_dir:
                    return None
                from PIL import Image
                import os
                if not hasattr(save_crop, "imgs"):
                    save_crop.imgs = {}
                if pno not in save_crop.imgs:
                    save_crop.imgs[pno] = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                im = save_crop.imgs[pno]
                Z = ZOOM
                box = (max(0, (lo-6)*Z), max(0, (top-16)*Z), min(im.width, (hi+6)*Z), min(im.height, (bot+16)*Z))
                c = im.crop(box)
                idx = len(measures)+1
                fn = os.path.join(crops_dir, f'm{idx:03d}.png')
                c.resize((int(c.width*1.7), int(c.height*1.7))).save(fn)
                base = os.path.basename(crops_dir.rstrip('/'))
                crops_meta.append({"idx": idx, "crop": f"{base}/m{idx:03d}.png"})

            for j in range(len(bnds)-1):
                lo, hi = bnds[j], bnds[j+1]
                me = [e for e in evs if lo <= e["x"] < hi]
                if not me:
                    # segmento sem glifo = barra falsa/borda de sistema -> ignora.
                    # (pausas reais, inclusive de compasso inteiro, têm glifo e já entram acima)
                    continue
                # TERCINAS: "3" sobre 3 notas -> cada nota x2/3 (3 no tempo de 2)
                notes_me = [e for e in me if e["kind"] == "n"]
                for tx, ty in tuplets3:
                    if not (lo <= tx < hi) or nearest_sys(ty) != sidx or len(notes_me) < 3:
                        continue
                    grp = sorted(sorted(notes_me, key=lambda e: abs(e["x"]-tx))[:3], key=lambda e: e["x"])
                    for e in grp:
                        e["dur"] = Fraction(str(e["dur"])) * 2 / 3
                # beam groups DENTRO do compasso (não cruzam barra): colcheias vizinhas beamadas => start..stop
                def flush(run):
                    if len(run) >= 2:
                        for i, e in enumerate(run):
                            e["beam"] = "start" if i == 0 else ("stop" if i == len(run)-1 else "continue")
                run = []
                for e in me:
                    if e["kind"] == "n" and e["nb"] >= 1:
                        if run and any(b["x0"]-3 <= run[-1]["stemx"] <= b["x1"]+3 and b["x0"]-3 <= e["stemx"] <= b["x1"]+3 for b in beams):
                            run.append(e)
                        else:
                            flush(run); run = [e]
                    else:
                        flush(run); run = []
                flush(run)
                toks = []
                for e in me:
                    if e["kind"] == "r":
                        toks.append(f"R:{e['dur']}")
                    else:
                        flags = []
                        if e["beam"]:
                            flags.append(f"beam-{e['beam']}")
                        if EMIT_SLURS and e["slur"]:
                            flags.append(f"slur-{e['slur']}")
                        if EMIT_SLURS and e["tie"]:
                            flags.append(f"tie-{e['tie']}")
                        t = f"{e['pitch']}:{e['dur']}"
                        if flags:
                            t += ":" + ";".join(flags)
                        toks.append(t)
                save_crop(lo, hi)
                measures.append(toks)
                rs, re_ = rep_start_at(lo), rep_end_at(hi)
                repeats.append("both" if rs and re_ else "start" if rs else "end" if re_ else "")
                mid = (lo + hi) / 2
                enum = ''
                for bx0, bx1, bnum in sys_brackets:
                    if bx0-6 <= mid <= bx1+6 and bnum:
                        enum = str(bnum); break
                endings.append(enum)
    if crops_dir:
        import json, os
        json.dump(crops_meta, open(os.path.join(os.path.dirname(crops_dir.rstrip('/')), 'vmeasures.json'), 'w'), ensure_ascii=False, indent=1)
    return measures, repeats, endings

def detect_key(pdf):
    doc = fitz.open(pdf)
    glyphs, horiz, vert, beams, slurs = collect(doc[0])
    systems = systems_from_lines(horiz)
    top, bot = systems[0][0], systems[0][-1]
    band = lambda g: top-30 < g["y"] < bot+30
    fn = min([g['x'] for g in glyphs if g['cp'] in NOTEHEADS and band(g)], default=999)
    sh = sum(1 for g in glyphs if g['cp'] == 0xE262 and band(g) and g['x'] < fn-5)
    fl = sum(1 for g in glyphs if g['cp'] == 0xE260 and band(g) and g['x'] < fn-5)
    return sh if sh else -fl

def detect_time(pdf):
    """Lê a fórmula de compasso pelos glifos SMuFL (E080-E089 dígitos, E08A common, E08B cut)."""
    doc = fitz.open(pdf)
    glyphs, horiz, vert, beams, slurs = collect(doc[0])
    systems = systems_from_lines(horiz)
    top, bot = systems[0][0], systems[0][-1]; mid = (top + bot) / 2
    band = lambda g: top-30 < g["y"] < bot+40
    fn = min([g['x'] for g in glyphs if g['cp'] in NOTEHEADS and band(g)], default=999)
    ts = [g for g in glyphs if 0xE080 <= g['cp'] <= 0xE08B and band(g) and g['x'] < fn]
    if not ts:
        return '4/4'
    for g in ts:
        if g['cp'] == 0xE08A: return '4/4'   # common time
        if g['cp'] == 0xE08B: return '2/2'   # cut time
    digs = [g for g in ts if g['cp'] <= 0xE089]
    num = sorted([g for g in digs if g['y'] < mid], key=lambda g: g['x'])
    den = sorted([g for g in digs if g['y'] >= mid], key=lambda g: g['x'])
    def val(gs, default): return int(''.join(str(g['cp']-0xE080) for g in gs)) if gs else default
    n = val(num, 4); d = val(den, 4)
    if n < 1 or n > 32 or d not in (1,2,4,8,16): return '4/4'
    return f"{n}/{d}"

def detect_tempo(pdf):
    doc = fitz.open(pdf)
    for b in doc[0].get_text("rawdict")["blocks"]:
        for l in b.get("lines", []):
            for s in l.get("spans", []):
                if s.get("font", "").startswith("Edwin") and s['bbox'][1] < 140:
                    txt = ''.join(ch['c'] for ch in s.get("chars", []))
                    m = re.search(r'=\s*(\d+)', txt)
                    if m:
                        return int(m.group(1))
    return 100

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf'); ap.add_argument('--sharps', type=int, default=None)
    ap.add_argument('--out', default=None, help='salvar transcription.json')
    ap.add_argument('--title', default=''); ap.add_argument('--artist', default='')
    ap.add_argument('--tempo', type=int, default=None)
    ap.add_argument('--crops', default=None, help='pasta p/ salvar recorte de cada compasso (alinhado)')
    ap.add_argument('--time', default=None, help='fórmula (ex 2/4); se omitido, detecta')
    a = ap.parse_args()
    if a.time is None:
        a.time = detect_time(a.pdf)
        print(f"[auto] fórmula detectada: {a.time}")
    if a.sharps is None:
        a.sharps = detect_key(a.pdf)
        print(f"[auto] armadura detectada: {a.sharps} ({'sustenidos' if a.sharps>=0 else 'bemóis'})")
    if a.tempo is None:
        a.tempo = detect_tempo(a.pdf)
        print(f"[auto] andamento detectado: ♩={a.tempo}")
    measures, repeats, endings = extract(a.pdf, a.sharps, crops_dir=a.crops)
    print(f"{len(measures)} compassos extraídos | repetições: "
          f"início={[i+1 for i,r in enumerate(repeats) if r in ('start','both')]} "
          f"fim={[i+1 for i,r in enumerate(repeats) if r in ('end','both')]}")
    casas = {i+1: e for i, e in enumerate(endings) if e}
    if casas:
        print(f"casas (voltas): {casas}")
    import json
    from fractions import Fraction
    beats = float(Fraction(a.time.split('/')[0]) / Fraction(a.time.split('/')[1]) * 4)
    for i, m in enumerate(measures):
        tot = sum((Fraction(t.split(':')[1]) for t in m), Fraction(0))
        flag = "" if tot == Fraction(a.time.split('/')[0])*4/int(a.time.split('/')[1]) else f"  <-- soma {float(tot)}"
        print(f" c{i+1:02d}: {' '.join(m)}{flag}")
    if a.out:
        spec = {"title": a.title, "artist": a.artist, "sharps": a.sharps, "flats": 0,
                "tempo": a.tempo, "time": a.time, "measures": measures, "repeats": repeats,
                "endings": endings}
        json.dump(spec, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print("->", a.out)

if __name__ == '__main__':
    main()
