# Bermond acceptance status

This matrix distinguishes local validation, browser review, preserved historical receipts, and live verification of the current deployment. A local pass does not establish network consensus or settlement.

## Current candidate: local validation

- [x] Audited the standalone contract ABI, storage mutation paths, evidence reads, consensus callbacks, claim/release paths, and frontend transaction flow.
- [x] GenVM lint and SDK semantic validation: `genvm-lint check contracts/bermond.py` passes all three lint checks and validation; schema reports 10 methods (3 views, 7 writes).
- [x] Python compilation passes.
- [x] Fake-runtime and native GenLayer Direct Mode suite: **57 passed** using the pinned GenVM runner bundle.
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

- [x] Source SHA-256 `102bcb26c4d62b8f2bb3488e56043be621339954bf0beaa5685958b254d8693b` is deployed at `0xA42B4f4fB758A74B65b48faddB9ec92Af58158d0` on chain `61997`; deployment transaction `0x29472498004fbef0399a42b0b10645acc7a12564595ffde6aaab90d3395b610b` finalized with agreement, exact byte parity, and the expected 10-method schema.
- [x] Equivalent-policy case `studio-equivalent-1792192420` finalized `COMPLIANT` with `MAJORITY_AGREE`; no claim was sent.
- [x] Improved-policy case `studio-improved-1792193606` finalized `COMPLIANT` with `MAJORITY_AGREE`; no claim was sent.
- [x] Missing-evidence case `studio-unavailable-1792192161` finalized and stored `UNRESOLVED`; no claim was sent.
- [x] Corrected breach case `studio-breach-1792193081` finalized `BREACHED`; one claim finalized in `0xa5b38789861ac8a8a5040a9ca66f4b57ffbcfce5a`. The beneficiary balance delta was `999873662249999177` wei. Finalized state reads showed `claimed=true`, `reserved_wei=0`, `pending_wei=1e18`, and `paid_wei=0`.
- [ ] The claim transfer remains pending in contract accounting because no authoritative settlement reconciliation path exists. The balance delta is independent evidence of this one transfer; it does not provide a safe generic recovery mechanism.
- [ ] Current-deployment expiry release, partial-claim, replay, and adversarial live scenarios remain unverified. The earlier successful release receipt belongs to a different source-matched deployment.
- [ ] Publisher identity and historical authority remain provider-declared. Final URL/redirect behavior for the pinned web transport is not established.
- [ ] Permissionless checks still require a caller to submit a transaction; no autonomous observer or keeper exists.
- [ ] Browser interaction with an injected wallet, independent security/fuzz review, and transfer-failure/reconciliation behavior remain outstanding.

The current source is deployed and verified, and live compliant, unavailable-evidence, breach, and claim paths have finalized. The remaining financial accounting, lifecycle, and browser limitations mean this is not a production-readiness claim. Preserved historical transactions and current receipts are separated in [`../deployments/studio-dev.json`](../deployments/studio-dev.json).

## CI evidence

The starting commit `b20e3ddaf6da14196b53e3f88133e35cb3ac4186` failed [run 38549571545](https://github.com/BeatyXO/Bermond-/actions/runs/38549571545) during GenVM lint/artifact validation. The current implementation at [`6f228fb8715ed2316c066257bfecede5b8cb3c0e`](https://github.com/BeatyXO/Bermond-/commit/6f228fb8715ed2316c066257bfecede5b8cb3c0e) passed [run 38982038494](https://github.com/BeatyXO/Bermond-/actions/runs/38982038494): frontend and contract-unit jobs both succeeded, including GenVM lint, SDK validation, and Direct Mode tests.
