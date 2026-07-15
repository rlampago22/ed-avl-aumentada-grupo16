# AVL: fator de balanceamento, rotações e comparativo com Rubro-Negra e Treap

> Documento de estudo, não de especificação do projeto. Objetivo: entender por completo, com exemplos numéricos concretos, como uma AVL se mantém balanceada e por que a estrutura escolhida pelo Grupo 16 (ver `docs/relatorio-enunciado-grupo16.md` e a decisão registrada nesta sessão) funciona do jeito que funciona. Serve de material de apoio para a "Justificativa de projeto" e para a defesa oral.

---

## 1. Recapitulando: por que uma BST comum não basta

Numa árvore de busca binária (BST), cada nó tem uma chave, um filho esquerdo (chaves menores) e um filho direito (chaves maiores). Buscar, inserir e remover custam O(altura da árvore).

O problema: a altura depende da **ordem de inserção**. Se você insere `10, 20, 30, 40, 50` nessa ordem, cada chave só pode virar filho direito da anterior — a árvore vira uma lista encadeada:

```
10
  \
   20
     \
      30
        \
         40
           \
            50
```

Altura 4 para 5 nós, quando o mínimo possível seria altura 2 (log₂5 ≈ 2.3). Nesse caso degenerado, toda operação volta a custar O(n). É exatamente esse cenário que o item 3 do estudo empírico (§7 do enunciado) pede para reproduzir e medir, com `--insert-order sorted`.

Uma árvore **balanceada** impede isso, restaurando ativamente uma condição de altura controlada depois de cada inserção/remoção, através de **rotações**.

---

## 2. O invariante da AVL

**Convenção de altura usada neste documento**: altura de uma subárvore vazia = **-1**; altura de uma folha = **0**; altura de qualquer outro nó = `1 + max(altura(esquerda), altura(direita))`.

**Fator de balanceamento** de um nó:

```
FB(nó) = altura(subárvore esquerda) - altura(subárvore direita)
```

**Invariante AVL**: para todo nó da árvore, `FB(nó) ∈ {-1, 0, 1}`.

- `FB > 1` ou `FB < -1` (ou seja, `FB = ±2`, já que a violação é sempre detectada assim que uma inserção/remoção desloca a diferença de altura em 1) → a árvore está desbalanceada naquele nó e precisa de uma rotação.

### Por que ±1 de folga, e não exigir `FB = 0` sempre?

Se você exigisse balanceamento perfeito (`FB = 0` em todo nó, ou seja, uma árvore completa), qualquer inserção poderia forçar reconstruir a árvore inteira — O(n) por operação, o que anula a vantagem de usar uma árvore. Permitir folga de ±1 é o ponto de equilíbrio: ainda garante altura O(log n) (prova abaixo), mas corrigir o invariante depois de uma inserção custa só O(1) rotações (veremos por quê na seção 6).

### Por que ±1 de folga já garante altura O(log n)

Seja `N(h)` o número mínimo de nós que uma AVL de altura `h` pode ter. No pior caso (a árvore "mais torta possível" que ainda respeita o invariante), cada nó tem uma subárvore de altura `h-1` e a outra de altura `h-2` (a diferença máxima permitida). Isso dá a recorrência:

```
N(h) = 1 + N(h-1) + N(h-2)
```

Essa é essencialmente a recorrência de Fibonacci. Resolvendo, `N(h)` cresce proporcionalmente a `φʰ` (φ = razão áurea ≈ 1.618), o que, invertido, dá:

```
altura ≤ 1.44 · log₂(n)
```

Ou seja, mesmo no pior caso permitido pelo invariante, a árvore nunca fica mais que ~44% mais alta que uma árvore perfeitamente balanceada. Essa é uma afirmação que dá para **verificar empiricamente**: medir a altura máxima real da árvore de vocês ao longo do trace e comparar com esse limite — é um ótimo ponto para o item 4 do estudo empírico (teoria × prática).

