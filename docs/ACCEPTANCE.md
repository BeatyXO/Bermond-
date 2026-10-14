# Bermond reviewer acceptance matrix

Status markers: [x] static/source artifact present, [ ] requires runtime/live verification.

## Code and security

- [x] Standalone contract with clear `gl.Contract` public ABI
- [x] Immutable frozen terms and baseline hash after creation
- [x] Subscriber set frozen after exact funding
- [x] Fixed 4-dimension classification schema and deterministic verdict
- [x] Semantic validator re-fetch and independently classify policy sources
- [x] One-claim-per-beneficiary and release-only-after-expiry logic
- [x] Fake-runtime tests exercise financial, expiry, validator, URL and state boundaries (22 cases pass on 2026-10-14)
- [x] Native Direct Mode tests are added for persistent storage, enrollment freeze, exact payable funding, web rendering mocks and validator dissent
- [ ] GenVM SDK semantic validation and typecheck on the SDK pinned by the contract dependency header
- [ ] Direct Mode tests executed successfully against the pinned GenVM artifact
- [ ] Studio integration tests for autonomous web rendering, leader/validator divergence and consensus timeout
- [ ] Independent technical security review/fuzz testing

## Frontend

- [x] Black/yellow original editorial UI with Comic Sans font stack
- [x] Overview, fixture-only proof lab, chain-only registry, multi-step create page and live bond detail actions
- [x] Explicit no-contract-address status without fake contract data
- [x] Wallet-aware writes with fee estimates, persisted transaction hashes and a finality-resume path
- [x] Create form checks the contract's coverage and claim-deadline bounds before submission
- [x] `npm run typecheck`, `npm run build`, `npm test` pass after installing locked dependencies
- [ ] Wallet/mobile/keyboard/browser accessibility review
- [x] Public Studio Dev deployment address, finalized receipt, schema and exact source parity are recorded
- [ ] Browser verification against the deployed contract

## Live evidence

- [x] Deploy source-matched `contracts/bermond.py` on Studio Dev; exact deployed bytes and schema verified
- [ ] Read finalized contract state and submit live lifecycle writes; Studio `gen_call` is currently failing server-side
- [ ] Scenario A: meaning-equivalent rewrite (`COMPLIANT`), no payout
- [ ] Scenario B: material unilateral quota reduction (`BREACHED`), one exact claim, replay blocked
- [ ] Scenario C: unavailable/mismatched evidence (`UNRESOLVED`), no payout
- [ ] Scenario D: improved retention (`COMPLIANT`), no payout
- [ ] Scenario E: expiry release returns only unused GEN, attempts to withdraw twice blocked
- [ ] Capture finalized transaction hashes, receipts, transfers, authoritative post-write state
- [ ] Publish wallet-free proof paths with live cards bound to exact contract IDs
- [ ] Confirm deployment code source SHA-256 equals release commit bytes
- [ ] Verify on fresh browser sessions; no fake or seeded `live` data

**Not launch-ready until every live/runtime/financial gate has passed.**

### Current host evidence (2026-10-14)

- `python -m py_compile contracts/bermond.py tools/studio_dev_deploy.py tools/studio_dev_lifecycle.py tools/verify_studio_dev.py`: passed.
- `python -m pytest -q tests/test_contract.py`: **22 passed**. The Direct Mode fixture runner stalled because no local GenLayer node is available.
- `genvm-lint lint contracts/bermond.py`: **3 checks passed**. SDK semantic validation/typecheck could not download the declared runner artifact; the official RPC schema was generated and verified instead.
- `npm run typecheck`: passed; `npm run build`: passed (Vite reports the main JS chunk exceeds 500 kB); `npm test`: **3 passed**.
- Studio Dev chain ID `61997`: deployment `0xe1902297a5466de8279325c488c2ea415f8cf0eff07ab75b61d412b9a0d586bb`, finalized `FINISHED_WITH_RETURN`, contract `0xda342EB824689891E020D1A503F527bff9fC5F26`. `gen_getContractCode` returned exact local bytes, SHA-256 `0e89aa135d2a818e548837777ecc5299ec24fcf94c5e957d2a3fb7669a6a85a3`; `gen_getContractSchema` exposes all nine expected methods.
- No live bond write was submitted: read-only `gen_call` repeatedly returned `-32603` with SQLAlchemy `Can't reconnect until invalid transaction is rolled back`. This blocks full-cycle receipts on this host/node. Studio also does not support external EOA GEN payouts, so claim settlement and expiry release remain unverified.
