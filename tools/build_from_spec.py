#!/usr/bin/env python3
"""
build_from_spec — constrói MusicXML a partir de uma transcrição por compasso (JSON).

transcription.json:
{
  "title": "...", "artist": "...", "sharps": 4, "flats": 0,
  "tempo": 90, "time": "4/4",
  "measures": [
     ["R:0.5","F#5:0.5","A5:0.5","F#5:0.5","A5:0.5","A5:0.5","B5:1"],   # 1 compasso
     ...
  ]
}
Tokens: "PITCH:QL[:tie]"  (tie = start|stop|continue) ou "R:QL".
QL em quarter-length (1=semínima, 0.5=colcheia, 0.25=semicolcheia, 1.5=pontuada, 2=mínima, 4=semibreve).

Uso: python3 build_from_spec.py transcription.json saida.musicxml
"""
import sys, json
from music21 import stream, note, meter, key, tempo, clef, instrument, duration
import music21.tie
import music21.spanner
import music21.bar

def build(spec, out):
    s = stream.Score(); p = stream.Part()
    inst = instrument.AltoSaxophone()
    inst.partName = ''; inst.partAbbreviation = ''   # não mostra "Alto Saxophone" na pauta
    p.insert(0, inst); p.insert(0, clef.TrebleClef())
    p.partName = ''; p.partAbbreviation = ''
    p.insert(0, meter.TimeSignature(spec.get('time', '4/4')))
    ks = spec.get('sharps', 0) or -spec.get('flats', 0)
    p.insert(0, key.KeySignature(ks))
    bpm = spec.get('tempo', 100)
    p.insert(0, tempo.MetronomeMark(number=bpm, referent=duration.Duration(1.0)))
    beats = meter.TimeSignature(spec.get('time', '4/4')).barDuration.quarterLength
    from fractions import Fraction
    def dur(x):
        # aceita fração exata ("1/3", "2/3") p/ tercinas/tuplets, ou decimal ("0.5", "1.5")
        x = x.strip()
        v = Fraction(x) if '/' in x else Fraction(str(x))
        return v  # music21 aceita Fraction e cria o tuplet certo
    warns = []
    for i, toks in enumerate(spec['measures']):
        m = stream.Measure(number=i+1)
        for t in toks:
            parts = t.split(':')
            if parts[0].upper() == 'R':
                m.append(note.Rest(quarterLength=dur(parts[1])))
            else:
                nn = note.Note(parts[0]); nn.quarterLength = dur(parts[1])
                if len(parts) > 2 and parts[2]:
                    for extra in parts[2].split(';'):
                        if extra.startswith('beam-'):
                            pass   # beaming é reagrupado por tempo via makeBeams (convenção 4/4)
                        elif extra.startswith('slur-'):
                            nn._slur = extra[5:]   # marcado; vira spanner depois
                        elif extra.startswith('tie-'):
                            nn.tie = music21.tie.Tie(extra[4:])   # tie-start/tie-stop
                        elif extra:
                            nn.tie = music21.tie.Tie(extra)
                m.append(nn)
        tot = sum((Fraction(e.quarterLength).limit_denominator(48) for e in m.notesAndRests), Fraction(0))
        if tot != Fraction(beats).limit_denominator(48):
            warns.append((i+1, float(tot), beats))
        p.append(m)
    # barras de repetição
    reps = spec.get('repeats', [])
    mlist = list(p.getElementsByClass('Measure'))
    for i, r in enumerate(reps):
        if i >= len(mlist) or not r:
            continue
        if r in ('start', 'both'):
            mlist[i].leftBarline = music21.bar.Repeat(direction='start')
        if r in ('end', 'both'):
            mlist[i].rightBarline = music21.bar.Repeat(direction='end')
    # casas 1a/2a (voltas) -> RepeatBracket. spec['endings'] paralelo a measures:
    # "" (sem casa), "1", "2", ... (agrupa compassos consecutivos de mesma casa).
    ends = spec.get('endings', [])
    i = 0
    while i < len(ends):
        e = str(ends[i]).strip().rstrip('.') if i < len(ends) and ends[i] else ''
        if e and i < len(mlist):
            j = i
            while j + 1 < len(ends) and str(ends[j+1]).strip().rstrip('.') == e:
                j += 1
            grp = [mlist[k] for k in range(i, min(j + 1, len(mlist)))]
            try:
                p.insert(0, music21.spanner.RepeatBracket(grp, number=int(e)))
            except Exception:
                pass
            i = j + 1
        else:
            i += 1
    s.append(p)
    # agrupa colcheias/semicolcheias POR TEMPO (convenção 4/4). makeBeams só funciona com a
    # fórmula DENTRO do compasso -> insere temporária, beama, remove.
    tstr = spec.get('time', '4/4')
    for meas in p.getElementsByClass('Measure'):
        try:
            tmp = meter.TimeSignature(tstr)
            meas.insert(0, tmp)
            meas.makeBeams(inPlace=True)
            meas.remove(tmp)
        except Exception:
            pass
    # cria ligaduras (slurs) a partir das marcas slur-start/slur-stop
    open_start = None
    for nn in p.recurse().notes:
        mk = getattr(nn, '_slur', None)
        if mk == 'start':
            open_start = nn
        elif mk == 'stop' and open_start is not None:
            p.insert(0, music21.spanner.Slur(open_start, nn))
            open_start = None
    # não mostra acidentes que já estão na armadura (F#/C#/G#/D# em 4 sustenidos, etc.)
    sharp_steps = ['F', 'C', 'G', 'D', 'A', 'E', 'B'][:ks] if ks > 0 else []
    flat_steps = ['B', 'E', 'A', 'D', 'G', 'C', 'F'][:(-ks)] if ks < 0 else []
    for nn in p.recurse().notes:
        for pp in (nn.pitches if hasattr(nn, 'pitches') else [nn.pitch]):
            if pp.accidental is not None:
                if (pp.accidental.name == 'sharp' and pp.step in sharp_steps) or \
                   (pp.accidental.name == 'flat' and pp.step in flat_steps):
                    pp.accidental.displayStatus = False
    s.write('musicxml', fp=out)
    return warns

def main():
    spec = json.load(open(sys.argv[1], encoding='utf-8'))
    out = sys.argv[2]
    warns = build(spec, out)
    print(f"MusicXML -> {out} ({len(spec['measures'])} compassos)")
    if warns:
        print("AVISO: compassos que não fecham na fórmula:")
        for n, tot, tgt in warns:
            print(f"  compasso {n}: {tot} (esperado {tgt})")
    else:
        print("Todos os compassos fecham na fórmula.")

if __name__ == '__main__':
    main()
