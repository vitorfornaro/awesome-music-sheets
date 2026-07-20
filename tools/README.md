# tools/ — pipeline sax-partituras

Transforma um **PDF de partitura de sax alto** (export do MuseScore) num **player HTML
karaokê** (toca com som de sax + cursor nota a nota) e mantém a **Biblioteca**. Tudo roda
localmente; os players são HTML autossuficientes (SVG + MP3 + PDF embutidos inline).

> Leia o `CLAUDE.md` na raiz para a visão geral, a estrutura de pastas (`songs/<slug>/`)
> e as regras do projeto. Este arquivo detalha os scripts.

## Dependências (1x por sessão)

```bash
pip install music21 verovio cairosvg pretty_midi opencv-python-headless numpy pillow --break-system-packages
# ffmpeg e poppler (pdftoppm/pdfinfo) já costumam estar instalados
```

## Scripts

| Script | O que faz |
|---|---|
| `vector_extract.py` | **OMR vetorial**: lê glifos SMuFL + traços do PDF → `spec.json` (compassos + `repeats`), detecta tom/andamento. Com `--crops` gera `vcrops/` + `vmeasures.json`. |
| `build_from_spec.py` | `spec.json` → MusicXML: beaming por tempo, tie vs slur, barras de repetição, esconde acidentes da armadura. |
| `make_song.py` | Orquestra: tempo → MIDI/MP3 de sax → player → QA → miniatura → `songs.json`/`Biblioteca.html` → página de validação. Grava tudo em `songs/<slug>/`. |
| `update_biblioteca.py` | Regenera `Biblioteca.html` a partir de `songs.json`. |
| `build_validation.py` | Página de validação compasso-a-compasso (transcrição × PDF). |
| `validate_qa.py` | QA isolado de uma música (checks abaixo). |
| `saxlib.py` | Biblioteca central (síntese de sax, verovio→SVG+timemap, `build_player`). Não roda sozinho. |
| `render_pages.py`, `segment_measures.py`, `detect_notes.py`, `compare_measures.py` | Apoio à transcrição manual (renderizar páginas, recortar compassos, grade de comparação). |

## Adicionar uma música (do PDF ao player)

Rode **da raiz do projeto**. Crie a pasta antes: `mkdir -p songs/<slug>/work`.

```bash
# 1) transcrição + recortes. vmeasures.json vai para a PASTA-PAI do --crops (=> .../work).
python3 tools/vector_extract.py "nova.pdf" --out songs/<slug>/spec.json \
    --crops songs/<slug>/work/vcrops        # opcional: --sharps N --tempo N

# 2) spec -> MusicXML
python3 tools/build_from_spec.py songs/<slug>/spec.json songs/<slug>/<slug>.musicxml

# 3) publica (player + mp3 + thumb + validação + songs.json + Biblioteca)
python3 tools/make_song.py --mxml songs/<slug>/<slug>.musicxml --pdf "nova.pdf" \
    --bpm 120 --title "Nome" --artist "Artista" --key "Lá maior (3 ♯)" \
    --bloco "Metaverso" --slug <slug> --render-dir songs/<slug>/work
```

Saídas em `songs/<slug>/`: `<slug>_sax.mp3`, `<slug>_player.html`, `<slug>_validacao.html`,
`thumb.png`, `source.pdf`, mais a entrada em `songs.json` e a Biblioteca regenerada.
Se a transcrição precisar de acerto fino, edite `songs/<slug>/spec.json` e repita 2–3.

Se você já tiver o **MusicXML/MIDI do MuseScore**, pule o passo 1 e vá direto ao 2/3 com
esse arquivo → fidelidade total.

## QA — o que é checado (`validate_qa.py`, chamado pelo make_song)

- **[RITMO]** todo compasso fecha na fórmula. **(trava a publicação)**
- **[SYNC]** IDs de nota do SVG batem 100% com o *timemap* do verovio e a duração do MP3 ≈ MIDI. **(trava)**
- **[ALCANCE]** notas no alcance escrito do sax alto (Si♭3–Sol6); fora disso vira **aviso** (possível erro de oitava).
- **[VISUAL]** gera `songs/<slug>/work/qa/qa_comparacao.png` (PDF original × transcrição).

`make_song` **não publica** se um check que trava falhar (use `--force` para ignorar — não recomendado).

## Observações

- Timbre de sax = síntese aditiva em numpy (sem soundfont/fluidsynth no ambiente). Consistente.
- OMR por imagem (oemer) não roda aqui (GitHub bloqueado) — por isso o caminho é vetorial.
- `songs/<slug>/work/` é scratch/relatório (regenerável, no `.gitignore`); os entregáveis
  ficam direto em `songs/<slug>/`.
- Ritmo sincopado de 16 avos denso é o ponto ainda a afinar no extrator.
