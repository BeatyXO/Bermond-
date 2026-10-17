import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const protocol = readFileSync(new URL('../src/protocol.ts', import.meta.url), 'utf8');
const chain = readFileSync(new URL('../src/chain.ts', import.meta.url), 'utf8');
const app = readFileSync(new URL('../src/main.tsx', import.meta.url), 'utf8');

async function importTypescript(path) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8');
  const js = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
}

class MemoryStorage {
  values = new Map();
  getItem(key) { return this.values.get(key) ?? null; }
  setItem(key, value) { this.values.set(key, String(value)); }
  removeItem(key) { this.values.delete(key); }
}

test('protocol defines exactly the four monitored terms and an unconfigured address default', () => {
  for (const key of ['allowance', 'retention', 'refunds', 'notice']) assert.ok(protocol.includes(key));
  assert.match(protocol, /VITE_BERMOND_CONTRACT_ADDRESS/);
});

test('preview examples remain clearly separate from the live registry', () => {
  const fixtures = readFileSync(new URL('../src/fixtures.ts', import.meta.url), 'utf8');
  assert.match(fixtures, /PREVIEW_CASES/);
  assert.match(app, /Verdicts here are fixtures demonstrating the proposed contract's rules, not validator receipts/);
  assert.match(app, /never silently substituted with demo fixtures/);
});

test('wallet connect is explicit and write path never re-prompts for account access', () => {
  assert.match(chain, /eth_requestAccounts/);
  assert.match(chain, /STUDIO_DEV_CHAIN_ID = '0xf22d'/);
  assert.match(chain, /switchToStudioDev/);
  assert.match(app, /Switch to GenLayer Studio Dev/);
  assert.match(chain, /authorizedWriteAccount/);
  const writePath = chain.slice(chain.indexOf('export async function writeBond'));
  assert.doesNotMatch(writePath, /eth_requestAccounts/);
  assert.match(writePath, /estimateTransactionFeesForWrite/);
  assert.match(writePath, /authorizedWriteAccount\(expectedAddress, provider\)/);
});

test('network switch targets only Studio Dev and adds it only when the wallet reports an unknown chain', async () => {
  const { switchToStudioDev, STUDIO_DEV_CHAIN_ID } = await importTypescript('../src/wallet-network.ts');
  const calls = [];
  const provider = { request: async (request) => {
    calls.push(request);
    if (request.method === 'wallet_switchEthereumChain' && calls.length === 1) {
      throw Object.assign(new Error('Unknown chain'), { code: 4902 });
    }
    return null;
  } };
  await switchToStudioDev(provider);
  assert.deepEqual(calls.map((call) => call.method), [
    'wallet_switchEthereumChain', 'wallet_addEthereumChain', 'wallet_switchEthereumChain',
  ]);
  assert.deepEqual(calls[0].params, [{ chainId: STUDIO_DEV_CHAIN_ID }]);
  assert.deepEqual(calls[1].params[0], {
    chainId: STUDIO_DEV_CHAIN_ID,
    chainName: 'GenLayer Studio Dev',
    nativeCurrency: { name: 'GEN', symbol: 'GEN', decimals: 18 },
    rpcUrls: ['https://studio-dev.genlayer.com/api'],
    blockExplorerUrls: ['https://explorer-studio-dev.genlayer.com'],
  });
});

test('wallet rejection during network switch is surfaced without adding a chain', async () => {
  const { switchToStudioDev } = await importTypescript('../src/wallet-network.ts');
  const rejection = Object.assign(new Error('User rejected request'), { code: 4001 });
  const calls = [];
  await assert.rejects(switchToStudioDev({ request: async (request) => {
    calls.push(request.method);
    throw rejection;
  } }), rejection);
  assert.deepEqual(calls, ['wallet_switchEthereumChain']);
});

test('connected account, network, accepted commitment and fresh state gate live actions', () => {
  assert.match(chain, /eth_accounts/);
  assert.match(chain, /eth_chainId/);
  assert.match(app, /walletAccountsChanged\(value\)/);
  assert.match(app, /accept_bond/);
  assert.match(app, /const writable=configured&&onStudioDev&&!!account&&!pending&&!busy/);
  assert.match(app, /Live actions are hidden until a finalized read succeeds/);
});

test('refresh after disconnect stays disconnected until explicit reconnect', async () => {
  const { currentAuthorizedAccount, walletAccountsChanged, markWalletConnected, markWalletDisconnected } = await importTypescript('../src/wallet-session.ts');
  const storage = new MemoryStorage();
  const account = '0x1234567890123456789012345678901234567890';
  assert.equal(currentAuthorizedAccount([account], storage), account);
  markWalletDisconnected(storage);
  assert.equal(currentAuthorizedAccount([account], storage), null);
  assert.equal(walletAccountsChanged([account], storage), null);
  assert.equal(currentAuthorizedAccount([account], storage), null);
  markWalletConnected(storage);
  assert.equal(currentAuthorizedAccount([account], storage), account);
  assert.equal(walletAccountsChanged([], storage), null);
  assert.equal(currentAuthorizedAccount([account], storage), null);
});

test('transaction outcome is successful only when both execution and finality are authoritative', async () => {
  const { classifyReceipt, submissionFailureMessage } = await importTypescript('../src/tx-state.ts');
  assert.equal(classifyReceipt({ statusName: 'ACCEPTED' }, true), 'UNRESOLVED');
  assert.equal(classifyReceipt({ lifecycle: { state: 'PENDING' } }, false), 'UNRESOLVED');
  assert.equal(classifyReceipt({ statusName: 'FINALIZED', txExecutionResultName: 'FINISHED_WITH_ERROR' }, false), 'FINALIZED_FAILED');
  assert.equal(classifyReceipt({ lifecycle: 'FINALIZED' }, true), 'FINALIZED_SUCCESS');
  assert.match(submissionFailureMessage({ code: 4001 }, 'claim_compensation'), /wallet rejected/);
  assert.match(submissionFailureMessage(new Error('RPC timeout'), 'claim_compensation'), /outcome may be unknown.*before retrying/);
  assert.match(chain, /outcome === 'UNRESOLVED'.*throw new Error\(unresolvedMessage/s);
  assert.match(chain, /lastWriteKey/);
});

test('baseline identity remains an explicit provider declaration and preview does not claim publisher authentication', () => {
  const contract = readFileSync(new URL('../../contracts/bermond.py', import.meta.url), 'utf8');
  assert.match(app, /does not authenticate the publisher or prove historical authority/);
  assert.match(contract, /PROVIDER_DECLARED_UNVERIFIED/);
  assert.match(contract, /historical_authenticity': 'UNVERIFIED'/);
});
