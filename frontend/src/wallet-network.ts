export const STUDIO_DEV_CHAIN_ID = '0xf22d';

export interface Eip1193Provider {
  request: (options: { method: string; params?: unknown[] }) => Promise<unknown>;
}

const studioDevChain = {
  chainId: STUDIO_DEV_CHAIN_ID,
  chainName: 'GenLayer Studio Dev',
  nativeCurrency: { name: 'GEN', symbol: 'GEN', decimals: 18 },
  rpcUrls: ['https://studio-dev.genlayer.com/api'],
  blockExplorerUrls: ['https://explorer-studio-dev.genlayer.com'],
};

function isUnknownChain(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false;
  const value = error as { code?: unknown; data?: { originalError?: { code?: unknown } } };
  return value.code === 4902 || value.data?.originalError?.code === 4902;
}

export async function switchToStudioDev(provider: Eip1193Provider): Promise<void> {
  try {
    await provider.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: STUDIO_DEV_CHAIN_ID }],
    });
  } catch (error) {
    if (!isUnknownChain(error)) throw error;
    await provider.request({ method: 'wallet_addEthereumChain', params: [studioDevChain] });
    await provider.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: STUDIO_DEV_CHAIN_ID }],
    });
  }
}