---

## 3. O que uma rotação faz (mecânica geral, antes dos casos)

Uma rotação simples troca um nó pai com um de seus filhos, **sem violar a ordem da BST**. O truque: o "neto do meio" (o filho do filho que fica entre os dois valores) precisa trocar de dono.

Rotação **à direita** em torno de um nó `z` (usada quando o lado esquerdo está pesado):

```
      z                y
     / \              / \
    y   C    ──►      A   z
   / \                   / \
  A   B                 B   C
```

- `y` (filho esquerdo de `z`) sobe e vira a nova raiz da subárvore.
- `z` desce e vira filho **direito** de `y`.
- `B` (que era filho direito de `y`, portanto maior que `y` e menor que `z`) muda de dono: vira filho **esquerdo** de `z`. Isso é obrigatório para manter a ordem — `B` continua entre `y` e `z` na ordenação, então continua entre eles na árvore.

Rotação **à esquerda** é o espelho exato (usada quando o lado direito está pesado).

Essa realocação de `B` é o detalhe que mais confunde quem vê rotação pela primeira vez — vale revisitar o exemplo numérico da seção 6 (passo 10) para ver isso acontecendo com números reais.

---

## 4. Os quatro casos de desbalanceamento

Quando uma inserção deixa algum nó `z` com `FB(z) = ±2`, existem 4 configurações possíveis, dependendo de para que lado `z` está pesado e para que lado o filho pesado de `z` está pesado:

| Caso | Condição | Correção |
|---|---|---|
| **LL** (esquerda-esquerda) | `FB(z) = +2`, filho esquerdo `y` com `FB(y) ≥ 0` | 1 rotação à **direita** em `z` |
| **RR** (direita-direita) | `FB(z) = -2`, filho direito `y` com `FB(y) ≤ 0` | 1 rotação à **esquerda** em `z` |
| **LR** (esquerda-direita) | `FB(z) = +2`, filho esquerdo `y` com `FB(y) < 0` | rotação à esquerda em `y`, depois à direita em `z` |
| **RL** (direita-esquerda) | `FB(z) = -2`, filho direito `y` com `FB(y) > 0` | rotação à direita em `y`, depois à esquerda em `z` |

LR e RL são "casos duplos": a primeira rotação (dentro do filho `y`) transforma a situação num caso LL ou RR simples, que a segunda rotação resolve. Não são um terceiro tipo de rotação — são duas rotações simples em sequência.

**Fato importante para a implementação**: no `insert`, no máximo **uma** dessas correções (1 ou 2 rotações) é necessária, sempre no nó desbalanceado mais próximo da chave inserida — depois de corrigido, a altura daquela subárvore volta a ser exatamente a que era antes da inserção, então nenhum ancestral acima precisa ser revisitado. Isso não é verdade para o `delete` (seção 7).

---

## 5. Exemplo completo: construindo uma AVL, inserção por inserção

Vamos inserir `50, 30, 70, 20, 40, 60, 80, 10, 25, 5`, nessa ordem, e acompanhar quando uma rotação é (ou não) disparada.

**Passos 1-3** (`50`, `30`, `70`): árvore fica perfeitamente balanceada, sem rotação:

```
     50
    /  \
   30   70
```

**Passos 4-7** (`20`, `40`, `60`, `80`): cada uma cai numa folha, mantendo tudo com `FB ∈ {-1,0,1}`, sem rotação:

```
         50
        /  \
       30    70
      /  \   /  \
     20  40 60  80
```

**Passo 8** (`10`): desce 50→30→20, insere à esquerda de 20:

```
              50
            /    \
          30       70
         /  \      /  \
       20    40   60   80
      /
    10
```

Checando de baixo para cima: `FB(20) = altura(10)-altura(vazio) = 0-(-1) = 1` (ok). `FB(30) = altura(20-subárvore)-altura(40) = 1-0 = 1` (ok). `FB(50) = altura(30-subárvore)-altura(70-subárvore) = 2-1 = 1` (ok). Nenhuma rotação — a folga de ±1 absorveu essa inserção.

