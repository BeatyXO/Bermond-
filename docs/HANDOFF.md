# Handoff status

## Completed

- The latest Studio Dev deployment finalized at `0xd2E64c15268edE3EfA637DD09496beC9c9F795C3` on chain ID `61997` in transaction `0x134140ee9918c4fef5c5e210435b0d952d58430df4ef8f36be871d26cdc4ede7`.
- The RPC-returned source is byte-for-byte identical to `contracts/bermond.py` (SHA-256 `b200f5138385219a3e9585ab442247f836922e5cea599013ecdc91881abd270d`). The live schema returns all nine expected public methods. Evidence is in `deployments/studio-dev.json`.
- Fixed payout execution: external EOA `emit_transfer` finalizes implicitly and does not accept an `on` keyword. The previous signature caused `TypeError: ContractProxy.emit_transfer() got an unexpected keyword argument 'on'`.
- A real 1-GEN bond completed create, enroll, fund, `BREACHED` policy check, and claim. The claim receipt emitted a finalized 1-GEN transfer to the beneficiary; its public balance increased by approximately 1 GEN net of intervening test fees.
- A separate ACTIVE test bond passed its deadline; `release_collateral` finalized and emitted 1 GEN back to the provider. The lifecycle runner correctly refused a second release attempt before submitting a transaction.
- Target runtime fixes: `TreeMap` imports from `genlayer.storage.tree_map`; the contract base is `genlayer.contract.Contract`; typed storage uses GenVM zero-initialization; runtime ABI annotations are not postponed.
- Added scripts to deploy, verify and attempt a two-wallet lifecycle without printing or persisting private keys. Wallet file path and labels are passed at runtime.
- `python -m pytest -q tests/test_contract.py`: 22 passed. Python compilation passed. `genvm-lint lint contracts/bermond.py`: 3 checks passed.
- Frontend typecheck and production build passed; `npm test` reports 3 passed. Browser QA exercised overview, proof scenarios, create steps, mobile-width overflow, and configured registry handling. The registry clearly displays Studio's RPC read error.
- Git remote is verified as `https://github.com/BeatyXO/Bermond-.git`, branch `main`.

## Remaining live checks

1. Retry `get_bond_ids` and post-write `get_bond` reads when Studio Dev `gen_call` is healthy; it currently returns `-32603` with a SQLAlchemy rollback error.
2. Retry GenLayer Direct Mode and SDK semantic validation when the pinned `py-genlayer` runner artifact is available in the local runner archive.
3. Query the contract-level duplicate-release guard after Studio `gen_call` recovers; the harness was verified to block a second release before submission.
