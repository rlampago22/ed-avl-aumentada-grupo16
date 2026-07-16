from __future__ import annotations

import argparse
import csv
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path
from statistics import median

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ed-avl-matplotlib")
)

import matplotlib.pyplot as plt


LABEL_PATTERN = re.compile(r"^(?P<scenario>.+)_r(?P<repetition>\d+)$")
COLORS = {"avl": "#176B87", "bst": "#C44536"}
MARKERS = {"avl": "o", "bst": "s"}
OPERATIONS = ("I", "D", "S", "RANK", "SELECT", "RANGE", "ALL")


def read_results(path: Path) -> list[dict[str, str | int | float]]:
    rows: list[dict[str, str | int | float]] = []
    with path.open(encoding="utf-8", newline="") as csv_file:
        for raw in csv.DictReader(csv_file):
            match = LABEL_PATTERN.fullmatch(raw["label"])
            if match is None:
                raise ValueError(f"rotulo de execucao invalido: {raw['label']}")
            rows.append(
                {
                    "scenario": match.group("scenario"),
                    "repetition": int(match.group("repetition")),
                    "structure": raw["structure"],
                    "operation": raw["operation"],
                    "p50_us": float(raw["p50_ns"]) / 1_000,
                    "p99_us": float(raw["p99_ns"]) / 1_000,
                    "mean_us": float(raw["mean_ns"]) / 1_000,
                    "final_height": int(raw["final_height"]),
                }
            )
    return rows


def validate(rows: list[dict[str, str | int | float]]) -> None:
    grouped: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    for row in rows:
        key = (
            str(row["scenario"]),
            str(row["structure"]),
            int(row["repetition"]),
        )
        grouped[key].add(str(row["operation"]))

    if len(rows) != 462 or len(grouped) != 66:
        raise ValueError(
            f"matriz incompleta: {len(rows)} linhas e {len(grouped)} execucoes"
        )
    expected = set(OPERATIONS)
    invalid = [key for key, operations in grouped.items() if operations != expected]
    if invalid:
        raise ValueError(f"execucoes sem todas as operacoes: {invalid}")


