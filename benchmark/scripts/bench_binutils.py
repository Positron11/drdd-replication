import sys
import tomllib

from functools        import partial
from itertools        import product
from pathlib          import Path
from algos            import ALGORITHMS
from bench.harness    import BenchTask, result_dir, run_all
from drivers.binutils import binutils_minimizer


PROGRAM_DIR = Path(__file__).resolve().parent


def main():
	pred_root = PROGRAM_DIR.parents[1] / "predicates" / "binutils"
	run_dir   = PROGRAM_DIR.parent / "runs" / result_dir("binutils")

	cases   = sorted(c for c in pred_root.iterdir() if c.is_dir() and c.name.startswith("bug-"))
	missing = [c for c in cases if not (c / "input").exists()]

	if missing:
		for c in missing: print(f"  missing: {c.name}/input", file=sys.stderr)

		sys.exit(1)

	print(f"\nBinutils Benchmark\n")
	print(f"cases      : {len(cases)}")
	print(f"algorithms : {', '.join(ALGORITHMS)}")
	print(f"output     : {run_dir}\n")

	configs = {}

	for case_dir in cases:
		config_path = case_dir / "config.toml"
		config      = tomllib.loads(config_path.read_text())

		for key in ("commit", "binary", "argv"):
			if key not in config:
				print(f"  missing '{key}' in {config_path}", file=sys.stderr)

				sys.exit(1)

		if ("signal" in config) == ("needle" in config):
			print(f"  must set exactly one of 'signal' or 'needle' in {config_path}", file=sys.stderr)

			sys.exit(1)

		configs[case_dir] = config

	tasks = [
		BenchTask(

			fn         = partial(binutils_minimizer,

				input_path  = case_dir / "input",
				algorithm   = algorithm,
				binary_path = pred_root / "lib" / f"{configs[case_dir]['binary']}-{configs[case_dir]['commit']}",
				argv        = configs[case_dir]["argv"],
				timeout     = configs[case_dir].get("timeout", 10.0),
				signal      = configs[case_dir].get("signal"),
				needle      = configs[case_dir]["needle"].encode() if "needle" in configs[case_dir] else None,
				stream      = configs[case_dir].get("stream", "stderr"),

			),
			input_path = case_dir / "input",
			algorithm  = algorithm,
			label      = case_dir.name,

		)

		for case_dir, algorithm in product(cases, ALGORITHMS)
	]

	run_all(tasks, run_dir)


if __name__ == "__main__":
	main()
