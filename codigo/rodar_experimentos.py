from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


GROUP_MIX = "35:30:35"
GROUP_SEED = 16


@dataclass(frozen=True)
class Scenario:
    name: str
    category: str
    universe: int
    operations: int
    theta: float
    insert_order: str

    @property
    def max_load(self) -> int:
        return max(1_000, self.universe * 2)


def scenarios_for(suite: str) -> list[Scenario]:
    if suite == "pilot":
        return [Scenario("pilot_n10000", "pilot", 10_000, 20_000, 0.6, "shuffle")]

    scenarios = [
        Scenario(f"scale_n{size}", "scale", size, size * 2, 0.6, "shuffle")
        for size in (100, 1_000, 10_000, 100_000, 1_000_000)
    ]
    scenarios.extend(
        Scenario(
            f"theta_{str(theta).replace('.', '_')}",
            "theta",
            100_000,
            200_000,
            theta,
            "shuffle",
        )
        for theta in (0.0, 0.6, 0.99, 1.2)
    )
    scenarios.extend(
        Scenario(f"order_{order}", "order", 10_000, 20_000, 0.6, order)
        for order in ("shuffle", "sorted")
    )

    unique = {scenario.name: scenario for scenario in scenarios}
    return list(unique.values())


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def write_scenarios(path: Path, scenarios: list[Scenario]) -> None:
    fieldnames = [
        "name",
        "category",
        "universe",
        "operations",
        "theta",
        "insert_order",
        "max_load",
        "mix",
        "seed",
    ]
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for scenario in scenarios:
            writer.writerow(
                {
                    **asdict(scenario),
                    "max_load": scenario.max_load,
                    "mix": GROUP_MIX,
                    "seed": GROUP_SEED,
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera e mede os cenarios reproduziveis do grupo 16."
    )
    parser.add_argument("--suite", choices=("pilot", "full"), default="pilot")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/osm_cellids_800M_uint64"),
    )
    parser.add_argument("--workloads", type=Path, default=Path("workloads"))
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("resultados/resultados.csv"),
    )
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--extra-queries", type=int, default=500)
    parser.add_argument(
        "--reset-results",
        action="store_true",
        help="apaga o CSV de resultados antes de iniciar",
    )
    args = parser.parse_args()

    if not args.data.exists():
        raise FileNotFoundError(f"conjunto OSM nao encontrado: {args.data}")
    if args.repetitions < 1:
        raise ValueError("repetitions deve ser pelo menos 1")

    args.workloads.mkdir(parents=True, exist_ok=True)
    args.results.parent.mkdir(parents=True, exist_ok=True)
    if args.reset_results and args.results.exists():
        args.results.unlink()

    scenarios = scenarios_for(args.suite)
    write_scenarios(args.results.with_name("cenarios.csv"), scenarios)

    for scenario in scenarios:
        prefix = args.workloads / scenario.name
        trace_path = prefix.with_suffix(".trace")
        expected_path = prefix.with_suffix(".expected")

        minimum_bytes = 8 + scenario.max_load * 8
        if args.data.stat().st_size < minimum_bytes:
            raise RuntimeError(
                f"arquivo OSM ainda nao possui os {minimum_bytes} bytes "
                f"necessarios para {scenario.name}"
            )

        if not trace_path.exists() or not expected_path.exists():
            run(
                [
                    sys.executable,
                    "-m",
                    "codigo.gen_workload",
                    "generate",
                    "--keys",
                    str(args.data),
                    "--format",
                    "sosd",
                    "--key-bytes",
                    "8",
                    "--max-load",
                    str(scenario.max_load),
                    "--out",
                    str(prefix),
                    "--ops",
                    str(scenario.operations),
                    "--universe",
                    str(scenario.universe),
                    "--mix",
                    GROUP_MIX,
                    "--theta",
                    str(scenario.theta),
                    "--insert-order",
                    scenario.insert_order,
                    "--seed",
                    str(GROUP_SEED),
                ]
            )

        for repetition in range(1, args.repetitions + 1):
            label = f"{scenario.name}_r{repetition}"
            for structure in ("avl", "bst"):
                run(
                    [
                        sys.executable,
                        "-m",
                        "codigo.benchmark",
                        str(trace_path),
                        "--structure",
                        structure,
                        "--label",
                        label,
                        "--csv",
                        str(args.results),
                        "--extra-queries",
                        str(args.extra_queries),
                    ]
                )

    print(f"[ok] resultados gravados em {args.results}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
