export type ReceiptOutcome = 'FINALIZED_SUCCESS' | 'FINALIZED_FAILED' | 'UNRESOLVED';

export interface ReceiptLike {
  statusName?: string;
  lifecycle?: { state?: string } | string;
  txExecutionResultName?: string;
}

export function classifyReceipt(receipt: ReceiptLike, sdkReportsSuccess: boolean): ReceiptOutcome {
  const lifecycle = typeof receipt.lifecycle === 'string' ? receipt.lifecycle : receipt.lifecycle?.state;
  const finalized = receipt.statusName?.toUpperCase() === 'FINALIZED' || lifecycle?.toLowerCase() === 'finalized';
  if (!finalized) return 'UNRESOLVED';
  return sdkReportsSuccess ? 'FINALIZED_SUCCESS' : 'FINALIZED_FAILED';
}

export function submissionFailureMessage(error: unknown, functionName: string): string {
  const value = error && typeof error === 'object' ? error as { code?: unknown; cause?: { code?: unknown }; message?: string } : {};
  if (value.code === 4001 || value.code === '4001' || value.cause?.code === 4001 || value.cause?.code === '4001') {
    return `The wallet rejected ${functionName}; no transaction hash was returned.`;
  }
  return `No transaction hash was returned for ${functionName}. The submission outcome may be unknown; inspect wallet activity and the Studio Dev explorer before retrying. ${value.message ?? ''}`.trim();
}
