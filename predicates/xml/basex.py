import hashlib
import socket
import subprocess
import time

from pathlib     import Path
from typing      import BinaryIO
from core.errors import OracleError


_HOST       = "127.0.0.1"
_USER       = "admin"
_PASS       = "password"
_PORT_START = 1984
_PORT_MAX   = 65535


class BaseXError(OracleError):
	"""Protocol-level or query-execution error from a BaseX server."""


def _recv_until_null(f:BinaryIO) -> bytes:
	"""Read from buffered file until unescaped \\x00, decoding \\xFF escapes."""

	buf = bytearray()

	while True:
		b = f.read(1)

		if not b: raise BaseXError("Connection closed unexpectedly")

		if b == b"\x00": return bytes(buf)

		if b == b"\xff":
			nb = f.read(1)

			if not nb: raise BaseXError("Connection closed during escape sequence")

			buf.append(nb[0])

		else: buf.append(b[0])


def _send_str(sock:socket.socket, s:str) -> None:
	"""Escape and send a null-terminated UTF-8 string."""

	data = s.encode("utf-8")
	data = data.replace(b"\xff", b"\xff\xff").replace(b"\x00", b"\xff\x00")

	sock.sendall(data + b"\x00")


class BaseXSession:
	"""Persistent TCP session to a running BaseX server."""

	def __init__(self, port:int) -> None:
		self._port               = port
		self._sock:socket.socket = None    # type: ignore[assignment]
		self._file:BinaryIO      = None    # type: ignore[assignment]


	def _authenticate(self) -> None:
		"""Run the BaseX login handshake, auto-detecting the server's auth scheme.

		The opening greeting doubles as the auth challenge, and its shape tells
		us which scheme to use: newer BaseX sends digest auth (`realm:nonce`),
		older versions send a bare CRAM-MD5 nonce. Detecting it per-connection
		lets one client speak to both jar versions in the good/bad pair.
		"""

		greeting = _recv_until_null(self._file).decode("utf-8")

		if ":" in greeting:

			# digest auth - realm:nonce
			realm, nonce = greeting.rsplit(":", 1)
			inner        = hashlib.md5(f"{_USER}:{realm}:{_PASS}".encode()).hexdigest()

		else: # CRAM-MD5 - nonce only
			nonce = greeting
			inner = hashlib.md5(_PASS.encode()).hexdigest()

		auth_hash = hashlib.md5((inner + nonce).encode()).hexdigest()

		self._sock.sendall(_USER.encode() + b"\x00")
		self._sock.sendall(auth_hash.encode() + b"\x00")

		status = self._file.read(1)

		if status != b"\x00": raise BaseXError(f"Authentication failed on {_HOST}:{self._port}")


	def _command(self, cmd:str) -> str:
		"""Execute a command via the command protocol."""

		self._sock.sendall(cmd.encode("utf-8") + b"\x00")

		result = _recv_until_null(self._file)
		info   = _recv_until_null(self._file)
		status = self._file.read(1)

		if status != b"\x00": raise BaseXError(info.decode("utf-8", errors="replace"))

		return result.decode("utf-8")


	def __enter__(self) -> "BaseXSession":
		"""Open and authenticate the socket, then switch the session to in-memory storage.

		`SET MAINMEM true` keeps every database this session creates in RAM.
		query() builds and drops a throwaway database for each candidate, so
		this keeps a full minimization run off the disk entirely.
		"""

		self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		self._sock.settimeout(30.0)
		self._sock.connect((_HOST, self._port))

		self._file = self._sock.makefile('rb')

		self._authenticate()
		self._command("SET MAINMEM true")

		return self


	def query(self, xquery:str, context:str) -> str:
		"""Run an XQuery against an XML document supplied as the context item.

		The protocol has no "query this literal document" verb, so each call
		stages the XML as a temporary in-memory database (the \\x08 command:
		name then content), runs the query against it, and drops it in a
		finally block. The drop is best-effort - a connection that died mid-call
		is left for the next candidate's create to surface.
		"""

		# create in-memory db from XML (\x08 + name\x00 + content\x00)
		self._sock.sendall(b"\x08")

		_send_str(self._sock, "_dd")
		_send_str(self._sock, context)

		info   = _recv_until_null(self._file)
		status = self._file.read(1)

		if status != b"\x00": raise BaseXError(f"CREATE DB failed: {info.decode('utf-8', errors='replace')}")

		# run XQuery against the open database (command protocol)
		try: return self._command("XQUERY " + xquery)

		finally: # drop the temp database
			try: self._command("DROP DB _dd")
			except (BaseXError, OSError): pass


	def __exit__(self, *_) -> None:
		if self._sock is None: return

		try: self._sock.sendall(b"exit\x00")
		except OSError: pass

		try:
			if self._file is not None: self._file.close()

		except OSError: pass

		try: self._sock.close()
		except OSError: pass

		self._sock = None    # type: ignore[assignment]
		self._file = None    # type: ignore[assignment]


