#!/usr/bin/env python3
"""Gera Validador_Menq.html — 1 HTML, comparação compasso a compasso (ORIGINAL x TRANSCRICAO)
das juninas Menq, COMPACTO e com botões de marcação por compasso.
Fatiamos os grids (150px/linha) em tiras por compasso (sem re-renderizar). Imagens por
caminho relativo (arquivo leve). Rode da raiz do projeto."""
import os, json, glob
from PIL import Image

ORDER = [
 ("Táxi Lunar","Ta_xi_Lunar"),("Nosso Xote","Nosso_Xote"),("Onde está você","Onde_esta_voce"),
 ("Último pau de arara","Ultimo_pau_de_arara"),("Baião","Baiao"),("Sanfona Sentida","Sanfona_Sentida"),
 ("Sabiá","Sabia"),("Espumas ao Vento","Espumas_ao_Vento"),("Anunciação","Anunciac_a_o"),
 ("Ai que saudade d'ocê","Ai_que_saudade_d_oce"),("Eu só quero um xodó","Eu_so_quero_um_xodo"),
 ("Asa Branca","Asa_Branca"),("Lindo Lago do Amor","Lindo_Lago_do_Amor"),("Xote das meninas","Xote_das_meninas"),
 ("Fogo e Paixão","Fogo_e_Paixao"),("Diamantina","Diamantina"),("Festa","Festa"),
 ("Festa no Interior","Festa_no_Interior"),("Olha pro céu","Olha_pro_ce_u"),("Pagode Russo","Pagode_Russo"),
 ("Frevo Mulher","Frevo_Mulher"),("Hino do Menq","Hino_Me_Enterra_na_Quarta"),
]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROWH = 150   # altura de cada linha nos grids do compare_measures
GW = 1600    # largura do grid; metade esquerda=ORIGINAL, direita=TRANSCRICAO

def autocrop(im, pad=7):
    from PIL import ImageChops
    bg = Image.new('RGB', im.size, (255, 255, 255))
    bbox = ImageChops.difference(im, bg).getbbox()
    if not bbox:
        return im
    x0, y0, x1, y1 = bbox
    return im.crop((max(0, x0-pad), max(0, y0-pad), min(im.width, x1+pad), min(im.height, y1+pad)))

