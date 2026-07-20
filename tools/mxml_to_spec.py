#!/usr/bin/env python3
"""
mxml_to_spec — deriva um spec.json a partir de um MusicXML já correto.

Use para músicas feitas ANTES do extrator vetorial (sem spec.json), quando
re-extrair do PDF introduziria erros. O MusicXML validado vira a fonte do spec,
que passa a ser a fonte-da-verdade editável (o pipeline padrão segue daí).

Captura: armadura, andamento, fórmula, notas (PITCH:QL) e pausas (R:QL), ties
(tie-start/stop/continue), slurs (slur-start/stop) e barras de repetição.

Uso: python3 mxml_to_spec.py entrada.musicxml saida_spec.json [--tempo N]
"""
import sys, json, argparse
from music21 import converter, spanner


def ql(x):
    # inteiro quando possível (0.5, 0.75, 1.0, 1.5, 2.0 ...)
    return int(x) if float(x).is_integer() else float(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mxml'); ap.add_argument('out')
    ap.add_argument('--tempo', type=int, default=None)
    a = ap.parse_args()

    s = converter.parse(a.mxml)
    p = s.parts[0]

    ks = 0
    kobj = p.recurse().getElementsByClass('KeySignature')
    if kobj:
        ks = kobj[0].sharps
    tsig = p.recurse().getElementsByClass('TimeSignature')
    time = tsig[0].ratioString if tsig else '4/4'
    tempo = a.tempo
    if tempo is None:
        mm = p.recurse().getElementsByClass('MetronomeMark')
        tempo = int(mm[0].number) if mm and mm[0].number else 100

    # notas dentro de slurs -> marca start/stop
    slur_start, slur_stop = set(), set()
    for sp in p.recurse().getElementsByClass(spanner.Slur):
        els = sp.getSpannedElements()
        if len(els) >= 2:
            slur_start.add(id(els[0])); slur_stop.add(id(els[-1]))

    measures, repeats = [], []
    for m in p.getElementsByClass('Measure'):
        toks = []
        for el in m.notesAndRests:
            if el.isRest:
                toks.append(f"R:{ql(el.quarterLength)}")
                continue
            nm = el.pitches[0].nameWithOctave if el.isChord else el.pitch.nameWithOctave
            extras = []
            if el.tie is not None:
                extras.append('tie-' + el.tie.type)
            if id(el) in slur_start:
                extras.append('slur-start')
            if id(el) in slur_stop:
                extras.append('slur-stop')
            tok = f"{nm}:{ql(el.quarterLength)}"
            if extras:
                tok += ':' + ';'.join(extras)
            toks.append(tok)
        measures.append(toks)
        # repetição
        r = ''
        lb = getattr(m, 'leftBarline', None); rb = getattr(m, 'rightBarline', None)
        ls = lb is not None and lb.classes and 'Repeat' in lb.classes
        rs = rb is not None and rb.classes and 'Repeat' in rb.classes
        if ls and rs: r = 'both'
        elif ls: r = 'start'
        elif rs: r = 'end'
        repeats.append(r)

    spec = {"title": "", "artist": "", "sharps": ks, "flats": 0,
            "tempo": tempo, "time": time, "measures": measures, "repeats": repeats,
            "source": "musicxml (pré-extrator; derivado por mxml_to_spec.py)"}
    json.dump(spec, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    nrep = [i+1 for i, x in enumerate(repeats) if x]
    print(f"{len(measures)} compassos -> {a.out} | ks={ks} time={time} tempo={tempo} | repeats@{nrep}")


if __name__ == '__main__':
    main()
