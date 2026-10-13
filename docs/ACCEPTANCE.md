# Bermond reviewer acceptance matrix

Status markers: [x] static/source artifact present, [ ] requires runtime/live verification.

## Code and security

- [x] Standalone contract with clear `gl.Contract` public ABI
- [x] Immutable frozen terms and baseline hash after creation
- [x] Subscriber set frozen after exact funding
- [x] Fixed 4-dimension classification schema and deterministic verdict
- [x] Semantic validator re-fetch and independently classify policy sources
- [x] One-claim-per-beneficiary and release-only-after-expiry logic
- [x] Local mocked tests exercising 20 security / lifecycle paths
- [ ] GenVM lint/validation/typecheck on selected runtime
- [ ] True GenLayer Direct Mode and Studio integration tests
- [ ] Independent technical security review/fuzz testing

## Frontend

- [x] Black/yellow original editorial UI with Comic Sans font stack
- [x] Overview, fixture-only proof lab, chain-only registry, multi-step create page and live bond detail actions
- [x] Explicit no-contract-address status without fake contract data
- [x] Wallet-aware writes with fee estimates and finalized receipt checks
- [ ] `npm run typecheck`, `npm run build`, `npm test` pass on a networked runner
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