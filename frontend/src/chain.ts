import { createClient, isSuccessful } from 'genlayer-js';
import { studioDevnet } from 'genlayer-js/chains';
import { TransactionHashVariant } from 'genlayer-js/types';
import type { TransactionHash } from 'genlayer-js/types';
import { contractAddress } from './protocol';
import type { Bond } from './protocol';
import { classifyReceipt, submissionFailureMessage } from './tx-state';
import { switchToStudioDev } from './wallet-network';
import {
  currentAuthorizedAccount,
  isWalletDisconnected,
  markWalletConnected,
  markWalletDisconnected,
} from './wallet-session';

type WalletProvider = {
  request: (options: { method: string; params?: unknown[] }) => Promise<unknown>;
  on?: (event: string, listener: (value: unknown) => void) => void;
  removeListener?: (event: string, listener: (value: unknown) => void) => void;
};
declare global { interface Window { ethereum?: WalletProvider } }

const chain = studioDevnet;
export const STUDIO_DEV_CHAIN_ID = '0xf22d';
const reader = createClient({ chain });
const pendingKey = 'bermond:pending-write';
const lastWriteKey = 'bermond:last-write';

export interface PendingWrite {
  hash: TransactionHash;
  functionName: string;
  submittedAt: number;
  phase: 'SUBMITTED' | 'ACCEPTED';
}
export interface LastWrite {
  hash: TransactionHash;
  functionName: string;
  submittedAt: number;
  outcome: 'FINALIZED_SUCCESS' | 'FINALIZED_FAILED' | 'TRANSFER_UNVERIFIED';
}

export function readPendingWrite(): PendingWrite | null {
  try {
    const raw = localStorage.getItem(pendingKey);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<PendingWrite>;
    return typeof value.hash === 'string' && /^0x[a-f\d]{64}$/i.test(value.hash)
      && typeof value.functionName === 'string' && typeof value.submittedAt === 'number'
      ? { hash: value.hash as TransactionHash, functionName: value.functionName,
          submittedAt: value.submittedAt, phase: value.phase === 'ACCEPTED' ? 'ACCEPTED' : 'SUBMITTED' }
      : null;
  } catch { return null; }
}

export function readLastWrite(): LastWrite | null {
  try {
    const raw = localStorage.getItem(lastWriteKey);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<LastWrite>;
    return typeof value.hash === 'string' && /^0x[a-f\d]{64}$/i.test(value.hash)
      && typeof value.functionName === 'string' && typeof value.submittedAt === 'number'
      && (value.outcome === 'FINALIZED_SUCCESS' || value.outcome === 'FINALIZED_FAILED' || value.outcome === 'TRANSFER_UNVERIFIED')
      ? value as LastWrite : null;
  } catch { return null; }
}

function deployed(): `0x${string}` {
  const value = contractAddress();
  if (!/^0x[a-f\d]{40}$/i.test(value)) throw new Error('Bermond is not deployed. Reviewer preview is available without a wallet.');
  return value as `0x${string}`;
}

export async function readBondIds(): Promise<string[]> {
  return await reader.readContract({ address: deployed(), functionName: 'get_bond_ids', args: [], transactionHashVariant: TransactionHashVariant.LATEST_FINAL }) as string[];
}
export async function readBond(id: string): Promise<Bond> {
  return await reader.readContract({ address: deployed(), functionName: 'get_bond', args: [id], transactionHashVariant: TransactionHashVariant.LATEST_FINAL }) as unknown as Bond;
}
export async function readAllBonds(): Promise<Bond[]> {
  const ids = await readBondIds();
  return Promise.all(ids.map(readBond));
}

export async function walletAddress(): Promise<string | null> {
  const provider = window.ethereum;
  if (!provider || isWalletDisconnected()) return null;
  const accounts = await provider.request({ method: 'eth_accounts' });
  return currentAuthorizedAccount(accounts);
}

export async function walletNetworkIsStudio(): Promise<boolean> {
  if (!window.ethereum) return false;
  const chainId = await window.ethereum.request({ method: 'eth_chainId' });
  return typeof chainId === 'string' && chainId.toLowerCase() === STUDIO_DEV_CHAIN_ID;
}

export async function switchWalletNetwork(): Promise<void> {
  const provider = window.ethereum;
  if (!provider) throw new Error('Install a compatible browser wallet (for example MetaMask or Rabby).');
  await switchToStudioDev(provider);
  if (!await walletNetworkIsStudio()) {
    throw new Error('The wallet did not switch to GenLayer Studio Dev (chain ID 61997).');
  }
}

export async function connectWallet(): Promise<string> {
  const provider = window.ethereum;
  if (!provider) throw new Error('Install a compatible browser wallet (for example MetaMask or Rabby).');
  const accounts = await provider.request({ method: 'eth_requestAccounts' });
  if (!Array.isArray(accounts) || typeof accounts[0] !== 'string' || !/^0x[a-f\d]{40}$/i.test(accounts[0])) {
    throw new Error('Wallet did not return a valid account.');
  }
  const chainId = await provider.request({ method: 'eth_chainId' });
  if (typeof chainId !== 'string' || chainId.toLowerCase() !== STUDIO_DEV_CHAIN_ID) {
    throw new Error('Wrong network. Switch your wallet to GenLayer Studio Dev (chain ID 61997) before connecting or writing.');
  }
  markWalletConnected();
  return accounts[0];
}

export function disconnectWallet(): void { markWalletDisconnected(); }

