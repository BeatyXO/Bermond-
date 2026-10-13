# Bermond reviewer acceptance matrix

Status markers: [x] static/source artifact present, [ ] requires runtime/live verification.

## Code and security

- [x] Standalone contract with clear `gl.Contract` public ABI
- [x] Immutable frozen terms and baseline hash after creation
- [x] Subscriber set frozen after exact funding
- [x] Fixed 4-dimension classification schema and deterministic verdict
- [x] Semantic validator re-fetch and independently classify policy sources
- [x] One-claim-per-beneficiary and release-only-after-expiry logic
- [x] Fake-runtime tests exercise financial, expiry, validator, URL and state boundaries (22 cases pass on 2026-10-13)
- [x] Native Direct Mode smoke tests are added for persistent storage, enrollment freeze and exact payable funding
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
- [ ] `npm ci`, `npm run typecheck`, `npm run build`, `npm test` pass on a networked runner
- [ ] Wallet/mobile/keyboard/browser accessibility review
- [ ] Public deployment address, environment and browser verification

## Live evidence

- [ ] Deploy source-matched `contracts/bermond.py` on GenLayer Studio Dev or chosen network
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

### Current host evidence (2026-10-13)

- `python -m pytest -q tests/test_contract.py`: **22 passed** on Python 3.12.10.
- `npm test`: **3 passed** on Node 24.16.0.
- `genvm-lint check` passed static lint. SDK validation, schema and typecheck could not load the pinned runner because the linter cache under `%USERPROFILE%\.cache\genvm-linter` is inaccessible to this workspace process.
- `npm run typecheck` could not start because dependency installation was interrupted by unavailable registry access; no lockfile has been generated yet.
- Studio credentials and an authoritative deployment were not available. No contract address, transaction hash, balances, transfers or receipt is asserted in the manifest.
- GenLayer Studio documentation states external EVM interface calls to EOAs are not implemented there. Studio is therefore insufficient to prove Bermond's external GEN payment child message; that proof requires a supporting network.
