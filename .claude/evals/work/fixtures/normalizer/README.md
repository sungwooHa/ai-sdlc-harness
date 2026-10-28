# Record normalization CLI

`node cli.mjs` reads JSON lines from stdin and writes one JSON result per nonblank line.
Each input is `{"operation":"create"|"update","value":{...}}`. Parse errors and unknown operations
are JSON error results; the process continues with the next line.

`normalizer.mjs` exports `normalizeCreate(value)` and `normalizeUpdate(value)`. Callers rely on
their current result shape, including the distinction between absent fields, empty strings,
null, numeric zero and string identifiers with leading zeros. The CLI wrapper is a caller.

This is internal processing with no user interface. Run `node --test *.test.mjs` for tests you add.
