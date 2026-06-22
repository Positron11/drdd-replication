import csv
import subprocess

from dataclasses import dataclass
from datetime    import datetime
from pathlib     import Path


@dataclass(frozen=True)
class RunResult:
	"""Outcome of one minimization run."""

	started         :datetime
	wall_time       :float
	calls           :int
	minimized_length:int | None
	error           :str | None


def result_dir(label:str) -> str:
	"""Construct a run directory name."""

	ts = datetime.now().strftime("%d-%m-%Y_%H:%M")

	try:
		commit = subprocess.check_output(

			["git", "rev-parse", "--short", "HEAD"],

			text   = True,
			stderr = subprocess.DEVNULL

		).strip()

	# git sha falls back to 'nogit' if unavailable
	except (subprocess.CalledProcessError, FileNotFoundError): commit = "nogit"

	return f"{label}_{ts}_git-{commit}"


def write_csv(rows:list[dict], out_csv:Path) -> None:
	"""Write rows to a CSV, unioning columns across rows so optional keys appear."""

	out_csv.parent.mkdir(parents=True, exist_ok=True)

	# union of keys across rows, in first-seen order
	fieldnames = list(dict.fromkeys(k for row in rows for k in row))

	with out_csv.open("w", newline="", encoding="utf-8") as f:

		# initialize CSV with all fields
		writer = csv.DictWriter(f, fieldnames=fieldnames)

		writer.writeheader()

		for r in rows: writer.writerow(r)
