# sax-partituras — guia do projeto

Converte PDFs de partitura de **sax alto (Mib)** exportados do MuseScore em um
**player HTML "karaokê"**: toca o áudio com timbre de sax e um cursor/retângulo
roxo acompanha nota a nota. Uma **Biblioteca** lista todas as músicas em cards.

Esta é a raiz do repositório. Comece a ler por aqui em qualquer sessão nova.

## Estrutura

```
sax-partituras/
├── CLAUDE.md              # este guia
├── README.md             # visão geral (humano)
├── Biblioteca.html       # página inicial (gerada) — abre por aqui
├── songs.json            # manifesto de todas as músicas (gerado/mantido)
├── tools/                # pipeline (scripts Python + template do player)
└── songs/
    └── <slug>/           # UMA pasta por música, tudo self-contained
        ├── source.pdf              # PDF original (fonte da verdade visual)
        ├── spec.json               # transcrição por compasso (fonte da verdade musical)
        ├── <slug>.musicxml         # MusicXML gerado do spec
        ├── <slug>_sax.mp3          # áudio sintetizado (repetições desdobradas)
        ├── <slug>_player.html      # player karaokê (self-contained: SVG+MP3+PDF inline)
        ├── <slug>_validacao.html   # página de validação compasso-a-compasso
        ├── thumb.png               # miniatura (topo da 1ª página do PDF)
        ├── feedback.json           # feedback do Vitor p/ calibrar o engine (opcional)
        └── work/                   # scratch: renders, crops, QA — descartável
```

Os players são **self-contained** (SVG do verovio, MP3 base64 e imagens do PDF
embutidos inline). Podem ser movidos/abertos sem dependências externas. A
`Biblioteca.html` (na raiz) linka para `songs/<slug>/<slug>_player.html`.

Obs.: `Mania_de_Voce` e `Sigo_rios` foram feitas antes do extrator; o `spec.json`
delas foi **derivado do `.musicxml` correto** (via `tools/mxml_to_spec.py`), não
extraído do PDF — porque re-extrair introduzia erros (Mania: ritmo sincopado;
Sigo: o extrator só lê 21 dos ~28 compassos por causa do 𝄋/D.S. e das duas seções
`|: :|`). O `Sigo_rios` **não tem página de validação** por esse desalinhamento de
compassos.

O `Sigo_rios` tem estrutura com **D.S. (Dal Segno)** que o verovio NÃO desdobra
sozinho (ele só desdobra `|: :|`). A representação tocável fica em
`work/spec_repeats.json` (48 compassos escritos): as seções **A(1-4), B(21-24) e
C(25-28) são barras de repetição de verdade** (verovio desdobra no áudio e o cursor
respeita, gerando múltiplas janelas por nota — igual ao Zero), e a **volta do D.S.
(5-20 e 21-24) é escrita 1×** logo depois de B, pois o verovio não desdobra D.S.
O `spec.json` canônico guarda os 28 compassos compactos + `navigation` (a estrutura)
+ `play_order` (a sequência completa, 60 compassos, p/ referência). Áudio final = 60
compassos. Ordem tocada: A×2, 5-20, B×2, D.S.→5-20, 21-24, C×2.
Para regerar: `build_from_spec work/spec_repeats.json Sigo_rios.musicxml` →
`make_song` (sem `--render-dir`).

## Exercícios & Arpejos (seção separada das músicas)

Biblioteca paralela de exercícios técnicos (escalas, arpejos, cromática, notas longas,
intervalos) **gerados programaticamente** (sem PDF). Entrada: `Exercicios.html` (na raiz).
- `tools/gen_exercises.py` — gera os specs (spelling correto por tom, divide em compassos).
- `tools/build_exercises.py [--cat Escalas]` — spec → musicxml → player (sem PDF) + thumb do
  render → `exercicios/<slug>/`; atualiza `exercicios.json`.
- `tools/update_exercicios.py` — gera `Exercicios.html` (filtro por categoria/tom).
Alturas são ESCRITAS (o que o sax lê). Biblioteca e Exercícios se linkam mutuamente.

## Pipeline (como uma música vira player)

1. **`tools/vector_extract.py`** — lê o PDF do MuseScore e extrai glifos SMuFL +
   vetores (pauta, hastes, beams, ligaduras) via PyMuPDF. Produz o `spec.json`
   (compassos + `repeats`), detecta tom e andamento. Com `--crops` gera também
   `vmeasures.json` + `vcrops/` (usados na página de validação).
   OMR por imagem (oemer) NÃO funciona aqui — GitHub bloqueado. Só extração vetorial.
