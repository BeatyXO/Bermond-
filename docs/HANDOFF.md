# Handoff status

## Implemented in this workspace

- Standalone GenLayer contract retains the required public ABI, exact collateral accounting, fixed four-clause semantics, independent leader/validator classification, single-claim accounting and expired-reserve release.
- Fake-runtime tests cover core security and lifecycle behavior, including multiple-bond reserve separation and the 12-subscriber limit.
- Native Direct Mode tests are present for persistent state, frozen enrollment, exact payable funding, mocked web rendering and validator dissent. They have not completed on this host.
- Frontend retains its black/yellow Comic Sans editorial design and adds contract-bound date checks plus a stored transaction hash and explicit finality-resume flow.
- CI installs pinned GenLayer test/lint tools, runs static contract lint and the pytest suite, and uses `npm ci` for frontend checks.
- `deployments/studio-dev.json` records only verified environment metadata and pending release fields; it contains no fabricated deployment or transaction data.

## Verification still required

1. Run `python -m pytest -q tests` after this handoff, then run the Direct Mode tests with the contract's pinned SDK artifact available.
2. Complete `genvm-lint validate`, `schema` and `typecheck` against the declared SDK dependency.
3. Install frontend dependencies from npm, generate and commit `frontend/package-lock.json`, then pass typecheck, build and frontend tests. The current host has no usable npm registry connection.
4. Run Studio consensus/web-render tests. Verify transaction-pinned dates, nested state encoding, validator disagreement and the real network behavior of consensus rejection.
5. Deploy and prove exact GEN transfer settlement on a network that supports external EVM messages. Studio alone cannot verify the EOA transfer implementation.
6. Populate the deployment manifest only from authoritative finalized reads, matching source bytes and actual transaction receipts.
7. Publish the site and push reviewed commits only after repository identity, remote history and deployment/release evidence are verified.

There is no Git metadata in the extracted folder, so this checkout has no local history or configured remote to reconcile. The source prompt asks for a specific GitHub destination, but this workspace has not yet verified that repository or its default branch. Do not claim a push, commit, deployment, published URL, validator execution, receipt or audit until observed directly.
