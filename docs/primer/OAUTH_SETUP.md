# Turn on "Sign in with GitHub" — one-time setup (~5 min)

The editor already contains the whole sign-in flow (device flow + token
refresh, PAT prompt kept as fallback). It stays dormant until the manifest
has an `oauth` block. Two account-bound steps light it up.

## 1. Create the GitHub App (~2 min)

github.com → Settings → Developer settings → **GitHub Apps** → New GitHub App

- **Name**: `Budget Primer Editor` (anything)
- **Homepage URL**: `https://dtomkatsu.github.io/BudgetPrimerFinal/`
- **Callback URL**: leave empty; check **Enable Device Flow**  ← the one that matters
- **Webhook**: uncheck Active
- **Permissions → Repository permissions**:
  - Contents: **Read and write**
  - Pull requests: **Read and write**
- **Where can this app be installed**: Any account (so collaborators outside
  your account can sign in)

Create it, then note the **Client ID** (top of the app page, `Iv23…` — public,
not a secret).

Finally: **Install App** (left sidebar) → your account → **Only select
repositories** → `BudgetPrimerFinal`. Collaborators' access = their repo
permission ∩ this install, so inviting someone = the normal GitHub
collaborator invite, nothing extra.

## 2. Deploy the relay (~3 min)

GitHub's login endpoints refuse cross-origin browser calls (verified — no
CORS on POST or preflight), so the device flow needs a ~40-line forwarder.
It holds **no secrets and no state**; tokens pass straight through to the
browser.

dash.cloudflare.com → Workers & Pages → Create → Worker → paste
`docs/primer/oauth-relay.js` → Deploy → note the `https://….workers.dev` URL.

Then edit the two constants at the top of the worker and redeploy:
- `CLIENT_ID` = the App's client id (locks the relay to this app)
- `ALLOW` = the editor's origins (the GitHub Pages origin is prefilled)

(Vercel/Netlify/anything that runs a fetch handler works the same; the file
is standard Workers syntax.)

## 3. Point the editor at both

In `report2027/tools/` wherever the manifest is generated — or directly in
`docs/primer/engine/manifest.json` until the next build — add:

```json
"oauth": {
  "client_id": "Iv23xxxxxxxxxxxx",
  "relay": "https://your-worker.workers.dev"
}
```

Done. Next time anyone presses **Save draft** without a token, they get a
code and a "Open GitHub" button instead of the paste-a-token prompt; approval
takes ~15 seconds, tokens auto-refresh for ~6 months, commits are attributed
to the real person. The **Token…** button still accepts a paste-in PAT for
anyone who prefers it.
