#!/usr/bin/env python3
"""publish.py <slug> [bloco] — roda make_song lendo meta do songs.json + spec.json."""
import sys, json, subprocess, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
slug = sys.argv[1]; bloco = sys.argv[2] if len(sys.argv) > 2 else 'Menq'
songs = json.load(open(os.path.join(ROOT, 'songs.json'), encoding='utf-8'))
s = next((x for x in songs if x.get('_slug') == slug or x.get('slug') == slug), {})
sp = json.load(open(os.path.join(ROOT, f'songs/{slug}/spec.json'), encoding='utf-8'))
KM = {0:'Dó maior',1:'Sol maior (1 ♯)',2:'Ré maior (2 ♯)',3:'Lá maior (3 ♯)',4:'Mi maior (4 ♯)',
      5:'Si maior (5 ♯)',-1:'Fá maior (1 ♭)',-2:'Sib maior (2 ♭)',-3:'Mib maior (3 ♭)',-4:'Láb maior (4 ♭)'}
key = KM.get(sp.get('sharps', 0), '')
d = os.path.join(ROOT, f'songs/{slug}')
subprocess.run([sys.executable, os.path.join(HERE, 'make_song.py'),
    '--mxml', f'{d}/{slug}.musicxml', '--pdf', f'{d}/source.pdf',
    '--bpm', str(sp.get('tempo', 100)), '--title', s.get('title', slug),
    '--artist', s.get('artist', ''), '--key', key, '--bloco', bloco,
    '--slug', slug, '--render-dir', f'{d}/work'])
