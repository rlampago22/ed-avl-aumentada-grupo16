# Relatório de leitura do enunciado — Projeto Final de Estruturas de Dados

**Grupo:** 16
**Fonte:** `docs/projeto_final_estruturas_de_dados.pdf`
**Propósito deste documento:** consolidar o enunciado, explicar cada exigência e destacar exatamente o que muda para o Grupo 16, para que o grupo entenda o projeto antes de escrever qualquer linha de código.

---

## 1. Do que se trata o projeto, em uma frase

Implementar uma **árvore de busca balanceada e aumentada** (AVL, rubro-negra ou treap — a escolha é do grupo), rodar essa estrutura sob uma carga de **dezenas de milhões de operações** derivada de um conjunto de chaves reais (SOSD), medir o desempenho empiricamente, comparar com os limites teóricos e defender tudo isso oralmente.

O ponto central do enunciado (§2) é que **o código é a menor parte da nota**. A maior parte (medição + interpretação + justificativa + prompts + defesa oral) é coisa que ninguém consegue terceirizar para uma IA de forma crível, porque depende da máquina do grupo, dos números que ela produziu e do raciocínio do grupo sobre esses números.

---

## 2. Objetivos (§1)

Ao final, o grupo precisa conseguir:

1. Implementar a estrutura aumentada mantendo os invariantes sob `insert`, `delete` e rotação.
2. Avaliar empiricamente inserção/remoção/busca em larga escala com dados reais.
3. Confrontar o comportamento medido com os limites teóricos (O(log n) etc.) e **explicar as divergências**.
4. Defender oralmente as decisões de projeto e o raciocínio de corretude.

## 3. Por que o projeto foge do "genérico" (§2)

Duas razões dadas no enunciado:

- A estrutura não é uma AVL "pura" de livro-texto: ela é **composta e aumentada** com campos extras por nó (tamanho de subárvore + agregado), e esses campos têm que continuar corretos depois de cada rotação. Isso é o tipo de coisa que uma implementação copiada da internet normalmente não trata direito.
- A nota pesa fortemente em medições feitas **na máquina do grupo**, interpretação **nas próprias palavras**, e uma defesa oral. Isso não é algo que se resolve pegando uma solução pronta.

Uso de LLMs é **permitido para o código**, mas o grupo precisa entender e defender tudo — inclusive precisa **enviar o histórico completo dos prompts usados** (isso vale 20% da nota, ver §9 abaixo).

---

## 4. A estrutura a implementar (§3) — núcleo obrigatório

Operações exigidas:

| Operação | Descrição |
|---|---|
| `insert(k)` | insere a chave `k` |
| `delete(k)` | remove a chave `k` |
| `search(k)` | informa se `k` está presente |
| `rank(k)` | número de chaves menores que `k` |
| `select(i)` | i-ésima menor chave (estatística de ordem) |
| `range_agg(a, b)` | agregado das chaves no intervalo `[a, b]` |

Pontos importantes:

- O balanceamento é livre: **AVL, rubro-negra ou treap**. O nome do repositório (`trabalho-ed-avl`) sugere que a escolha do grupo já foi AVL — vale confirmar isso com o grupo antes de seguir.
- `rank` e `select` exigem manter, em cada nó, o **tamanho da subárvore**.
- `range_agg` exige manter, em cada nó, o **agregado da subárvore** (soma, contagem, mínimo ou máximo — depende do grupo, ver seção 8).
- **O ponto mais avaliado do código**: recomputar corretamente `tamanho` e `agregado` em toda rotação. Uma rotação que esquece de atualizar esses campos quebra `rank`/`select`/`range_agg` silenciosamente — o código continua "funcionando" (não trava, não dá exceção), só que devolve respostas erradas. É exatamente esse tipo de bug que o oráculo de corretude (§6.2) foi desenhado para pegar.
- Extensão opcional (não obrigatória): trocar o núcleo por uma **fila de prioridade parcialmente retroativa**, em que inserções/remoções podem ser aplicadas "no passado". Isso é bem mais difícil e só vale a pena se o grupo já estiver confortável com o núcleo obrigatório.

---

## 5. O conjunto de dados — SOSD (§4)

