# Biblioteca de Partituras — Sax Alto (Mib)

Players "karaokê" gerados a partir de PDFs de partitura do MuseScore: o áudio
toca com timbre de sax e um cursor acompanha nota a nota.

**Abra `Biblioteca.html`** para ver todas as músicas e clicar em qualquer uma.

## O que tem cada música (`songs/<slug>/`)

- `<slug>_player.html` — o player karaokê (play, velocidade, comparar com o PDF,
  clicar num compasso pra tocar a partir dele, cursor + retângulo roxo).
- `<slug>_validacao.html` — conferência compasso a compasso (transcrição × PDF).
- `source.pdf` — partitura original.
- `spec.json` — a transcrição (quando feita pelo extrator vetorial).
- `<slug>.musicxml`, `<slug>_sax.mp3`, `thumb.png`.

## Músicas

Veja `songs.json` para a lista atualizada. Atualmente: Abracadabra, Firework,
Zero, Mania de Você e I Follow Rivers — bloco Metaverso.

## Para desenvolvedores / novas sessões do Claude

Leia o **`CLAUDE.md`** na raiz: explica o pipeline (`tools/`), a estrutura de
pastas, como adicionar uma música e as regras do projeto.
