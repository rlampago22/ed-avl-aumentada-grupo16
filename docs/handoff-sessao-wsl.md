# Handoff de sessão — Projeto Final Estruturas de Dados (Grupo 16)

> Cole este arquivo (ou seu conteúdo) como primeira mensagem numa nova sessão do Claude Code rodando dentro do WSL. Ele existia numa sessão anterior rodando no Windows; a memória dessa sessão **não** é compartilhada automaticamente com uma sessão aberta a partir de um caminho de projeto diferente (ex. `/home/<usuário>/trabalho-ed-avl` no WSL é um projeto diferente de `C:\Users\usuario\raphael\...` no Windows).

## Contexto do projeto

Trabalho final de Estruturas de Dados: implementar uma árvore de busca balanceada **aumentada** (AVL, rubro-negra ou treap), rodar sob carga sintética derivada do benchmark real **SOSD**, medir desempenho empiricamente e defender oralmente. O enunciado completo já foi lido e resumido em `docs/relatorio-enunciado-grupo16.md` — **leia esse arquivo primeiro**, ele tem a análise completa do PDF em `docs/projeto_final_estruturas_de_dados.pdf`.

## Regra de trabalho crítica — não pular esta

**O usuário pediu explicitamente para NUNCA fazer modificações de código de modo automático.** Ele precisa entender cada parte do projeto pessoalmente (vai defender oralmente e vai enviar o dump de prompts, que vale 20% da nota). Isso significa:
- Não implementar a árvore, os scripts ou qualquer parte do código sem que o usuário peça explicitamente e acompanhe.
- Preferir explicar, revisar, apontar decisões — não decidir por ele.
- Perguntar antes de agir sempre que houver ambiguidade de decisão de projeto (isso já vem sendo feito via `AskUserQuestion` nesta sessão, ex. para decidir RAM/CPU do WSL).

## Parâmetros oficiais do Grupo 16 (não usar os de outro grupo)

| Parâmetro | Valor |
|---|---|
| Conjunto de dados | `osm` (`osm_cellids_800M_uint64`, o mais difícil do SOSD — lacunas irregulares) |
| `--theta` | `0.6` |
| `--mix` (I:D:S) | `35:30:35` |
| `range_agg` | **soma** |
| Ordem de inserção | `shuffle` (mas o enunciado exige testar `sorted` separadamente como caso patológico, §7 item 3) |
| `--seed` | `16` (sempre) |

## Estado atual do repositório (antes da cópia para o WSL)

```
docs/projeto_final_estruturas_de_dados.pdf     # enunciado original
docs/relatorio-enunciado-grupo16.md            # análise completa do enunciado + seção sobre setup WSL
workload/gen_workload_1.py                     # script do professor — AINDA NÃO REVISADO nesta sessão
```

Nome do repositório sugere que a estrutura escolhida provavelmente é **AVL**, mas isso não foi confirmado explicitamente com o usuário — vale perguntar antes de assumir.

## O que já foi feito

1. Leitura e análise completa do enunciado (PDF), com relatório em `docs/relatorio-enunciado-grupo16.md` cobrindo: objetivos, estrutura obrigatória, dataset SOSD, geração de trace/oráculo, estudo empírico exigido, entregáveis, critérios de avaliação, regras, e os parâmetros específicos do Grupo 16.
2. Configuração do ambiente WSL2 no Windows do usuário:
   - Máquina: **Intel i5-12400T** (6 núcleos / 12 threads), **~15,7 GiB RAM física total**.
   - WSL2 já estava instalado (Ubuntu 26.04 LTS), mas limitado a 4GB RAM / 2 CPUs por padrão.
   - `.wslconfig` do usuário (`C:\Users\usuario\.wslconfig`) foi atualizado para:
     ```ini
     [wsl2]
     memory=12GB
     processors=8
     swap=4GB
     localhostForwarding=true
     ```
   - Racional: 12GB/8CPUs para o WSL, deixando ~3,7GiB/4 CPUs de folga para Windows host + Docker Desktop (que compartilha a mesma VM WSL2). Aplicado via `wsl --shutdown` e confirmado (WSL reporta ~11GiB RAM, 8 CPUs).
   - Isso está documentado na Seção 13 de `docs/relatorio-enunciado-grupo16.md`, incluindo o porquê (§7 do enunciado exige declarar máquina/metodologia nos gráficos).
3. Usuário copiou o repositório para dentro do WSL e está trocando a janela do VS Code para *Remote - WSL*.

## O que falta (próximos passos sugeridos, não executar sem o usuário confirmar)

1. Confirmar o caminho onde o repositório ficou dentro do WSL (recomendado: filesystem nativo Linux, ex. `~/trabalho-ed-avl`, **não** `/mnt/c/...` — I/O em `/mnt/c` é sensivelmente mais lento no WSL2, relevante para um dataset de 6,4 GB).
2. Instalar dependências do `download.sh` do SOSD dentro do Ubuntu: `zstd`, `python3-pip`, `m4`, `cmake`, `clang`, `libboost-all-dev`, `numpy`, `scipy` (Rust só necessário se for construir os RMIs do SOSD — não exigido por este projeto).
3. Revisar o conteúdo de `workload/gen_workload_1.py` junto com o usuário (ainda não foi lido nesta sessão) — confirmar se é o `gen_workload.py` mencionado no enunciado e se os parâmetros batem com a tabela do Grupo 16.
4. Baixar o dataset `osm_cellids_800M_uint64` (via Zenodo, comando já está em `docs/relatorio-enunciado-grupo16.md` §5.1) — confirmar checksum com `md5sum`.
5. Só depois disso: discutir com o usuário a escolha da estrutura (AVL confirmada?), os invariantes da árvore aumentada, e como será a implementação — sempre em modo de explicação/acompanhamento, não implementação autônoma.

## Estilo de colaboração observado nesta sessão

- Usuário prefere decisões de infraestrutura (RAM/CPU do WSL etc.) discutidas via perguntas de múltipla escolha antes de aplicar, especialmente quando afeta recursos compartilhados com o host (Docker Desktop rodando na mesma VM).
- Usuário corrige premissas técnicas quando erradas (ex.: apontou que 8 CPUs não é 100% do processador — corrigiu para considerar os 12 lógicos do i5-12400T corretamente).
- Respostas devem ser diretas e técnicas, em pt-BR.
