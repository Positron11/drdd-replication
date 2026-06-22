import sys

from contextlib  import contextmanager
from pathlib     import Path
from core.errors import DDError
from utils.fmt   import fmt_bytes, fit


def report(
		out_path :Path, 
		in_bytes :int, 
		out_bytes:int, 
		n_calls  :int, 
		verbose  :bool) -> None:
	
	"""Print the minimization result summary."""

	if verbose:
		print(

			f"\n - Minimized: {fmt_bytes(in_bytes)} -> {fmt_bytes(out_bytes)}"
			f"\n - Oracle:    {n_calls} calls"
			f"\n - Output:    {fit(str(out_path), width=50, front=True)}"

		)

	else: print(f"Wrote minimized file to: {out_path}")


@contextmanager
def cli_guard(verbose:bool=False):
	"""Handle anticipated (DDError) failures cleanly; let anything unexpected crash with a trace."""

	try: yield

	except DDError as e:
		print(f"Error: {e}", file=sys.stderr)

		sys.exit(1)

	except KeyboardInterrupt:
		if verbose: print("\n\nInterrupted by user (130)", file=sys.stderr)

		sys.exit(130)
