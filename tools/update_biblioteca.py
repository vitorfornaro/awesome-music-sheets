#!/usr/bin/env python3
"""
update_biblioteca — gera Biblioteca.html a partir do manifesto songs.json.

songs.json (na raiz do projeto) = lista de:
  {"title","artist","key","instrument","tempo","bloco":[...],"file","thumb"}
'thumb' é caminho relativo a um PNG (ou vazio). É embutido em base64.

Uso: python3 update_biblioteca.py [--root <pasta_projeto>]
"""
import argparse, os, json, base64

PAGE = '''<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"><meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0">
<title>Biblioteca de Partituras — Sax Alto</title>
<style>
  :root{ --accent:#c0392b; --bg:#faf9f7; --ink:#1a1a1a; --card:#fff; }
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);}
  header{padding:34px 24px 10px;max-width:1000px;margin:0 auto;}
  h1{font-size:28px;margin:0 0 4px;letter-spacing:-.4px;}
  .sub{color:#666;font-size:14px;margin:0;} .count{color:#999;font-size:13px;margin-top:6px;}
  main{max-width:1000px;margin:0 auto;padding:18px 24px 60px;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;}
  .card{background:var(--card);border:1px solid #ececec;border-radius:16px;overflow:hidden;cursor:pointer;text-decoration:none;color:inherit;transition:transform .12s,box-shadow .12s;display:flex;flex-direction:column;}
  .card:hover{transform:translateY(-3px);box-shadow:0 12px 28px rgba(0,0,0,.10);}
  .thumb{background:#fff;border-bottom:1px solid #f0f0f0;height:150px;overflow:hidden;display:flex;align-items:center;justify-content:center;}
  .thumb img{width:100%;object-fit:cover;object-position:top;}
  .body{padding:16px 18px 18px;}
  .title{font-size:18px;font-weight:700;margin:0 0 2px;}
  .key{color:var(--accent);font-size:14px;font-weight:600;margin:0 0 10px;}
  .meta{color:#777;font-size:12.5px;margin:0 0 10px;display:flex;gap:12px;flex-wrap:wrap;}
  .tags{display:flex;gap:8px;flex-wrap:wrap;} .tag{display:inline-flex;background:#f2efe9;color:#555;border-radius:20px;padding:5px 11px;font-size:12px;font-weight:600;}
  .badge{display:inline-block;background:#faeceb;color:var(--accent);border-radius:20px;padding:7px 14px;font-size:13px;font-weight:600;margin-top:12px;}
  footer{max-width:1000px;margin:0 auto;padding:0 24px 40px;color:#aaa;font-size:12px;}
  .rep-h{max-width:1000px;margin:10px auto 0;padding:20px 24px 0;border-top:1px solid #ececec;}
  .rep-h h2{font-size:19px;margin:14px 0 2px;} .rep-h p{color:#999;font-size:13px;margin:0;}
  #repgrid{max-width:1000px;margin:0 auto;padding:18px 24px 60px;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;}
  .card.soon{cursor:default;opacity:.72;filter:saturate(.5);}
  .card.soon:hover{transform:none;box-shadow:none;}
  .card.soon .thumb{background:#f4f2ee;}
  .soonbadge{background:#e6e3de;color:#888;border-radius:20px;padding:6px 14px;font-size:12px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;}
  .badge.soon-b{background:#eee;color:#999;}
  #filters{max-width:1000px;margin:0 auto;padding:6px 24px 0;display:flex;flex-wrap:wrap;gap:20px;align-items:center;}
  .fgroup{display:flex;gap:8px;align-items:center;flex-wrap:wrap;}
  .flabel{font-size:11px;color:#999;text-transform:uppercase;letter-spacing:.6px;}
  .fbtn{border:1px solid #ddd;background:#fff;color:#555;border-radius:16px;padding:6px 13px;font-size:13px;font-weight:600;cursor:pointer;}
  .fbtn.on{background:var(--accent);border-color:var(--accent);color:#fff;}
</style></head><body>
<header><h1>Biblioteca de Partituras</h1>
<p class="sub">Sax Alto (Mib) · toque com áudio e acompanhe nota a nota</p>
<p class="count" id="count"></p>
<p style="display:flex;gap:18px;flex-wrap:wrap;">
<a href="Exercicios.html" style="color:#2e7d5b;font-size:13px;font-weight:600;text-decoration:none;">🎵 Exercícios & Arpejos →</a>
<a href="Validador.html" style="color:#2e7d5b;font-size:13px;font-weight:600;text-decoration:none;">🎷 Validador (compasso a compasso) →</a>
<a href="SightReader.html" style="color:#2e7d5b;font-size:13px;font-weight:600;text-decoration:none;">🎮 Sight Reader (jogo) →</a></p></header>
<div id="filters">
  <div class="fgroup"><span class="flabel">Bloco</span><span id="fbloco"></span></div>
  <div class="fgroup"><span class="flabel">Status</span><span id="fstatus"></span></div>
</div>
<main id="grid"></main>
<footer>Clique numa música pronta para abrir o player.</footer>
<script>
const SONGS=__SONGS__;
const grid=document.getElementById('grid');
const STLABEL={pronto:'Prontas',rascunho:'Rascunhos',futuro:'Em breve'};
SONGS.forEach(s=>{
  const blocos=(s.bloco||[]), soon=s.status==='futuro';
  const el=document.createElement(soon?'div':'a');
  el.className='card'+(soon?' soon':'');
  el.dataset.blocos=blocos.join('|'); el.dataset.status=s.status||'pronto';
  if(!soon) el.href=s.file;
  const tags=blocos.map(b=>`<span class="tag">${b}</span>`).join('');
  if(soon){
    el.innerHTML=`<div class="thumb"><span class="soonbadge">em breve</span></div>
      <div class="body"><p class="title">${s.title}</p>
      <p class="meta"><span>${s.artist||'—'}</span><span>${s.vozes?s.vozes+' vozes':''}</span></p>
      <div class="tags">${tags}</div><span class="badge soon-b">na fila #${s.fila||''}</span></div>`;
  }else{
    const rasc=s.status==='rascunho'?'<span class="tag" style="background:#fdecd8;color:#a86520">rascunho</span>':'';
    el.innerHTML=`<div class="thumb">${s.thumb?`<img src="${s.thumb}" alt="">`:''}</div>
      <div class="body"><p class="title">${s.title}</p><p class="key">${s.key||''}</p>
      <p class="meta"><span>${s.artist||''}</span><span>${s.instrument||''}</span><span>${s.tempo||''}</span></p>
      <div class="tags">${tags}${rasc}</div><span class="badge">▶ Abrir player</span></div>`;
  }
  grid.appendChild(el);
});
let fB='*', fS='*';
const blocosSet=[...new Set(SONGS.flatMap(s=>s.bloco||[]))].sort();
const statusSet=['pronto','rascunho','futuro'].filter(st=>SONGS.some(s=>(s.status||'pronto')===st));
function chips(cont,list,cur,labelAll,labelFn,set){
  cont.innerHTML='';
  const mk=(v,txt)=>{const b=document.createElement('button');b.className='fbtn'+(cur===v?' on':'');b.textContent=txt;b.onclick=()=>{set(v);render();};return b;};
  cont.appendChild(mk('*',labelAll));
  list.forEach(v=>cont.appendChild(mk(v,labelFn?labelFn(v):v)));
}
function render(){
  chips(document.getElementById('fbloco'),blocosSet,fB,'Todos',null,v=>fB=v);
  chips(document.getElementById('fstatus'),statusSet,fS,'Todas',v=>STLABEL[v],v=>fS=v);
  let n=0;
  document.querySelectorAll('#grid .card').forEach(c=>{
    const okB=fB==='*'||c.dataset.blocos.split('|').includes(fB);
    const okS=fS==='*'||c.dataset.status===fS;
    const show=okB&&okS; c.style.display=show?'':'none'; if(show)n++;
  });
  document.getElementById('count').textContent=n+' música'+(n===1?'':'s');
}
render();
</script></body></html>'''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args()
    songs = json.load(open(os.path.join(a.root, 'songs.json'), encoding='utf-8'))
    for s in songs:
        # cache-busting: cada rebuild do player vira uma URL nova (evita cache do navegador)
        fp = os.path.join(a.root, s.get('file', ''))
        if s.get('file') and os.path.exists(fp):
            s['file'] = s['file'] + '?v=' + str(int(os.path.getmtime(fp)))
        th = s.get('thumb')
        if th and not th.startswith('data:'):
            p = os.path.join(a.root, th)
            if os.path.exists(p):
                s['thumb'] = 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode()
            else:
                s['thumb'] = ''
    html = PAGE.replace('__SONGS__', json.dumps(songs, ensure_ascii=False))
    out = os.path.join(a.root, 'Biblioteca.html')
    open(out, 'w', encoding='utf-8').write(html)
    print(f"Biblioteca.html gerada com {len(songs)} música(s) -> {out}")

if __name__ == '__main__':
    main()
