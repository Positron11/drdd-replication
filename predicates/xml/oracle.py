import os
import re

from contextlib  import contextmanager
from pathlib     import Path
from saxonche    import PySaxonProcessor, PySaxonApiError
from core.oracle import Oracle
from core.config import Config, require
from .basex      import BaseXSession, BaseXServerPair, BaseXError


_ID_RE = re.compile(r'id="([^"]*)"')
_LIB   = Path(__file__).resolve().parent / "lib"


def _extract_ids(text:str) -> list[str]:
	"""Extract id attribute values from XML output, filtering blanks."""

	return [m for m in _ID_RE.findall(text) if m.strip()]


@contextmanager
def _silence_fd2(devnull:int):
	"""Redirect fd 2 (Saxon's C-level stderr) to `devnull` for the block, then restore it."""

	saved = os.dup(2)

	os.dup2(devnull, 2)

	try: yield

	finally:
		os.dup2(saved, 2)
		os.close(saved)


class BaseXOracle(Oracle[int]):
	"""Three-way oracle: Saxon (reference) vs. bad-BaseX vs. good-BaseX."""

	def __init__(self, config:Config) -> None:
		super().__init__()

		self._query_text = require(config["query"]).read_text()
		self._good_jar   = require(_LIB / f"basex-{config['good_version']}.jar")
		self._bad_jar    = require(_LIB / f"basex-{config['bad_version']}.jar")

		self._servers:BaseXServerPair   = None    # type: ignore[assignment]
		self._saxon:PySaxonProcessor    = None    # type: ignore[assignment]
		self._bad_session:BaseXSession  = None    # type: ignore[assignment]
		self._good_session:BaseXSession = None    # type: ignore[assignment]
		self._devnull                   = -1


	def __enter__(self) -> "BaseXOracle":
		"""Start BaseX servers, initialize saxonche, open TCP sessions."""

		try:
			self._servers      = BaseXServerPair(self._good_jar, self._bad_jar).__enter__()
			self._bad_session  = BaseXSession(port=self._servers.bad_port).__enter__()
			self._good_session = BaseXSession(port=self._servers.good_port).__enter__()

		except Exception: self.__exit__(None, None, None); raise

		# saxon setup
		self._saxon = PySaxonProcessor(license=False)
		self._xq    = self._saxon.new_xquery_processor()

		self._xq.set_query_content(self._query_text)

		# hold devnull open for per-call fd-2 silencing of Saxon's C-level parse noise
		self._devnull = os.open(os.devnull, os.O_WRONLY)

		return self


	def _call(self, candidate) -> bool:
		"""Reproduces iff bad-BaseX diverges from Saxon while good-BaseX matches."""

		xml_str = bytes(candidate).decode("utf-8", errors="replace")

		# saxon reference (fd 2 silenced only around the C-level parse/query)
		try:
			with _silence_fd2(self._devnull):
				node = self._saxon.parse_xml(xml_text=xml_str)
				
				self._xq.set_context(xdm_item=node)
				
				saxon_result = self._xq.run_query_to_string()

		# Saxon rejection: ill-formed XML -> a definitive non-reproduction (true X);
		# distinct from the BaseX branch's operational failures below
		except PySaxonApiError: return False

		if saxon_result is None: return False

		saxon_ids = _extract_ids(saxon_result)

		# BaseX queries
		try:
			bad_result  = self._bad_session.query(self._query_text, xml_str)
			good_result = self._good_session.query(self._query_text, xml_str)

		# operational failure (server down, dropped socket) -> non-reproduction (?->X)
		except (BaseXError, ConnectionError, OSError):
			return False

		bad_ids  = _extract_ids(bad_result)
		good_ids = _extract_ids(good_result)

		# three-way predicate
		return bad_ids != saxon_ids and good_ids == saxon_ids


	def __exit__(self, *_) -> None:
		"""Clean up context managers."""

		if self._devnull != -1:
			os.close(self._devnull)

			self._devnull = -1

		for resource in (self._bad_session, self._good_session, self._servers):
			if resource is None: continue

			try: resource.__exit__(None, None, None)
			except Exception: pass
