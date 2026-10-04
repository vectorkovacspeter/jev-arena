import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import i18next from 'i18next';
import { slug, packLabel, familyLabel } from '../src/labels.ts';

const load = code => JSON.parse(readFileSync(new URL(`../../../locales/${code}/ui.json`, import.meta.url)));

test('Hungarian resolves keys, falls back to English for empty values, keeps placeholders', async () => {
  const i = i18next.createInstance();
  await i.init({ lng: 'hu', fallbackLng: 'en', returnEmptyString: false,
    resources: { en: { translation: { ...load('en'), probe: { empty: 'English' } } },
                 hu: { translation: { ...load('hu'), probe: { empty: '' } } } } });
  assert.equal(i.t('nav.results'), 'Eredmények');
  assert.equal(i.t('probe.empty'), 'English');
  assert.equal(i.t('shell.workspaceLabel', { appName: 'Jev Arena' }), 'Jev Arena munkaterület');
});

test('slug makes stable catalog keys from pack names', () => {
  assert.equal(slug('Arena Fresh'), 'arena-fresh');
  assert.equal(slug('JevBench public'), 'jevbench-public');
  assert.equal(slug('SST-2'), 'sst-2');
  assert.equal(slug('Sci/Tech'), 'sci-tech');
});

test('packLabel/familyLabel translate when a key exists and fall back to the raw name', async () => {
  const i = i18next.createInstance();
  await i.init({ lng: 'hu', fallbackLng: 'en', returnEmptyString: false,
    resources: { hu: { translation: { packs: { 'arena-fresh': 'Friss aréna' }, families: { 'sci-tech': 'Tudomány' } } } } });
  assert.equal(packLabel(i.t, 'Arena Fresh'), 'Friss aréna');
  assert.equal(familyLabel(i.t, 'Sci/Tech'), 'Tudomány');
  assert.equal(packLabel(i.t, 'Unknown Pack'), 'Unknown Pack');
  assert.equal(familyLabel(i.t, 'Unknown Family'), 'Unknown Family');
});
