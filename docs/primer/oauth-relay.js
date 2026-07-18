/**
 * Sign-in relay for the draft editor — a Cloudflare Worker.
 *
 * GitHub's OAuth device flow needs no client secret, only the App's PUBLIC
 * client id — but github.com's login endpoints refuse cross-origin browser
 * calls (verified: no CORS headers on POST or preflight, 2026-07). This
 * worker forwards exactly two of them with CORS added and holds NOTHING:
 * no secret, no token, no state. Every token goes straight back to the
 * browser that asked.
 *
 * Deploy (~3 min, free tier is plenty):
 *   dash.cloudflare.com -> Workers & Pages -> Create -> Worker
 *   -> paste this file -> Deploy -> note the *.workers.dev URL.
 * Then fill in the two constants below and redeploy.
 */

// The editor origins allowed to use this relay.
const ALLOW = [
  'https://dtomkatsu.github.io',
  'http://localhost:8777',
];

// Your GitHub App's client id (Settings -> Developer settings -> GitHub Apps).
// The relay refuses every other app, so it cannot be borrowed as a generic
// proxy. Leave '' only while testing.
const CLIENT_ID = '';

const UPSTREAM = {
  '/device/code':  'https://github.com/login/device/code',
  '/device/token': 'https://github.com/login/oauth/access_token',
};

export default {
  async fetch(req) {
    const origin = req.headers.get('Origin') || '';
    const cors = {
      'Access-Control-Allow-Origin': ALLOW.includes(origin) ? origin : ALLOW[0],
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'content-type, accept',
      'Vary': 'Origin',
    };
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });

    const upstream = UPSTREAM[new URL(req.url).pathname];
    if (!upstream || req.method !== 'POST')
      return new Response('{"error":"not found"}', { status: 404, headers: cors });

    const body = await req.json().catch(() => ({}));
    if (CLIENT_ID && body.client_id !== CLIENT_ID)
      return new Response('{"error":"wrong app"}', { status: 403, headers: cors });

    const r = await fetch(upstream, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return new Response(await r.text(), {
      status: r.status,
      headers: { ...cors, 'Content-Type': 'application/json' },
    });
  },
};