async function authorizedWriteAccount(expectedAddress: string, provider: WalletProvider): Promise<string> {
  if (isWalletDisconnected()) throw new Error('Connect your wallet before writing.');
  const [accounts, chainId] = await Promise.all([
    provider.request({ method: 'eth_accounts' }), provider.request({ method: 'eth_chainId' }),
  ]);
  const address = currentAuthorizedAccount(accounts);
  if (!address || address.toLowerCase() !== expectedAddress.toLowerCase()) {
    throw new Error('The connected account changed. Review the new wallet account before submitting.');
  }
  if (typeof chainId !== 'string' || chainId.toLowerCase() !== STUDIO_DEV_CHAIN_ID) {
    throw new Error('Wrong network. Switch your wallet to GenLayer Studio Dev (chain ID 61997) before writing.');
  }
  return address;
}

function persistFinalWrite(pending: PendingWrite, outcome: Exclude<LastWrite['outcome'], 'TRANSFER_UNVERIFIED'>, callback?: (pending: PendingWrite | null) => void): void {
  const recordedOutcome = outcome === 'FINALIZED_SUCCESS' && ['claim_compensation', 'release_collateral'].includes(pending.functionName)
    ? 'TRANSFER_UNVERIFIED' : outcome;
  localStorage.setItem(lastWriteKey, JSON.stringify({ ...pending, outcome: recordedOutcome } satisfies LastWrite));
  if (readPendingWrite()?.hash === pending.hash) localStorage.removeItem(pendingKey);
  callback?.(null);
}

function persistAccepted(hash: TransactionHash, callback?: (pending: PendingWrite | null) => void): void {
  const current = readPendingWrite();
  if (current?.hash !== hash) return;
  const accepted = { ...current, phase: 'ACCEPTED' as const };
  localStorage.setItem(pendingKey, JSON.stringify(accepted));
  callback?.(accepted);
}

function unresolvedMessage(hash: string): string {
  return `Transaction ${hash} has not reached an authoritative finalized outcome. It remains saved; inspect or resume this exact transaction before another write.`;
}

export async function resumePendingWrite(onSubmitted?: (pending: PendingWrite | null) => void): Promise<string> {
  const pending = readPendingWrite();
  if (!pending) throw new Error('There is no pending transaction to resume.');
  const receipt = await reader.waitForFinalization({ hash: pending.hash });
  const outcome = classifyReceipt(receipt, isSuccessful(receipt));
  if (outcome === 'UNRESOLVED') throw new Error(unresolvedMessage(pending.hash));
  persistFinalWrite(pending, outcome, onSubmitted);
  if (outcome === 'FINALIZED_FAILED') {
    throw new Error(`Transaction ${pending.hash} finalized with ${receipt.statusName ?? 'unknown status'} / ${receipt.txExecutionResultName ?? 'unknown execution result'}; no successful contract execution was recorded.`);
  }
  return pending.hash;
}

export async function writeBond(
  functionName: string,
  args: unknown[] = [],
  value?: bigint,
  expectedAddress?: string,
  onSubmitted?: (pending: PendingWrite | null) => void,
): Promise<string> {
  const provider = window.ethereum;
  if (!provider) throw new Error('Install a compatible wallet before writing.');
  const existing = readPendingWrite();
  if (existing) throw new Error(`A previous transaction (${existing.hash}) is still pending. Resume its finalization check before submitting another write.`);
  if (!expectedAddress) throw new Error('Connect your wallet before writing.');
  const address = await authorizedWriteAccount(expectedAddress, provider);
  const client = createClient({ chain, account: address as `0x${string}`, provider: provider as never });
  const call = { address: deployed(), functionName, args: args as never[], ...(value !== undefined ? { value } : {}) };
  const estimate = await client.estimateTransactionFeesForWrite(call);

  // Re-read account and network after estimation; a user can switch either while the wallet is open.
  const confirmedAddress = await authorizedWriteAccount(expectedAddress, provider);
  if (confirmedAddress.toLowerCase() !== address.toLowerCase()) {
    throw new Error('The wallet account changed during fee estimation. No transaction was submitted.');
  }
  let hash: TransactionHash;
  try {
    hash = await client.writeContract({ ...call, fees: { distribution: estimate.distribution, feeValue: estimate.feeValue } });
  } catch (error) {
    throw new Error(submissionFailureMessage(error, functionName));
  }
  const submitted: PendingWrite = { hash, functionName, submittedAt: Date.now(), phase: 'SUBMITTED' };
  localStorage.setItem(pendingKey, JSON.stringify(submitted));
  onSubmitted?.(submitted);
  void client.waitForDecision({ hash }).then(decision => {
    if (decision.statusName?.toUpperCase() === 'ACCEPTED') persistAccepted(hash, onSubmitted);
  }).catch(() => { /* Finalization status remains the authority; pending state is preserved. */ });

  const receipt = await client.waitForFinalization({ hash });
  const outcome = classifyReceipt(receipt, isSuccessful(receipt));
  if (outcome === 'UNRESOLVED') throw new Error(unresolvedMessage(hash));
  persistFinalWrite(submitted, outcome, onSubmitted);
  if (outcome === 'FINALIZED_FAILED') {
    throw new Error(`Transaction ${hash} finalized with ${receipt.statusName ?? 'unknown status'} / ${receipt.txExecutionResultName ?? 'unknown execution result'}; no successful contract execution was recorded.`);
  }
  return hash;
}

export const explorerUrl = (hash: string) => `https://explorer-studio-dev.genlayer.com/tx/${hash}`;
