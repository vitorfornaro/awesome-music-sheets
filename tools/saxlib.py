#!/usr/bin/env python3
"""
saxlib — biblioteca central do fluxo de partituras para sax alto.

Funções reutilizáveis:
  - inject_tempo(mxml_path, bpm)        : garante <sound tempo> no MusicXML (verovio lê)
  - musicxml_to_midi(mxml, midi)        : MusicXML -> MIDI (via music21)
  - synth_sax(midi, wav)                : MIDI -> WAV timbre de sax (síntese aditiva)
  - wav_to_mp3(wav, mp3)                : WAV -> MP3 (ffmpeg)
  - render_svg_timemap(mxml, bpm)       : -> (svg_responsivo, {id:{start,end}})
  - build_player(mxml, mp3, meta, out)  : player HTML estático (SVG+timemap+MP3 embutidos)

Depende de: music21, verovio, pretty_midi, numpy, ffmpeg (no PATH).
"""
import os, re, json, subprocess, wave
import numpy as np

SR = 44100

# ---------------------------------------------------------------- MusicXML/MIDI
def inject_tempo(mxml_path, bpm):
    x = open(mxml_path, encoding='utf-8').read()
    if '<sound tempo' in x:
        return
    d = (f'      <direction placement="above">\n'
         f'        <direction-type><metronome parentheses="no">'
         f'<beat-unit>quarter</beat-unit><per-minute>{int(bpm)}</per-minute></metronome></direction-type>\n'
         f'        <sound tempo="{int(bpm)}"/>\n'
         f'      </direction>\n')
    if '      </attributes>\n' in x:
        x = x.replace('      </attributes>\n', '      </attributes>\n' + d, 1)
        open(mxml_path, 'w', encoding='utf-8').write(x)

def musicxml_to_midi(mxml, midi):
    from music21 import converter
    s = converter.parse(mxml)
    s.write('midi', fp=midi)

# ---------------------------------------------------------------- Síntese sax
_HARM = np.array([1.0, 0.55, 0.72, 0.30, 0.22, 0.14, 0.10, 0.07, 0.05, 0.035])

def _adsr(n, A=.02, D=.06, S=.82, R=.06):
    a, d, r = int(A*SR), int(D*SR), int(R*SR)
    s = max(1, n-a-d-r)
    env = np.concatenate([
        np.linspace(0, 1, a, endpoint=False) if a else np.array([]),
        np.linspace(1, S, d, endpoint=False) if d else np.array([]),
        np.full(s, S),
        np.linspace(S, 0, r) if r else np.array([]),
    ])
    if len(env) < n:
        env = np.concatenate([env, np.full(n-len(env), 0.)])
    return env[:n]

def synth_sax(midi, wav):
    import pretty_midi
    pm = pretty_midi.PrettyMIDI(midi)
    notes = pm.instruments[0].notes if pm.instruments else []
    end = pm.get_end_time() + 0.6
    buf = np.zeros(int(end*SR)+1)
    for nt in notes:
        f0 = 440*2**((nt.pitch-69)/12); n = int((nt.end-nt.start)*SR)
        if n <= 0:
            continue
        t = np.arange(n)/SR; onset = int(.12*SR); vib = np.zeros(n)
        if n > onset:
            ramp = np.clip((np.arange(n)-onset)/(.15*SR), 0, 1)
            vib = .006*ramp*np.sin(2*np.pi*5*t)
        ph = 2*np.pi*f0*(t + np.cumsum(vib)/SR); w = np.zeros(n)
        for k, a in enumerate(_HARM, 1):
            if f0*k > 12000:
                break
            w += a*np.sin(k*ph)
        w /= _HARM.sum()
        sig = (w + np.random.randn(n)*.015) * _adsr(n) * (nt.velocity/127)
        st = int(nt.start*SR); buf[st:st+n] += sig
    pk = np.max(np.abs(buf))
    if pk > 0:
        buf = buf/pk*0.89
    buf = np.tanh(buf*1.1)/np.tanh(1.1)
    w = wave.open(wav, 'w'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((buf*32767).astype(np.int16).tobytes()); w.close()
    return end

def wav_to_mp3(wav, mp3, bitrate='192k'):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav,
                    '-codec:a', 'libmp3lame', '-b:a', bitrate, mp3], check=True)

