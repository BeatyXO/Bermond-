# Handoff status

## Completed

- The latest Studio Dev deployment finalized at `0x8A5cb514A6b8Eae009cB896F0EcAC2F208d954F9` on chain ID `61997` in transaction `0x0a37753101ddc15e274c3dbe0e744dc5c2138575dfb4006a21df43c1df82a8af`.
- The RPC-returned source is byte-for-byte identical to `contracts/bermond.py` (SHA-256 `e1987c6d5b2cff228025e5be8d20d570cd436e05f797569b66020906f0cc1554`). The live schema returns all nine expected public methods. Evidence is in `deployments/studio-dev.json`.
- Fixed payout execution: external EOA `emit_transfer` finalizes implicitly and does not accept an `on` keyword. The previous signature caused `TypeError: ContractProxy.emit_transfer() got an unexpected keyword argument 'on'`.
- A real two-wallet 1-GEN bond completed create, enroll, fund, policy check, and claim. The claim transaction finalized and its receipt contains a 1-GEN transfer message to the beneficiary. The policy verdict and committed post-write state cannot be independently read while Studio `gen_call` is failing.
- On the latest deployment, separate test bond `studio-release-1791980857` finalized create, enroll, fund, and expiry `release_collateral`. Release transaction `0xc47b0c4887c0218c4f0e0ffacc4ef39543f479f6b638e61a36fb56f87a866008` succeeded and its receipt contains a 1-GEN transfer message back to the provider.
- Target runtime fixes: `TreeMap` imports from `genlayer.storage.tree_map`; the contract base is `genlayer.contract.Contract`; typed storage uses GenVM zero-initialization; runtime ABI annotations are not postponed.
- Added scripts to deploy, verify and attempt a two-wallet lifecycle without printing or persisting private keys. Wallet file path and labels are passed at runtime.
- `python -m pytest -q tests`: 35 passed, including native Direct Mode against the pinned SDK via the project adapter. `genvm-lint` check and validation pass. Frontend typecheck, production build, and 7 tests pass.
- Git remote is verified as `https://github.com/BeatyXO/Bermond-.git`, branch `main`.

## Remaining checks

1. Retry `get_bond_ids` and post-write `get_bond` reads when Studio Dev `gen_call` is healthy; it currently returns `-32603` with a SQLAlchemy rollback error.
2. Browser verification against the deployed address and wallet-based fresh-session QA remain outstanding.
3. Query the contract-level duplicate-release guard after Studio `gen_call` recovers; the lifecycle runner refuses a second release after finalization.