Fonte: [github.com/learnedsystems/SOSD](https://github.com/learnedsystems/SOSD), benchmark com conjuntos de 200–800 milhões de inteiros sem sinal extraídos de dados reais.

| Conjunto | Origem | Característica |
|---|---|---|
| `amzn` | popularidade de vendas de livros (Amazon) | distribuição moderadamente enviesada |
| `face` | identificadores de usuários (Facebook) | lacunas grandes e regulares |
| `wiki` | timestamps de edições de artigos | quase denso, com agrupamentos temporais |
| `osm` | dados do OpenStreetMap | lacunas muito irregulares — **o mais difícil** |

**→ O Grupo 16 usa `osm`** (ver §8), ou seja, o conjunto classificado pelo próprio enunciado como o mais difícil, por causa da irregularidade das lacunas entre chaves. Isso é relevante na hora de discutir distribuição de chaves e comportamento de balanceamento no relatório empírico e na defesa oral.

Formato binário: 8 bytes iniciais com a quantidade de chaves (`uint64`, little-endian), seguidos das chaves (`uint32` ou `uint64`; `osm` é `uint64`).

**Atenção central do enunciado**: o SOSD por si só é uma carga *somente leitura* — não tem inserções/remoções. A sequência de operações usada no projeto é **gerada artificialmente** a partir dessas chaves reais pelo script `gen_workload.py`. Como o grupo deriva essa sequência (mix, enviesamento, ordem de inserção) é, em si, uma decisão de projeto que será avaliada.

### 5.1 Como obter os dados (§5)

Dois caminhos:

1. **Arquivo isolado (recomendado)** — baixar só o conjunto do grupo via espelho Zenodo, com checagem de integridade por `md5sum`. Para o Grupo 16 (`osm`), o exemplo do próprio PDF já usa esse arquivo:
   ```
   wget -O osm_cellids_800M_uint64 \
     "https://zenodo.org/records/15240501/files/osm_cellids_800M_uint64?download=1"
   echo "70670bf41196b9591e07d0128a281b9a  osm_cellids_800M_uint64" | md5sum -c
   ```
2. **Suíte completa via repositório SOSD** — clonar o repo e rodar `./scripts/download.sh` (requer Linux apt-based, ≥16 GiB RAM, ≥50 GiB disco livre, `zstd`, Python+numpy/scipy; Rust só é necessário se for construir os RMIs/benchmark original, o que **não** é necessário para este projeto).

Pontos de atenção específicos para o Grupo 16:

- O arquivo `osm_cellids_800M_uint64` tem **6,4 GB**. Carregar tudo na RAM pode não ser viável dependendo da máquina do grupo.
- O script fornece a opção `--max-load N`, que lê apenas as primeiras N chaves direto do preâmbulo binário, sem carregar o arquivo inteiro — essencial para esse conjunto.
- Se o link de download quebrar (o enunciado avisa que isso acontece periodicamente), a alternativa é baixar manualmente pelo Zenodo e colocar em `data/`.

---

## 6. Carga de trabalho e oráculo de corretude (§6)

O script `gen_workload.py` (fornecido pelo professor — **ainda não está neste repositório**, ver seção 11 "pontos em aberto") transforma as chaves do SOSD em:

- um **trace** reproduzível de operações (`I`, `D`, `S` por linha);
- um **gabarito** (`.expected`) com as respostas esperadas das buscas.

Exemplo de geração (adaptado do PDF, com os parâmetros trocados pelos do Grupo 16 — ver seção 8):

```
python3 gen_workload.py generate \
  --keys osm_cellids_800M_uint64 --format sosd --key-bytes 8 \
  --max-load 20000000 \
  --out g16 --ops 50000000 \
  --universe 10000000 --mix 35:30:35 --theta 0.6 --seed 16
```

Parâmetros principais:

- `--mix I:D:S`: proporção de inserção, remoção, busca.
- `--theta`: enviesamento Zipfiano (estilo YCSB). `0` = uniforme; valores maiores concentram acesso em poucas chaves "quentes".
- `--universe`: número de chaves distintas envolvidas.
- `--insert-order`: `shuffle` (padrão), `popularity` ou `sorted`. `sorted` é o caso patológico clássico para BSTs sem balanceamento — degenera em lista encadeada se a árvore não rebalancear.
- `--seed`: reprodutibilidade. **O enunciado exige `--seed` igual ao número do grupo** — para o Grupo 16, `--seed 16`.

### 6.1 Oráculo de corretude (§6.2)

A verificação é **transitiva**: o resultado esperado de cada busca depende de todas as inserções/remoções anteriores no trace. Um `insert` ou `delete` com bug não quebra na hora — ele só se manifesta numa busca *posterior* que diverge do gabarito. Parte das buscas "miss" mira deliberadamente chaves já removidas, então "esquecer de remover de verdade" também é pego.

Contrato de saída: a implementação do grupo lê o `.trace`, emite uma linha `<chave> <FOUND|NOT_FOUND>` por operação `S`, e o professor confere com:

```
python3 gen_workload.py verify --expected g16.expected --candidate minha_saida.out
```

---

## 7. Estudo empírico exigido (§7) — 30% da nota, o maior peso individual

Não basta funcionar; é preciso medir e **explicar**. Mínimo exigido:

1. **Escala**: tempo médio por operação + percentis `p50`/`p99`, variando `n` em pelo menos **4 ordens de grandeza**, até o limite da máquina do grupo.
2. **Sensibilidade ao enviesamento**: repetir com `--theta` em `{0.0, 0.6, 0.99, 1.2}` e explicar o efeito da concentração de acessos no rebalanceamento e na localidade de cache. (Nota: `0.6` é justamente o `theta` fixo do Grupo 16 na geração principal — então esse ponto específico do gráfico de sensibilidade já é, por coincidência, a configuração "oficial" do grupo.)
3. **Caso patológico**: comparar `--insert-order shuffle` vs `sorted`, mostrando o efeito no balanceamento. Isso vale mesmo o Grupo 16 tendo `shuffle` como ordem "oficial" (ver seção 8) — o enunciado pede a comparação como execução **separada**, então rodar também com `sorted` é obrigatório independentemente da ordem oficial do grupo.
4. **Teoria × prática**: para cada operação, comparar tempo medido com o limite teórico (O(log n) para insert/delete/search/rank/select numa árvore balanceada) e explicar divergências — constantes, efeitos de cache, custo amortizado de rotações, alocação de memória.
5. **Linha de base**: comparar contra uma estrutura ingênua deliberada (lista ordenada ou BST sem balanceamento) e localizar o ponto de cruzamento (a partir de qual `n` a estrutura balanceada compensa o overhead).

Exigência transversal: todos os gráficos precisam vir de medições **reais**, feitas na máquina do grupo, com máquina/compilador/metodologia identificados. Números fabricados ou inconsistentes **zeram esse componente** (§11).

---

## 8. Parametrização específica do Grupo 16 (§9)

Da tabela do enunciado (linha do Grupo 16):

| Parâmetro | Valor |
|---|---|
| Conjunto de dados | `osm` (o mais difícil — lacunas irregulares) |
| `--theta` | `0.6` |
| `--mix` (I:D:S) | `35:30:35` |
| `range_agg` | **soma** |
| Ordem de inserção | `shuffle` |
| `--seed` | `16` |

Leituras que valem a pena registrar desde já, porque provavelmente vão aparecer na defesa oral:

- **`osm` + lacunas irregulares**: distribuição de chaves nada uniforme. Vale já antecipar como isso pode afetar a forma da árvore e a variância dos tempos de operação, comparado a um conjunto mais denso como `wiki`.
- **`mix 35:30:35`**: é o mix mais "equilibrado" entre inserção/remoção/busca da tabela inteira (a maioria dos grupos tem inserção dominante, ex. 50–60%). Isso significa que o Grupo 16 vai rebalancear com bastante frequência tanto por inserção quanto por remoção — bom argumento para discutir custo amortizado de rotação nos dois sentidos.
- **`range_agg` = soma**: dos quatro agregados possíveis (soma, contagem, mínimo, máximo), soma é o único que corre risco de overflow em somas de muitas chaves grandes (`osm` usa `uint64`) — vale decidir desde já o tipo usado para acumular o agregado (ex. `uint64`/`unsigned long long` vs. algo maior) e justificar essa escolha na "Justificativa de projeto" (§3 do PDF pede exatamente esse tipo de decisão).
- **Ordem `shuffle`**: é a ordem "não patológica". Mesmo assim, o item 3 do estudo empírico (§7) exige rodar `sorted` como comparação separada — não é opcional só porque a ordem oficial do grupo é outra.
- **`--seed 16`**: usar sempre esse valor para reprodutibilidade — é assim que o professor vai conferir os resultados do grupo.

---

## 9. Entregáveis (§8)

| # | Entregável | Descrição |
|---|---|---|
| 1 | Código-fonte | implementação completa, compilável, com instruções de execução |
| 2 | Relatório empírico | gráficos e interpretação das medições (§7) |
| 3 | Justificativa de projeto | por que essa estrutura, alternativas descartadas e a que custo medido; invariantes da árvore aumentada e argumento informal de que se mantêm sob rotação |
| 4 | Apresentação oral | ~10 min; perguntas do tipo "o que acontece se removermos esta rotação?" ou "por que seu p99 cresce aqui?" |

---

## 10. Critérios de avaliação (§9 do PDF, "Critérios de avaliação")

| Peso | Componente | O que se avalia |
|---|---|---|
| 20% | Implementação | corretude, verificada pelo oráculo |
| **30%** | Estudo empírico | qualidade das medições e, sobretudo, a **interpretação** delas |
| 20% | Justificativa | clareza do raciocínio sobre corretude e decisões |
| 20% | Prompts | qualidade dos prompts usados — enviar o dump completo e organizado dos chats. Avalia-se raciocínio e iteração, **não volume** |
| 10% | Defesa oral | domínio demonstrado ao vivo |

Frase-chave do enunciado: **80% da nota não depende do código simplesmente funcionar** — depende de o grupo entender e explicar o que construiu e mediu.

Implicação prática: vale a pena, desde já, organizar/exportar as conversas com ferramentas de IA num formato limpo (não é preciso volume, é preciso mostrar raciocínio e iteração de verdade).

---

## 11. Regras (§11)

- Ferramentas de auxílio (IA) são permitidas para o código, mas todo o conteúdo entregue deve ser compreendido pelo grupo — a defesa oral verifica isso ao vivo.
- O relatório empírico deve refletir medições **reais** da máquina do grupo. Números fabricados ou inconsistentes com a metodologia descrita **zeram o componente**.
- Qualquer parte cuja autoria não seja do grupo precisa ser identificada claramente no relatório.
- O grupo precisa fornecer o passo a passo para a solução ser reproduzida.

---

## 12. Referências citadas no PDF

- A. Kipf et al., *SOSD: A Benchmark for Learned Indexes*, arXiv:1911.13014.
- Repositório SOSD — github.com/learnedsystems/SOSD
- B. F. Cooper et al., *Benchmarking Cloud Serving Systems with YCSB*, SoCC 2010 (distribuição Zipfiana de acessos).
- J. Gray et al., *Quickly Generating Billion-Record Synthetic Databases*, SIGMOD 1994 (geração Zipfiana).
- T. Cormen et al., *Introduction to Algorithms*, capítulo sobre árvores de busca aumentadas.

---

## 13. Ambiente de execução — WSL2 (Windows, máquina do Grupo 16)

O enunciado (§5.2) assume uma máquina Linux baseada em `apt` (Ubuntu/Debian) para rodar os scripts de download do SOSD (`zstd`, Python+numpy/scipy, opcionalmente Rust). A máquina usada pelo grupo é Windows, então a decisão foi usar **WSL2 com Ubuntu** em vez de tentar replicar esse ambiente nativamente no Windows (o que exigiria instalar substitutos de `wget`, `md5sum`, `zstd`, etc. via Git Bash/Chocolatey, com mais atrito e menos garantia de compatibilidade).

### 13.1 Por que isso é relevante para o relatório empírico

O enunciado (§7) exige identificar **máquina, compilador e metodologia** em todo gráfico produzido. Rodar dentro do WSL2 significa que a "máquina" do relatório é, tecnicamente, uma VM leve dentro do Windows — isso deve ser declarado explicitamente na metodologia, junto com os limites de RAM/CPU configurados (abaixo), porque eles afetam diretamente o item 1 do estudo empírico (limite de escala que "a máquina suportar").

### 13.2 Estado da máquina e decisão tomada

- Hardware do host: **Intel i5-12400T — 6 núcleos físicos / 12 processadores lógicos (Hyper-Threading)**, **~15,7 GiB de RAM física total**.
- O enunciado pede "pelo menos 16 GiB de RAM" para rodar a suíte SOSD completa — a máquina do grupo já está no limite desse requisito mesmo antes de dividir recursos com o WSL. Isso reforça a importância de usar `--max-load` na geração do trace (§6 deste relatório) em vez de carregar o arquivo `osm` (6,4 GB) inteiro.
- WSL2 já estava instalado (Ubuntu 26.04 LTS), mas configurado com limites baixos (4 GB RAM / 2 CPUs) — provavelmente para não competir com o uso normal do Windows e do Docker Desktop, que roda na mesma VM subjacente do WSL2.
- Novo `.wslconfig` (`C:\Users\usuario\.wslconfig`) aplicado para este projeto:

  ```ini
  [wsl2]
  memory=12GB
  processors=8
  swap=4GB
  localhostForwarding=true
  ```

- Racional da divisão: dos ~15,7 GiB / 12 CPUs físicos, **12 GB de RAM e 8 CPUs (66% dos lógicos) vão para o WSL**, deixando ~3,7 GiB e 4 CPUs lógicas de folga para o Windows host e o Docker Desktop (que compartilha a mesma VM). Alocar 100% dos recursos ao WSL foi descartado porque deixaria o host sem CPU/RAM garantida, arriscando travamentos durante execuções longas de benchmark.
- Aplicação exigiu `wsl --shutdown` (reinicia todas as distros WSL, inclusive Docker Desktop) para os novos limites entrarem em vigor. Confirmado após o reinício: WSL reporta ~11 GiB de RAM disponível (pequeno desconto é overhead do kernel Linux) e 8 CPUs.

### 13.3 O que ainda falta configurar dentro do WSL

Isto é setup de ambiente, não implementação do projeto em si — ainda precisa ser feito antes da Seção 5 (obtenção dos dados) ser executada de fato:

- Instalar dependências do `download.sh` dentro da distro Ubuntu: `zstd`, `python3-pip`, `m4`, `cmake`, `clang`, `libboost-all-dev`, `numpy`, `scipy` (Rust só é necessário se o grupo for construir os RMIs do SOSD, o que não é exigido por este projeto).
- Confirmar onde os arquivos de dados (`osm_cellids_800M_uint64`, ~6,4 GB) serão armazenados — recomenda-se o filesystem **nativo do Linux dentro do WSL** (ex. `~/sosd/data/`), não `/mnt/c/...`, porque I/O em `/mnt/c` é sensivelmente mais lento no WSL2.

## 14. Pontos em aberto para o grupo resolver antes de começar

Estes não estão respondidos pelo PDF nem pelo estado atual do repositório — vale decidir com o grupo/professor:

1. **`gen_workload.py` não está no repositório.** O enunciado diz "fornecido", mas o repositório (`trabalho-ed-avl`) hoje só tem o PDF em `docs/`. É preciso confirmar de onde esse script vem (moodle, repositório da disciplina, anexo separado) antes de conseguir gerar `trace`/`expected`.
2. **Escolha da estrutura de balanceamento** (AVL, rubro-negra ou treap) — o nome do repositório sugere AVL, mas vale confirmar com o grupo se essa decisão já está fechada, já que ela precisa ser justificada em §3 dos entregáveis ("por que esta estrutura, quais alternativas foram descartadas e a que custo medido").
3. **Linguagem/ambiente de implementação** — o enunciado assume Linux apt-based para os scripts de download; nada obriga a implementação da árvore em si a ser em nenhuma linguagem específica. Vale decidir isso cedo, já que afeta como medir p50/p99 e como ler o binário SOSD (8 bytes de header + chaves `uint64`).
4. **Tamanho de `n` a testar** — o enunciado pede "pelo menos quatro ordens de grandeza, até o limite que sua máquina suportar"; vale mapear logo no início quanta RAM a máquina do grupo tem disponível, para dimensionar `--max-load` e os pontos da curva de escala.
