import assert from 'node:assert/strict';
import test from 'node:test';
import { answerId, runLanguage, unpreparedSlots, slug } from '../src/labels.ts';
import { languageName } from '../src/format.ts';

test('episode answers compare by stable id on Hungarian runs and by answer on English runs', () => {
  assert.equal(answerId({ answer: 'Felülvizsgálat', answer_id: 'Review' }), 'Review');
  assert.equal(answerId({ answer: 'Review' }), 'Review');
  assert.equal(answerId({ answer: 'ismeretlen', answer_id: null }), 'ismeretlen');
  assert.equal(answerId({ answer: null }), null);
  assert.equal(answerId(undefined), null);
});

test('run language defaults to English for runs recorded before i18n', () => {
  assert.equal(runLanguage({ manifest: {} }), 'en');
  assert.equal(runLanguage({ manifest: { language: 'hu' } }), 'hu');
  assert.equal(runLanguage(undefined), 'en');
});

test('only fillable slots count as unprepared', () => {
  const slots = [
    { slot: 'sst2', source: 'native', ready: false, expected: 500 },
    { slot: 'abcd', source: 'missing', ready: false, expected: null },
    { slot: 'abcd-en', source: 'native', ready: false, expected: null },
    { slot: 'fresh', source: 'generated', ready: true, expected: 1440 },
  ];
  assert.deepEqual(unpreparedSlots(slots).map((s) => s.slot), ['sst2']);
  assert.deepEqual(unpreparedSlots(undefined), []);
});

test('Hungarian native family names have stable catalog slugs', () => {
  assert.deepEqual(['HuSST', 'SIB-200', 'HuCommitmentBank', 'MASSIVE'].map(slug), ['husst', 'sib-200', 'hucommitmentbank', 'massive']);
});

test('language names follow the display language', () => {
  assert.equal(languageName('en', 'hu'), 'Hungarian');
  assert.equal(languageName('hu', 'hu'), 'magyar');
  assert.equal(languageName('xx_YY', 'en'), 'English');
});
