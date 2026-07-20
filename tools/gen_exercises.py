#!/usr/bin/env python3
"""
gen_exercises — gera specs de exercícios tradicionais de sax alto (escalas, arpejos,
cromática, notas longas, terças, saltos de oitava), com spelling correto por tom e
divisão automática em compassos. Retorna uma lista de dicts (catálogo).

Alturas ESCRITAS (o que o saxofonista lê/dedilha). Registro confortável do alto:
escrito ~Sib3 a Fá6; aqui uso oitavas centrais (4–5).
"""
from fractions import Fraction

LET = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
SHARP_ORDER = ['F', 'C', 'G', 'D', 'A', 'E', 'B']
FLAT_ORDER = ['B', 'E', 'A', 'D', 'G', 'C', 'F']
# tônica maior por nº de acidentes (sustenidos>0, bemóis<0)
MAJ_TONIC = {0: 'C', 1: 'G', 2: 'D', 3: 'A', 4: 'E', 5: 'B',
             -1: 'F', -2: 'B-', -3: 'E-', -4: 'A-', -5: 'D-'}
# nome PT do tom
PT = {'C': 'Dó', 'D': 'Ré', 'E': 'Mi', 'F': 'Fá', 'G': 'Sol', 'A': 'Lá', 'B': 'Si',
      'C#': 'Dó#', 'F#': 'Fá#', 'B-': 'Sib', 'E-': 'Mib', 'A-': 'Láb', 'D-': 'Réb'}


def keysig_map(k):
    m = {L: '' for L in LET}
    if k > 0:
        for L in SHARP_ORDER[:k]:
            m[L] = '#'
    elif k < 0:
        for L in FLAT_ORDER[:-k]:
            m[L] = '-'
    return m


def scale_letters(tonic_letter, n=8):
    s = LET.index(tonic_letter)
    return [LET[(s + i) % 7] for i in range(n)]


def with_octaves(letters, start_oct):
    out, oc = [], start_oct
    for i, L in enumerate(letters):
        if i > 0 and LET.index(L) < LET.index(letters[i - 1]):
            oc += 1
        out.append((L, oc))
    return out


def note(letter_oct, km):
    L, oc = letter_oct
    return f"{L}{km[L]}{oc}"


def chunk(tokens, beats=Fraction(4)):
    """divide lista de tokens (PITCH:QL) em compassos que somam `beats`."""
    meas, cur, acc = [], [], Fraction(0)
    for t in tokens:
        d = Fraction(t.split(':')[1])
        if acc + d > beats and cur:
            meas.append(cur); cur = []; acc = Fraction(0)
        cur.append(t); acc += d
    if cur:
        meas.append(cur)
    # preenche o último compasso com pausa se não fechar
    if meas:
        s = sum(Fraction(t.split(':')[1]) for t in meas[-1])
        if s < beats:
            meas[-1].append(f"R:{beats - s}")
    return meas


def dur(d):
    return d if '/' in str(d) else str(d)


# ---- geradores por tipo ----
def major_scale(k, start_oct=4):
    km = keysig_map(k); ton = MAJ_TONIC[k]
    letters = scale_letters(ton[0], 8)
    up = with_octaves(letters, start_oct)
    seq = up + list(reversed(up[:-1]))          # sobe 8, desce 7 (termina na tônica)
    toks = [note(x, km) + ':0.5' for x in seq[:-1]] + [note(seq[-1], km) + ':1']
    return chunk(toks)


def minor_scale(k, start_oct=4):
    # menor natural = maior relativa começando 6 graus acima; usa a mesma armadura
    km = keysig_map(k); ton = MAJ_TONIC[k]
    minton = scale_letters(ton[0], 6)[-1]       # 6º grau = tônica relativa menor
    letters = scale_letters(minton, 8)
    up = with_octaves(letters, start_oct)
    seq = up + list(reversed(up[:-1]))
    toks = [note(x, km) + ':0.5' for x in seq[:-1]] + [note(seq[-1], km) + ':1']
    return chunk(toks), minton, km


def major_arpeggio(k, start_oct=4):
    km = keysig_map(k); ton = MAJ_TONIC[k]
    letters = scale_letters(ton[0], 8)
    idx = [0, 2, 4, 7]                            # 1 3 5 8
    up = with_octaves([letters[i] for i in idx], start_oct)
    seq = up + list(reversed(up[:-1]))
    toks = [note(x, km) + ':0.5' for x in seq[:-1]] + [note(seq[-1], km) + ':1']
    return chunk(toks)


