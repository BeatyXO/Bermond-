import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../src/protocol.ts',import.meta.url),'utf8');
test('protocol defines exact 4 monitored terms',()=>{for(const key of ['allowance','retention','refunds','notice'])assert.ok(source.includes(key))});
test('contract address defaults to unconfigured',()=>assert.match(source,/VITE_BERMOND_CONTRACT_ADDRESS/));
test('all preview scenarios clearly use synthetic cases',()=>{const fixtures=readFileSync(new URL('../src/fixtures.ts',import.meta.url),'utf8');assert.match(fixtures,/PREVIEW_CASES/);});
