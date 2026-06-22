import json
import os
import select
import subprocess
import tempfile

from pathlib     import Path
from core.errors import OracleError


class WorkerError(OracleError):
	"""Worker process protocol or startup error."""


class WorkerSession:
	"""Persistent stdin/stdout pipe to a long-lived `node worker.mjs` process.

	Each query() writes the candidate bytes to a per-session tempfile inside
	the lib/ tree (so ../instrumented/lodash/* relative imports resolve), then
	asks the worker to import + run the file. Worker uses ?t=<counter> cache
	busting so a freshly mutated candidate is never served from ESM cache.
	"""

	def __init__(self, lib_path:Path) -> None:
		self._lib_path              = lib_path
		self._proc:subprocess.Popen = None    # type: ignore[assignment]
		self._tmp_path:Path         = None    # type: ignore[assignment]


	def __enter__(self) -> "WorkerSession":

		# stage tempfile inside lib/ so relative ../instrumented imports resolve
		stage_dir = self._lib_path / "case-staging"

		stage_dir.mkdir(exist_ok=True)

		fd, tmp        = tempfile.mkstemp(dir=stage_dir, prefix="dd_", suffix=".spec.js")
		self._tmp_path = Path(tmp)

		os.close(fd)

		self._spawn()

		return self


	def _spawn(self) -> None:
		"""(Re)start the worker process and consume its ready handshake."""

		self._proc = subprocess.Popen(

			args    = ["node", "worker.mjs"],
			stdin   = subprocess.PIPE,
			stdout  = subprocess.PIPE,
			stderr  = subprocess.DEVNULL,    # pathological candidates spew ESM errors here
			cwd     = str(self._lib_path),
			text    = True,
			bufsize = 1,
			env     = {**os.environ, "NODE_NO_WARNINGS": "1"},

		)

		# read ready handshake
		line = self._proc.stdout.readline()    # type: ignore[union-attr]

		if not line: raise WorkerError("worker did not produce a ready line")

		ready = json.loads(line)
		
		if not ready.get("ready"): raise WorkerError(f"worker reported {ready}")


	def _kill(self) -> None:
		"""Terminate the worker (if any) and forget it."""

		if self._proc is None: return

		for stream in (self._proc.stdin, self._proc.stdout):
			try:
				if stream is not None: stream.close()

			except OSError: pass

		try: self._proc.kill()
		except OSError: pass

		try: self._proc.wait(timeout=2)
		except subprocess.TimeoutExpired: pass

		self._proc = None   # type: ignore[assignment]


	def query(self, candidate:bytes, timeout:float | None = None) -> dict:
		"""Write candidate to staged tempfile and ask worker to run it.

		Pathological candidates can crash the worker outright (e.g. a fatal ESM
		resolution error from an over-reduced import). A dead or unparseable
		worker is reported as WorkerError (-> oracle False, which is correct: it
		did not reproduce the target signature) and respawned lazily on the next
		call, so one bad candidate can't abort a whole minimization.
		"""

		self._tmp_path.write_bytes(candidate)

		# (re)start the worker if it is absent or has exited
		if self._proc is None or self._proc.poll() is not None: self._spawn()

		try:
			self._proc.stdin.write(str(self._tmp_path) + "\n")    # type: ignore[union-attr]
			self._proc.stdin.flush()                              # type: ignore[union-attr]

			# a non-terminating candidate (e.g. an infinite loop) would block readline
			# forever, so wait for output with a timeout and kill the worker if it stalls
			if timeout is not None and not select.select([self._proc.stdout], [], [], timeout)[0]:
				self._kill()
				
				raise WorkerError(f"worker timed out after {timeout}s")

			line = self._proc.stdout.readline()    # type: ignore[union-attr]

		except OSError as e:
			self._kill()
			
			raise WorkerError(f"worker pipe error: {e}")

		if not line:
			self._kill()
			
			raise WorkerError("worker exited unexpectedly")

		try: return json.loads(line)

		except json.JSONDecodeError:
			self._kill()
			
			raise WorkerError(f"worker emitted non-JSON: {line!r}")


	def __exit__(self, *_) -> None:
		if self._proc is not None:
			try:
				if self._proc.stdin is not None: self._proc.stdin.close()

			except OSError: pass

			try: self._proc.wait(timeout=5)
			except subprocess.TimeoutExpired: self._kill()

			self._proc = None    # type: ignore[assignment]

		if self._tmp_path is not None:
			self._tmp_path.unlink(missing_ok=True)
			
			self._tmp_path = None    # type: ignore[assignment]
