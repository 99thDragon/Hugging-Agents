# Handoff: wire the Hug app to Hug Guardian

For Sal (and Sal's AI assistant). Read this first, then `README.md` and `CLAUDE.md` if you need more.

## Your task

Connect the **Sell Your Hugs** app (https://github.com/pumptool/Hug, vanilla JS PWA) to the live Hug Guardian API:

1. When the user taps **Book**, send the booking to `POST /screen`.
2. Show a loading state (a call takes a few seconds; it is an AI agent).
3. Show the decision on a small result screen.

Keep app changes small. The agent and the self-improvement loop are what get judged, not the app.

## API

Base URL: `https://hugging-agents.vercel.app` (CORS is open, call it straight from the browser).

Try every endpoint in the browser at https://hugging-agents.vercel.app/docs

### `GET /users`

Demo users for a dropdown (16 of them). Show `label`, send `id` as `user_id`.

```json
[{ "id": "u01", "name": "Maya", "label": "Maya (22 hugs)" }]
```

### `POST /screen`

```js
const res = await fetch("https://hugging-agents.vercel.app/screen", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    user_id: "u01",              // required, from /users
    location: "Central Park",    // required
    when: "2026-09-27T14:00",    // required
    duration_minutes: 30,        // optional, default 30
    message: "Quick hug after my exam!"  // optional
  })
});
const d = await res.json();
```

Response:

```json
{
  "decision": "approve",
  "reason": "One sentence explaining the decision.",
  "risk_signals": ["short phrase", "short phrase"],
  "followup_question": null,
  "harness_version": 3,
  "booking_id": "b_1a2b3c"
}
```

- `decision` is one of `approve`, `ask_followup`, `reject`.
- `followup_question` is only set when `decision` is `ask_followup`.
- `?version=1` screens with the old v1 rulebook (for the before/after demo).

## Result screen

| decision | color | show |
|---|---|---|
| `approve` | green | `reason` |
| `ask_followup` | yellow | `followup_question`, then `reason` |
| `reject` | red | `reason` |

Also show `risk_signals` as small tags and "Screened by harness v{harness_version}" in small text. Handle a failed request with a plain "Could not screen this booking, try again" message.

## Demo script

1. Safe: user `u01` (Maya), "Central Park", afternoon, friendly message. Expect `approve`.
2. Risky: user `u04` (Derek, 2 past reports), "my apartment", 11pm. Expect `reject` or `ask_followup`.
3. Before/after: send the risky booking to `POST /screen?version=1` to show the old rulebook missing it.
4. Open https://hugging-agents.vercel.app/dashboard to show the score rising across versions.

These expectations are from the test data. Live `/screen` has not been clicked through end to end yet, so check the first responses.

Other users worth trying: `u08` Chris (1-day-old, unverified account), `u06` Leo and `u11` Victor (1 report each), `u07` Ana (41 hugs, clean).

## Rules

- Each `/screen` call spends a fraction of a cent from a shared $10 OpenRouter credit. Do not call it in a loop or on every keystroke.
- Do not call `POST /harness/active` (it switches the live rulebook; v3 is set on purpose).
- Never commit keys or the MongoDB URI. They live in Vercel env vars and local `.env` only.
- Pushing to `main` of this repo redeploys the API. App changes go in the Hug repo, not here.
