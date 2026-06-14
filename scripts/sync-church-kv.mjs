// Sync the repo's *structural* church config to Cloudflare KV (kyrka_content)
// without clobbering admin-edited editorial content.
//
// Why merge, not overwrite: the admin-web content editor writes the full
// church document to KV (names, announcements, upcoming, …). The repo's
// churches/<id>/content.json is only authoritative for STRUCTURAL_FIELDS
// (the live-stream wiring). A blind repo→KV overwrite on deploy would erase
// what church admins edited in the UI. So per church we:
//   GET current KV doc → overlay ONLY STRUCTURAL_FIELDS from the repo → PUT.
// Safety: 404 (no doc yet) → seed with the full repo doc; any other GET error
// → throw and abort, so a transient failure can never blank a church.
//
// Run by .github/workflows/sync-content-kv.yml on push to main when a church
// content.json changes. Manual: CLOUDFLARE_ACCOUNT_ID=… CLOUDFLARE_API_TOKEN=…
// KV_NAMESPACE_ID=… node scripts/sync-church-kv.mjs
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import path from 'node:path';

export const STRUCTURAL_FIELDS = [
  'youtube_channel_id',
  'youtube_handle',
  'live_schedule',
  'live_embed',
];

// Overlay only STRUCTURAL_FIELDS from repoDoc onto the live kvDoc. Everything
// else in kvDoc (admin-edited) is preserved untouched. If there is no kvDoc
// yet, seed with the full repo document.
export function mergeStructural(kvDoc, repoDoc) {
  if (!kvDoc || typeof kvDoc !== 'object' || Array.isArray(kvDoc)) {
    return repoDoc;
  }
  const out = JSON.parse(JSON.stringify(kvDoc));
  out.church = out.church || {};
  const repoChurch = (repoDoc && repoDoc.church) || {};
  for (const field of STRUCTURAL_FIELDS) {
    if (Object.prototype.hasOwnProperty.call(repoChurch, field)) {
      out.church[field] = repoChurch[field];
    }
    // If the repo doesn't define the field, leave KV as-is — never delete.
  }
  return out;
}

const CHURCHES_DIR = 'frontend/member-portal/churches';

function kvUrl(account, ns, key) {
  return `https://api.cloudflare.com/client/v4/accounts/${account}/storage/kv/namespaces/${ns}/values/${key}`;
}

async function kvGet(account, token, ns, key) {
  const r = await fetch(kvUrl(account, ns, key), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (r.status === 200) return JSON.parse(await r.text());
  if (r.status === 404) return null;
  throw new Error(`KV GET ${key} -> ${r.status}: ${await r.text()}`);
}

async function kvPut(account, token, ns, key, doc) {
  const r = await fetch(kvUrl(account, ns, key), {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(doc),
  });
  if (!r.ok) throw new Error(`KV PUT ${key} -> ${r.status}: ${await r.text()}`);
}

async function main() {
  const account = process.env.CLOUDFLARE_ACCOUNT_ID;
  const token = process.env.CLOUDFLARE_API_TOKEN;
  const ns = process.env.KV_NAMESPACE_ID;
  if (!account || !token || !ns) {
    throw new Error('Missing CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN / KV_NAMESPACE_ID');
  }

  const churches = readdirSync(CHURCHES_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);

  for (const church of churches) {
    const file = path.join(CHURCHES_DIR, church, 'content.json');
    if (!existsSync(file)) continue;
    const repoDoc = JSON.parse(readFileSync(file, 'utf8'));
    const kvDoc = await kvGet(account, token, ns, church);
    const merged = mergeStructural(kvDoc, repoDoc);
    await kvPut(account, token, ns, church, merged);
    console.log(
      `synced ${church}: ${kvDoc ? 'merged structural fields (editorial preserved)' : 'seeded full doc (no prior KV)'}`
    );
  }
  console.log(`done: ${churches.length} church(es) processed`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((e) => {
    console.error(e.message || e);
    process.exit(1);
  });
}
