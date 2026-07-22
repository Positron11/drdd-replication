import sys

from contextlib  import contextmanager
from core.errors import DDError


@contextmanager
def cli_guard(verbose:bool=False):
	"""Handle anticipated (DDError) failures cleanly; let anything unexpected crash with a trace.

	Library code here raises DDError for the failures a user can act on - an
	unbuilt oracle, a malformed manifest, a case id that does not exist. Those
	are reported as a message and a non-zero exit; anything else is a bug and
	keeps its traceback.

	It lives in the library rather than beside any one entry point because every
	entry point needs it, including the ones inside a predicate family.
	"""

	try: yield

	except DDError as e:
		print(f"Error: {e}", file=sys.stderr)

		sys.exit(1)

	except KeyboardInterrupt:
		if verbose: print("\n\nInterrupted by user (130)", file=sys.stderr)

		sys.exit(130)
