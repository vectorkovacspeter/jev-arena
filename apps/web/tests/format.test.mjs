import assert from 'node:assert/strict';
import test from 'node:test';
import { number, fixed, percent, duration, shortDate, points, safeLocale } from '../src/format.ts';

// Normalize ICU's non-breaking spaces and Unicode minus for stable comparisons.
const nb = s => s.replace(/[\u00a0\u202f]/g, ' ').replace(/\u2212/g, '-');

test('English formatting matches the previous hand-built output', () => {
  assert.equal(percent('en', 0.1234), '12.3%');
  assert.equal(percent('en', null), '—');
  assert.equal(number('en', 7671), '7,671');
  assert.equal(fixed('en', 0.12345, 4), '0.1235');
  assert.equal(duration('en', 0.4), '<1 ms');
  assert.equal(duration('en', 12.3), '12 ms');
  assert.equal(duration('en', 1250), '1.25 s');
  assert.equal(points('en', 0.012), '+1.2');
});

test('Hungarian uses comma decimals and space grouping', () => {
  assert.equal(nb(percent('hu', 0.1234)), '12,3%');
  assert.equal(nb(number('hu', 12345)), '12 345');
  assert.equal(number('hu', 7671), '7671'); // CLDR: Hungarian does not group 4-digit numbers
  assert.equal(nb(duration('hu', 1250)), '1,25 s');
  assert.equal(nb(points('hu', -0.012)), '-1,2');
  assert.match(shortDate('hu', 1759579200), /okt\. 4\./);
});

test('malformed locale tags fall back to en instead of throwing', () => {
  assert.equal(safeLocale('xx_YY'), 'en');
  assert.equal(safeLocale('hu'), 'hu');
  assert.equal(percent('xx_YY', 0.5), percent('en', 0.5));
  assert.doesNotThrow(() => shortDate('xx_YY', 1759579200));
});