def slice_song(sl):
    gdir = os.path.join(ROOT, f'songs/{sl}/work/comparacao')
    grids = sorted(glob.glob(gdir+'/grid_*.png'))
    outdir = os.path.join(gdir, 'rows'); os.makedirs(outdir, exist_ok=True)
    for f in glob.glob(outdir+'/*.png'): os.remove(f)
    idx = 0; rows = []
    for g in grids:
        im = Image.open(g).convert('RGB'); W, H = im.size
        half = W // 2
        for r in range(H // ROWH):
            idx += 1
            y0 = r*ROWH + 30                        # pula o cabeçalho (rótulos)
            orig = autocrop(im.crop((0, y0, half, (r+1)*ROWH)))       # ORIGINAL (PDF)
            trans = autocrop(im.crop((half, y0, W, (r+1)*ROWH)))      # TRANSCRICAO (player)
            orig.save(os.path.join(outdir, f'o{idx:03d}.png'))
            trans.save(os.path.join(outdir, f't{idx:03d}.png'))
            rows.append([f'songs/{sl}/work/comparacao/rows/o{idx:03d}.png',
                         f'songs/{sl}/work/comparacao/rows/t{idx:03d}.png'])
    return rows

def main():
    data = []
    for title, sl in ORDER:
        rows = slice_song(sl)
        v = int(os.path.getmtime(os.path.join(ROOT, rows[0][0]))) if rows else 0
        rows = [[o+f'?v={v}', t+f'?v={v}'] for o, t in rows]
        data.append({"title": title, "slug": sl, "rows": rows, "nc": len(rows)})
    html = TPL.replace('__DATA__', json.dumps(data, ensure_ascii=False))
    out = os.path.join(ROOT, 'Validador_Menq.html')
    open(out, 'w', encoding='utf-8').write(html)
    print(f"Validador_Menq.html -> {out} ({len(data)} músicas, {sum(d['nc'] for d in data)} compassos)")

TPL = r'''<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache"><title>Validador Menq — compasso a compasso</title>
<style>
:root{--rox:#7b2d8e;--am:#f4c518;--bg:#faf7fb;--ink:#1a1a1a}
*{box-sizing:border-box} body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink)}
#app{display:flex;min-height:100vh}
#side{width:270px;flex:none;background:#fff;border-right:1px solid #ece6f0;position:sticky;top:0;height:100vh;overflow-y:auto}
#side h1{font-size:15px;margin:0;padding:14px 14px 4px;color:var(--rox)}
#side .subt{font-size:11px;color:#999;padding:0 14px 8px;border-bottom:1px solid #efe9f3}
.item{display:flex;gap:8px;align-items:center;padding:8px 14px;cursor:pointer;border-bottom:1px solid #f4eff7;font-size:13.5px}
.item:hover{background:#faf5fc} .item.on{background:linear-gradient(90deg,#f6ecfa,#fff);border-left:4px solid var(--rox);padding-left:10px}
.item .num{width:20px;height:20px;flex:none;border-radius:50%;background:#efe1f4;color:var(--rox);font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center}
.item.rev .num{background:#2e7d5b;color:#fff}
.item .t{flex:1;line-height:1.1} .item .c{font-size:10.5px;color:#aaa}
.item .badcount{font-size:10.5px;color:#c0392b;font-weight:700}
#main{flex:1;min-width:0}
#top{position:sticky;top:0;z-index:5;background:rgba(255,255,255,.97);backdrop-filter:blur(6px);border-bottom:1px solid #ece6f0;padding:10px 20px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
#top h2{font-size:17px;margin:0;flex:1;min-width:200px} #top h2 span{color:var(--rox)}
button{font-size:13px;padding:7px 12px;border:0;border-radius:16px;background:var(--rox);color:#fff;cursor:pointer;font-weight:600}
button.ghost{background:#efe1f4;color:var(--rox)} #revbtn.on{background:#2e7d5b}
#dl{background:var(--am);color:#5a4300}
#rows{max-width:1250px;margin:0 auto;padding:6px 16px 90px}
.mrow{display:flex;gap:10px;align-items:center;border-bottom:2px solid #eee7f0;padding:6px 4px}
.mrow.ok{background:#eafaf0} .mrow.bad{background:#fdf0ee}
.mrow .idx{width:30px;flex:none;text-align:center;font-weight:700;color:#7b2d8e;font-size:15px}
.mrow .cmp{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.mrow .cmp .pr{display:flex;align-items:center;gap:8px}
.mrow .cmp .pr .lbl{width:52px;flex:none;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;text-align:right;color:#bbb}
.mrow .cmp .pr.o .lbl{color:#8a8a8a} .mrow .cmp .pr.t .lbl{color:#7b2d8e}
.mrow .cmp .pr img{height:135px;width:auto;max-width:100%;object-fit:contain;object-position:left;display:block}
.mrow .cmp .pr.o{border-bottom:1px dashed #e5dcec;padding-bottom:2px}
.ctrls{flex:none;width:330px;display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.vb{width:28px;height:28px;border-radius:50%;padding:0;font-size:13px;background:#fff;border:2px solid #ddd;color:#888}
.mrow.ok .vb.k{background:#2e7d5b;border-color:#2e7d5b;color:#fff} .mrow.bad .vb.x{background:#c0392b;border-color:#c0392b;color:#fff}
.chip{font-size:11px;padding:3px 8px;border-radius:12px;border:1px solid #d9d4cc;background:#fff;color:#777;font-weight:600}
.chip.on{background:#c0392b;border-color:#c0392b;color:#fff}
.hint{color:#aaa;font-size:12px;text-align:center;padding:30px}
@media(max-width:820px){#side{position:fixed;left:-270px;transition:.2s;z-index:20;box-shadow:0 0 30px rgba(0,0,0,.2)}#side.show{left:0}#burger{display:inline-block}.ctrls{width:100%}.mrow{flex-wrap:wrap}}
#burger{display:none}
</style></head><body>
<div id="app">
 <nav id="side"><h1>💜💛 Validador Menq</h1>
   <div class="subt">compasso a compasso · ORIGINAL × TRANSCRIÇÃO</div><div id="list"></div></nav>
 <div id="main">
   <div id="top">
     <button id="burger" onclick="document.getElementById('side').classList.toggle('show')">☰</button>
     <h2 id="title"></h2>
     <button class="ghost" onclick="go(-1)">←</button><button class="ghost" onclick="go(1)">→</button>
     <button id="revbtn" onclick="toggleRev()">revisada ✓</button>
     <button id="dl" onclick="download()">⬇ baixar feedback</button>
   </div>
   <div id="rows"><div class="hint">Selecione uma música.</div></div>
 </div>
</div>
<script>
const DATA=__DATA__;
const TAGS=[["nota_errada","nota errada"],["nota_faltante","nota faltante"],["ritmo","ritmo"],["ligadura","ligadura"],["beaming","beaming"]];
let cur=+(localStorage.getItem('menq_cur')||0);
let st=JSON.parse(localStorage.getItem('menq_val')||'{}');   // st[slug][m]={ok:bool,tags:[]}
let rev=new Set(JSON.parse(localStorage.getItem('menq_rev')||'[]'));
function save(){localStorage.setItem('menq_val',JSON.stringify(st))}
function sd(sl){return st[sl]||(st[sl]={})}
function badCount(sl){const o=st[sl]||{};return Object.values(o).filter(v=>v&&v.tags&&v.tags.length||v&&v.bad).length}
const list=document.getElementById('list');
function paintList(){list.innerHTML='';DATA.forEach((d,i)=>{
  const bc=badCount(d.slug);
  const el=document.createElement('div');el.className='item'+(i===cur?' on':'')+(rev.has(d.slug)?' rev':'');
  el.innerHTML=`<span class="num">${rev.has(d.slug)?'✓':i+1}</span><span class="t">${d.title}<div class="c">${d.nc} comp. ${bc?`· <span class="badcount">${bc} 👎</span>`:''}</div></span>`;
  el.onclick=()=>{cur=i;render();document.getElementById('side').classList.remove('show')};list.appendChild(el);});}
function render(){
  localStorage.setItem('menq_cur',cur);const d=DATA[cur];const S=sd(d.slug);
  document.getElementById('title').innerHTML=`${cur+1}. <span>${d.title}</span> <small style="color:#bbb;font-weight:400">· ${d.nc} comp.</small>`;
  const revb=document.getElementById('revbtn');revb.className=rev.has(d.slug)?'on':'';
  const box=document.getElementById('rows');box.innerHTML='';
  d.rows.forEach((pair,mi)=>{
    const m=mi+1;const v=S[m]||{};
    const row=document.createElement('div');row.className='mrow'+(v.ok?' ok':'')+((v.tags&&v.tags.length||v.bad)?' bad':'');
    row.innerHTML=`<div class="idx">${m}</div>
      <div class="cmp"><div class="pr o"><span class="lbl">PDF</span><img loading="lazy" src="${pair[0]}"></div>
      <div class="pr t"><span class="lbl">player</span><img loading="lazy" src="${pair[1]}"></div></div>
      <div class="ctrls">
       <button class="vb k" title="idêntico">✓</button>
       <button class="vb x" title="tem problema">👎</button>
       ${TAGS.map(([k,l])=>`<button class="chip" data-t="${k}">${l}</button>`).join('')}
      </div>`;
    const set=()=>{row.className='mrow'+(S[m]&&S[m].ok?' ok':'')+((S[m]&&(S[m].tags||[]).length||S[m]&&S[m].bad)?' bad':'');
      row.querySelectorAll('.chip').forEach(c=>c.classList.toggle('on',S[m]&&(S[m].tags||[]).includes(c.dataset.t)));};
    row.querySelector('.vb.k').onclick=()=>{S[m]=S[m]||{};S[m].ok=!S[m].ok;if(S[m].ok){S[m].bad=false;S[m].tags=[];}save();set();paintList();};
    row.querySelector('.vb.x').onclick=()=>{S[m]=S[m]||{};S[m].bad=!S[m].bad;if(S[m].bad)S[m].ok=false;save();set();paintList();};
    row.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{S[m]=S[m]||{tags:[]};S[m].tags=S[m].tags||[];const t=c.dataset.t;const i=S[m].tags.indexOf(t);
      if(i<0){S[m].tags.push(t);S[m].ok=false;}else S[m].tags.splice(i,1);save();set();paintList();});
    box.appendChild(row);set();
  });
  window.scrollTo(0,0);paintList();
}
function go(dir){cur=(cur+dir+DATA.length)%DATA.length;render()}
function toggleRev(){const s=DATA[cur].slug;if(rev.has(s))rev.delete(s);else rev.add(s);localStorage.setItem('menq_rev',JSON.stringify([...rev]));render()}
function download(){
  const out=DATA.map(d=>{const S=st[d.slug]||{};const probs=Object.keys(S).filter(m=>S[m].bad||(S[m].tags||[]).length)
     .map(m=>({compasso:+m,tipos:S[m].tags||[]})).sort((a,b)=>a.compasso-b.compasso);
     const oks=Object.keys(S).filter(m=>S[m].ok).map(Number).sort((a,b)=>a-b);
     return {musica:d.title,slug:d.slug,revisada:rev.has(d.slug),validados:oks,problemas:probs};}).filter(x=>x.problemas.length||x.validados.length||x.revisada);
  const blob=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='menq_feedback.json';a.click();}
document.addEventListener('keydown',e=>{if(e.target.tagName==='BUTTON')return;if(e.key==='ArrowLeft')go(-1);if(e.key==='ArrowRight')go(1)});
render();
</script></body></html>'''

if __name__ == '__main__':
    main()
