// Numeric C/JS boundary, separate from the executable's C checks.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

const { default: createModel } = await import(pathToFileURL(process.argv[2]).href);
const model = await createModel();
model._sim_reset();
model._app_reset();
assert.equal(model._sim_output(), 0);
console.log('BOOT wasm module: output=0');
model._sim_advance(10);
assert.equal(model._app_step(), -1); // unavailable
assert.equal(model._sim_inject(250), 0);
assert.equal(model._app_step(), 0);
assert.equal(model._sim_output(), 0);
assert.equal(model._sim_inject(750), 0);
assert.equal(model._app_step(), 1); // no time advanced
assert.equal(model._sim_output(), 0);
model._sim_advance(10);
assert.equal(model._app_step(), 0);
assert.equal(model._sim_output(), 1);
assert.equal(model._sim_inject(-1), -3); // rejected, state preserved
model._sim_advance(10);
assert.equal(model._app_step(), 0);
assert.equal(model._sim_output(), 1);
model._sim_reset();
model._app_reset();
assert.equal(model._sim_output(), 0);
console.log('PASS wasm interop: input, time, output, rejection, reset');
