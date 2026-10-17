type WalletError = {
  code?: unknown;
  message?: unknown;
  shortMessage?: unknown;
  reason?: unknown;
  data?: { message?: unknown; originalError?: { code?: unknown } };
};

export function walletErrorText(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  if (!error || typeof error !== 'object') return 'The wallet request failed.';

  const walletError = error as WalletError;
  const code = walletError.code ?? walletError.data?.originalError?.code;
  if (code === 4001 || code === '4001' || code === 'ACTION_REJECTED') {
    return 'Wallet request was rejected.';
  }

  for (const message of [walletError.message, walletError.shortMessage, walletError.reason, walletError.data?.message]) {
    if (typeof message === 'string' && message.trim()) return message;
  }
  return 'The wallet request failed.';
}
