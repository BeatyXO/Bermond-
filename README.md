# Bermond ✳

**Promises, with consequences.** A standalone GenLayer Intelligent Contract for bonding public service commitments and adjudicating material policy drift.

> **Build stage (2026-10-13):** source implementation + editorial frontend + deterministic local tests. **NOT DEPLOYED. NOT AUDITED.** No live transactions, onchain contract address or completed GenVM validation are claimed. The interactive proof lab uses clearly labeled illustrative fixtures.

## Why this exists

When a service provider changes an API quota, data retention term, refund right or advance-notice commitment, simply diffing the words cannot determine whether the promise was broken. Bermond enables a provider to reserve **GEN collateral** behind four frozen policy rights. Independent GenLayer execution reads the archived baseline and the current published policy and classifies their **meaning**. The contract derives the verdict, controls who is eligible and allows each enrolled beneficiary at most one exact compensation claim.

**Not MatchPay:** Bermond is continuous policy assurance rather than purchase-order / invoice / receipt reconciliation. Its innovations include changing-public-policy detection, explicit time-based coverage, predetermined multi-beneficiary reserves, subscriber freeze and a claim grace window. The visual experience is intentionally different: high-contrast black/yellow Comic Sans with illustrated policy tickets, clause-diff explorer and bond registry.

## Repo map

```text
contracts/bermond.py               One standalone GenLayer Intelligent Contract
tests/test_contract.py             Lightweight contract-state tests with mocked GenLayer runtime
tests/test_direct_mode.py          Native GenLayer Direct Mode persistence/funding smoke tests
tests/conftest.py                  Isolated GenLayer test double
frontend/src/main.tsx             React UI: marketing, proof lab, registry, create, detail/actions
frontend/src/styles.css            Original black/yellow Comic Sans design
frontend/src/chain.ts              GenLayerJS read/write, fee-estimate, finality handling
frontend/src/fixtures.ts           Clearly labeled fictional proof-lab fixtures
frontend/src/protocol.ts           Types, BigInt parsing, verdict helpers
docs/PROTOCOL.md                   Protocol specification and state machine
docs/THREAT_MODEL.md               Security boundaries and open issues
docs/ACCEPTANCE.md                 Review-ready verification matrix
docs/HANDOFF.md                    Explicit remaining steps
CODEX_FINISH_PROMPT.md             Paste-ready autonomous coding agent brief
.github/workflows/ci.yml           Python + frontend quality gates
```

## Protocol

1. Provider calls `create_bond`, committing the baseline HTTPS URL + mandatory SHA-256 digest, current policy URL, four protected clauses, exact per-beneficiary GEN amount, coverage end and claim deadline.
2. Provider calls `enroll_subscriber` for up to 12 distinct eligible wallets while still in `DRAFT`.
3. Provider calls payable `fund_bond` with **exactly** `(per_beneficiary_amount × beneficiary_count)` GEN. The subscriber set freezes and coverage becomes `ACTIVE`.
4. Anyone calls `check_policy` during the coverage period. Leader and validators independently retrieve both sources; validators compare the four material statuses, not prose. The contract derives `BREACHED` if any clause is breached, otherwise `UNRESOLVED` if any clause is unresolved, otherwise `COMPLIANT` (stored as `ACTIVE`).
5. In `BREACHED`, each pre-enrolled beneficiary may call `claim_compensation` exactly once by the claim deadline. Contract code fixes the amount and claimant recipient.
6. After the claim deadline the provider may call `release_collateral` to reclaim remaining funds and close the bond. A claimed amount cannot be reclaimed.

The LLM cannot choose a payment, set a beneficiary or change the collateral reserve. No administrator has emergency confiscation authority. **Breach validation is only as strong as the source provenance and frozen rules.**

## Run locally

```bash
python -m pytest -q tests
cd frontend
npm install
npm run typecheck
npm run build
npm test
npm run dev
```

`tests/test_contract.py` uses fake GenLayer infrastructure; it does not prove GenVM behavior. `tests/test_direct_mode.py` uses the `genlayer-test` Direct Mode fixtures and the SDK identified by the contract's `Depends` header. Studio consensus and network-finalized receipts remain separate launch gates. Install the pinned Python tools with `python -m pip install -r requirements-dev.txt`. CI installs those tools and runs `genvm-lint check` plus the complete pytest suite. The frontend targets `genlayer-js@2.0.0-rc.1` and the Studio development preview (chain 61997).

### Frontend environments

```bash
cp frontend/.env.example frontend/.env
# Leave VITE_BERMOND_CONTRACT_ADDRESS empty until deployment and live proofs succeed.
```

With no contract address, the product intentionally disables all onchain writes and displays a *review mode* instead of faking live state. `/proof` contains four labeled fictional scenarios so reviewers can understand the intended decisions without connecting a wallet. `/app` is a strictly chain-backed registry when configured.

### GEN transfer and finality

`fund_bond` is the only payable method. The JS adapter estimates protocol fees separately from its GEN deposit and waits for finalized successful execution before showing a transaction as complete. Once a write returns a hash, the app stores it before waiting and offers a finality-resume action after a timeout or reload; it blocks another write until the pending receipt is checked. Transfers are emitted at finalization, after internal claim state has been written.

Studio supports consensus and simulated native transfers, but does not implement `@gl.evm.contract_interface` calls to EOAs. A Studio run can validate contract decisions and message construction; it cannot prove that the external GEN transfer child transaction paid its recipient. Verify transfer settlement on a network that supports those external messages before enabling real-value use. See [`deployments/studio-dev.json`](deployments/studio-dev.json) for the pending, explicitly unproven release record.

## Source and release honesty

- No score, audit result, validator execution, published production URL, or verified deployment is claimed here.
- Document URL hashes attest content equality at render time, *not* source ownership or historical existence.
- A service provider may control its current policy page; a neutral archived baseline with authenticated provenance is needed for stronger guarantees.
- Consensus rejection may leave a transaction undecided rather than committing an `UNRESOLVED` state. Test this on the target network.
- The live proof must use stable public evidence, finalized receipts and authoritative reads. See `docs/ACCEPTANCE.md`.

Official references: [GenLayer storage](https://docs.genlayer.com/developers/intelligent-contracts/features/storage) · [GenLayer transaction timestamps](https://docs.genlayer.com/developers/intelligent-contracts/features/transaction-context) · [GenLayer value transfers](https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers) · [GenLayerJS writes](https://docs.genlayer.com/developers/decentralized-applications/writing-data).
