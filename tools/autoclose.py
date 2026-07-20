#!/usr/bin/env python3
"""
autoclose — conserta compassos que não fecham em 4/4 num spec.json, com heurística
de TERCINA. Uso: python3 autoclose.py spec.json

Regra:
- compasso com 6 notas (sem pausa) somando 6.0 (lidas como semínimas) => tercina de
  semínima: cada nota vira 2/3 (soma 4.0). É o caso comum de run de tercinas.
- compasso com 3 notas somando 3.0 no 1º-2º tempo + resto => 1ª metade tercina (2/3)
  se com isso fechar.
- senão: fecha mecanicamente (pausa no fim se faltar; corta do fim se sobrar) e MARCA.
Imprime o que fez p/ a auto-avaliação.
"""
import sys, json
from fractions import Fraction

BEATS = Fraction(4)   # sobrescrito em main() pela fórmula do spec
def dur(t): return Fraction(t.split(':')[1])
def tot(m): return sum((dur(t) for t in m), Fraction(0))
def isnote(t): return not t.upper().startswith('R')

def fix(m):
    t = tot(m)
    if t == BEATS: return m, None
    notes = [x for x in m if isnote(x)]
    # caso tercina: 6 notas, sem pausa, soma 6 (semínimas) -> 2/3 cada (só faz sentido em 4/4)
    if BEATS == 4 and len(m) == 6 and all(isnote(x) for x in m) and t == 6:
        return [x.rsplit(':',1)[0] + ':2/3' if x.count(':')>=1 else x for x in
                [ (':'.join(x.split(':')[:1]) + ':2/3' + ('' if len(x.split(':'))<3 else ':'+':'.join(x.split(':')[2:]))) for x in m]], 'tercina'
    # 3 notas somando 3 no começo + resto que fecha com tercina na 1a metade
    if BEATS == 4 and len(notes) >= 3 and all(isnote(x) for x in m[:3]) and dur(m[0])==1 and dur(m[1])==1 and dur(m[2])==1:
        cand = [m[0].split(':')[0]+':2/3', m[1].split(':')[0]+':2/3', m[2].split(':')[0]+':2/3'] + m[3:]
        if tot(cand) == 4: return cand, 'tercina(1/2)'
    # fechamento mecânico
    m = list(m)
    if t < BEATS: m = m + [f'R:{BEATS-t}']
    else:
        over = t - BEATS
        while over > 0 and m:
            d = dur(m[-1])
            if d <= over: over -= d; m.pop()
            else:
                h = m[-1].split(':'); h[1] = str(d-over); m[-1] = ':'.join(h); over = Fraction(0)
    return m, 'mecânico'

def main():
    global BEATS
    sp = sys.argv[1]; s = json.load(open(sp)); M = s['measures']
    t = s.get('time', '4/4').split('/'); BEATS = Fraction(int(t[0]))*4/int(t[1])
    trip, mech = [], []
    for i, m in enumerate(M):
        nm, how = fix(m)
        if how == 'tercina' or how == 'tercina(1/2)': M[i] = nm; trip.append(i+1)
        elif how == 'mecânico': M[i] = nm; mech.append(i+1)
    json.dump(s, open(sp, 'w'), ensure_ascii=False, indent=1)
    print(f"tercinas: {trip}")
    print(f"fechados mecanicamente (conferir): {mech}")

if __name__ == '__main__':
    main()
