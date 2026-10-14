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
- `python -m pytest -q tests/test_contract.py`: **22 passed**. The Direct Mode fixture runner stalled because no local GenLayer node is available.
- `genvm-lint lint contracts/bermond.py`: **3 checks passed**. SDK semantic validation/typecheck could not download the declared runner artifact; the official RPC schema was generated and verified instead.
- `npm run typecheck`: passed; `npm run build`: passed (Vite reports the main JS chunk exceeds 500 kB); `npm test`: **3 passed**.
- Studio Dev chain ID `61997`: deployment `0x134140ee9918c4fef5c5e210435b0d952d58430df4ef8f36be871d26cdc4ede7`, finalized `FINISHED_WITH_RETURN`, contract `0xd2E64c15268edE3EfA637DD09496beC9c9F795C3`. `gen_getContractCode` returned exact local bytes, SHA-256 `b200f5138385219a3e9585ab442247f836922e5cea599013ecdc91881abd270d`; `gen_getContractSchema` exposes all nine expected methods.
- A real 1-GEN lifecycle finalized successfully through `create_bond`, `enroll_subscriber`, `fund_bond`, `check_policy` (`BREACHED`), and `claim_compensation`. The claim receipt contains a finalized EOA transfer message for `1000000000000000000` wei; the beneficiary's public balance increased by approximately 1 GEN net of intervening test fees. Receipt hashes are recorded in `deployments/studio-dev.json`.
- Expiry release test bond `studio-release-1791968775` matured past its deadline. Its provider `release_collateral` transaction `0xeb4965a939072756f93c7acf999e3848789c87d95b9277ff6260889e4f513352` finalized successfully and emitted a 1-GEN finalized transfer to the provider. The runner rejected a repeated release locally.
- Studio's `gen_call` still returns `-32603` with SQLAlchemy `Can't reconnect until invalid transaction is rolled back`, so authoritative post-write state reads and the contract-level duplicate-release guard cannot be independently queried. GenVM SDK validation and Direct Mode tests fail before execution because the pinned `py-genlayer` runner artifact is absent from the local cached runner archive.
- Local browser review covered the overview, all four proof-lab cases, create-form steps, unconfigured safe mode, and configured registry error handling. At 393px viewport, document width was 378px with no horizontal overflow; navigation and case accordion controls are keyboard-focusable. The Studio registry exposes the read RPC failure clearly. No connected-wallet write was submitted through the browser.
