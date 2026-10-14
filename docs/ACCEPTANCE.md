# Bermond reviewer acceptance matrix

Status markers: [x] static/source artifact present, [ ] requires runtime/live verification.

## Code and security

- [x] Standalone contract with clear `gl.Contract` public ABI
- [x] Immutable frozen terms and baseline hash after creation
- [x] Subscriber set frozen after exact funding
- [x] Fixed 4-dimension classification schema and deterministic verdict
- [x] Semantic validator re-fetch and independently classify policy sources
- [x] One-claim-per-beneficiary and release-only-after-expiry logic
- [x] Fake-runtime tests exercise financial, expiry, validator, URL and state boundaries (32 cases pass after source-evidence hardening)
- [x] Native Direct Mode tests are added for persistent storage, enrollment freeze, exact payable funding, web rendering mocks and validator dissent
- [x] GenVM SDK semantic validation and typecheck on the SDK pinned by the contract dependency header
- [x] Direct Mode tests executed successfully against the pinned GenVM artifact through the project-local archive/API compatibility adapter
- [ ] Studio integration tests for autonomous web rendering, leader/validator divergence and consensus timeout
- [ ] Independent technical security review/fuzz testing

## Frontend

- [x] Black/yellow original editorial UI with Comic Sans font stack
- [x] Overview, fixture-only proof lab, chain-only registry, multi-step create page and live bond detail actions
- [x] Explicit no-contract-address status without fake contract data
- [x] Injected EIP-1193 connect/disconnect, refresh restore, account-change handling, Studio Dev chain guard, fee estimates, persisted hashes and finality-resume path
- [x] Create form checks the contract's coverage and claim-deadline bounds before submission
- [x] `npm run typecheck`, `npm run build`, `npm test` pass after installing locked dependencies
- [ ] Wallet/mobile/keyboard/browser accessibility review
- [x] Public Studio Dev deployment address, finalized receipt, schema and exact source parity are recorded
- [ ] Browser verification against the deployed contract

## Live evidence

- [x] Deploy source-matched `contracts/bermond.py` on Studio Dev; exact deployed bytes and schema verified
- [x] Submit live lifecycle writes for a breach scenario; finalized state reads remain blocked by Studio `gen_call`
- [ ] Scenario A: meaning-equivalent rewrite (`COMPLIANT`), no payout
- [x] Scenario B: material unilateral quota reduction (`BREACHED`) and one exact 1-GEN claim
- [ ] Scenario B: replay claim is blocked
- [ ] Scenario C: unavailable/mismatched evidence (`UNRESOLVED`), no payout
- [ ] Scenario D: improved retention (`COMPLIANT`), no payout
- [x] Scenario E: expiry `release_collateral` finalized and emitted the unused 1-GEN collateral back to provider
- [x] Scenario E: lifecycle runner refused a second release after finalization; on-chain replay guard not independently queried
- [x] Capture finalized transaction hashes, receipts, and emitted 1-GEN transfer
- [ ] Read authoritative post-write state after Studio `gen_call` recovers
- [ ] Publish wallet-free proof paths with live cards bound to exact contract IDs
- [x] Confirm deployment code source SHA-256 equals deployed release bytes
- [ ] Verify on fresh browser sessions; no fake or seeded `live` data

**Not launch-ready until every live/runtime/financial gate has passed.**

### Current host evidence (2026-10-14)

- `python -m py_compile contracts/bermond.py tools/studio_dev_deploy.py tools/studio_dev_lifecycle.py tools/verify_studio_dev.py`: passed.
- `python -m pytest -q tests`: **35 passed**, including 3 Direct Mode tests against the pinned SDK with `tools/genvm_zip_compat.py`.
- `genvm-lint check` and `validate` pass (3 lint checks); `npm run typecheck`, `npm run build`, and `npm test` pass (7 tests). Vite reports that the main JS chunk exceeds 500 kB.
- Studio Dev chain ID `61997`: deployment `0x0a37753101ddc15e274c3dbe0e744dc5c2138575dfb4006a21df43c1df82a8af` finalized as `FINISHED_WITH_RETURN`, contract `0x8A5cb514A6b8Eae009cB896F0EcAC2F208d954F9`. `gen_getContractCode` returned exact local bytes, SHA-256 `e1987c6d5b2cff228025e5be8d20d570cd436e05f797569b66020906f0cc1554`; `gen_getContractSchema` exposes all nine expected methods.
- A real two-wallet 1-GEN lifecycle finalized successfully through `create_bond`, `enroll_subscriber`, `fund_bond`, `check_policy`, and `claim_compensation`. The claim receipt contains an accepted/finalized EOA transfer message for `1000000000000000000` wei to the beneficiary. The receipt does not expose a consensus verdict, and Studio `gen_call` remains broken, so committed contract state and verdict cannot be independently confirmed. Receipt hashes are recorded in `deployments/studio-dev.json`.
- On the current deployment, expiry bond `studio-release-1791980857` finalized create, enroll, fund, and release. `release_collateral` transaction `0xc47b0c4887c0218c4f0e0ffacc4ef39543f479f6b638e61a36fb56f87a866008` succeeded; its finalized receipt includes a `1000000000000000000` wei (1 GEN) transfer message to provider `0xD6423aE82a975d55C6CeaC222827A727325e0459`. The runner refuses a repeated release locally.
- Studio's `gen_call` and transaction-specific fee estimate return `-32603` with SQLAlchemy `Can't reconnect until invalid transaction is rolled back`; authoritative post-write state and verdict reads and the contract-level duplicate-release guard cannot be independently queried.
- Local browser review covered the overview, all four proof-lab cases, create-form steps, unconfigured safe mode, and configured registry error handling. At 393px viewport, document width was 378px with no horizontal overflow; navigation and case accordion controls are keyboard-focusable. The Studio registry exposes the read RPC failure clearly. No connected-wallet write was submitted through the browser.
- Latest pre-hardening GitHub Actions run: [38549571545](https://github.com/BeatyXO/Bermond-/actions/runs/38549571545). Frontend job passed; contract job failed at the same missing py-genlayer artifact, and its later test step was skipped. Workflow now marks the test step `if: always()` so SDK artifact failures no longer skip it.
- Current verified deployment source SHA-256 is `e1987c6d5b2cff228025e5be8d20d570cd436e05f797569b66020906f0cc1554` and is byte-identical to the local contract.
