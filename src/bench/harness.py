import hashlib
import sys
import time

from pathlib import Path

from datetime       import datetime, timezone, timedelta
from dataclasses    import dataclass
from typing         import Callable
from core.oracle    import Oracle
from core.errors    import DDError, ConfigError
from reducers       import REDUCERS, PROBABILISTIC
from loader         import load_dataset, Family, Case
from runtime.runner import run_minimization
from bench.results  import RunResult, write_csv
from bench.logging  import TerminalView, FileView


_INTERRUPTED = "Interrupted"


@dataclass
class BenchTask:
	label     :str
	input_path:Path
	reducer   :str
	reducer_fn:Callable
	oracle    :Oracle
	kwargs    :dict


def _sha256_hex(path:Path) -> str:
	"""Compute hash of file contents."""

	try: return hashlib.sha256(path.read_bytes()).hexdigest()
	except FileNotFoundError: return ""


def _file_size_bytes(path:Path) -> int:
	"""Compute file size in bytes."""

	try: return path.stat().st_size
	except FileNotFoundError: return -1


def _run_one(task:BenchTask, views:list, started:datetime) -> RunResult:
	"""Run one minimization and capture its outcome."""

	start_perf = time.perf_counter()
	minimized  = None
	error      = None

	try: minimized = run_minimization(

		data    = task.input_path.read_bytes(),
		reducer = task.reducer_fn,
		oracle  = task.oracle,
		views   = views,

		**task.kwargs

	)

	except KeyboardInterrupt: error = _INTERRUPTED
	except Exception as e:    error = f"{type(e).__name__}: {e}"

	finally: wall_time = time.perf_counter() - start_perf

	return RunResult(

		started          = started,
		wall_time        = wall_time,
		calls            = task.oracle.calls,
		minimized_length = len(minimized) if minimized is not None else None,
		error            = error,

	)


def _row(task:BenchTask, result:RunResult) -> dict:
	"""Flatten a task and its result into a CSV row."""

	ok = result.minimized_length is not None

	row = {

		"ts_start"          : result.started.isoformat(),
		"ts_end"            : (result.started + timedelta(seconds=result.wall_time)).isoformat(),
		"predicate"         : task.label,
		"input_bytes"       : _file_size_bytes(task.input_path),
		"input_sha256"      : _sha256_hex(task.input_path),
		"reducer"           : task.reducer,
		"minimized_length"  : result.minimized_length if ok else "",
		"oracle_invocations": result.calls            if ok else "",

	}

	if result.error: row["error"] = result.error

	return row


def _run_task(i:int, n_tasks:int, task:BenchTask, log_dir:Path) -> RunResult:
	"""Run one task against its own log file and a live terminal view."""

	log_path    = log_dir / f"{i:04d}_{task.label}_{task.reducer}.log"
	started     = datetime.now(timezone.utc)
	counter_str = f"{i + 1:>4}/{n_tasks}"
	input_bytes = _file_size_bytes(task.input_path)

	with log_path.open("w", encoding="utf-8", buffering=1) as lf:

		# user-facing logger
		terminal_v = TerminalView(

			input_size  = input_bytes,
			counter_str = counter_str,
			reducer     = task.reducer,
			label       = task.label

		)

		# back-end logfile logger
		file_v = FileView(

			stream     = lf,
			input_size = input_bytes,
			reducer    = task.reducer,
			label      = task.label,
			started    = started,
			interval   = 5.0

		)

		# execute test
		result = _run_one(

			task    = task,
			views   = [terminal_v, file_v],
			started = started

		)

		# close loggers
		terminal_v.done(result)
		file_v.done(result)

	return result


def _run_all(tasks:list[BenchTask], run_dir:Path) -> None:
	"""Run a series of benchmark tasks, writing per-task logs and a summary CSV."""

	if not tasks: print("No tasks to run."); return

	n_tasks   = len(tasks)
	log_dir   = run_dir / "logs"
	csv_path  = run_dir / "result.csv"

	log_dir.mkdir(parents=True, exist_ok=True)

	rows      = []
	interrupt = False

	try:
		for i, task in enumerate(tasks):
			result = _run_task(i, n_tasks, task, log_dir)
			
			rows.append(_row(task, result))

			# rewrite after every task so an unexpected crash can't lose the whole run
			write_csv(rows, csv_path)

			if result.error == _INTERRUPTED: interrupt = True; break

	except KeyboardInterrupt: interrupt = True

	errs = sum(1 for r in rows if r.get("error"))

	if interrupt: print(f"\nInterrupted after {len(rows)} task(s) ({errs} failed).\n")
	else:         print(f"\nCompleted {n_tasks} task(s) ({errs} failed).\n")

	if rows: write_csv(rows, csv_path)


def _exit(message:str) -> None:
	"""Report a setup failure and abort the benchmark."""

	print(f"  {message}", file=sys.stderr)

	sys.exit(1)


def _build_tasks(
		family  :Family, 
		cases   :list[Case], 
		reducers:list[str]) -> list[BenchTask]:
	
	"""Every (selected case x reducer) as a ready-to-run BenchTask, oracle built and validated here."""

	tasks = []

	for c in cases:
		for reducer in reducers:

			# constructing the oracle surfaces any setup failure for this case
			# (ConfigError, or anything a third-party oracle.py raises -> DDError)
			try: oracle = family.oracle(c.config)
			except DDError as e: _exit(f"{c.id}: {e}")

			tasks.append(BenchTask(

				label      = c.id,
				input_path = c.path,
				reducer    = reducer,
				reducer_fn = REDUCERS[reducer],
				oracle     = oracle,
				kwargs     = {"p_0": family.tuning["p_0"]} if (reducer in PROBABILISTIC and "p_0" in family.tuning) else {},

			))

	return tasks


def run_family_benchmark(
		predicates_root:Path,
		name           :str,
		reducers       :list[str],
		ids            :list[str],
		run_dir        :Path) -> None:

	"""Run `reducers` x selected cases from a dataset's manifest.json."""

	family   = load_dataset(predicates_root / name)
	selected = set(ids) if ids else family.cases.keys()

	# materialize each selected case (case() surfaces an unknown id or a missing input)
	try: cases = [family.case(i) for i in selected]
	except ConfigError as e: _exit(str(e))

	print(

		f"\n{name} Benchmark\n\n"
		f"cases      : {len(cases)}\n"
		f"reducers   : {', '.join(reducers)}\n"
		f"output     : {run_dir}\n"

	)

	_run_all(_build_tasks(family, cases, reducers), run_dir)
