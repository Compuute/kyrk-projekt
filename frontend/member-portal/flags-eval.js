// Pure, edge-agnostic feature-flag evaluation for the member portal.
//
// No SDK, no tracking (docs/15 Option B): a flag is "on" for a deterministic
// percentage of visitors, identified by a non-PII bucket (0-99) carried in a
// functional cookie `ab`. The same logic runs at the Cloudflare edge
// (functions/_middleware.ts) and in unit tests here.
//
//   flag = { enabled: boolean, rollout: 0-100 }
//     enabled: false  -> kill switch, off for everyone regardless of rollout
//     on iff           enabled === true && bucket < rollout
//
// Progressive rollout = bump `rollout` 0 -> 5 -> 25 -> 100.
// Instant rollback     = set `enabled: false` (no redeploy if config is in KV).
'use strict';

// The visitor's stable bucket (0-99) from the Cookie header, or null if unset.
function parseBucket(cookieHeader) {
  const m = (cookieHeader || '').match(/(?:^|;\s*)ab=(\d{1,2})(?:;|$)/);
  if (!m) return null;
  const n = parseInt(m[1], 10);
  return Number.isInteger(n) && n >= 0 && n <= 99 ? n : null;
}

// A fresh bucket for a new visitor. randomFn defaults to Math.random in the
// edge runtime; tests inject a deterministic value.
function pickBucket(randomFn) {
  const r = (randomFn || Math.random)();
  return Math.floor(r * 100); // 0-99
}

// Evaluate every flag in `config` for a given bucket. Returns { [name]: bool }.
function evaluateFlags(config, bucket) {
  const out = {};
  const flags = (config && config.flags) || {};
  for (const name of Object.keys(flags)) {
    const f = flags[name] || {};
    const rollout = Math.max(0, Math.min(100, Number(f.rollout) || 0));
    out[name] = f.enabled === true && Number(bucket) < rollout;
  }
  return out;
}

module.exports = { parseBucket, pickBucket, evaluateFlags };
