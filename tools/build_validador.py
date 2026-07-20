#!/usr/bin/env python3
"""Gera Validador.html — 1 HTML com a comparação compasso a compasso (ORIGINAL x
TRANSCRICAO) de TODAS as músicas da plataforma (com filtro por bloco), compacto e com
botões de marcação por compasso. Fatia os grids em tiras (sem re-renderizar).
Rode da raiz do projeto."""
import os, json, glob
from PIL import Image, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROWH = 150
# ordem preferida do Menq (junino); o resto entra pela ordem do songs.json
MENQ_ORDER = ["Ta_xi_Lunar","Nosso_Xote","Onde_esta_voce","Ultimo_pau_de_arara","Baiao",
 "Sanfona_Sentida","Sabia","Espumas_ao_Vento","Anunciac_a_o","Ai_que_saudade_d_oce",
 "Eu_so_quero_um_xodo","Asa_Branca","Lindo_Lago_do_Amor","Xote_das_meninas","Fogo_e_Paixao",
 "Diamantina","Festa","Festa_no_Interior","Olha_pro_ce_u","Pagode_Russo","Frevo_Mulher",
 "Hino_Me_Enterra_na_Quarta"]

def autocrop(im, pad=7):
    bg = Image.new('RGB', im.size, (255, 255, 255))
    bbox = ImageChops.difference(im, bg).getbbox()
    if not bbox: return im
    x0, y0, x1, y1 = bbox
    return im.crop((max(0, x0-pad), max(0, y0-pad), min(im.width, x1+pad), min(im.height, y1+pad)))

