#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_workload.py -- Gerador de cargas de trabalho (insercao/remocao/busca) e
oraculo de referencia para avaliacao de estruturas de dados em larga escala.

Subcomandos:
  generate  -> a partir de um conjunto de chaves reais (SOSD ou texto),
               produz um arquivo de TRACE (.trace) e o gabarito (.expected).
  verify    -> compara a saida da estrutura do aluno (.out) com o gabarito.

Formato do TRACE (uma operacao por linha):
    I <chave>      insercao
    D <chave>      remocao
    S <chave>      busca

Formato do gabarito (.expected), apenas para operacoes S, na ordem:
    <chave> <FOUND|NOT_FOUND>

A correcao das operacoes I e D e verificada de forma TRANSITIVA: o resultado
esperado de cada busca depende de todas as insercoes e remocoes anteriores,
de modo que uma implementacao incorreta de I ou D produz divergencia em S.

O padrao de acesso segue uma distribuicao Zipfiana (estilo YCSB): poucas
chaves concentram a maior parte das buscas e remocoes, estressando o
rebalanceamento e a localidade de cache de formas diferentes de um acesso
uniforme.
"""

import argparse
import struct
import sys
import random
import numpy as np


# ---------------------------------------------------------------------------
# Gerador Zipfiano (Gray et al., "Quickly Generating Billion-Record Synthetic
# Databases"), o mesmo esquema usado pelo YCSB.
# ---------------------------------------------------------------------------
class Zipfian:
    def __init__(self, n, theta, seed):
        if n < 1:
            n = 1
        self.n = n
        self.theta = theta
        self.rng = random.Random(seed)
        self.zeta_n = self._zeta(n, theta)
        self.zeta2 = self._zeta(2, theta)
        self.alpha = 1.0 / (1.0 - theta)
        self.eta = (1.0 - (2.0 / n) ** (1.0 - theta)) / (1.0 - self.zeta2 / self.zeta_n)

    @staticmethod
    def _zeta(n, theta):
        # Soma de 1/i^theta para i = 1..n, calculada em blocos para limitar memoria.
        total = 0.0
        chunk = 1_000_000
        i = 1
        while i <= n:
            j = min(i + chunk - 1, n)
            idx = np.arange(i, j + 1, dtype=np.float64)
            total += float(np.sum(1.0 / np.power(idx, theta)))
            i = j + 1
        return total

    def next_rank(self):
        """Retorna um rank em [0, n); ranks baixos sao os mais 'quentes'."""
        u = self.rng.random()
        uz = u * self.zeta_n
        if uz < 1.0:
            return 0
        if uz < 1.0 + (0.5 ** self.theta):
            return 1
        return int(self.n * ((self.eta * u - self.eta + 1.0) ** self.alpha))


# ---------------------------------------------------------------------------
# Conjunto "vivo" com amostragem por posicao em O(1): array + mapa indice.
# A remocao usa o truque swap-with-last.
# ---------------------------------------------------------------------------
class LiveSet:
    def __init__(self):
        self.arr = []          # chaves atualmente inseridas
        self.pos = {}          # chave -> indice em arr

    def __len__(self):
        return len(self.arr)

    def contains(self, key):
        return key in self.pos

    def add(self, key):
        if key in self.pos:
            return False
        self.pos[key] = len(self.arr)
        self.arr.append(key)
        return True

    def remove(self, key):
        i = self.pos.get(key)
        if i is None:
            return False
        last = self.arr[-1]
        self.arr[i] = last
        self.pos[last] = i
        self.arr.pop()
        del self.pos[key]
        return True

    def at_rank(self, rank):
        # Zipfiano "embaralhado" sobre o conjunto vivo: a posicao quente varia
        # conforme insercoes/remocoes, decorrelacionando rank de valor de chave.
        return self.arr[rank % len(self.arr)]


# ---------------------------------------------------------------------------
# Leitura das chaves
# ---------------------------------------------------------------------------
def load_keys(path, fmt, key_bytes, max_load=0):
    if fmt == "sosd" or (fmt == "auto" and not path.endswith((".txt", ".csv"))):
        dtype = np.uint32 if key_bytes == 4 else np.uint64
        with open(path, "rb") as f:
            n = struct.unpack("<Q", f.read(8))[0]
            if max_load:
                n = min(n, max_load)            # le apenas as primeiras n chaves
            arr = np.fromfile(f, dtype=dtype, count=n)
        return arr.astype(np.uint64)
    # texto: um inteiro por linha
    rows = max_load if max_load else None
    return np.loadtxt(path, dtype=np.uint64, max_rows=rows)


def synthetic_keys(n, seed):
    rng = np.random.default_rng(seed)
    # chaves densas com lacunas irregulares, lembrando dados reais
    gaps = rng.integers(1, 40, size=n, dtype=np.uint64)
    return np.cumsum(gaps, dtype=np.uint64)


# ---------------------------------------------------------------------------
# Geracao do trace + gabarito
# ---------------------------------------------------------------------------
def generate(args):
    if args.synthetic:
        keys = synthetic_keys(args.synthetic, args.seed)
    else:
        keys = load_keys(args.keys, args.format, args.key_bytes, args.max_load)

    keys = np.unique(keys)                      # garante chaves distintas
    rng = random.Random(args.seed)

    U = min(args.universe, len(keys)) if args.universe else len(keys)
    idx = list(range(len(keys)))
    rng.shuffle(idx)
    chosen = keys[idx[:U]]

    # Reserva uma fracao de chaves que NUNCA sao inseridas, para testar buscas
    # com resultado NOT_FOUND de forma garantida.
    R = int(U * args.reserve)
    reserved = chosen[:R]
    insertable = chosen[R:]

    # Ordem de insercao
    if args.insert_order == "sorted":
        insert_order = np.sort(insertable).tolist()     # caso patologico p/ BST
    elif args.insert_order == "popularity":
        insert_order = insertable.tolist()              # ordem ja embaralhada
    else:
        order = list(insertable)
        rng.shuffle(order)
        insert_order = order

    live = LiveSet()
    deleted = []          # chaves removidas (nunca reinseridas) -> testam D via S
    zipf_live = Zipfian(max(len(insertable), 1), args.theta, args.seed + 1)
    zipf_miss = Zipfian(max(len(reserved), 1), args.theta, args.seed + 2)

    p_ins, p_del, p_srch = _mix(args.mix)
    next_insert = 0
    n_ins = n_del = n_srch = n_hit = n_miss = 0

    with open(args.out + ".trace", "w") as ft, open(args.out + ".expected", "w") as fe:
        ft.write(f"# universe={U} reserve={R} mix={args.mix} theta={args.theta} "
                 f"seed={args.seed} insert_order={args.insert_order} ops={args.ops}\n")
        for _ in range(args.ops):
            r = rng.random()

            # Forca insercoes enquanto o conjunto vivo estiver vazio.
            if len(live) == 0:
                op = "I"
            elif r < p_ins and next_insert < len(insert_order):
                op = "I"
            elif r < p_ins + p_del:
                op = "D"
            else:
                op = "S"

            if op == "I":
                if next_insert >= len(insert_order):
                    op = "S"                     # esgotou chaves inseriveis
                else:
                    key = insert_order[next_insert]
                    next_insert += 1
                    live.add(int(key))
                    ft.write(f"I {int(key)}\n")
                    n_ins += 1
                    continue

            if op == "D":
                if rng.random() < args.absent and R > 0:
                    key = int(reserved[zipf_miss.next_rank() % R])    # remover ausente
                else:
                    key = int(live.at_rank(zipf_live.next_rank()))
                    live.remove(key)
                    deleted.append(key)          # passa a ser alvo de buscas-miss
                ft.write(f"D {key}\n")
                n_del += 1
                continue

            # op == "S"
            want_hit = (rng.random() < args.hit) and len(live) > 0
            if want_hit:
                key = int(live.at_rank(zipf_live.next_rank()))
                result = "FOUND"
                n_hit += 1
            else:
                # Busca-miss: ora chave reservada (nunca inserida), ora chave
                # ja REMOVIDA. Esta ultima e o que testa a corretude de D via S.
                if deleted and rng.random() < args.deleted_miss:
                    key = int(deleted[rng.randrange(len(deleted))])
                elif R > 0:
                    key = int(reserved[zipf_miss.next_rank() % R])
                elif deleted:
                    key = int(deleted[rng.randrange(len(deleted))])
                else:
                    key = int(live.at_rank(zipf_live.next_rank()))
                    result = "FOUND"
                    n_hit += 1
                    ft.write(f"S {key}\n")
                    fe.write(f"{key} {result}\n")
                    n_srch += 1
                    continue
                result = "NOT_FOUND"
                n_miss += 1
            ft.write(f"S {key}\n")
            fe.write(f"{key} {result}\n")
            n_srch += 1

    sys.stderr.write(
        f"[ok] {args.out}.trace e {args.out}.expected gerados\n"
        f"     insercoes={n_ins}  remocoes={n_del}  buscas={n_srch} "
        f"(hits={n_hit}, misses={n_miss})\n"
        f"     chaves vivas ao final={len(live)}  universo={U}  reservadas={R}\n"
    )


def _mix(spec):
    parts = [float(x) for x in spec.split(":")]
    s = sum(parts)
    return parts[0] / s, parts[1] / s, parts[2] / s


# ---------------------------------------------------------------------------
# Verificacao da saida do aluno
# ---------------------------------------------------------------------------
def verify(args):
    mism = 0
    total = 0
    first = None
    with open(args.expected) as fe, open(args.candidate) as fc:
        for ln, (e, c) in enumerate(zip(fe, fc), 1):
            total += 1
            if e.strip() != c.strip():
                mism += 1
                if first is None:
                    first = (ln, e.strip(), c.strip())
    if mism == 0:
        print(f"[OK] {total} buscas conferidas, nenhuma divergencia.")
        return 0
    print(f"[FALHA] {mism}/{total} divergencias.")
    if first:
        print(f"       1a divergencia na linha {first[0]}: "
              f"esperado='{first[1]}'  obtido='{first[2]}'")
    return 1


# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="gera trace + gabarito")
    src = g.add_mutually_exclusive_group(required=True)
    src.add_argument("--keys", help="arquivo de chaves (SOSD binario ou texto)")
    src.add_argument("--synthetic", type=int, help="gera N chaves sinteticas (teste)")
    g.add_argument("--format", choices=["auto", "sosd", "text"], default="auto")
    g.add_argument("--key-bytes", type=int, choices=[4, 8], default=8)
    g.add_argument("--max-load", type=int, default=0,
                   help="le no maximo N chaves do arquivo (limita memoria; 0 = todas)")
    g.add_argument("--out", required=True, help="prefixo de saida")
    g.add_argument("--ops", type=int, default=1_000_000, help="numero de operacoes")
    g.add_argument("--universe", type=int, default=0,
                   help="num. de chaves distintas usadas (0 = todas)")
    g.add_argument("--mix", default="50:20:30",
                   help="proporcao I:D:S (ex.: 50:20:30)")
    g.add_argument("--theta", type=float, default=0.99,
                   help="parametro Zipfiano (0=uniforme; 0.99 = YCSB padrao)")
    g.add_argument("--reserve", type=float, default=0.10,
                   help="fracao de chaves nunca inseridas (testes de miss)")
    g.add_argument("--hit", type=float, default=0.7,
                   help="fracao alvo de buscas com sucesso")
    g.add_argument("--absent", type=float, default=0.05,
                   help="fracao de remocoes de chave ausente")
    g.add_argument("--deleted-miss", type=float, default=0.5,
                   help="fracao das buscas-miss que miram chaves ja removidas")
    g.add_argument("--insert-order", choices=["shuffle", "sorted", "popularity"],
                   default="shuffle")
    g.add_argument("--seed", type=int, default=42)
    g.set_defaults(func=generate)

    v = sub.add_parser("verify", help="compara saida do aluno com o gabarito")
    v.add_argument("--expected", required=True)
    v.add_argument("--candidate", required=True)
    v.set_defaults(func=verify)

    args = p.parse_args()
    rc = args.func(args)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