**Passo 9** (`25`): desce 50→30→20→(direita, pois 25>20), insere à direita de 20:

```
              50
            /    \
          30       70
         /  \      /  \
       20    40   60   80
      /  \
    10    25
```

`FB(20) = 0-0 = 0`. `FB(30) = 1-0 = 1`. `FB(50) = 2-1 = 1`. Ainda tudo dentro da folga — sem rotação.

**Passo 10** (`5`): desce 50→30→20→10→(esquerda), insere à esquerda de 10:

```
              50
            /    \
          30       70
         /  \      /  \
       20    40   60   80
      /  \
    10    25
    /
   5
```

Agora, checando de baixo para cima:
- `FB(10) = altura(5)-altura(vazio) = 0-(-1) = 1` (ok, `10`-subárvore tem altura 1).
- `FB(20) = altura(10-subárvore)-altura(25) = 1-0 = 1` (ok, `20`-subárvore tem altura 2).
- `FB(30) = altura(20-subárvore)-altura(40) = 2-0 = 2` → **violação!** `z = 30`.

`y = z.esquerda = 20`. `FB(y=20) = altura(10-subárvore)-altura(25) = 1-0 = 1 ≥ 0` → **caso LL** → uma rotação **à direita** em `z=30`.

Isolando a subárvore afetada (raiz `30`) antes da rotação:

```
        30
       /  \
      20    40
     /  \
   10    25
   /
  5
```

Aplicando a mecânica da seção 3 (`z=30`, `y=20`, e o "neto do meio" é a subárvore `25`, que era filho direito de `y=20`):

```
        20
       /  \
      10    30
     /      /  \
    5      25   40
```

Note que `25` (que era filho direito de `20`, portanto maior que `20` e menor que `30`) virou filho **esquerdo** de `30` — exatamente a realocação descrita na seção 3, preservando a ordem: `5 < 10 < 20 < 25 < 30 < 40`.

Recolocando essa subárvore corrigida no lugar de `30` (filha de `50`):

```
              50
            /    \
          20       70
         /  \      /  \
        10   30   60   80
       /    /  \
      5   25   40
```

Verificando que a correção realmente resolveu tudo: `FB(20) = altura(10-subárvore,1) - altura(30-subárvore,1) = 0` (ok). `FB(50) = altura(20-subárvore,2) - altura(70-subárvore,1) = 1` (ok). Como a altura da subárvore que era filha de `50` **voltou a ser 2** (a mesma de antes da inserção de `5`), nenhuma verificação a mais é necessária subindo — é exatamente o "no máximo uma correção" mencionado no fim da seção 4.

---

## 6. Por que `delete` é mais traiçoeiro que `insert`

No `insert`, a rotação que conserta o nó desbalanceado **restaura** a altura original daquela subárvore — então o efeito da inserção "para de se propagar" para os ancestrais. No `delete`, isso nem sempre acontece: às vezes, mesmo depois de rotacionar para corrigir um nó, a altura daquela subárvore fica **1 a menos** do que era antes da remoção — e essa redução pode desbalancear o próximo ancestral acima, exigindo outra rotação ali, e assim por diante, potencialmente até a raiz.

Ilustração esquemática (usando alturas simbólicas, não chaves concretas, porque o efeito só aparece de forma clara numa árvore com vários níveis):

```
Antes de remover, subárvore de z balanceada:

          z                    alturas:
         / \                   A: h+1
        A   B                  B: h
                                z: h+2

Remover um nó do fundo de B faz altura(B) cair para h-1.
FB(z) passa de (h+1)-h=1 para (h+1)-(h-1)=2  → violação, precisa rotacionar em z.

Depois de rotacionar (caso LL, já que A estava mais alta):

          A'
         /  \
       A''   z
             / \
           B''  B

A altura da subárvore inteira (antes h+2) agora é h+1 — CAIU 1 em relação
ao que era antes da remoção. Se o pai de z, lá em cima, tinha uma folga
de exatamente 1 do lado de z, essa redução de altura desbalanceia o pai
também — e o processo se repete subindo.
```