def slice_song(sl):
    gdir = os.path.join(ROOT, f'songs/{sl}/work/comparacao')
    grids = sorted(glob.glob(gdir+'/grid_*.png'))
    if not grids: return []
    outdir = os.path.join(gdir, 'rows'); os.makedirs(outdir, exist_ok=True)
    for f in glob.glob(outdir+'/*.png'): os.remove(f)
    idx = 0; rows = []
    for g in grids:
        im = Image.open(g).convert('RGB'); W, H = im.size; half = W//2
        for r in range(H // ROWH):
            idx += 1; y0 = r*ROWH + 30
            autocrop(im.crop((0, y0, half, (r+1)*ROWH))).save(os.path.join(outdir, f'o{idx:03d}.png'))
            autocrop(im.crop((half, y0, W, (r+1)*ROWH))).save(os.path.join(outdir, f't{idx:03d}.png'))
            rows.append([f'songs/{sl}/work/comparacao/rows/o{idx:03d}.png',
                         f'songs/{sl}/work/comparacao/rows/t{idx:03d}.png'])
    return rows

def main():
    songs = json.load(open(os.path.join(ROOT, 'songs.json'), encoding='utf-8'))
    by_slug = {(s.get('slug') or s.get('_slug')): s for s in songs}
    ordered = [sl for sl in MENQ_ORDER if sl in by_slug]
    ordered += [sl for sl in by_slug if sl not in ordered]
    from qa_notecount import pdf_heads_per_measure, spec_notes_per_measure
    data = []
    for sl in ordered:
        s = by_slug[sl]
        rows = slice_song(sl)
        if not rows: continue
        v = int(os.path.getmtime(os.path.join(ROOT, rows[0][0])))
        rows = [[o+f'?v={v}', t+f'?v={v}'] for o, t in rows]
        bloco = 'Menq' if sl in MENQ_ORDER else ((s.get('bloco') or ['Metaverso'])[0])
        # CHECAGEM DE CONTAGEM: cabeças de nota no PDF × notas no spec, por compasso.
        # Só é confiável quando o nº de compassos ALINHA (PDF==spec==linhas). Se a
        # estrutura difere (repetição/casa/D.S. não desdobrada, spec derivado etc.),
        # a comparação por índice vira ruído -> marca a música como "estrutura difere".
        warns = [None] * len(rows)
        align = True; ndiff = None
        try:
            pc = pdf_heads_per_measure(os.path.join(ROOT, 'songs', sl, 'source.pdf'))
            sc = spec_notes_per_measure(os.path.join(ROOT, 'songs', sl, 'spec.json'))
            if len(pc) == len(sc) == len(rows):
                for i in range(len(rows)):
                    if pc[i] != sc[i]:
                        warns[i] = {"pdf": pc[i], "spec": sc[i]}
            else:
                align = False; ndiff = [len(pc), len(sc), len(rows)]
        except Exception:
            align = False
        nwarn = sum(1 for w in warns if w)
        data.append({"title": s['title'], "slug": sl, "bloco": bloco,
                     "status": s.get('status', 'pronto'), "rows": rows, "nc": len(rows),
                     "warns": warns, "nwarn": nwarn, "align": align, "ndiff": ndiff})
    html = TPL.replace('__DATA__', json.dumps(data, ensure_ascii=False))
    open(os.path.join(ROOT, 'Validador.html'), 'w', encoding='utf-8').write(html)
    print(f"Validador.html -> {len(data)} músicas, {sum(d['nc'] for d in data)} compassos")

TPL = r'''<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache"><title>Validador — compasso a compasso</title>
<style>
:root{--rox:#7b2d8e;--am:#f4c518;--bg:#faf7fb;--ink:#1a1a1a}
*{box-sizing:border-box} body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink)}
#app{display:flex;min-height:100vh}
#side{width:280px;flex:none;background:#fff;border-right:1px solid #ece6f0;position:sticky;top:0;height:100vh;overflow-y:auto}
#side h1{font-size:15px;margin:0;padding:14px 14px 6px;color:var(--rox)}
#fbloco{display:flex;gap:6px;flex-wrap:wrap;padding:0 14px 10px;border-bottom:1px solid #efe9f3}
.fbtn{border:1px solid #ddd;background:#fff;color:#666;border-radius:14px;padding:5px 10px;font-size:12px;font-weight:600;cursor:pointer}
.fbtn.on{background:var(--rox);border-color:var(--rox);color:#fff}
.item{display:flex;gap:8px;align-items:center;padding:8px 14px;cursor:pointer;border-bottom:1px solid #f4eff7;font-size:13.5px}
.item:hover{background:#faf5fc} .item.on{background:linear-gradient(90deg,#f6ecfa,#fff);border-left:4px solid var(--rox);padding-left:10px}
.item .num{width:20px;height:20px;flex:none;border-radius:50%;background:#efe1f4;color:var(--rox);font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center}
.item.rev .num{background:#2e7d5b;color:#fff}
.item .t{flex:1;line-height:1.1} .item .c{font-size:10.5px;color:#aaa}
.item .bl{font-size:9.5px;color:#a98bbb;font-weight:700;text-transform:uppercase}
.item .badcount{font-size:10.5px;color:#c0392b;font-weight:700}
#main{flex:1;min-width:0}
#top{position:sticky;top:0;z-index:5;background:rgba(255,255,255,.97);backdrop-filter:blur(6px);border-bottom:1px solid #ece6f0;padding:10px 20px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
#top h2{font-size:17px;margin:0;flex:1;min-width:200px} #top h2 span{color:var(--rox)}
button{font-size:13px;padding:7px 12px;border:0;border-radius:16px;background:var(--rox);color:#fff;cursor:pointer;font-weight:600}
button.ghost{background:#efe1f4;color:var(--rox)} #revbtn.on{background:#2e7d5b} #dl{background:var(--am);color:#5a4300}
#rows{max-width:1250px;margin:0 auto;padding:6px 16px 90px}
.mrow{display:flex;gap:10px;align-items:center;border-bottom:2px solid #eee7f0;padding:6px 4px}
.mrow.ok{background:#eafaf0} .mrow.bad{background:#fdf0ee}
.mrow.cntwarn{box-shadow:inset 4px 0 0 #e67e22;background:#fff7ee}
.mrow .idx .cw{margin-top:4px;font-size:10px;font-weight:800;color:#fff;background:#e67e22;border-radius:6px;padding:2px 4px;line-height:1.15;white-space:nowrap;cursor:help}
.mrow .idx{width:44px;flex:none;text-align:center;font-weight:700;color:#7b2d8e;font-size:15px}
.mrow .cmp{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.mrow .cmp .pr{display:flex;align-items:center;gap:8px}
.mrow .cmp .pr .lbl{width:52px;flex:none;font-size:10px;font-weight:700;text-transform:uppercase;text-align:right;color:#bbb}
.mrow .cmp .pr.t .lbl{color:#7b2d8e}
.mrow .cmp .pr img{height:135px;width:auto;max-width:100%;object-fit:contain;object-position:left;display:block}
.mrow .cmp .pr.o{border-bottom:1px dashed #e5dcec;padding-bottom:2px}
.ctrls{flex:none;width:330px;display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.vb{width:28px;height:28px;border-radius:50%;padding:0;font-size:13px;background:#fff;border:2px solid #ddd;color:#888}
.mrow.ok .vb.k{background:#2e7d5b;border-color:#2e7d5b;color:#fff} .mrow.bad .vb.x{background:#c0392b;border-color:#c0392b;color:#fff}
.chip{font-size:11px;padding:3px 8px;border-radius:12px;border:1px solid #d9d4cc;background:#fff;color:#777;font-weight:600}
.chip.on{background:#c0392b;border-color:#c0392b;color:#fff}
.hint{color:#aaa;font-size:12px;text-align:center;padding:30px}
@media(max-width:820px){#side{position:fixed;left:-280px;transition:.2s;z-index:20;box-shadow:0 0 30px rgba(0,0,0,.2)}#side.show{left:0}#burger{display:inline-block}.ctrls{width:100%}.mrow{flex-wrap:wrap}}
#burger{display:none}
</style></head><body>
<div id="app">
 <nav id="side"><h1>🎷 Validador</h1>
 <div style="padding:0 14px 10px;display:flex;gap:14px;flex-wrap:wrap;border-bottom:1px solid #efe9f3">
   <a href="Biblioteca.html" style="color:var(--rox);font-size:12px;font-weight:600;text-decoration:none">← Biblioteca</a>
   <a href="Exercicios.html" style="color:var(--rox);font-size:12px;font-weight:600;text-decoration:none">Exercícios →</a>
   <a href="SightReader.html" style="color:var(--rox);font-size:12px;font-weight:600;text-decoration:none">🎮 Sight Reader →</a></div>
 <div id="fbloco"></div><div id="list"></div></nav>
 <div id="main">
   <div id="top"><button id="burger" onclick="document.getElementById('side').classList.toggle('show')">☰</button>
     <h2 id="title"></h2>
     <button class="ghost" onclick="go(-1)">←</button><button class="ghost" onclick="go(1)">→</button>
     <button id="revbtn" onclick="toggleRev()">revisada ✓</button>
     <button id="dl" onclick="download()">⬇ feedback</button></div>
   <div id="rows"><div class="hint">Selecione uma música.</div></div>
 </div></div>
<script>
const DATA=__DATA__;
const TAGS=[["nota_errada","nota errada"],["nota_faltante","nota faltante"],["ritmo","ritmo"],["ligadura","ligadura"],["beaming","beaming"]];
const BLOCOS=['Todos',...[...new Set(DATA.map(d=>d.bloco))]];
let fbloco=localStorage.getItem('val_bloco')||'Todos';
let cur=+(localStorage.getItem('val_cur')||0);
let st=JSON.parse(localStorage.getItem('val_st')||'{}');
let rev=new Set(JSON.parse(localStorage.getItem('val_rev')||'[]'));
function save(){localStorage.setItem('val_st',JSON.stringify(st))}
function sd(sl){return st[sl]||(st[sl]={})}
function badCount(sl){const o=st[sl]||{};return Object.values(o).filter(v=>v&&((v.tags&&v.tags.length)||v.bad)).length}
function visible(){return DATA.map((d,i)=>[d,i]).filter(([d])=>fbloco==='Todos'||d.bloco===fbloco)}
function paintBloco(){const c=document.getElementById('fbloco');c.innerHTML='';
  BLOCOS.forEach(b=>{const btn=document.createElement('button');btn.className='fbtn'+(b===fbloco?' on':'');btn.textContent=b;
    btn.onclick=()=>{fbloco=b;localStorage.setItem('val_bloco',b);const vis=visible();if(!vis.find(([,i])=>i===cur)&&vis.length)cur=vis[0][1];render();};c.appendChild(btn);});}
function paintList(){const list=document.getElementById('list');list.innerHTML='';
  visible().forEach(([d,i])=>{const bc=badCount(d.slug);
    const el=document.createElement('div');el.className='item'+(i===cur?' on':'')+(rev.has(d.slug)?' rev':'');
    const cnt=d.align===false?`· <span class="badcount" style="color:#888" title="nº de compassos PDF×spec×imagens difere — checagem por compasso indisponível (repetição/casa/D.S. ou spec derivado)">estrutura⧗</span>`:(d.nwarn?`· <span class="badcount" style="color:#e67e22">⚠${d.nwarn}</span>`:'');
    el.innerHTML=`<span class="num">${rev.has(d.slug)?'✓':'♪'}</span><span class="t">${d.title}<div class="c"><span class="bl">${d.bloco}</span> · ${d.nc} comp. ${cnt} ${bc?`· <span class="badcount">${bc}👎</span>`:''}</div></span>`;
    el.onclick=()=>{cur=i;render();document.getElementById('side').classList.remove('show')};list.appendChild(el);});}
function render(){
  localStorage.setItem('val_cur',cur);const d=DATA[cur];const S=sd(d.slug);
  document.getElementById('title').innerHTML=`<span>${d.title}</span> <small style="color:#bbb;font-weight:400">· ${d.bloco} · ${d.nc} comp.</small>`;
  document.getElementById('revbtn').className=rev.has(d.slug)?'on':'';
  const box=document.getElementById('rows');box.innerHTML='';
  d.rows.forEach((pair,mi)=>{const m=mi+1;const v=S[m]||{};const w=(d.warns&&d.warns[mi])||null;
    const row=document.createElement('div');row.className='mrow'+(v.ok?' ok':'')+((v.tags&&v.tags.length||v.bad)?' bad':'')+(w?' cntwarn':'');
    row.innerHTML=`<div class="idx">${m}${w?`<div class="cw" title="cabeças de nota: PDF=${w.pdf} × player=${w.spec}. Provável nota faltante/sobrando (mesmo fechando na fórmula).">⚠ ${w.pdf}≠${w.spec}</div>`:''}</div>
      <div class="cmp"><div class="pr o"><span class="lbl">PDF</span><img loading="lazy" src="${pair[0]}"></div>
      <div class="pr t"><span class="lbl">player</span><img loading="lazy" src="${pair[1]}"></div></div>
      <div class="ctrls"><button class="vb k">✓</button><button class="vb x">👎</button>
       ${TAGS.map(([k,l])=>`<button class="chip" data-t="${k}">${l}</button>`).join('')}</div>`;
    const set=()=>{row.className='mrow'+(S[m]&&S[m].ok?' ok':'')+((S[m]&&(S[m].tags||[]).length||S[m]&&S[m].bad)?' bad':'');
      row.querySelectorAll('.chip').forEach(c=>c.classList.toggle('on',S[m]&&(S[m].tags||[]).includes(c.dataset.t)));};
    row.querySelector('.vb.k').onclick=()=>{S[m]=S[m]||{};S[m].ok=!S[m].ok;if(S[m].ok){S[m].bad=false;S[m].tags=[];}save();set();paintList();};
    row.querySelector('.vb.x').onclick=()=>{S[m]=S[m]||{};S[m].bad=!S[m].bad;if(S[m].bad)S[m].ok=false;save();set();paintList();};
    row.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{S[m]=S[m]||{tags:[]};S[m].tags=S[m].tags||[];const t=c.dataset.t,ix=S[m].tags.indexOf(t);
      if(ix<0){S[m].tags.push(t);S[m].ok=false;}else S[m].tags.splice(ix,1);save();set();paintList();});
    box.appendChild(row);set();});
  window.scrollTo(0,0);paintBloco();paintList();
}
function go(dir){const vis=visible().map(([,i])=>i);let p=vis.indexOf(cur);p=(p+dir+vis.length)%vis.length;cur=vis[p];render()}
function toggleRev(){const s=DATA[cur].slug;if(rev.has(s))rev.delete(s);else rev.add(s);localStorage.setItem('val_rev',JSON.stringify([...rev]));render()}
function download(){const out=DATA.map(d=>{const S=st[d.slug]||{};
   const probs=Object.keys(S).filter(m=>S[m].bad||(S[m].tags||[]).length).map(m=>({compasso:+m,tipos:S[m].tags||[]})).sort((a,b)=>a.compasso-b.compasso);
   const oks=Object.keys(S).filter(m=>S[m].ok).map(Number).sort((a,b)=>a-b);
   return {musica:d.title,slug:d.slug,bloco:d.bloco,revisada:rev.has(d.slug),validados:oks,problemas:probs};}).filter(x=>x.problemas.length||x.validados.length||x.revisada);
  const b=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='validador_feedback.json';a.click();}
document.addEventListener('keydown',e=>{if(e.target.tagName==='BUTTON')return;if(e.key==='ArrowLeft')go(-1);if(e.key==='ArrowRight')go(1)});
render();
</script></body></html>'''

if __name__ == '__main__':
    main()
