// Tests for the structural-merge logic that protects admin-edited KV content.
// Run: node --test scripts/sync-church-kv.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mergeStructural, STRUCTURAL_FIELDS, STRUCTURAL_TOPLEVEL_FIELDS } from './sync-church-kv.mjs';

const repoDoc = {
  church: {
    name: { sv: 'Repo Name' },
    youtube_channel_id: 'UC_repo',
    youtube_handle: 'repohandle',
    live_schedule: [{ day: 'sun', start: '07:00', duration_min: 240 }],
    address: 'Repo address',
  },
  upcoming: [{ title: { sv: 'Repo event' } }],
};

test('overlays structural fields from repo onto the live KV doc', () => {
  const kv = { church: { youtube_channel_id: '', youtube_handle: '' }, announcements: [] };
  const out = mergeStructural(kv, repoDoc);
  assert.equal(out.church.youtube_channel_id, 'UC_repo');
  assert.equal(out.church.youtube_handle, 'repohandle');
  assert.deepEqual(out.church.live_schedule, repoDoc.church.live_schedule);
});

test('preserves admin-edited editorial content (never clobbered)', () => {
  const kv = {
    church: {
      name: { sv: 'Admin-Edited Name', am: 'አድሚን' },
      address: 'Admin address',
      youtube_channel_id: '',
    },
    announcements: [{ title: { sv: 'Viktigt meddelande från admin' } }],
    upcoming: [{ title: { sv: 'Admin-händelse' } }],
  };
  const out = mergeStructural(kv, repoDoc);
  // editorial preserved exactly
  assert.deepEqual(out.church.name, { sv: 'Admin-Edited Name', am: 'አድሚን' });
  assert.equal(out.church.address, 'Admin address');
  assert.deepEqual(out.announcements, kv.announcements);
  assert.deepEqual(out.upcoming, kv.upcoming);
  // structural overlaid
  assert.equal(out.church.youtube_channel_id, 'UC_repo');
});

test('does not delete a KV field the repo does not define', () => {
  const repoNoHandle = { church: { youtube_channel_id: 'UC_x' } };
  const kv = { church: { youtube_handle: 'keepme', name: { sv: 'X' } } };
  const out = mergeStructural(kv, repoNoHandle);
  assert.equal(out.church.youtube_handle, 'keepme'); // untouched
  assert.equal(out.church.youtube_channel_id, 'UC_x');
});

test('seeds the full repo doc when KV has no prior value (null)', () => {
  const out = mergeStructural(null, repoDoc);
  assert.deepEqual(out, repoDoc);
});

test('overlays top-level structural collection (education) from repo', () => {
  const edu = [{ id: 'fredagsskola', payment: { org_number: '802407-2673' } }];
  const repo = { church: { name: { sv: 'X' } }, education: edu };
  const kv = { church: { name: { sv: 'Admin Name' } }, announcements: [{ x: 1 }] };
  const out = mergeStructural(kv, repo);
  // education (structural, git-owned) is overlaid from repo …
  assert.deepEqual(out.education, edu);
  // … while editorial church/announcements stay admin-owned.
  assert.deepEqual(out.church.name, { sv: 'Admin Name' });
  assert.deepEqual(out.announcements, kv.announcements);
});

test('does not delete education the repo no longer defines', () => {
  const kv = { church: {}, education: [{ id: 'keep' }] };
  const out = mergeStructural(kv, { church: {} });
  assert.deepEqual(out.education, [{ id: 'keep' }]); // untouched
});

test('only the allowlisted fields are treated as structural', () => {
  assert.deepEqual(STRUCTURAL_FIELDS, [
    'youtube_channel_id',
    'youtube_handle',
    'live_schedule',
    'live_embed',
  ]);
  // a non-structural repo field must NOT overwrite the admin value
  const kv = { church: { address: 'Admin address', youtube_channel_id: '' } };
  const out = mergeStructural(kv, repoDoc);
  assert.equal(out.church.address, 'Admin address'); // repo's "Repo address" ignored
});
