# Projeto Final de Estruturas de Dados

Implementacao em Python de uma arvore AVL aumentada, acompanhada por uma BST
sem balanceamento usada como linha de base experimental.

## Equipe

- Marcus Querol
- Raphael Nunes
- Grupo 16

## Parametros do grupo 16

- Conjunto SOSD: `osm_cellids_800M_uint64`
- Mistura `I:D:S`: `35:30:35`
- Theta principal: `0.6`
- Agregado de intervalo: soma
- Ordem principal de insercao: `shuffle`
- Seed: `16`

## Organizacao

- `codigo/`: AVL, BST, gerador, executor e ferramentas de experimento.
- `testes/`: testes unitarios, de invariantes e diferenciais.
- `resultados/`: CSV final com as 66 execucoes da matriz experimental.
- `graficos/`: cinco figuras do relatorio e o script que as gera.

O conjunto OSM, os traces e os resultados intermediarios ficam apenas na
maquina local por causa do tamanho. O CSV final e os graficos sao versionados.

## Campos de cada no AVL

Cada no armazena `key`, `left`, `right`, `height`, `size` e `subtree_sum`.
Os tres metadados sao recalculados de baixo para cima:

```text
height = 1 + max(height(left), height(right))
size = 1 + size(left) + size(right)
subtree_sum = key + sum(left) + sum(right)
```

As chaves duplicadas sao ignoradas, portanto a arvore representa um conjunto.
`select(i)` usa posicoes iniciadas em 1.

## Operacoes e complexidade da AVL

| Operacao | Complexidade |
|---|---:|
| `insert(k)` | `O(log n)` |
| `delete(k)` | `O(log n)` |
| `search(k)` | `O(log n)` |
| `rank(k)` | `O(log n)` |
| `select(i)` | `O(log n)` |
| `range_agg(a, b)` | `O(log n)` |

O intervalo e calculado como `prefix_sum(b) - prefix_sum(a - 1)`. A BST
ingenua nao guarda `size` nem soma de subarvore; por isso suas consultas
aumentadas podem visitar `O(n)` nos piores casos.

## Requisitos

```powershell
python --version
python -m pip install -r requirements.txt
```

O desenvolvimento atual usa Python 3.14 e NumPy 2.5.1.

## Testes

```powershell
python -m unittest discover -s testes -v
```

Os testes cobrem metadados, quatro casos de rotacao, insercao, remocao,
busca, rank, select, soma em intervalo, leitura de trace e comparacao
aleatoria com estruturas de referencia do Python.

## Dados OSM

Fonte: <https://zenodo.org/records/15240501>

```powershell
New-Item -ItemType Directory -Path data -Force
curl.exe -L --fail --continue-at - --retry 5 --retry-delay 10 `
  --output "data\osm_cellids_800M_uint64" `
  "https://zenodo.org/records/15240501/files/osm_cellids_800M_uint64?download=1"
```

O arquivo completo possui `6.400.000.008` bytes. Conferencia do MD5:

```powershell
Get-FileHash -Algorithm MD5 "data\osm_cellids_800M_uint64"
```

Valor esperado: `70670BF41196B9591E07D0128A281B9A`.

## Geracao e verificacao de um trace

Exemplo pequeno com a configuracao principal do grupo:

```powershell
python -m codigo.gen_workload generate `
  --keys "data\osm_cellids_800M_uint64" --format sosd --key-bytes 8 `
  --max-load 20000 --out osm_pilot `
  --ops 20000 --universe 10000 `
  --mix 35:30:35 --theta 0.6 --insert-order shuffle --seed 16

python -m codigo.executar_trace osm_pilot.trace osm_pilot.out --validate-every 1000

python -m codigo.gen_workload verify `
  --expected osm_pilot.expected --candidate osm_pilot.out
```

Como o gerador nao reinsere chaves removidas, usamos aproximadamente
`ops = 2 * universe`. Isso evita esgotar as chaves inseriveis e mantem o mix
real proximo de `35:30:35`.

## Experimentos

Piloto:

```powershell
python -m codigo.rodar_experimentos --suite pilot --repetitions 1 `
  --results resultados/resultados_pilot.csv --reset-results
```

Matriz completa:

```powershell
python -m codigo.rodar_experimentos --suite full --repetitions 3 `
  --results resultados/resultados.csv --reset-results

python graficos/gerar_graficos.py `
  --results resultados/resultados.csv --output graficos
```

A matriz completa mede cinco escalas entre `10^2` e `10^6`, os thetas
`0.0`, `0.6`, `0.99` e `1.2`, as ordens `shuffle` e `sorted`, e compara AVL
com BST. Os resultados incluem insercao, remocao, busca, rank, select,
range, altura final e quantidade de rotacoes. O ultimo comando valida as 66
execucoes esperadas e produz cinco graficos a partir da mediana das tres
repeticoes de cada cenario.
