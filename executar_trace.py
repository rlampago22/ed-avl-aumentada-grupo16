from __future__ import annotations

import argparse
import sys
from pathlib import Path

from avl_aumentada import Node, delete, insert, search, validate_invariants


def execute_trace(
    trace_path: Path,
    output_path: Path,
    validate_every: int = 0,
) -> tuple[Node | None, dict[str, int]]:
    """Executa um trace I/D/S e grava as respostas das buscas."""

    root: Node | None = None
    counts = {"I": 0, "D": 0, "S": 0}
    operation_count = 0

    with trace_path.open("r", encoding="utf-8") as trace_file, output_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as output_file:
        for line_number, line in enumerate(trace_file, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            try:
                operation, raw_key = stripped.split()
                key = int(raw_key)
            except ValueError as error:
                raise ValueError(
                    f"linha {line_number} invalida: {line.rstrip()}"
                ) from error

            if operation == "I":
                root = insert(root, key)
            elif operation == "D":
                root = delete(root, key)
            elif operation == "S":
                result = "FOUND" if search(root, key) else "NOT_FOUND"
                output_file.write(f"{key} {result}\n")
            else:
                raise ValueError(
                    f"operacao desconhecida na linha {line_number}: {operation}"
                )

            counts[operation] += 1
            operation_count += 1
            if validate_every and operation_count % validate_every == 0:
                validate_invariants(root)

    if validate_every:
        validate_invariants(root)
    return root, counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa um trace do gen_workload usando a AVL aumentada."
    )
    parser.add_argument("trace", type=Path, help="arquivo .trace de entrada")
    parser.add_argument("output", type=Path, help="arquivo de respostas")
    parser.add_argument(
        "--validate-every",
        type=int,
        default=0,
        metavar="N",
        help="valida todos os invariantes a cada N operacoes (modo de teste)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root, counts = execute_trace(args.trace, args.output, args.validate_every)
    live_keys = 0 if root is None else root.size
    print(
        f"[ok] I={counts['I']} D={counts['D']} S={counts['S']} "
        f"chaves_vivas={live_keys}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