Esse é o motivo teórico pelo qual, no pior caso, `delete` pode disparar **O(log n) rotações** (uma por nível, até a raiz), enquanto `insert` nunca passa de 1 correção. Na prática, para a maioria das remoções isso não acontece (a maior parte das remoções não reduz a altura da subárvore, só remove um nó "de sobra" dentro da folga), mas é um caso de pior-caso real, não hipotético — e é relevante para o Grupo 16 porque o mix `35:30:35` estressa remoção quase tanto quanto inserção. Vale medir, no estudo empírico, quantas rotações cada `delete` disparou (não só o tempo), para conseguir mostrar concretamente se esse pior caso apareceu com frequência real no trace de vocês ou se ficou raro na prática.

---

## 7. Como os campos aumentados (tamanho, soma) se atualizam numa rotação

Cada nó guarda, além da chave:

```
tamanho(nó) = 1 + tamanho(esquerda) + tamanho(direita)
soma(nó)    = chave(nó) + soma(esquerda) + soma(direita)
```

Retomando a rotação do passo 10 (seção 5) com números reais. **Antes** da rotação, subárvore raiz `30`:

```
        30
       /  \
      20    40
     /  \
   10    25
   /
  5
```

Tamanho e soma de cada nó (calculados bottom-up, da folha para a raiz):

| nó | tamanho | soma |
|---|---|---|
| 5 | 1 | 5 |
| 10 | 1+1+0 = 2 | 10+5+0 = 15 |
| 25 | 1 | 25 |
| 40 | 1 | 40 |
| 20 | 1+2+1 = 4 | 20+15+25 = 60 |
| 30 | 1+4+1 = 6 | 30+60+40 = 130 |

**Depois** da rotação (mesmos 6 nós, nova forma):

```
        20
       /  \
      10    30
     /      /  \
    5      25   40
```

A ordem certa de recomputar é **de baixo para cima, começando pelo nó que desceu (`30`)**:

1. `30` (agora só com filhos `25` e `40`, perdeu a referência antiga a `20`): `tamanho = 1+1+1 = 3`, `soma = 30+25+40 = 95`.
2. `20` (agora raiz da subárvore, com filhos `10` e o `30` **já recomputado**): `tamanho = 1+2+3 = 6`, `soma = 20+15+95 = 130`.

Conferindo: o conjunto de nós não mudou (mesmos 6), então tamanho total (6) e soma total (130) da subárvore inteira batem antes e depois — só a distribuição entre os nós individuais mudou, porque cada nó agora "enxerga" um conjunto diferente de descendentes.

**Este é o erro mais fácil de cometer**: se você recomputar `20` **antes** de recomputar `30` (ordem invertida), o `soma` de `30` usado no cálculo de `20` ainda estaria com o valor antigo (que incluía a subárvore de `20` inteira, um bug de dupla contagem) ou com um valor de filhos errado (se `30.direita` ainda apontasse para a estrutura antiga). Daí a regra prática: **numa rotação, sempre recompute primeiro o nó que desceu, depois o nó que subiu** — nunca na ordem contrária.

---

## 8. Comparativo: AVL vs. Rubro-Negra vs. Treap