# ---------------------------------------------------------------- Verovio render
def render_svg_timemap(mxml, bpm):
    import verovio
    inject_tempo(mxml, bpm)
    tk = verovio.toolkit()
    tk.setOptions({"pageWidth": 1500, "pageHeight": 14000, "scale": 42,
                   "adjustPageHeight": True, "breaks": "auto", "footer": "none",
                   "header": "none", "spacingStaff": 12, "font": "Leipzig",
                   "pageMarginTop": 40})
    # remove o nome do instrumento (não deve ficar sobre a pauta)
    data = open(mxml, encoding='utf-8').read()
    data = re.sub(r'<part-name[^>]*>.*?</part-name>', '<part-name/>', data, flags=re.S)
    data = re.sub(r'<part-abbreviation[^>]*>.*?</part-abbreviation>', '', data, flags=re.S)
    tk.loadData(data); tk.redoLayout()
    svg = tk.renderToSVG(1)
    m = re.search(r'<svg width="(\d+)px" height="(\d+)px"', svg)
    if m:
        W, H = m.group(1), m.group(2)
        svg = svg.replace(f'<svg width="{W}px" height="{H}px"',
                          f'<svg viewBox="0 0 {W} {H}" width="100%" preserveAspectRatio="xMidYMid meet"', 1)
    tm = tk.renderToTimemap({"includeMeasures": False, "includeRests": False})
    if isinstance(tm, str):
        tm = json.loads(tm)
    # timemap desdobra repetições (2a volta = id "-rend2"); junta as janelas pelo id base do SVG
    def base(i):
        return re.sub(r'-rend\d+$', '', i)
    notes = {}      # base_id -> [[start,end], ...]
    openw = {}      # rend_id -> start
    last = 0
    for e in tm:
        last = max(last, e["tstamp"])
        for i in e.get('on', []):
            openw[i] = e["tstamp"]
        for i in e.get('off', []):
            if i in openw:
                notes.setdefault(base(i), []).append([openw.pop(i), e["tstamp"]])
    for i, s in openw.items():
        notes.setdefault(base(i), []).append([s, last+300])
    # MIDI do verovio (já desdobrado) para o áudio respeitar a repetição
    import base64 as _b64
    midi_bytes = _b64.b64decode(tk.renderToMIDI())
    return svg, notes, midi_bytes

# ---------------------------------------------------------------- Player HTML
_TEMPLATE = os.path.join(os.path.dirname(__file__), 'player_template.html')

def _pdf_images_html(pdf_path):
    """Renderiza cada página do PDF original em PNG base64 (para painel de comparação)."""
    if not pdf_path or not os.path.exists(pdf_path):
        return ""
    import base64
    try:
        import fitz
        doc = fitz.open(pdf_path)
        imgs = []
        for pg in doc:
            pix = pg.get_pixmap(matrix=fitz.Matrix(2, 2))
            b = base64.b64encode(pix.tobytes("png")).decode()
            imgs.append(f'<img src="data:image/png;base64,{b}" alt="">')
        return "".join(imgs)
    except Exception:
        return ""

def build_player(mxml, mp3, meta, out_html, bpm, pdf_path=None):
    import base64, tempfile
    svg, notes, midi_bytes = render_svg_timemap(mxml, bpm)
    # sintetiza o MP3 a partir do MIDI do verovio (repetições já desdobradas)
    md = tempfile.mktemp(suffix='.mid'); open(md, 'wb').write(midi_bytes)
    wav = tempfile.mktemp(suffix='.wav'); synth_sax(md, wav)
    wav_to_mp3(wav, mp3)
    tpl = open(_TEMPLATE, encoding='utf-8').read()
    b64 = base64.b64encode(open(mp3, 'rb').read()).decode()
    sub = f"{meta.get('instrument','Sax Alto (Mib)')} · ♩ = {int(bpm)} · {meta.get('key','')} · som de sax + marcação nota a nota"
    html = (tpl.replace('__TITLE__', meta.get('title', ''))
               .replace('__ARTIST__', meta.get('artist', ''))
               .replace('__SUBLINE__', sub)
               .replace('__SVG__', svg)
               .replace('__ORIGINAL__', _pdf_images_html(pdf_path))
               .replace('__LOOP__', 'true' if meta.get('loop') else 'false')
               .replace('__TIMEMAP__', json.dumps(notes))
               .replace('__MP3_SRC__', 'data:audio/mp3;base64,'+b64))
    open(out_html, 'w', encoding='utf-8').write(html)
    missing = [i for i in notes if f'id="{i}"' not in svg]
    return {"notes": len(notes), "missing_ids": len(missing), "kb": round(len(html)/1024)}
