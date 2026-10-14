# Handoff status

## Completed

- The Studio Dev deployment finalized successfully at `0xda342EB824689891E020D1A503F527bff9fC5F26` on chain ID `61997` in transaction `0xe1902297a5466de8279325c488c2ea415f8cf0eff07ab75b61d412b9a0d586bb`.
- The RPC-returned source is byte-for-byte identical to `contracts/bermond.py` (SHA-256 `0e89aa135d2a818e548837777ecc5299ec24fcf94c5e957d2a3fb7669a6a85a3`). The live schema returns all nine expected public methods. Evidence is in `deployments/studio-dev.json`.
- Target runtime fixes: `TreeMap` imports from `genlayer.storage.tree_map`; the contract base is `genlayer.contract.Contract`; typed storage uses GenVM zero-initialization; runtime ABI annotations are not postponed.
- Added scripts to deploy, verify and attempt a two-wallet lifecycle without printing or persisting private keys. Wallet file path and labels are passed at runtime.
- `python -m pytest -q tests/test_contract.py`: 22 passed. Python compilation passed. `genvm-lint lint contracts/bermond.py`: 3 checks passed.
- Frontend typecheck and production build passed; `npm test` reports 3 passed. Studio Dev is not configured in the frontend because its read endpoint is currently failing.
- Git remote is verified as `https://github.com/BeatyXO/Bermond-.git`, branch `main`.

## Blocking live lifecycle verification

The lifecycle runner did not submit a bond write. `gen_call` repeatedly returned `-32603` with `Can't reconnect until invalid transaction is rolled back`, including for the direct documented request shape. This appears to be a Studio Dev node/database failure. The deployment, code and schema read endpoints remain available. Do not retry writes until a finalized state read succeeds.

Studio Dev also does not implement `@gl.evm.contract_interface` EOA settlement, so even after the node read path recovers it cannot prove customer GEN payout settlement. The claim grace period must expire before the provider release path can be exercised. These limits are reflected in the manifest; no live bond transactions or payouts are claimed.

## Remaining checks

1. Retry a finalized `get_bond_ids` read when Studio Dev `gen_call` is healthy.
2. Run `tools/studio_dev_lifecycle.py` with two Studio Dev test wallets; inspect every finalized receipt and state before continuing.
3. Verify external GEN claim and release settlement on a network that supports EOA external messages, then configure the frontend address and run browser checks.
4. Run GenLayer Direct Mode with a local node and semantic SDK validation/typecheck when the declared runner artifact is available.
