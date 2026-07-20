#!/usr/bin/env python3
"""
build_validation — página HTML de validação compasso a compasso.

Para cada compasso, mostra lado a lado: o recorte do PDF ORIGINAL e a
minha TRANSCRIÇÃO (renderizada). Autossuficiente (imagens em base64).
Cada linha tem um marcador ✓/✗ que persiste (localStorage) p/ acompanhar a revisão.

Uso:
  python3 build_validation.py --mxml Firework.musicxml --render-dir _work/firework \
     --measures _work/firework/vmeasures.json --out Firework_validacao.html --title "Firework"
"""
import argparse, os, json, base64, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))

def render_measure_png(measure_stream, ks, ts, tmpdir, i, g0=0):
    from music21 import stream, clef, meter, key
    import verovio, cairosvg
    sc = stream.Score(); p = stream.Part()
    p.insert(0, clef.TrebleClef()); p.insert(0, key.KeySignature(ks)); p.insert(0, meter.TimeSignature(ts))
    sharp_steps = ['F', 'C', 'G', 'D', 'A', 'E', 'B'][:ks] if ks > 0 else []
    flat_steps = ['B', 'E', 'A', 'D', 'G', 'C', 'F'][:(-ks)] if ks < 0 else []
    for el in list(measure_stream.getElementsByClass(['MetronomeMark', 'TempoIndication'])):
        measure_stream.remove(el)
    # numera as NOTAS sequencialmente: verso 1 = índice no compasso, verso 2 = índice global
    loc = 0
    for el in measure_stream.notesAndRests:
        if el.isRest:
            continue
        loc += 1
        try:
            el.addLyric(str(loc))            # local (posição da nota no compasso)
            el.addLyric(str(g0 + loc))       # global (posição da nota na música)
        except Exception:
            pass
    p.append(measure_stream)
    for nn in p.recurse().notes:
        for pp in (nn.pitches if hasattr(nn, 'pitches') else [nn.pitch]):
            if pp.accidental is not None and (
               (pp.accidental.name == 'sharp' and pp.step in sharp_steps) or
               (pp.accidental.name == 'flat' and pp.step in flat_steps)):
                pp.accidental.displayStatus = False
    sc.append(p)
    xml = os.path.join(tmpdir, f'm{i}.xml'); sc.write('musicxml', fp=xml)
    tk = verovio.toolkit()
    tk.setOptions({"pageWidth": 1200, "pageHeight": 500, "scale": 55, "adjustPageHeight": True,
                   "footer": "none", "header": "none", "font": "Leipzig"})
    tk.loadFile(xml); tk.redoLayout()
    png = os.path.join(tmpdir, f'm{i}.png')
    cairosvg.svg2png(bytestring=tk.renderToSVG(1).encode(), write_to=png, output_width=620, background_color='white')
    _autocrop(png)
    return png, loc

def _autocrop(png, pad=8):
    from PIL import Image, ImageChops
    im = Image.open(png).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bbox = ImageChops.difference(im, bg).getbbox()
    if bbox:
        x0, y0, x1, y1 = bbox
        im.crop((max(0, x0-pad), max(0, y0-pad), min(im.width, x1+pad), min(im.height, y1+pad))).save(png)