def _port_free(port:int) -> bool:
	"""Check if a port is free."""

	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.settimeout(0.1)

		return s.connect_ex((_HOST, port)) != 0


def _find_free_pair(start:int=_PORT_START) -> tuple[int, int]:
	"""Find a pair of free ports with gap for BaseX event ports.

	BaseX claims port+1 as its event port, so each server needs two
	consecutive ports. We allocate p and p+2 to avoid collision.
	"""

	p = start

	while p + 3 < _PORT_MAX:
		if all(_port_free(p + i) for i in range(4)): return p, p + 2

		p += 1

	raise BaseXError("No free port group found")


def _wait_for_server(port:int, timeout:float=30.0) -> None:
	"""Poll until the server at `port` accepts an authenticated session.

	Covers both startup phases - the socket coming up and the `-c PASSWORD`
	command running - so connection refusals and auth failures are retried
	until the deadline.
	"""

	deadline = time.monotonic() + timeout
	last:Exception | None = None

	while time.monotonic() < deadline:

		try:
			with BaseXSession(port): return

		except (BaseXError, OSError) as e:
			last = e

			time.sleep(0.1)

	raise BaseXError(f"Timed out waiting for {_HOST}:{port}") from last


def _start_server(jar_path:Path, port:int) -> subprocess.Popen:
	"""Start a BaseX server."""

	return subprocess.Popen(
		args = [

			"java",
			"-cp", str(jar_path), "org.basex.BaseXServer",
			"-n",  _HOST,
			"-p",  str(port),
			"-c",  f"PASSWORD {_PASS}"

		],

		stdout = subprocess.DEVNULL,
		stderr = subprocess.DEVNULL
	)


class BaseXServerPair:
	"""Context manager that starts a good/bad pair of BaseX servers and stops them on exit."""

	def __init__(self, good_jar:Path, bad_jar:Path) -> None:
		self._good_jar  = good_jar
		self._bad_jar   = bad_jar
		self._good_port = None
		self._bad_port  = None
		self._good_proc = None
		self._bad_proc  = None


	@property
	def good_port(self) -> int:
		if self._good_port is None: raise RuntimeError("BaseXServerPair not started")

		return self._good_port


	@property
	def bad_port(self) -> int:
		if self._bad_port is None: raise RuntimeError("BaseXServerPair not started")

		return self._bad_port


	def __enter__(self) -> "BaseXServerPair":
		"""Start the good/bad server pair, retrying if a chosen port is lost to a race.

		_find_free_pair picks ports that are free *now*, but another process can
		claim one before the server binds it. On a startup timeout we kill both
		processes, advance past the contested range, and retry up to three times.
		"""

		start = _PORT_START

		for attempt in range(3):
			self._good_port, self._bad_port = _find_free_pair(start)

			self._bad_proc  = _start_server(self._bad_jar, self.bad_port)
			self._good_proc = _start_server(self._good_jar, self.good_port)

			try:
				_wait_for_server(self._bad_port)
				_wait_for_server(self._good_port)

				return self

			# port likely grabbed between availability check and server start
			except BaseXError:
				for proc in (self._good_proc, self._bad_proc):
					if proc is None: continue

					try: proc.kill()
					except OSError: pass

					try: proc.wait(timeout=2)
					except subprocess.TimeoutExpired: pass

				self._good_proc = None
				self._bad_proc  = None
				start           = self._bad_port + 2

				if attempt == 2: raise

		return self  # unreachable


	def __exit__(self, *_) -> None:
		for proc in (self._good_proc, self._bad_proc):
			if proc is None: continue

			try: proc.terminate()
			except OSError:	pass

			try: proc.wait(timeout=5)

			except subprocess.TimeoutExpired:
				try: proc.kill()
				except OSError: pass

				try: proc.wait(timeout=2)
				except subprocess.TimeoutExpired: pass
