// A minimal in-memory GitHub REST + Git Data API, enough to drive the editor's
// gh() calls (docsync/editor/edit.html) end to end without ever touching the
// real github.com. Register with page.route BEFORE any navigation.
//
// Why a fake server instead of stubbing each call: saveDraft()/publish() chain
// several endpoints (ref -> commit -> tree -> commit -> ref update) where each
// response feeds the next request. A handful of independent mocks drift out of
// sync with that chain the first time it changes; one small stateful backend
// stays correct because it behaves like git actually does.
const REPO = 'dtomkatsu/BudgetPrimerFinal';

function sha(seed) {
  return seed.toString(16).padStart(40, '0').slice(0, 40);
}

class FakeGitHub {
  constructor() {
    this.login = 'test-user';
    this.refs = new Map();       // branch -> commit sha
    this.commits = new Map();    // commit sha -> { tree: sha, parents: [] }
    this.trees = new Map();      // tree sha -> [{path, content}]
    this.contents = new Map();   // "branch:path" -> content string
    this.pulls = [];
    this._seq = 1;
    this.refs.set('main', sha(this._seq++));
    this.commits.set(this.refs.get('main'), { tree: sha(0), parents: [] });
    this.trees.set(sha(0), []);
  }

  // --- route handling -------------------------------------------------
  // Accepts a Page or a BrowserContext — both expose the same .route() shape.
  // Callers should pass the context (registered before any page/navigation
  // exists) to avoid racing the very first requests of an immediate goto().
  async install(routable) {
    await routable.route('https://api.github.com/**', route => this._handle(route));
    await routable.route('https://raw.githubusercontent.com/**', route => this._handleRaw(route));
  }

  _handleRaw(route) {
    const url = new URL(route.request().url());
    const [, , , branch, ...rest] = url.pathname.split('/'); // /repo/owner/branch/path...
    const path = rest.join('/');
    const body = this.contents.get(`${branch}:${path}`);
    if (body === undefined) return route.fulfill({ status: 404, body: 'Not Found' });
    return route.fulfill({ status: 200, body });
  }

