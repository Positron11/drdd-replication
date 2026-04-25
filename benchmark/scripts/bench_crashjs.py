import sys
import tomllib

from functools       import partial
from itertools       import product
from pathlib         import Path
from algos           import ALGORITHMS
from bench.harness   import BenchTask, result_dir, run_all
from drivers.crashjs import crashjs_minimizer


PROGRAM_DIR = Path(__file__).resolve().parent


def main():
	pred_root = PROGRAM_DIR.parents[1] / "predicates" / "crashjs"
	run_dir   = PROGRAM_DIR.parent / "runs" / result_dir("crashjs")
	lib_path  = pred_root / "lib"

	cases   = sorted(c for c in pred_root.iterdir() if c.is_dir() and c.name.startswith("lodash-"))
	missing = [c for c in cases if not (c / "input").exists()]

	if missing:
		for c in missing: print(f"  missing: {c.name}/input", file=sys.stderr)

		sys.exit(1)

	if not (lib_path / "worker.mjs").exists():
		print(f"  worker not built: {lib_path}/worker.mjs (run `make -C predicates/crashjs`)", file=sys.stderr)

		sys.exit(1)

	print(f"\nCrashJS Benchmark\n")
	print(f"cases      : {len(cases)}")
	print(f"algorithms : {', '.join(ALGORITHMS)}")
	print(f"output     : {run_dir}\n")

	configs = {}

	for case_dir in cases:
		config_path = case_dir / "config.toml"
		config      = tomllib.loads(config_path.read_text())

		for key in ("errType", "errMsg", "topFile"):
			if key not in config:
				print(f"  missing '{key}' in {config_path}", file=sys.stderr)

				sys.exit(1)

		configs[case_dir] = config

	tasks = [
		BenchTask(

			fn         = partial(crashjs_minimizer,

				input_path = case_dir / "input",
				algorithm  = algorithm,
				lib_path   = lib_path,
				err_type   = configs[case_dir]["errType"],
				err_msg    = configs[case_dir]["errMsg"],
				top_file   = configs[case_dir]["topFile"],
				timeout    = configs[case_dir].get("timeout", 10.0),

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
