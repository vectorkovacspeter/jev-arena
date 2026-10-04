import assert from 'node:assert/strict';
import test from 'node:test';
import i18next from 'i18next';
import { errorText } from '../src/labels.ts';

async function make() {
  const i = i18next.createInstance();
  await i.init({ lng: 'hu', fallbackLng: 'en', returnEmptyString: false, interpolation: { escapeValue: false },
    resources: {
      en: { translation: { errors: { run_not_found: 'Run not found', setup_needed: 'Setup needed: {{details}}' }, readiness: { no_weights: 'No weights' }, custom: { key: 'Custom {{n}}' } } },
      hu: { translation: { errors: { run_not_found: 'A futtatás nem található', setup_needed: 'Beállítás szükséges: {{details}}' }, readiness: { no_weights: 'Nincs súly' } } },
    } });
  return i.t;
}
const err = (message, extra) => Object.assign(new Error(message), extra);

test('coded error is translated', async () => {
  assert.equal(errorText(await make(), err('Run not found', { code: 'run_not_found' })), 'A futtatás nem található');
});

test('setup_needed re-translates reason codes in params.models', async () => {
  const e = err('Setup needed: x', { code: 'setup_needed', params: { models: [{ name: 'm1', reason_code: 'no_weights' }, { name: 'm2', reason_code: 'no_weights' }] } });
  assert.equal(errorText(await make(), e), 'Beállítás szükséges: m1: Nincs súly; m2: Nincs súly');
});

test('client-side key path uses params and falls back to message', async () => {
  const t = await make();
  assert.equal(errorText(t, err('msg', { key: 'custom.key', params: { n: 3 } })), 'Custom 3');
  assert.equal(errorText(t, err('fallback msg', { key: 'custom.missing' })), 'fallback msg');
});

test('unknown code falls back to detail/message; plain errors return message', async () => {
  const t = await make();
  assert.equal(errorText(t, err('Server said no', { code: 'brand_new_code' })), 'Server said no');
  assert.equal(errorText(t, err('plain')), 'plain');
});