def b64(path):
    return 'data:image/png;base64,' + base64.b64encode(open(path, 'rb').read()).decode() if path and os.path.exists(path) else ''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mxml', required=True); ap.add_argument('--render-dir', required=True)
    ap.add_argument('--measures', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--title', default='')
    a = ap.parse_args()
    from music21 import converter
    meas = json.load(open(a.measures, encoding='utf-8'))
    sc = converter.parse(a.mxml); part = sc.parts[0]
    ks = part.keySignature.sharps if part.keySignature else 0
    ts = part.getTimeSignatures()[0].ratioString if part.getTimeSignatures() else '4/4'
    mm = list(part.getElementsByClass('Measure'))
    n = max(len(meas), len(mm))
    tmp = tempfile.mkdtemp()
    rows = []
    gcount = 0
    for i in range(n):
        orig = b64(os.path.join(a.render_dir, meas[i]['crop'])) if i < len(meas) else ''
        mine = ''
        if i < len(mm):
            try:
                png, loc = render_measure_png(mm[i], ks, ts, tmp, i, g0=gcount)
                gcount += loc
                mine = b64(png)
            except Exception as e:
                print("render err", i+1, e)
        rows.append((i+1, orig, mine))
    def img(src):
        return '<img src="' + src + '">' if src else '<i>—</i>'
    def rowhtml(num, o, m):
        n = str(num)
        return ('<tr data-m="' + n + '">'
                '<td class="mn">' + n + '</td>'
                '<td class="sc">' + img(m) + '</td>'
                '<td class="sc">' + img(o) + '</td>'
                '<td class="av">'
                '<button class="chk" title="idêntico" onclick="ok(' + n + ')">&#10003;</button>'
                '<button class="bad" title="tem problema" onclick="bad(' + n + ')">&#128078;</button>'
                '</td>'
                '<td class="obs">'
                '<div class="chips">'
                '<button class="chip" data-t="ligadura" onclick="tag(' + n + ',\'ligadura\')">ligadura</button>'
                '<button class="chip" data-t="nota_errada" onclick="tag(' + n + ',\'nota_errada\')">nota errada</button>'
                '<button class="chip" data-t="nota_faltante" onclick="tag(' + n + ',\'nota_faltante\')">nota faltante</button>'
                '<button class="chip" data-t="ritmo" onclick="tag(' + n + ',\'ritmo\')">ritmo errado</button>'
                '<button class="chip" data-t="beaming" onclick="tag(' + n + ',\'beaming\')">beaming errado</button>'
                '</div>'
                '<textarea placeholder="observação livre (opcional)…" oninput="note(' + n + ',this.value)"></textarea>'
                '</td>'
                '</tr>')
    cards = "\n".join(rowhtml(num, o, m) for num, o, m in rows)
    html = f'''<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0">
<title>Validação — {a.title}</title>
<style>
:root{{--accent:#c0392b}} *{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:#faf9f7;color:#1a1a1a}}
header{{padding:14px 20px;border-bottom:1px solid #e6e3de}}
h1{{font-size:19px;margin:0}} .sub{{color:#777;font-size:13px;margin:4px 0 0}}
#prog{{color:var(--accent);font-weight:600}}
main{{padding:0 12px 60px}}
table{{border-collapse:collapse;width:100%;max-width:1080px;margin:0 auto;table-layout:fixed}}
col.c-mn{{width:40px}} col.c-sc{{width:330px}} col.c-av{{width:96px}}
thead th{{position:sticky;top:0;background:#f2efe9;font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:#666;padding:8px;border-bottom:2px solid #ddd;text-align:left;z-index:2}}
td{{border-bottom:1px solid #eee;padding:5px 8px;vertical-align:middle}}
tr.ok td{{background:#eafaf0}} tr.bad td{{background:#fdecea}}
td.mn{{font-weight:700;color:#999;text-align:center}}
td.sc img{{height:76px;width:auto;max-width:100%;display:block}} td.sc i{{color:#bbb}}
td.av{{text-align:center;white-space:nowrap}}
.chk,.bad{{width:34px;height:34px;border-radius:50%;border:2px solid #ddd;background:#fff;font-size:15px;cursor:pointer;line-height:1;margin:0 2px}}
tr.ok .chk{{border-color:#27ae60;background:#27ae60;color:#fff}}
tr.bad .bad{{border-color:#c0392b;background:#c0392b}}
td.obs .chips{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:5px}}
.chip{{border:1px solid #d9d4cc;background:#fff;color:#666;border-radius:14px;padding:4px 10px;font-size:12px;cursor:pointer}}
.chip.active{{background:#c0392b;border-color:#c0392b;color:#fff}}
td.obs textarea{{width:100%;min-height:38px;border:1px solid #e0ddd6;border-radius:8px;padding:6px;font:inherit;font-size:12px;resize:vertical;background:#fff}}
tr.bad td.obs textarea{{border-color:#e0b4ae}}
</style></head><body>
<header><h1>Validação compasso a compasso — {a.title}</h1>
<p class="sub">Coluna 1 = <b>transcrição</b>, coluna 2 = <b>PDF original</b>. Marque ✓ (idêntico) ou 👎 (problema); pode escolher <b>vários</b> motivos. <span id="prog"></span></p></header>
<main><table>
<colgroup><col class="c-mn"><col class="c-sc"><col class="c-sc"><col class="c-av"><col></colgroup>
<thead><tr><th>#</th><th>Transcrição (karaokê)</th><th>PDF original</th><th>Avaliação</th><th>Observação</th></tr></thead>
<tbody>{cards}</tbody></table>
<div style="text-align:center;padding:28px 0 60px">
<button id="exp" style="background:#c0392b;color:#fff;border:0;border-radius:18px;padding:12px 24px;font-weight:600;font-size:15px;cursor:pointer">⬇ Baixar observações</button>
<p style="color:#999;font-size:12px;margin-top:8px">salve o arquivo em <b>feedback/</b> (ou me envie) para eu calibrar o engine.</p></div>
</main>
<script>
const KEY="val_{a.title}", TITLE="{a.title}", N={n};
let st=JSON.parse(localStorage.getItem(KEY)||'{{"ok":[],"bad":{{}}}}');
if(!st.bad)st.bad={{}}; if(!st.ok)st.ok=[];
// migra formato antigo (string) -> objeto
for(const m in st.bad){{ if(typeof st.bad[m]==='string') st.bad[m]={{tags:[],txt:st.bad[m]}}; }}
function ensure(m){{ if(!(m in st.bad)) st.bad[m]={{tags:[],txt:""}}; st.ok=st.ok.filter(x=>x!==m); }}
function save(){{localStorage.setItem(KEY,JSON.stringify(st));paint();}}
function paint(){{document.querySelectorAll('tr[data-m]').forEach(r=>{{const m=+r.dataset.m;
 const isbad=m in st.bad;
 r.classList.toggle('ok',st.ok.includes(m)); r.classList.toggle('bad',isbad);
 const ta=r.querySelector('textarea'); if(ta){{const v=isbad?st.bad[m].txt:""; if(ta.value!==v)ta.value=v;}}
 r.querySelectorAll('.chip').forEach(c=>c.classList.toggle('active',isbad&&st.bad[m].tags.includes(c.dataset.t)));
 }});
 const nbad=Object.keys(st.bad).length;
 document.getElementById('prog').textContent=st.ok.length+" ✓  ·  "+nbad+" 👎  ·  de "+N+" compassos";}}
function ok(m){{if(st.ok.includes(m))st.ok=st.ok.filter(x=>x!==m);else{{st.ok.push(m);delete st.bad[m];}}save();}}
function bad(m){{if(m in st.bad)delete st.bad[m];else ensure(m);save();}}
function tag(m,t){{ensure(m);const T=st.bad[m].tags;const i=T.indexOf(t);if(i<0)T.push(t);else T.splice(i,1);save();}}
function note(m,v){{ensure(m);st.bad[m].txt=v;localStorage.setItem(KEY,JSON.stringify(st));}}
document.getElementById('exp').onclick=()=>{{
 const obs=Object.keys(st.bad).map(m=>({{compasso:+m,tipos:st.bad[m].tags,observacao:st.bad[m].txt}})).sort((a,b)=>a.compasso-b.compasso);
 const data={{musica:TITLE,validados:st.ok.sort((a,b)=>a-b),problemas:obs}};
 const blob=new Blob([JSON.stringify(data,null,2)],{{type:"application/json"}});
 const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=TITLE.replace(/\\s+/g,'_')+"_feedback.json";a.click();}};
paint();
</script></body></html>'''
    open(a.out, 'w', encoding='utf-8').write(html)
    print(f"página de validação -> {a.out} ({n} compassos, {round(len(html)/1024)} KB)")

if __name__ == '__main__':
    main()