2. **`tools/build_from_spec.py spec.json saida.musicxml`** — spec → MusicXML.
   Faz beaming por tempo, ligaduras (tie vs slur), barras de repetição, e esconde
   acidentes já presentes na armadura.
3. **`tools/make_song.py`** — orquestrador. Injeta tempo → MIDI/MP3 de sax →
   player HTML → QA → miniatura → atualiza `songs.json` → regenera Biblioteca →
   gera a página de validação. Grava tudo em `songs/<slug>/`.
4. **`tools/update_biblioteca.py`** — regenera `Biblioteca.html` a partir do `songs.json`.

Apoio: `saxlib.py` (render verovio, timemap, síntese de sax, build_player),
`build_validation.py` (página de validação), `validate_qa.py` (checks de QA),
`compare_measures.py`, `detect_notes.py`, `render_pages.py`, `segment_measures.py`.

### Adicionar uma música nova

Rode da raiz do projeto (não de `tools/`). Crie a pasta antes: `mkdir -p songs/<slug>/work`.

```bash
# 1) extrai a transcrição + recortes. --crops aponta p/ .../work/vcrops;
#    o vmeasures.json é gravado na PASTA-PAI do --crops (ou seja, .../work/).
python3 tools/vector_extract.py "<pdf>" --out songs/<slug>/spec.json \
    --crops songs/<slug>/work/vcrops
# (opcional: --sharps N --tempo N se a auto-detecção errar)

# 2) spec -> MusicXML
python3 tools/build_from_spec.py songs/<slug>/spec.json songs/<slug>/<slug>.musicxml

# 3) publica tudo em songs/<slug>/ (player, mp3, thumb, validação, songs.json, Biblioteca).
#    --render-dir = a pasta que CONTÉM vmeasures.json (songs/<slug>/work).
python3 tools/make_song.py --mxml songs/<slug>/<slug>.musicxml --pdf "<pdf>" \
    --bpm <n> --title "<Título>" --artist "<Artista>" --key "<Tom>" \
    --bloco "Metaverso" --slug <slug> --render-dir songs/<slug>/work
```

### Editar uma música já existente (NÃO re-extrair por cima)

O `spec.json` salvo é a **fonte da verdade** e pode conter correções manuais que o
extrator sozinho não reproduz. **Não rode `vector_extract` por cima de um `spec.json`
existente** — você apaga as correções. Para ajustar uma música já feita, edite o
`songs/<slug>/spec.json` na mão e rode só os passos 2 e 3.

Exemplo real: o `vector_extract` detecta repetições falsas na Abracadabra
(início=[17,32], fim=[4,8,20,35]); o PDF **não tem repetição**, então o
`spec.json` dela tem `repeats: []` corrigido à mão. Re-extrair reintroduziria o erro.
Quando o extrator erra assim, o conserto certo é calibrar o `vector_extract.py`
(causa-raiz) — ver `feedback.json` e a regra de feedback abaixo.

## Regras (NÃO negociáveis)

- **Transcrição idêntica ao PDF**: mesmas notas, acidentes, ritmos, agrupamentos,
  ligaduras, repetições.
- **Beaming sempre por tempo** (convenção 4/4: 4+4 ou 2+2, nunca 8 colcheias numa
  barra só). O `makeBeams` do music21 só funciona com a fórmula DENTRO do compasso.
- **Tercinas/tuplets**: o `build_from_spec` aceita duração em fração (`1/3` = tercina de
  colcheia, `2/3` = tercina de semínima). O music21 cria o tuplet real e o verovio/MIDI
  tocam certo. Se um compasso "não fecha" e o PDF tem colchete "3", é tercina — NÃO
  preencher com pausa; usar durações de tercina (as somas fecham exatas com Fraction).
  O `vector_extract.py` **detecta tercinas automaticamente**: lê o glifo "3" (fonte
  Edwin, x>75 p/ excluir número de compasso) e multiplica ×2/3 as 3 notas mais
  próximas do marcador. **Limitação conhecida**: quando o MESMO compasso tem colcheias
  soltas ADJACENTES à tercina (ex.: Xote c16/c17, casa 2ª), o "3 mais próximas" pega
  notas erradas e gera durações mistas (`D5:1/3`+`F#5:2/3`) ou pausas impossíveis
  (`R:5/6`). Sinais de alerta p/ auto-avaliar: durações fora de {1/3,2/3} tipo `4/3`,
  `5/6`, ou mistura 1/3+2/3 no mesmo grupo. Nesses casos, ler o PDF em alta-res
  (glifos + linhas da pauta p/ altura) e reescrever o compasso na mão. Melhoria de
  causa-raiz pendente: usar a EXTENSÃO do colchete (não só o centro do "3") p/ saber
  exatamente quais notas pertencem à tercina.
