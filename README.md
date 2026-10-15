# Bermond

Bermond is a GenLayer service-assurance protocol. A provider locks GEN collateral behind four frozen public commitments—allowance, retention, refunds, and notice. Registered beneficiaries accept the frozen fingerprint before funding. During coverage, anyone may ask independent validators to compare the committed and current policy evidence. The contract alone determines eligibility, fixed payouts, claim deadlines, and release rules.

## Current status

The current contract is deployed and source-matched on Studio Dev (chain ID `61997`) at `0x50039c8Aa426aF3e2F3Cc2DB0677BdfaC5c57A37`. Deployment transaction: `0xd925f95f25c2508b2e4bf5987c501c89e3f8a70d64fdecccb08ce90cd828f96c`. The deployed bytes exactly match source SHA-256 `94f4c585126a8d99348ffcca478b8dd4a157aaf2ca93c84d6a8864585493ac5a`. This verifies deployment and schema, not a successful compensation lifecycle.

The preserved Studio Dev manifest records an earlier deployment at `0x8A5cb514A6b8Eae009cB896F0EcAC2F208d954F9` (chain ID `61997`), deployment transaction `0x0a37753101ddc15e274c3dbe0e744dc5c2138575dfb4006a21df43c1df82a8af`, and source SHA-256 `e1987c6d5b2cff228025e5be8d20d570cd436e05f797569b66020906f0cc1554`. Its claim and expiry-release transaction evidence remains in [`deployments/studio-dev.json`](deployments/studio-dev.json). Those receipts belong to the earlier source. They show finalized contract executions and emitted external-message records, not authoritative beneficiary balance changes.

The candidate's finalized reads and fee estimation worked during the current Studio Dev run. A one-beneficiary bond was created, accepted, and funded with 1 GEN. Two finalized `check_policy` attempts ended `undetermined` with `MAJORITY_DISAGREE`; the bond stayed `ACTIVE`, and no claim was sent. After expiry, release transaction `0x3d7756ce5416ed3990e9574671e20362d0308e82245bf632be4ae22440e640fb` finalized with agreement. The bond is `CLOSED` with zero reserve, and the provider's finalized balance rose by `999873680999999177` wei after the 1 GEN release transaction. The contract still records the emitted amount as `pending_wei=1e18` and `released_wei=0`, so its internal accounting cannot reconcile the observed transfer. The breach payout and broader lifecycle matrix remain unverified. See [`deployments/studio-dev.json`](deployments/studio-dev.json).

## Contract lifecycle

1. The provider creates a bond with four bounded terms, a baseline URL and SHA-256, a provider-declared baseline document identity/publisher/version, current policy URL, fixed per-beneficiary payout, and coverage/claim deadlines.
2. The provider enrolls beneficiaries while the bond is in `DRAFT`. Each enrolled beneficiary signs a transaction accepting the exact policy fingerprint. The first acceptance freezes the subscriber set. Funding requires every subscriber to accept.
3. The provider funds exactly `payout × beneficiary count`. Each bond tracks its own reserve and accounting values.
4. During coverage, anyone may call `check_policy`. This is permissionless but not autonomous monitoring: the chain does not fetch or inspect a policy until a transaction initiates a check.
5. Independent GenVM execution compares source excerpts, source digests, source roles, normalized factual premises, and four dimension/status decisions. Ambiguous or unavailable evidence that reaches consensus is a non-paying `UNRESOLVED` result. Consensus failure is a failed/undecided transaction, not a stored `UNRESOLVED` result.
6. An enrolled beneficiary can claim once after a finalized `BREACHED` result through the claim deadline. The contract reserves the fixed amount and records the outgoing transfer as pending. After the deadline, the provider can close the bond and emit a transfer for only the remaining reserve; that emitted amount also remains pending until independently reconciled.

The provider's declared baseline identity is bound to the bond fingerprint and beneficiary acceptance, but a digest and declaration do not prove publisher identity or historical policy authority. The contract records that limitation; it is a voluntary provider commitment, not centralized certification.

## Test and build

Python checks use the pinned GenLayer v0.6 RC tool family. `genvm-lint check` runs the GenVM lint and SDK semantic validation stages. Direct Mode uses the official `genlayer-test` runner and a small helper that arranges the official downloaded runner artifacts in the supported `GENVM_PREBUILT_DIR` layout. The latest local suite recorded 55 passing tests. Direct Mode tests execute the contract locally with GenVM; they do not represent live Studio consensus or live transfer settlement.

```bash
python -m pip install -r requirements-dev.txt
python -m py_compile contracts/bermond.py
genvm-lint check contracts/bermond.py
GENVM_VERSION=v0.6.0-rc5 GENVM_PREBUILT_DIR="$(python -m tools.prepare_genvm_prebuilt)" python -m pytest -q -p no:cacheprovider tests
```

The frontend remains the existing React/Vite application. It uses injected EIP-1193 wallets and `genlayer-js@2.0.0-rc.1` with the Studio Dev chain preset (61997). It does not use a wallet connection as transaction authorization: each write rechecks the active account and chain after fee estimation. Submitted writes persist until a final receipt is authoritative. A finalized claim/release contract execution is displayed separately from independent verification of the EOA transfer.

```bash
cd frontend
npm ci
npm run typecheck
npm run build
npm test
```

For Vercel on Studio Dev, set `VITE_BERMOND_CONTRACT_ADDRESS=0x50039c8Aa426aF3e2F3Cc2DB0677BdfaC5c57A37`. This address matches the verified source SHA above. Keep the variable empty to show the review-mode interface without synthetic live registry state. The proof lab uses illustrative scenarios; `/app` reads only the configured contract.

## Remaining release blockers

- Two live checks on the breached fixture finalized as `MAJORITY_DISAGREE`, so the breach payout scenario was safely withheld. The reason for validator dissent is not included in the public finalized receipt and needs a code-level diagnosis.
- The expiry release did transfer value to the provider, confirmed by the finalized balance delta and closed bond state, but the contract retains it as pending. There is no contract-level reconciliation path for moving that amount into `released_wei`.
- The other requested live scenarios—compliant and improved changes, finalized unresolved evidence, partial claims, replay rejection, and adversarial classifications—have not all been demonstrated on the current deployment.
- A finalized contract execution alone does not prove an EOA balance change. This release did have a balance delta; the breach payout and general transfer failure/recovery behavior remain unverified.
- The provider-declared policy baseline is not publisher-authenticated or historically proven; runtime URL redirect/final-origin guarantees are not established.
- Permissionless checks still require a human or client to submit a transaction before coverage ends. Policy changes can go unnoticed.
- Desktop review covered the live registry, illustrative proof lab, and create-bond wizard. A real injected-wallet browser session remains outstanding; frontend tests do not replace it.

See [`docs/PROTOCOL.md`](docs/PROTOCOL.md), [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md), [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md), and the deployment evidence in [`deployments/studio-dev.json`](deployments/studio-dev.json).
