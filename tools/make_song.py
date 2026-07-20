#!/usr/bin/env python3
"""
make_song — orquestra a publicação de UMA música já transcrita (MusicXML).

Faz: injeta tempo -> MIDI -> MP3 de sax -> player HTML -> QA -> (se QA essencial
passar) gera miniatura, atualiza songs.json e regenera a Biblioteca.

Todos os artefatos da música vão para songs/<slug>/ (player, mp3, musicxml,
validacao, thumb, source.pdf; scratch/QA em songs/<slug>/work/).

Uso:
  python3 make_song.py \
     --mxml song.musicxml --pdf original.pdf --bpm 112 \
     --title "Mania de Você" --artist "Rita Lee" \
     --key "Dó# menor (4 ♯)" --bloco "Metaverso" "Lança Perfume" \
     --slug Mania_de_Voce [--root <pasta>] [--force]

--force publica mesmo com falha nos checks que travam (não recomendado).
"""
import argparse, os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import saxlib

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mxml', required=True); ap.add_argument('--pdf', required=True)
    ap.add_argument('--bpm', type=float, required=True)
    ap.add_argument('--title', required=True); ap.add_argument('--artist', default='')
    ap.add_argument('--key', default=''); ap.add_argument('--instrument', default='Sax Alto (Mib)')
    ap.add_argument('--bloco', nargs='*', default=[])
    ap.add_argument('--slug', required=True)
    ap.add_argument('--root', default=os.path.dirname(HERE))
    ap.add_argument('--render-dir', default=None, help='pasta com vmeasures.json/vcrops p/ gerar a página de validação')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    root = a.root
    # cada música mora em songs/<slug>/ com tudo self-contained
    sdir = os.path.join(root, 'songs', a.slug); os.makedirs(sdir, exist_ok=True)
    work = os.path.join(sdir, 'work'); os.makedirs(work, exist_ok=True)

    meta = {"title": a.title, "artist": a.artist, "key": a.key,
            "instrument": a.instrument, "tempo": f"♩ = {int(a.bpm)}",
            "bloco": a.bloco, "slug": a.slug,
            "file": f"songs/{a.slug}/{a.slug}_player.html",
            "thumb": f"songs/{a.slug}/thumb.png"}

    # guarda uma cópia do PDF de origem dentro da pasta da música
    src_pdf = os.path.join(sdir, 'source.pdf')
    if os.path.abspath(a.pdf) != os.path.abspath(src_pdf):
        import shutil; shutil.copyfile(a.pdf, src_pdf)

    # 1) tempo
    saxlib.inject_tempo(a.mxml, a.bpm)
    mp3 = os.path.join(sdir, f"{a.slug}_sax.mp3")

    # 2) player (sintetiza o MP3 a partir do MIDI do verovio: repetições desdobradas)
    player = os.path.join(root, meta["file"])
    info = saxlib.build_player(a.mxml, mp3, meta, player, a.bpm, pdf_path=a.pdf)
    print("MP3:", mp3, "| Player:", player, info)

    # 3) QA
    qa_out = os.path.join(work, 'qa'); os.makedirs(qa_out, exist_ok=True)
    qa = subprocess.run([sys.executable, os.path.join(HERE, 'validate_qa.py'),
                         '--mxml', a.mxml, '--mp3', mp3, '--pdf', a.pdf,
                         '--bpm', str(a.bpm), '--out', qa_out, '--title', a.title])
    passed = (qa.returncode == 0)
    if not passed and not a.force:
        print("\n>>> QA travou. Corrija (veja songs/%s/work/qa/qa_comparacao.png) ou use --force." % a.slug)
        sys.exit(2)

    # 4) thumbnail (topo da 1a página do PDF)
    base = os.path.join(work, a.slug+'_pg')
    subprocess.run(['pdftoppm', '-r', '150', '-png', '-f', '1', '-l', '1', a.pdf, base], check=True)
    from PIL import Image
    pgs = sorted(f for f in os.listdir(work) if f.startswith(a.slug+'_pg') and f.endswith('.png'))
    if pgs:
        im = Image.open(os.path.join(work, pgs[0])).convert('RGB')
        t = im.crop((60, 60, im.width-40, 700)); r = 680/t.width; t = t.resize((680, int(t.height*r)))
        t.save(os.path.join(sdir, 'thumb.png'))

    # 5) manifest + biblioteca
    manifest = os.path.join(root, 'songs.json')
    songs = json.load(open(manifest, encoding='utf-8')) if os.path.exists(manifest) else []
    songs = [s for s in songs if s.get('file') != meta['file'] and s.get('slug') != a.slug]
    songs.append(meta)
    json.dump(songs, open(manifest, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    subprocess.run([sys.executable, os.path.join(HERE, 'update_biblioteca.py'), '--root', root], check=True)

    # 6) página de validação (SEMPRE que houver render-dir do extrator)
    rd = a.render_dir or work
    vmeas = os.path.join(rd, 'vmeasures.json')
    if os.path.exists(vmeas):
        val = os.path.join(sdir, f"{a.slug}_validacao.html")
        subprocess.run([sys.executable, os.path.join(HERE, 'build_validation.py'),
                        '--mxml', a.mxml, '--render-dir', rd, '--measures', vmeas,
                        '--out', val, '--title', a.title])
        print("Validação:", val)
    else:
        print("(sem vmeasures.json em %s — página de validação não gerada; rode vector_extract com --crops)" % rd)
    print("\nPUBLICADO:" if passed else "PUBLICADO (--force, com avisos):", a.title)

if __name__ == '__main__':
    main()