- **Fórmula de compasso**: o `vector_extract.detect_time` lê a fórmula pelos glifos
  (E080-E089, common/cut) e grava em `spec.time`; o `build_from_spec` e o `autoclose`
  usam esse valor. Repertório junino (baião/xote/forró) é muito 2/4 — se "todos os
  compassos falham" somando ~2.0, é 2/4, não erro. `make_song` usa a fórmula do musicxml.
- **Página de validação SEMPRE** que criar música nova ou refatorar uma existente.
- **Auto-avaliação SEMPRE (Claude é o 1º validador)**: depois de publicar, rode
  `compare_measures.py` e o próprio Claude LÊ os grids e avalia **compasso a compasso**
  (PDF original × transcrição), igual o Vitor faz no HTML. Grava o veredito em
  `songs/<slug>/work/autoavaliacao.md` (✓/✗ por compasso + motivo). Só entrega a música
  como "pronta p/ validação do Vitor" depois de corrigir o que a auto-avaliação pegou.
  Nunca dependa só de a música "fechar em 4/4" — fechar não é o mesmo que estar idêntica.
- **Checagem de CONTAGEM de notas OBRIGATÓRIA (`tools/qa_notecount.py`)**: a leitura
  visual em miniatura NÃO pega o erro clássico "1ª nota da frase virou semínima, come
  tempo e a nota final some" (Asa Branca c10/c11) — porque o compasso continua somando
  4/4. Rode `python3 tools/qa_notecount.py songs/<slug>` (ou `--all`): ele conta as
  CABEÇAS DE NOTA do PDF (glifos SMuFL, independente da lógica de duração/autoclose
  que gera o bug) × nº de notas no spec, por compasso, e marca divergências. O
  `Validador.html` também mostra esse selo laranja (⚠ PDF≠player) por compasso e o total
  na lista lateral. IMPORTANTE: a checagem por compasso só é confiável quando o nº de
  compassos ALINHA (PDF==spec==imagens). Se "estrutura difere" (repetição/casa/D.S. não
  desdobrada, ou spec derivado do musicxml como Mania/Sigo), a comparação por índice não
  vale — resolver a estrutura antes.
- **Casas 1ª/2ª e repetições no player**: `vector_extract` detecta `repeats` (barra de
  repetição via dots E044) e `endings` (casas 1ª/2ª: texto "1."/"2." em Edwin-Bold +
  colchete horizontal acima da pauta). `build_from_spec` emite `music21.bar.Repeat` +
  `RepeatBracket` (volta). O verovio **desdobra tudo** (repetição + casas) no MIDI e no
  timemap — então áudio E cursor seguem a ordem de execução correta (provado: repetição
  com casa 1ª/2ª sai `A,x → A,y`). D.S./D.C. o verovio NÃO desdobra (ver Sigo).
- **Repetições respeitadas**: detectar `||: :||` e desdobrar no áudio + no cursor.
- **Feedback calibra o engine**: as observações do Vitor (`feedback.json`) apontam
  causas-raiz no `vector_extract.py`, não são correções pontuais numa música.

- **Pauta quebrada por compasso**: alguns PDFs (ex.: repertório Menq) desenham as linhas da pauta como segmentos curtos por compasso; `collect()` aceita horizontais >40pt (não >100) senão só o 1º sistema é lido e a música sai como TRECHO. Se uma música vier curta demais, cheque isso.

## Restrições do ambiente

- Bash roda em sandbox isolado (paths `/sessions/.../mnt/...`); cada chamada é
  independente; sem processos em background persistentes; timeout ~45s.
- Sem fluidsynth/soundfont e sem sudo → áudio é síntese aditiva em numpy (sax).
- Para apagar arquivos criados pelo app, pedir permissão via delete do Cowork.
- Cache do `file://` no Chrome/Mac é traiçoeiro: a Biblioteca usa `?v=<mtime>` e
  meta no-cache; se ainda vier o antigo, use DevTools → "Disable cache".
