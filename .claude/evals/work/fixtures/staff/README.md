# Staff registration

This small owner app uses its existing theme and a local HTTP/SQLite backend. It has no account
or connection to a deployed service. All records here must be synthetic.

Run from this directory:

```sh
python3 server.py --port 0 --db /absolute/path/outside-the-workspace/staff.sqlite3
```

The first stdout line is the actual loopback URL. Keep the database outside the source checkout.
Stop the owned process when finished. `--drop-response-once` commits the first new batch, then
closes its connection before delivering the response. It is a local recovery testing option.

## Existing contracts

- `fields.mjs` exports the shared draft/input functions used by the UI. Phone segments are
  four ASCII digits, leading zeros included. Account values contain ASCII digits. A bank choice
  and a custom bank name are independent from the account value. Custom text is retained when
  switching bank choices. Phone identity is the complete prefix and both segments.
- Hourly pay starts at the store's configured value. A notice may compare hourly amounts with
  that value. There is no configured weekly schedule or monthly minimum. Account details are
  optional and do not block registration when absent.
- `state.mjs` exports draft and submission transitions. Rows are local accumulated entries;
  `current` is the current form. `pending` contains the exact request being resolved.
  Leaving the form retains the draft locally. Confirmed completion clears it.
- `app.mjs` renders the normal controls and performs requests. The server is the persistence
  authority. A success message or local draft is not evidence of saved rows.

## Backend

POST `/api/batches` accepts `{request_id, entries}`, one to ten complete employees. It atomically
saves the batch and returns `{request_id, count, ids}`. Repeating an identical request ID and
payload returns the same result without another write. Reusing the ID for a different payload
returns 409. A validation failure returns 400 without saving.

GET `/api/results/<request_id>` returns a committed result, or 404 if this local synchronous
server has no committed request with that ID. A disconnected request or unsuccessful query is
not evidence of non-registration. GET `/api/entries` reads committed employees afresh.

Use `node --test *.test.mjs` for client tests you add. Preserve these module interfaces and the
server contract while repairing the requested client behavior.
