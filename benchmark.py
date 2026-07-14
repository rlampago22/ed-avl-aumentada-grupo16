from __future__ import annotations

import argparse
import csv
import math
from array import array
from pathlib import Path
from time import perf_counter_ns

import avl_aumentada as avl
import bst_ingenua as bst


def percentile(samples: array, percentage: float) -> int:
    if not samples:
        return 0
    ordered = sorted(samples)
    index = max(0, math.ceil(percentage * len(ordered)) - 1)
    return ordered[index]


def benchmark_trace(
    trace_path: Path,
    structure: str,
    extra_queries: int = 0,
) -> tuple[list[dict[str, int | float | str]], int]:
    if structure == "avl":
        insert_fn = avl.insert
        delete_fn = avl.delete
        search_fn = avl.search
        rank_fn = avl.rank
        select_fn = avl.select
        range_fn = avl.range_agg
        avl.reset_rotation_counts()
    else:
        insert_fn = bst.insert
        delete_fn = bst.delete
        search_fn = bst.search
        rank_fn = bst.rank
        select_fn = bst.select
        range_fn = bst.range_agg

    root = None
    operation_order = ("I", "D", "S", "RANK", "SELECT", "RANGE")
    samples = {operation: array("Q") for operation in operation_order}
    query_keys = array("Q")
    checksum = 0

    with trace_path.open("r", encoding="utf-8") as trace_file:
        for line_number, line in enumerate(trace_file, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                operation, raw_key = stripped.split()
                key = int(raw_key)
            except ValueError as error:
                raise ValueError(f"linha {line_number} invalida") from error

            started = perf_counter_ns()
            if operation == "I":
                root = insert_fn(root, key)
            elif operation == "D":
                root = delete_fn(root, key)
            elif operation == "S":
                checksum += int(search_fn(root, key))
                if len(query_keys) < extra_queries:
                    query_keys.append(key)
            else:
                raise ValueError(f"operacao desconhecida: {operation}")
            samples[operation].append(perf_counter_ns() - started)

    if structure == "avl":
        final_size = avl.node_size(root)
        final_height = avl.node_height(root)
        rotations = avl.rotation_counts()
    else:
        final_size = bst.tree_size(root)
        final_height = bst.tree_height(root)
        rotations = {"left": 0, "right": 0}

    for index, key in enumerate(query_keys):
        started = perf_counter_ns()
        checksum += rank_fn(root, key)
        samples["RANK"].append(perf_counter_ns() - started)

        if final_size:
            position = (key % final_size) + 1
            started = perf_counter_ns()
            checksum += select_fn(root, position)
            samples["SELECT"].append(perf_counter_ns() - started)

        other_key = query_keys[(index + 1) % len(query_keys)]
        start, end = sorted((key, other_key))
        started = perf_counter_ns()
        checksum += range_fn(root, start, end)
        samples["RANGE"].append(perf_counter_ns() - started)

    rows: list[dict[str, int | float | str]] = []
    all_samples = array("Q")
    for operation in operation_order:
        operation_samples = samples[operation]
        if not operation_samples:
            continue
        all_samples.extend(operation_samples)
        total_ns = sum(operation_samples)
        rows.append(
            {
                "operation": operation,
                "count": len(operation_samples),
                "mean_ns": total_ns / len(operation_samples)
                if operation_samples
                else 0,
                "p50_ns": percentile(operation_samples, 0.50),
                "p99_ns": percentile(operation_samples, 0.99),
                "total_seconds": total_ns / 1_000_000_000,
                "final_size": final_size,
                "final_height": final_height,
                "rotations_left": rotations["left"],
                "rotations_right": rotations["right"],
            }
        )

    total_ns = sum(all_samples)
    rows.append(
        {
            "operation": "ALL",
            "count": len(all_samples),
            "mean_ns": total_ns / len(all_samples) if all_samples else 0,
            "p50_ns": percentile(all_samples, 0.50),
            "p99_ns": percentile(all_samples, 0.99),
            "total_seconds": total_ns / 1_000_000_000,
            "final_size": final_size,
            "final_height": final_height,
            "rotations_left": rotations["left"],
            "rotations_right": rotations["right"],
        }
    )
    return rows, checksum


def append_csv(
    csv_path: Path,
    label: str,
    structure: str,
    rows: list[dict[str, int | float | str]],
) -> None:
    fieldnames = [
        "label",
        "structure",
        "operation",
        "count",
        "mean_ns",
        "p50_ns",
        "p99_ns",
        "total_seconds",
        "final_size",
        "final_height",
        "rotations_left",
        "rotations_right",
    ]
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow({"label": label, "structure": structure, **row})


def main() -> int:
    parser = argparse.ArgumentParser(description="Mede AVL ou BST sobre um trace.")
    parser.add_argument("trace", type=Path)
    parser.add_argument("--structure", choices=("avl", "bst"), required=True)
    parser.add_argument("--label", default="")
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument(
        "--extra-queries",
        type=int,
        default=0,
        metavar="N",
        help="mede ate N consultas rank/select/range apos executar o trace",
    )
    args = parser.parse_args()

    label = args.label or args.trace.stem
    rows, checksum = benchmark_trace(
        args.trace,
        args.structure,
        args.extra_queries,
    )
    append_csv(args.csv, label, args.structure, rows)

    overall = rows[-1]
    print(
        f"[ok] {label} {args.structure}: n={overall['count']} "
        f"media={overall['mean_ns']:.1f}ns p50={overall['p50_ns']}ns "
        f"p99={overall['p99_ns']}ns altura={overall['final_height']} "
        f"checksum={checksum}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
