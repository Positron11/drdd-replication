// Long-running mocha-free worker for CrashJS lodash predicates.
//
// Protocol:
//   stdin  : one path-to-test-file per line (UTF-8)
//   stdout : one JSON line per request:
//              { "ok": bool, "errType": str|null, "errMsg": str|null, "topFile": str|null }
//            "ok" = true  iff the test ran without throwing
//            "ok" = false iff the test threw
//
// Each test file is expected to contain a single describe(...) -> it(...) pair.
// The describe/it globals are stubbed to capture the async body, which we then
// invoke once. ESM module cache is bypassed for the test file by appending a
// per-call "?t=<counter>" query — lodash internals are imported by static path
// and remain cached across calls.

import path              from "node:path";
import readline          from "node:readline";
import { pathToFileURL } from "node:url";

const PROJECT_TAG = "/instrumented/lodash/";    // first project frame matcher

let captured = null;

globalThis.describe = (_name, fn) => fn();
globalThis.it       = (_name, fn) => { captured = fn; };

function topProjectFile(stack) {
	if (typeof stack !== "string") return null;

	for (const line of stack.split("\n")) {
		const idx = line.indexOf(PROJECT_TAG);

		if (idx < 0) continue;

		// extract filename (last path component before any line:col suffix)
		const after = line.slice(idx + PROJECT_TAG.length);
		const m     = after.match(/^([^\s:)]+\.js)/);

		if (m) return m[1];
	}

	return null;
}

let counter = 0;

async function runOne(file) {
	captured  = null;
	counter  += 1;

	const url = pathToFileURL(path.resolve(file)).href + "?t=" + counter;

	try { await import(url); }
	
	// import-time error (syntax error, etc.) — treat as failure
	catch (e) {
		return { 
			ok     : false, 
			errType: e?.constructor?.name ?? "Error",
			errMsg : e?.message ?? String(e), 
			topFile: topProjectFile(e?.stack) 
		};
	}

	// no it() registered — test file structure broken
	if (typeof captured !== "function") {
		return { 
			ok     : false, 
			errType: "NoTest", 
			errMsg : "no it() body registered", 
			topFile: null 
		};
	}

	try {
		await captured();

		return { 
			ok     : true, 
			errType: null, 
			errMsg : null, 
			topFile: null 
		};
	}

	catch (e) {
		return { 
			ok     : false, 
			errType: e?.constructor?.name ?? "Error",
			errMsg : e?.message ?? String(e), 
			topFile: topProjectFile(e?.stack) 
		};
	}
}

const rl = readline.createInterface({ input: process.stdin });

// announce ready
process.stdout.write(JSON.stringify({ ready: true }) + "\n");

for await (const line of rl) {
	const file = line.trim();
	if (!file) continue;

	const result = await runOne(file);

	process.stdout.write(JSON.stringify(result) + "\n");
}
