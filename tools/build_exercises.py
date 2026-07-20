#!/usr/bin/env python3
"""
build_exercises — gera o catálogo de exercícios (gen_exercises), constrói cada um
(spec → musicxml → player com áudio+cursor, SEM PDF), faz thumb do render e escreve
exercicios.json. Depois rode update_exercicios.py p/ a página.

Uso: python3 build_exercises.py [--only slugsubstring]
"""
import os, sys, json, re, subprocess, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gen_exercises, saxlib

def slugify(t):
    import unicodedata
    t = t.replace('#', 'sharp').replace('♭', 'b')
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+', '_', t).strip('_')

def thumb_from_svg(svg, out_png):
    import cairosvg
    from PIL import Image
    tmp = out_png + '.full.png'
    cairosvg.svg2png(bytestring=svg.encode(), write_to=tmp, output_width=700, background_color='white')
    im = Image.open(tmp).convert('RGB')
    im.crop((0, 0, im.width, min(190, im.height))).save(out_png)
    os.remove(tmp)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--only', default=''); ap.add_argument('--cat', default='')
    a = ap.parse_args()
    cat = gen_exercises.catalog()
    if a.cat:
        cat = [e for e in cat if e['categoria'] == a.cat]
    manifest = []
    KM = {0:'Dó maior',1:'Sol maior (1 ♯)',2:'Ré maior (2 ♯)',3:'Lá maior (3 ♯)',
          -1:'Fá maior (1 ♭)',-2:'Sib maior (2 ♭)'}
    for e in cat:
        slug = slugify(e['title'])
        if a.only and a.only.lower() not in slug.lower():
            continue
        d = os.path.join(ROOT, 'exercicios', slug); os.makedirs(d, exist_ok=True)
        spec = {k: e[k] for k in ('title','sharps','flats','tempo','time','measures','repeats')}
        json.dump(spec, open(f'{d}/spec.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
        mxml = f'{d}/{slug}.musicxml'
        subprocess.run([sys.executable, os.path.join(HERE,'build_from_spec.py'), f'{d}/spec.json', mxml],
                       capture_output=True)
        meta = {"title": e['title'], "artist": e['categoria'], "instrument": "Sax Alto (Mib)",
                "key": KM.get(e['sharps'], ''), "loop": True}   # exercícios repetem no play
        saxlib.inject_tempo(mxml, e['tempo'])
        svg, notes, midi = saxlib.render_svg_timemap(mxml, e['tempo'])
        saxlib.build_player(mxml, f'{d}/{slug}_sax.mp3', meta, f'{d}/{slug}_player.html', e['tempo'])
        try:
            thumb_from_svg(svg, f'{d}/thumb.png')
        except Exception as ex:
            print('thumb err', slug, ex)
        manifest.append({"title": e['title'], "categoria": e['categoria'], "tom": e.get('tom',''),
                         "instrument": "Sax Alto (Mib)", "tempo": f"♩ = {e['tempo']}",
                         "slug": slug, "file": f"exercicios/{slug}/{slug}_player.html",
                         "thumb": f"exercicios/{slug}/thumb.png"})
        print("ok", e['title'])
    # merge com manifesto existente (por slug)
    mf = os.path.join(ROOT, 'exercicios.json')
    old = {x['slug']: x for x in (json.load(open(mf, encoding='utf-8')) if os.path.exists(mf) else [])}
    for m in manifest: old[m['slug']] = m
    json.dump(list(old.values()), open(mf,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"\nexercicios.json: {len(old)} exercícios")

if __name__ == '__main__':
    main()
