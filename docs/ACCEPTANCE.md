# Bermond acceptance status

This matrix distinguishes local validation, browser review, historical Studio Dev receipts, and live verification of the current candidate. A local pass does not establish network consensus, deployed source parity, or settlement.

## Current candidate: local validation

- [x] Audited the standalone contract ABI, storage mutation paths, evidence reads, consensus callbacks, claim/release paths, and frontend transaction flow.
- [x] GenVM lint and SDK semantic validation: `genvm-lint check contracts/bermond.py` passes all three lint checks and validation; schema reports 10 methods (3 views, 7 writes).
- [x] Python compilation passes.
- [x] Fake-runtime and native GenLayer Direct Mode suite: **52 passed** (46 contract/fake-runtime tests and 6 local Direct Mode tests using the pinned GenVM runner bundle).
- [x] Frontend TypeScript typecheck passes; `npm test` passes **7 tests**; production build succeeds.
- [x] Local browser review: registry empty state, proof lab, create flow, unconfigured live-write block, missing-wallet error, mobile-width layout, and keyboard focus progression were observed. No horizontal overflow was visible in the reviewed mobile-width screen.
- [ ] Desktop-width browser review and browser interaction with an injected wallet were not completed; the in-app browser had no wallet provider. Wallet state transitions are covered by local frontend tests, not by an injected-wallet session.
- [ ] Production bundle size warning remains: main JavaScript chunk is about 887 kB before gzip (about 217 kB gzip).

The Direct Mode suite executes the contract through the local GenVM harness. It is not Studio validator consensus or evidence of live transfers. Browser review used the local development server; the configured live registry was empty because no current candidate address is published.

## Historical Studio Dev evidence

The preserved deployment at `0x8A5cb514A6b8Eae009cB896F0EcAC2F208d954F9` was finalized on chain `61997` by transaction `0x0a37753101ddc15e274c3dbe0e744dc5c2138575dfb4006a21df43c1df82a8af`. Its historical source SHA-256 is `e1987c6d5b2cff228025e5be8d20d570cd436e05f797569b66020906f0cc1554`, and that source was byte-matched to the deployed code at the time. It is not the current candidate.

The manifest retains historical finalized claim and expiry-release receipts. Those receipts show successful contract execution and outgoing message records, including a 1 GEN beneficiary claim and 1 GEN provider release. They do not prove recipient balance deltas, current candidate behavior, or on-chain replay rejection. Historical post-write reads were blocked by the Studio `gen_call` error.

## Current candidate: network and release gates

- [ ] Candidate source SHA-256 `94f4c585126a8d99348ffcca478b8dd4a157aaf2ca93c84d6a8864585493ac5a` has not been deployed; there is no current source-matched address, deployment transaction, or candidate schema receipt.
- [ ] Read-only `get_bond_ids` calls at `LATEST_FINAL` against both preserved Studio Dev contracts returned the same server-side SQLAlchemy error: `Can't reconnect until invalid transaction is rolled back`. This establishes a shared read-service failure for these probes, not its full network-wide scope.
- [ ] No candidate lifecycle writes were attempted. A fresh deployment and economic tests were withheld while finalized-state reads and fee estimation are unhealthy.
- [ ] Studio documentation and existing receipts support outgoing EOA messages, but no authoritative balance delta or failure/recovery semantics were demonstrated for the current source. The contract conservatively records outgoing amounts in `pending_wei`; the candidate has no settlement reconciliation path. This is a production blocker.
- [ ] Publisher identity and historical authority of baseline documents remain provider-declared, not independently authenticated. Final URL/redirect behavior for the pinned web transport is not verified.
- [ ] Permissionless policy checks require a caller to submit a transaction; there is no autonomous observer or keeper.
- [ ] Independent security review, fuzzing, Studio consensus disagreement/timeout tests, and economic lifecycle tests for the current source remain outstanding.

The project is **not ready for production or a new economic deployment**. All preserved historical transaction records remain in [`../deployments/studio-dev.json`](../deployments/studio-dev.json); no new receipt has been added or inferred.

## CI evidence

The latest workflow for the starting remote commit `b20e3ddaf6da14196b53e3f88133e35cb3ac4186` was [run 38549571545](https://github.com/BeatyXO/Bermond-/actions/runs/38549571545): frontend passed, while the contract job failed at GenVM lint/artifact validation and skipped tests. The candidate workflow uses the compatible pinned RC tool family, official runner-artifact preparation, and a contract test step that still runs after an earlier failure. Candidate commit [`c6c116b5abd16bdd962d0bd88ea8ef65698ddfa8`](https://github.com/BeatyXO/Bermond-/commit/c6c116b5abd16bdd962d0bd88ea8ef65698ddfa8) passed [GitHub Actions run 38644855655](https://github.com/BeatyXO/Bermond-/actions/runs/38644855655): frontend and contract jobs succeeded, including GenVM lint, SDK validation, official runner preparation, and all 52 tests.