  async _handle(route) {
    const req = route.request();
    const url = new URL(req.url());
    const parts = url.pathname.split('/').filter(Boolean); // repos, owner, name, ...
    const method = req.method();

    if (parts[0] === 'user') {
      return route.fulfill({ json: { login: this.login } });
    }
    if (parts[0] !== 'repos' || `${parts[1]}/${parts[2]}` !== REPO) {
      return route.fulfill({ status: 404, json: { message: 'Not Found' } });
    }
    const sub = parts.slice(3); // after repos/owner/name

    // GET /repos/:repo — token capability check
    if (sub.length === 0 && method === 'GET') {
      return route.fulfill({ json: { permissions: { push: true } } });
    }

    // git/ref/heads/:branch  (singular "ref" — get one)
    if (sub[0] === 'git' && sub[1] === 'ref' && sub[2] === 'heads') {
      const branch = decodeURIComponent(sub.slice(3).join('/'));
      const s = this.refs.get(branch);
      if (!s) return route.fulfill({ status: 404, json: { message: 'Not Found' } });
      return route.fulfill({ json: { object: { sha: s } } });
    }

    // git/refs  POST — create a branch (inherits the source commit's files)
    if (sub[0] === 'git' && sub[1] === 'refs' && sub.length === 2 && method === 'POST') {
      const body = req.postDataJSON();
      const branch = body.ref.replace(/^refs\/heads\//, '');
      this.refs.set(branch, body.sha);
      this._materialize(branch, body.sha);
      return route.fulfill({ status: 201, json: { ref: body.ref, object: { sha: body.sha } } });
    }

    // git/refs/heads/:branch  PATCH (fast-forward) / DELETE
    if (sub[0] === 'git' && sub[1] === 'refs' && sub[2] === 'heads') {
      const branch = decodeURIComponent(sub.slice(3).join('/'));
      if (method === 'PATCH') {
        const body = req.postDataJSON();
        this.refs.set(branch, body.sha);
        this._materialize(branch, body.sha);
        return route.fulfill({ json: { object: { sha: body.sha } } });
      }
      if (method === 'DELETE') {
        this.refs.delete(branch);
        return route.fulfill({ status: 204, body: '' });
      }
    }

    // git/commits/:sha  GET
    if (sub[0] === 'git' && sub[1] === 'commits' && sub.length === 3 && method === 'GET') {
      const c = this.commits.get(sub[2]);
      if (!c) return route.fulfill({ status: 404, json: { message: 'Not Found' } });
      return route.fulfill({ json: { sha: sub[2], tree: { sha: c.tree }, parents: c.parents } });
    }

    // git/trees  POST — create a tree from base_tree + file overrides
    if (sub[0] === 'git' && sub[1] === 'trees' && sub.length === 2 && method === 'POST') {
      const body = req.postDataJSON();
      const base = this.trees.get(body.base_tree) || [];
      const byPath = new Map(base.map(f => [f.path, f.content]));
      for (const f of body.tree) byPath.set(f.path, f.content);
      const entries = [...byPath].map(([path, content]) => ({ path, content }));
      const s = sha(this._seq++);
      this.trees.set(s, entries);
      return route.fulfill({ status: 201, json: { sha: s } });
    }

    // git/commits  POST — create a commit
    if (sub[0] === 'git' && sub[1] === 'commits' && sub.length === 2 && method === 'POST') {
      const body = req.postDataJSON();
      const s = sha(this._seq++);
      this.commits.set(s, { tree: body.tree, parents: body.parents || [] });
      return route.fulfill({ status: 201, json: { sha: s } });
    }

    // contents/:path  GET (sha lookup for overwrite) / PUT (image upload)
    if (sub[0] === 'contents') {
      const path = decodeURIComponent(sub.slice(1).join('/'));
      const branch = url.searchParams.get('ref') || 'main';
      if (method === 'GET') {
        const body = this.contents.get(`${branch}:${path}`);
        if (body === undefined) return route.fulfill({ status: 404, json: { message: 'Not Found' } });
        return route.fulfill({ json: { sha: sha(path.length), content: Buffer.from(body).toString('base64') } });
      }
      if (method === 'PUT') {
        const body = req.postDataJSON();
        const branch2 = body.branch || 'main';
        const content = Buffer.from(body.content, 'base64').toString('utf8');
        this.contents.set(`${branch2}:${path}`, content);
        return route.fulfill({ status: 201, json: { content: { path, sha: sha(this._seq++) } } });
      }
    }

    // pulls  GET (list/find open PR for a head) / POST (create)
    if (sub[0] === 'pulls' && sub.length === 1) {
      if (method === 'GET') {
        const head = url.searchParams.get('head') || '';
        const branch = head.split(':').slice(1).join(':');
        return route.fulfill({ json: this.pulls.filter(p => p.head === branch && p.open) });
      }
      if (method === 'POST') {
        const body = req.postDataJSON();
        const pr = { number: this.pulls.length + 1, head: body.head, base: body.base, open: true };
        this.pulls.push(pr);
        return route.fulfill({ status: 201, json: pr });
      }
    }

    // pulls/:number/merge  PUT
    if (sub[0] === 'pulls' && sub[2] === 'merge' && method === 'PUT') {
      const n = Number(sub[1]);
      const pr = this.pulls.find(p => p.number === n);
      if (!pr) return route.fulfill({ status: 404, json: { message: 'Not Found' } });
      pr.open = false;
      // Merging fast-forwards main to the head branch's tip, like squash-merge would.
      const headSha = this.refs.get(pr.head);
      if (headSha) { this.refs.set('main', headSha); this._materialize('main', headSha); }
      return route.fulfill({ json: { merged: true, sha: headSha } });
    }

    return route.fulfill({ status: 404, json: { message: `fake-github: unhandled ${method} ${url.pathname}` } });
  }

  /** Seed a file as it exists on `branch` today (what fromBranch()/contents-GET see). */
  seedFile(branch, path, content) {
    this.contents.set(`${branch}:${path}`, content);
  }

  /** Write every file a commit's tree names into that branch's content map,
   *  so a later contents-GET or raw fetch sees what was just committed. */
  _materialize(branch, commitSha) {
    const commit = this.commits.get(commitSha);
    if (!commit) return;
    const entries = this.trees.get(commit.tree) || [];
    for (const { path, content } of entries) this.contents.set(`${branch}:${path}`, content);
  }
}

module.exports = { FakeGitHub, REPO };
