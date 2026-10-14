export const WALLET_DISCONNECTED_KEY = 'bermond:wallet-disconnected';

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export function isWalletDisconnected(storage: StorageLike = localStorage): boolean {
  return storage.getItem(WALLET_DISCONNECTED_KEY) === 'true';
}

export function currentAuthorizedAccount(accounts: unknown, storage: StorageLike = localStorage): string | null {
  if (isWalletDisconnected(storage) || !Array.isArray(accounts)) return null;
  return typeof accounts[0] === 'string' && /^0x[a-f\d]{40}$/i.test(accounts[0]) ? accounts[0] : null;
}

export function walletAccountsChanged(accounts: unknown, storage: StorageLike = localStorage): string | null {
  if (isWalletDisconnected(storage)) return null;
  const account = currentAuthorizedAccount(accounts, storage);
  if (!account) storage.setItem(WALLET_DISCONNECTED_KEY, 'true');
  return account;
}

export function markWalletConnected(storage: StorageLike = localStorage): void {
  storage.removeItem(WALLET_DISCONNECTED_KEY);
}

export function markWalletDisconnected(storage: StorageLike = localStorage): void {
  storage.setItem(WALLET_DISCONNECTED_KEY, 'true');
}