def summarized(
    rows: list[dict[str, str | int | float]],
) -> dict[tuple[str, str, str], dict[str, float]]:
    values: dict[tuple[str, str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        key = (
            str(row["scenario"]),
            str(row["structure"]),
            str(row["operation"]),
        )
        for metric in ("p50_us", "p99_us", "mean_us", "final_height"):
            values[key][metric].append(float(row[metric]))

    return {
        key: {metric: median(samples) for metric, samples in metrics.items()}
        for key, metrics in values.items()
    }


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linestyle": "--",
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def save_figure(figure: plt.Figure, path: Path) -> None:
    figure.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    print(f"[ok] {path}")


def plot_scale_heights(summary: dict, output: Path) -> None:
    sizes = (100, 1_000, 10_000, 100_000, 1_000_000)
    figure, axis = plt.subplots(figsize=(8.8, 4.8))
    for structure in ("avl", "bst"):
        heights = [
            summary[(f"scale_n{size}", structure, "ALL")]["final_height"]
            for size in sizes
        ]
        axis.plot(
            sizes,
            heights,
            color=COLORS[structure],
            marker=MARKERS[structure],
            linewidth=2.2,
            markersize=6,
            label=structure.upper(),
        )
    axis.set_xscale("log")
    axis.set_xticks(sizes, ("100", "1 mil", "10 mil", "100 mil", "1 milhão"))
    axis.set_xlabel("Tamanho do universo (n)")
    axis.set_ylabel("Altura final")
    axis.set_title("Crescimento da altura com entradas embaralhadas")
    axis.legend()
    figure.tight_layout()
    save_figure(figure, output / "escala_altura.png")


def plot_scale_queries(summary: dict, output: Path) -> None:
    sizes = (100, 1_000, 10_000, 100_000, 1_000_000)
    operations = ("RANK", "SELECT", "RANGE")
    titles = {"RANK": "rank(k)", "SELECT": "select(i)", "RANGE": "range_agg(a, b)"}
    figure, axes = plt.subplots(1, 3, figsize=(13.2, 4.5), sharex=True)
    for axis, operation in zip(axes, operations):
        for structure in ("avl", "bst"):
            values = [
                summary[(f"scale_n{size}", structure, operation)]["p50_us"]
                for size in sizes
            ]
            axis.plot(
                sizes,
                values,
                color=COLORS[structure],
                marker=MARKERS[structure],
                linewidth=2,
                markersize=5,
                label=structure.upper(),
            )
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_title(titles[operation])
        axis.set_xlabel("n")
    axes[0].set_ylabel("p50 (microssegundos, escala log)")
    axes[0].legend()
    figure.suptitle("Escalabilidade das consultas aumentadas", fontsize=14)
    figure.tight_layout()
    save_figure(figure, output / "escala_consultas_aumentadas.png")


def plot_theta(summary: dict, output: Path) -> None:
    scenarios = ("theta_0_0", "theta_0_6", "theta_0_99", "theta_1_2")
    theta_values = (0.0, 0.6, 0.99, 1.2)
    groups = (
        (("I", "D", "S"), "Operações básicas"),
        (("RANK", "SELECT", "RANGE"), "Consultas aumentadas"),
    )
    operation_colors = {
        "I": "#176B87",
        "D": "#C44536",
        "S": "#4C956C",
        "RANK": "#176B87",
        "SELECT": "#C44536",
        "RANGE": "#D59F2A",
    }
    figure, axes = plt.subplots(1, 2, figsize=(11.2, 4.5), sharex=True)
    for axis, (operations, title) in zip(axes, groups):
        for operation in operations:
            values = [
                summary[(scenario, "avl", operation)]["p50_us"]
                for scenario in scenarios
            ]
            axis.plot(
                theta_values,
                values,
                marker="o",
                linewidth=2,
                color=operation_colors[operation],
                label=operation,
            )
        axis.set_title(title)
        axis.set_xlabel("theta")
        axis.set_xticks(theta_values)
        axis.legend()
    axes[0].set_ylabel("p50 da AVL (microssegundos)")
    figure.suptitle("Sensibilidade da AVL à concentração de acessos", fontsize=14)
    figure.tight_layout()
    save_figure(figure, output / "theta_latencias_avl.png")


def average_metric(
    summary: dict,
    scenario: str,
    structure: str,
    operations: tuple[str, ...],
    metric: str,
) -> float:
    return sum(summary[(scenario, structure, op)][metric] for op in operations) / len(
        operations
    )


def plot_order(summary: dict, output: Path) -> None:
    orders = ("shuffle", "sorted")
    scenarios = {order: f"order_{order}" for order in orders}
    panels = (
        (("I",), "p50 de inserção", "microssegundos"),
        (("S",), "p50 de busca", "microssegundos"),
        (("ALL",), "Altura final", "níveis"),
    )
    figure, axes = plt.subplots(1, 3, figsize=(13.2, 4.7))
    x_positions = (0, 1)
    width = 0.34
    for axis, (operations, title, unit) in zip(axes, panels):
        for offset, structure in ((-width / 2, "avl"), (width / 2, "bst")):
            if title == "Altura final":
                values = [
                    summary[(scenarios[order], structure, "ALL")]["final_height"]
                    for order in orders
                ]
            else:
                values = [
                    average_metric(
                        summary,
                        scenarios[order],
                        structure,
                        operations,
                        "p50_us",
                    )
                    for order in orders
                ]
            axis.bar(
                [position + offset for position in x_positions],
                values,
                width,
                color=COLORS[structure],
                label=structure.upper(),
            )
        axis.set_yscale("log")
        axis.set_xticks(x_positions, ("shuffle", "sorted"))
        axis.set_title(title)
        axis.set_ylabel(f"{unit} (escala log)")
    axes[0].legend()
    figure.suptitle("Efeito da ordem de inserção sobre AVL e BST", fontsize=14)
    figure.tight_layout()
    save_figure(figure, output / "ordem_avl_bst.png")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida resultados e gera os quatro graficos finais."
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("resultados/resultados.csv"),
    )
    parser.add_argument("--output", type=Path, default=Path("graficos"))
    args = parser.parse_args()

    rows = read_results(args.results)
    validate(rows)
    summary = summarized(rows)
    args.output.mkdir(parents=True, exist_ok=True)
    setup_style()

    plot_scale_heights(summary, args.output)
    plot_scale_queries(summary, args.output)
    plot_theta(summary, args.output)
    plot_order(summary, args.output)
    print("[ok] matriz validada: 462 linhas, 66 execucoes completas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