def minor_arpeggio(k, start_oct=4):
    meas, minton, km = None, None, None
    km = keysig_map(k); ton = MAJ_TONIC[k]
    minton = scale_letters(ton[0], 6)[-1]
    letters = scale_letters(minton, 8)
    idx = [0, 2, 4, 7]
    up = with_octaves([letters[i] for i in idx], start_oct)
    seq = up + list(reversed(up[:-1]))
    toks = [note(x, km) + ':0.5' for x in seq[:-1]] + [note(seq[-1], km) + ':1']
    return chunk(toks), minton


def chromatic(start='C', start_oct=4, n=13):
    # cromática ascendente/descendente com sustenidos (uma oitava)
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    seq = []
    oc = start_oct
    for i in range(n):
        nm = names[i % 12]
        if i > 0 and nm == 'C':
            oc += 1
        seq.append(f"{nm}{oc}")
    full = seq + list(reversed(seq[:-1]))
    toks = [s + ':0.5' for s in full[:-1]] + [full[-1] + ':1']
    return chunk(toks)


def long_tones(start_oct=4, n=8):
    names = ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'C']
    seq = with_octaves(scale_letters('C', n), start_oct)
    km = keysig_map(0)
    toks = [note(x, km) + ':4' for x in seq]     # semibreves
    return chunk(toks)


def thirds(k, start_oct=4):
    km = keysig_map(k); ton = MAJ_TONIC[k]
    letters = scale_letters(ton[0], 8)
    oct_letters = with_octaves(letters, start_oct)
    toks = []
    for i in range(6):                            # C-E, D-F, E-G, F-A, G-B, A-C
        toks.append(note(oct_letters[i], km) + ':0.5')
        toks.append(note(oct_letters[i + 2], km) + ':0.5')
    toks[-1] = toks[-1].rsplit(':', 1)[0] + ':1'
    return chunk(toks)


def octaves(k, start_oct=4):
    km = keysig_map(k); ton = MAJ_TONIC[k]
    letters = scale_letters(ton[0], 8)
    lo = with_octaves(letters, start_oct)
    hi = with_octaves(letters, start_oct + 1)
    toks = []
    for i in range(5):
        toks.append(note(lo[i], km) + ':0.5')
        toks.append(note(hi[i], km) + ':0.5')
    toks[-1] = toks[-1].rsplit(':', 1)[0] + ':1'
    return chunk(toks)


# ---- gerador por SEMITONS (escalas não-diatônicas) ----
NAMES_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
NAMES_FLAT = ['C', 'D-', 'D', 'E-', 'E', 'F', 'G-', 'G', 'A-', 'A', 'B-', 'B']
PC = {'C': 0, 'C#': 1, 'D-': 1, 'D': 2, 'E-': 3, 'E': 4, 'F': 5, 'F#': 6,
      'G': 7, 'A-': 8, 'A': 9, 'B-': 10, 'B': 11}
SCALES = {
    'harm':  [0, 2, 3, 5, 7, 8, 11, 12],       # menor harmônica
    'mel':   [0, 2, 3, 5, 7, 9, 11, 12],       # menor melódica (asc)
    'whole': [0, 2, 4, 6, 8, 10, 12],          # tons inteiros
    'pentM': [0, 2, 4, 7, 9, 12],              # pentatônica maior
    'pentm': [0, 3, 5, 7, 10, 12],             # pentatônica menor
    'blues': [0, 3, 5, 6, 7, 10, 12],          # blues (menor)
    'dim':   [0, 2, 3, 5, 6, 8, 9, 11, 12],    # diminuta (tom-semitom)
    'domdim':[0, 1, 3, 4, 6, 7, 9, 10, 12],    # diminuta dominante (semitom-tom)
    'alt':   [0, 1, 3, 4, 6, 8, 10, 12],       # alterada (super lócrio)
}
MODES = {                                       # modos gregos (a partir da tônica)
    'Jônio':      [0, 2, 4, 5, 7, 9, 11, 12],
    'Dórico':     [0, 2, 3, 5, 7, 9, 10, 12],
    'Frígio':     [0, 1, 3, 5, 7, 8, 10, 12],
    'Lídio':      [0, 2, 4, 6, 7, 9, 11, 12],
    'Mixolídio':  [0, 2, 4, 5, 7, 9, 10, 12],
    'Eólio':      [0, 2, 3, 5, 7, 8, 10, 12],
    'Lócrio':     [0, 1, 3, 5, 6, 8, 10, 12],
}

def _prefer(root):
    return 'flat' if root in ('F', 'B-', 'E-', 'A-', 'D-') else 'sharp'