|  | **AVL** | **Rubro-Negra** | **Treap** |
|---|---|---|---|
| Invariante | `FB(nó) ∈ {-1,0,1}` em todo nó | regras de cor (raiz preta; filho de nó vermelho é preto; mesmo nº de nós pretos em todo caminho raiz→folha) | é uma BST por chave **e**, simultaneamente, um heap por uma prioridade aleatória sorteada por nó |
| Limite de altura | ≤ 1.44 · log₂n (o mais "achatado" dos três — ver prova na seção 2) | ≤ 2 · log₂(n+1) (até ~2× mais alto que AVL) | O(log n) **esperado**, com alta probabilidade — não é garantia de pior caso determinística |
| Rotações no `insert` | no máximo 1 correção (simples ou dupla) | no máximo 2 rotações (mas pode precisar recolorir vários nós subindo, o que é barato) | O(1) esperado — o nó sobe enquanto violar a propriedade de heap com o pai |
| Rotações no `delete` | pode chegar a O(log n) no pior caso (seção 6) | no máximo 3 rotações (teorema clássico) | O(log n) esperado — o nó desce (trocando de lugar com o filho de maior prioridade) até virar folha, e então é removido |
| Robustez à ordem de inserção (`sorted` vs `shuffle`) | garantida pelo invariante de altura, ativamente mantido | garantida pelo invariante de cor | garantida pela aleatoriedade das prioridades — **estruturalmente independente** da ordem das chaves inseridas |
| Complexidade de implementação | moderada — 4 casos de rotação (LL/RR/LR/RL), bem documentados | alta — o desfazimento (*fixup*) do `delete` tem cerca de 6 casos, dobrando com espelhamento esquerda/direita | baixa — sem casos especiais; a mesma lógica de "rotacionar e recomputar" se repete em todo lugar |
| Reprodutibilidade com seed fixo | determinística: mesma árvore sempre, dado o mesmo trace | determinística, mesmo motivo | precisa de uma segunda fonte de aleatoriedade (as prioridades dos nós), separada do seed do trace — exige seed própria para os resultados serem reprodutíveis |

### Por que o Grupo 16 escolheu AVL

Decisão registrada: **AVL**, por ser o meio-termo mais "nivelado" entre as três — garantia de pior caso mais forte que a treap (sem depender de uma segunda fonte de aleatoriedade, o que evitaria complicar a reprodutibilidade exigida pelo `--seed 16`), e com menos casos de rotação para implementar corretamente do que a rubro-negra (o que reduz o risco do tipo de bug mais cobrado na correção: uma rotação que esquece de recomputar `tamanho`/`soma`, seção 7).

Consequência prática a ter em mente durante a implementação e a defesa: como o mix do Grupo 16 é `35:30:35` (inserção e remoção quase empatadas), o caso de pior desempenho teórico da AVL — `delete` cascateando rotações até a raiz (seção 6) — é mais estressado neste projeto do que seria num mix inserção-dominante. Vale a pena medir explicitamente a frequência de rotações por `delete` no estudo empírico, para poder afirmar com dados se esse pior caso teórico realmente apareceu com frequência relevante na prática, ou se ficou raro (como costuma acontecer com chaves não adversariais).

---

## 9. Checklist para a defesa oral

Perguntas plausíveis do tipo "o que acontece se removermos esta rotação?" (mencionado no enunciado, §8) que este documento prepara você a responder:

- [ ] Definir fator de balanceamento e o invariante AVL, incluindo por que a folga é ±1 e não 0.
- [ ] Explicar de cabeça, com um desenho, os 4 casos (LL/RR/LR/RL) e por que LR/RL são duas rotações simples, não um terceiro tipo de rotação.
- [ ] Explicar por que uma rotação simples preserva a ordem da BST (o destino do "neto do meio").
- [ ] Explicar por que `insert` nunca precisa de mais de uma correção, mas `delete` pode precisar de várias, até a raiz.
- [ ] Explicar a ordem correta de recomputar `tamanho`/`soma` numa rotação (nó que desceu primeiro, nó que subiu depois) e o que dá errado se a ordem for invertida.
- [ ] Justificar a escolha de AVL frente a rubro-negra e treap, com argumentos técnicos (não só "foi a que aprendemos primeiro").
- [ ] Relacionar o mix `35:30:35` do Grupo 16 com o caso de pior desempenho teórico da AVL (delete cascateando).
