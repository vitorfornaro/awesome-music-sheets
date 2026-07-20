#!/usr/bin/env python3
"""update_exercicios — gera Exercicios.html a partir de exercicios.json (com filtro por categoria/tom)."""
import argparse, os, json, base64

PAGE = '''<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0">
<title>Exercícios — Sax Alto</title>
<style>
  :root{ --accent:#2e7d5b; --bg:#faf9f7; --ink:#1a1a1a; --card:#fff; }
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);}
  header{padding:34px 24px 10px;max-width:1000px;margin:0 auto;}
  h1{font-size:28px;margin:0 0 4px;letter-spacing:-.4px;}
  .sub{color:#666;font-size:14px;margin:0;} .count{color:#999;font-size:13px;margin-top:6px;}
  a.nav{color:var(--accent);font-size:13px;font-weight:600;text-decoration:none;}
  #filters{max-width:1000px;margin:0 auto;padding:6px 24px 0;display:flex;flex-wrap:wrap;gap:20px;align-items:center;}
  .fgroup{display:flex;gap:8px;align-items:center;flex-wrap:wrap;}
  .flabel{font-size:11px;color:#999;text-transform:uppercase;letter-spacing:.6px;}
  .fbtn{border:1px solid #ddd;background:#fff;color:#555;border-radius:16px;padding:6px 13px;font-size:13px;font-weight:600;cursor:pointer;}
  .fbtn.on{background:var(--accent);border-color:var(--accent);color:#fff;}
  main{max-width:1000px;margin:0 auto;padding:18px 24px 60px;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px;}
  .card{background:var(--card);border:1px solid #ececec;border-radius:16px;overflow:hidden;cursor:pointer;text-decoration:none;color:inherit;transition:transform .12s,box-shadow .12s;display:flex;flex-direction:column;}
  .card:hover{transform:translateY(-3px);box-shadow:0 12px 28px rgba(0,0,0,.10);}
  .thumb{background:#fff;border-bottom:1px solid #f0f0f0;height:120px;overflow:hidden;display:flex;align-items:center;justify-content:center;}
  .thumb img{width:100%;object-fit:cover;object-position:top;}
  .body{padding:14px 16px 16px;}
  .title{font-size:16px;font-weight:700;margin:0 0 6px;}
  .meta{color:#777;font-size:12.5px;margin:0 0 10px;display:flex;gap:10px;flex-wrap:wrap;}
  .tag{display:inline-flex;background:#e7f2ec;color:var(--accent);border-radius:20px;padding:5px 11px;font-size:12px;font-weight:600;}
  .badge{display:inline-block;background:#e7f2ec;color:var(--accent);border-radius:20px;padding:7px 14px;font-size:13px;font-weight:600;margin-top:10px;}
  footer{max-width:1000px;margin:0 auto;padding:0 24px 40px;color:#aaa;font-size:12px;}
</style></head><body>
<header><h1>Exercícios & Arpejos</h1>
<p class="sub">Sax Alto (Mib) · escalas, arpejos, cromática, notas longas e intervalos · som de sax + cursor</p>
<p class="count" id="count"></p>
<p style="display:flex;gap:18px;flex-wrap:wrap;">
<a class="nav" href="Biblioteca.html">← Biblioteca de músicas</a>
<a class="nav" href="Validador.html">🎷 Validador (compasso a compasso) →</a>
<a class="nav" href="SightReader.html">🎮 Sight Reader (jogo) →</a></p></header>
<div id="filters">
  <div class="fgroup"><span class="flabel">Categoria</span><span id="fcat"></span></div>
  <div class="fgroup"><span class="flabel">Tom</span><span id="ftom"></span></div>
</div>
<main id="grid"></main>
<footer>Clique num exercício para praticar com o player.</footer>
<script>
const EX=__EX__;
const grid=document.getElementById('grid');
EX.forEach(s=>{
  const a=document.createElement('a'); a.className='card'; a.href=s.file;
  a.dataset.cat=s.categoria||''; a.dataset.tom=s.tom||'';
  a.innerHTML=`<div class="thumb">${s.thumb?`<img src="${s.thumb}" alt="">`:''}</div>
    <div class="body"><p class="title">${s.title}</p>
    <p class="meta"><span>${s.instrument||''}</span><span>${s.tempo||''}</span></p>
    <div><span class="tag">${s.categoria||''}</span></div><span class="badge">▶ Praticar</span></div>`;
  grid.appendChild(a);
});
let fC='*', fT='*';
const cats=[...new Set(EX.map(s=>s.categoria).filter(Boolean))];
const toms=[...new Set(EX.map(s=>s.tom).filter(Boolean))];
function chips(cont,list,cur,set){
  cont.innerHTML='';
  const mk=(v,txt)=>{const b=document.createElement('button');b.className='fbtn'+(cur===v?' on':'');b.textContent=txt;b.onclick=()=>{set(v);render();};return b;};
  cont.appendChild(mk('*','Todas')); list.forEach(v=>cont.appendChild(mk(v,v)));
}
function render(){
  chips(document.getElementById('fcat'),cats,fC,v=>fC=v);
  chips(document.getElementById('ftom'),toms,fT,v=>fT=v);
  let n=0;
  document.querySelectorAll('#grid .card').forEach(c=>{
    const ok=(fC==='*'||c.dataset.cat===fC)&&(fT==='*'||c.dataset.tom===fT);
    c.style.display=ok?'':'none'; if(ok)n++;
  });
  document.getElementById('count').textContent=n+' exercício'+(n===1?'':'s');
}
render();
</script></body></html>'''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args()
    ex = json.load(open(os.path.join(a.root, 'exercicios.json'), encoding='utf-8'))
    order = {'Escalas':0,'Arpejos':1,'Cromática':2,'Intervalos':3,'Notas longas':4}
    ex.sort(key=lambda s: (order.get(s.get('categoria'),9), s.get('title','')))
    for s in ex:
        fp = os.path.join(a.root, s.get('file',''))
        if s.get('file') and os.path.exists(fp):
            s['file'] = s['file'] + '?v=' + str(int(os.path.getmtime(fp)))
        th = s.get('thumb')
        if th and not th.startswith('data:'):
            p = os.path.join(a.root, th)
            s['thumb'] = 'data:image/png;base64,' + base64.b64encode(open(p,'rb').read()).decode() if os.path.exists(p) else ''
    html = PAGE.replace('__EX__', json.dumps(ex, ensure_ascii=False))
    out = os.path.join(a.root, 'Exercicios.html')
    open(out, 'w', encoding='utf-8').write(html)
    print(f"Exercicios.html gerada com {len(ex)} exercício(s) -> {out}")

if __name__ == '__main__':
    main()
