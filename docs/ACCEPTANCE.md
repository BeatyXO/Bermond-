# Bermond acceptance status

This matrix distinguishes local validation, browser review, preserved historical receipts, and live verification of the current deployment. A local pass does not establish network consensus or settlement.

## Current candidate: local validation

- [x] Audited the standalone contract ABI, storage mutation paths, evidence reads, consensus callbacks, claim/release paths, and frontend transaction flow.
- [x] GenVM lint and SDK semantic validation: `genvm-lint check contracts/bermond.py` passes all three lint checks and validation; schema reports 10 methods (3 views, 7 writes).
- [x] Python compilation passes.
- [x] Fake-runtime and native GenLayer Direct Mode suite: **55 passed** using the pinned GenVM runner bundle.
- [x] Frontend TypeScript typecheck passes; `npm test` passes **7 tests**; production build succeeds.
- [x] Local browser review: registry empty state, proof lab, create flow, unconfigured live-write block, missing-wallet error, mobile-width layout, and keyboard focus progression were observed. No horizontal overflow was visible in the reviewed mobile-width screen.
- [x] Desktop browser review of the live registry, illustrative proof lab, and all three create-bond steps; the live bond appeared from chain state and the on-chain create action stayed disabled with missing required identity fields.
- [ ] Browser interaction with an injected wallet was not completed; the in-app browser had no wallet provider. Wallet state transitions are covered by local frontend tests, not by an injected-wallet session.
- [ ] Production bundle size warning remains: main JavaScript chunk is about 887 kB before gzip (about 217 kB gzip).

The Direct Mode suite executes the contract through the local GenVM harness. It is not Studio validator consensus or evidence of live transfers. Browser review used the local development server; an injected-wallet browser session remains outstanding.

## Historical Studio Dev evidence

The preserved deployment at `0x8A5cb514A6b8Eae009cB896F0EcAC2F208d954F9` was finalized on chain `61997` by transaction `0x0a37753101ddc15e274c3dbe0e744dc5c2138575dfb4006a21df43c1df82a8af`. Its historical source SHA-256 is `e1987c6d5b2cff228025e5be8d20d570cd436e05f797569b66020906f0cc1554`, and that source was byte-matched to the deployed code at the time. It is not the current candidate.

The manifest retains historical finalized claim and expiry-release receipts. Those receipts show successful contract execution and outgoing message records, including a 1 GEN beneficiary claim and 1 GEN provider release. They do not prove recipient balance deltas, current candidate behavior, or on-chain replay rejection. Historical post-write reads were blocked by the Studio `gen_call` error.

## Current deployment: network and release gates

- [x] Source SHA-256 `94f4c585126a8d99348ffcca478b8dd4a157aaf2ca93c84d6a8864585493ac5a` is deployed at `0x50039c8Aa426aF3e2F3Cc2DB0677BdfaC5c57A37` on chain `61997`; deployment transaction `0xd925f95f25c2508b2e4bf5987c501c89e3f8a70d64fdecccb08ce90cd828f96c` finalized with agreement, exact byte parity, and the expected 10-method schema.
- [x] A current candidate bond was created, enrolled, accepted, and funded with exactly 1 GEN. Finalized reads returned its state and accounting.
- [ ] Two live `check_policy` transactions finalized `undetermined` after validator disagreement. The latest finalized read showed `ACTIVE`, `checks=0`, `funded_wei=1e18`, `reserved_wei=1e18`, and `pending_wei=0`. No compensation claim was submitted. This is a non-paying consensus failure, not a stored `UNRESOLVED` result.
- [x] Expiry release finalized with agreement in transaction `0x3d7756ce5416ed3990e9574671e20362d0308e82245bf632be4ae22440e640fb`. The post-state is `CLOSED`, `reserved_wei=0`, and the provider's finalized balance increased by `999873680999999177` wei after the 1 GEN transfer transaction.
- [ ] The contract still reports `released_wei=0` and `pending_wei=1e18` for that closed bond. The balance delta confirms this test transfer, but there is no contract-level settlement reconciliation path. No live breach payout has been confirmed.
- [ ] Publisher identity and historical authority of baseline documents remain provider-declared, not independently authenticated. Final URL/redirect behavior for the pinned web transport is not verified.
- [ ] Permissionless policy checks require a caller to submit a transaction; there is no autonomous observer or keeper.
- [ ] The remaining live scenario matrix (compliant, breach payout, finalized unresolved, improved policy, partial claims, replays, and adversarial consensus), desktop/injected-wallet browser coverage, and independent security/fuzz review remain outstanding.

The current source is deployed and verified, but the requested live lifecycle and browser matrix are incomplete. This evidence is not a production-readiness claim. Preserved historical transactions and current candidate receipts are separated in [`../deployments/studio-dev.json`](../deployments/studio-dev.json).

## CI evidence

The starting commit `b20e3ddaf6da14196b53e3f88133e35cb3ac4186` failed [run 38549571545](https://github.com/BeatyXO/Bermond-/actions/runs/38549571545) during GenVM lint/artifact validation. The later candidate workflow passed on [`282a5b6d64427d38b51fb09780dbd7fbf53a1bc2`](https://github.com/BeatyXO/Bermond-/commit/282a5b6d64427d38b51fb09780dbd7fbf53a1bc2) in [run 38645305068](https://github.com/BeatyXO/Bermond-/actions/runs/38645305068), including frontend and contract jobs. That CI result predates the uncommitted deployment/lifecycle-tool updates in this working tree; those local changes still need their own checks and push.
