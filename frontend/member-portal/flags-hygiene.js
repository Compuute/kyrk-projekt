// Feature-flag governance/hygiene rules — the "flags are tech debt" discipline
// that Netflix/Google automate. Pure, so tests/test_flags_hygiene.js can run it
// against the registry on every CI run and fail when a flag goes stale.
//
// Rules:
//   - every flag: type (release|experiment|ops|permission), owner, description,
//     boolean enabled, integer rollout 0-100
//   - release & experiment flags MUST have a future `expires` (they are
//     short-lived). An expired flag FAILS CI — that is what forces cleanup.
//   - ops & permission flags are long-lived and may omit `expires`.
'use strict';

const TYPES = ['release', 'experiment', 'ops', 'permission'];
const MUST_EXPIRE = ['release', 'experiment'];

function isIsoDate(s) {
  return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s);
}

// Returns an array of error strings for one flag (empty = valid).
function validateFlag(name, flag, today) {
  const errs = [];
  flag = flag || {};
  if (!TYPES.includes(flag.type)) errs.push(`${name}: type must be one of ${TYPES.join('|')}`);
  if (!flag.owner) errs.push(`${name}: missing owner`);
  if (!flag.description) errs.push(`${name}: missing description`);
  if (typeof flag.enabled !== 'boolean') errs.push(`${name}: enabled must be a boolean`);
  const r = Number(flag.rollout);
  if (!Number.isInteger(r) || r < 0 || r > 100) errs.push(`${name}: rollout must be an integer 0-100`);
  if (flag.expires !== undefined && !isIsoDate(flag.expires)) {
    errs.push(`${name}: expires must be YYYY-MM-DD`);
  }
  if (MUST_EXPIRE.includes(flag.type)) {
    if (!isIsoDate(flag.expires)) {
      errs.push(`${name}: ${flag.type} flag must set 'expires' (YYYY-MM-DD)`);
    } else if (flag.expires < today) {
      errs.push(`${name}: EXPIRED ${flag.expires} — remove the flag and its now-permanent code`);
    }
  }
  return errs;
}

// Validate the whole registry against `today` (YYYY-MM-DD). Returns string[].
function validateRegistry(config, today) {
  const errors = [];
  const flags = (config && config.flags) || {};
  for (const name of Object.keys(flags)) {
    errors.push(...validateFlag(name, flags[name], today));
  }
  return errors;
}

module.exports = { TYPES, isIsoDate, validateFlag, validateRegistry };