def by_semitones(root, intervals, start_oct=4):
    tab = NAMES_SHARP if _prefer(root) == 'sharp' else NAMES_FLAT
    base = PC[root] + 12 * (start_oct + 1)
    return [f"{tab[(base+iv) % 12]}{(base+iv)//12 - 1}" for iv in intervals]

def sc_exercise(root, intervals, start_oct=4):
    up = by_semitones(root, intervals, start_oct)
    seq = up + list(reversed(up[:-1]))
    toks = [s + ':0.5' for s in seq[:-1]] + [seq[-1] + ':1']
    return chunk(toks)


def spec(title, cat, k, bpm, measures, tom=''):
    return {"title": title, "categoria": cat, "sharps": k, "flats": 0, "tempo": bpm,
            "time": "4/4", "tom": tom, "measures": measures, "repeats": [""] * len(measures)}


def catalog():
    out = []
    maj_keys = [0, 1, 2, -1, -2, 3]   # C G D F Bb A
    for k in maj_keys:
        t = MAJ_TONIC[k]
        out.append(spec(f"Escala Maior de {PT[t]}", "Escalas", k, 80, major_scale(k), PT[t]))
        out.append(spec(f"Arpejo Maior de {PT[t]}", "Arpejos", k, 80, major_arpeggio(k), PT[t]))
    for k in [0, 1, -1]:              # menores relativas: Lá, Mi, Ré
        ms, mt, km = minor_scale(k)
        out.append(spec(f"Escala Menor de {PT[mt]}", "Escalas", k, 80, ms, PT[mt] + ' menor'))
        ma, mt2 = minor_arpeggio(k)
        out.append(spec(f"Arpejo Menor de {PT[mt2]}", "Arpejos", k, 80, ma, PT[mt2] + ' menor'))
    out.append(spec("Escala Cromática", "Cromática", 0, 80, chromatic(), 'cromática'))
    out.append(spec("Notas Longas (Dó maior)", "Notas longas", 0, 60, long_tones(), 'Dó'))
    out.append(spec("Terças de Dó maior", "Intervalos", 0, 80, thirds(0), 'Dó'))
    out.append(spec("Saltos de Oitava (Dó)", "Intervalos", 0, 76, octaves(0), 'Dó'))
    # menor harmônica / melódica
    for root in ['A', 'E', 'D']:
        out.append(spec(f"Menor Harmônica de {PT[root]}", "Escalas", 0, 80, sc_exercise(root, SCALES['harm']), PT[root]+' menor'))
        out.append(spec(f"Menor Melódica de {PT[root]}", "Escalas", 0, 80, sc_exercise(root, SCALES['mel']), PT[root]+' menor'))
    # pentatônicas e blues
    for root in ['C', 'G', 'F']:
        out.append(spec(f"Pentatônica Maior de {PT[root]}", "Pentatônicas", 0, 84, sc_exercise(root, SCALES['pentM']), PT[root]))
    for root in ['A', 'E', 'D']:
        out.append(spec(f"Pentatônica Menor de {PT[root]}", "Pentatônicas", 0, 84, sc_exercise(root, SCALES['pentm']), PT[root]+' menor'))
    for root in ['C', 'G', 'F']:
        out.append(spec(f"Blues de {PT[root]}", "Pentatônicas", 0, 84, sc_exercise(root, SCALES['blues']), PT[root]))
    # simétricas
    for root in ['C', 'D-']:
        out.append(spec(f"Tons Inteiros de {PT[root]}", "Simétricas", 0, 80, sc_exercise(root, SCALES['whole']), PT[root]))
    for root in ['C', 'C#', 'D']:
        out.append(spec(f"Diminuta de {PT[root]}", "Simétricas", 0, 80, sc_exercise(root, SCALES['dim']), PT[root]))
    for root in ['C', 'G']:
        out.append(spec(f"Diminuta Dominante de {PT[root]}", "Simétricas", 0, 80, sc_exercise(root, SCALES['domdim']), PT[root]))
    for root in ['C', 'G']:
        out.append(spec(f"Escala Alterada de {PT[root]}", "Simétricas", 0, 80, sc_exercise(root, SCALES['alt']), PT[root]))
    # modos gregos (sobre Dó)
    for name, iv in MODES.items():
        out.append(spec(f"{name} de Dó", "Modos", 0, 80, sc_exercise('C', iv), 'Dó'))
    return out


if __name__ == '__main__':
    import json
    for e in catalog():
        tot = [float(sum(Fraction(t.split(':')[1]) for t in m)) for m in e['measures']]
        print(f"{e['title']:32} {e['categoria']:12} {len(e['measures'])}c somas={set(tot)}")
