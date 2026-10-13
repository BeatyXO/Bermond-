# Handoff: work completed and unverified

## Implemented in this handoff

- 448-line standalone Python GenLayer Intelligent Contract in `contracts/bermond.py` (line count may change)
- local isolated fake-runtime tests covering 20 lifecycle/security cases; command: `python -m pytest -q tests`
- complete responsive React/Vite frontend with black / electric yellow Comic Sans typography, tailored illustrated paper-bond hero, four fictional proof cases, clause comparator, real (read-only) registry, create form, exact payable funding, provider enrollment, policy checking, eligible beneficiary claims and expired reserve release
- explicit source-level threat model, protocol state machine, acceptance criteria, CI workflow

## Critical work Codex must execute on a networked machine

1. Run and fix frontend install/build. This environment could not reach npm registry; do not mark it tested here.
2. Run native `genvm-lint` and Direct Mode with actual latest target SDK (rather than only fake Python tests), resolving any runtime API mismatches. Pin versions.
3. Run E2E contract execution and integration on Studio Dev. Verify consensus failure behavior and external GEN transfers.
4. Validate source-authentication and dynamic rendering under live Web Render.
5. Decide whether extra provenance witnesses/archiving are essential for reviewer claims; add without pretending hashed content authenticates publishers.
6. Add or harden actual live proof fixtures + deployed transaction receipt manifest. No dummy hashes or fabricated state.
7. Fix frontend wallet provider errors and optionally add wallet-app messaging and transaction-resume handling.
8. Deploy frontend to public HTTPS only after address and release verified. Public proof routes should transparently distinguish simulated fixtures from live consensus.
9. Push final commits to exactly `https://github.com/BeatyXO/Bermond-.git`, no destructive force push.

The reviewer score is not predictable. Distinguish implemented, mocked-tested, Studio-tested, chain-finalized and production-ready statements in docs and UI.