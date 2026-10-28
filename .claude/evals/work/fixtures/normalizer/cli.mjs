import { createInterface } from "node:readline";
import { normalizeCreate, normalizeUpdate } from "./normalizer.mjs";

const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of lines) {
  if (!line.trim()) continue;
  let request;
  try {
    request = JSON.parse(line);
  } catch {
    console.log(JSON.stringify({ error: "invalid_json" }));
    continue;
  }
  let result;
  if (request?.operation === "create") result = normalizeCreate(request.value);
  else if (request?.operation === "update") result = normalizeUpdate(request.value);
  else result = { error: "operation_required" };
  console.log(JSON.stringify(result));
}
