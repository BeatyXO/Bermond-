# Bermond security and failure model

| Threat | Implemented defense | Remaining exposure |
|---|---|---|
| Prompt injection in policy text | Evidence is declared untrusted; each resolved clause must cite an exact bounded excerpt and matching source SHA-256; validators independently fetch and classify; contract controls all amounts and recipients | Model may still misclassify or validators may collude. Agreement reduces, but cannot eliminate, semantic error |
| Baseline content replacement | Mandatory provider-self-attested SHA-256 commitment; validators re-fetch and verify exact source bytes; findings bind their excerpt to source digest | Hash alone does not establish issuer authority or historical existence. Both remain explicitly unverified |
| Publisher and evidence provenance | Contract records the assurance level as provider self-attestation; UI states current publisher authentication and historical authenticity are unverified | No decentralized publisher-signature or trusted archive proof is available in this release; do not market the sources as authenticated |
| Source unavailable | Deterministic `UNRESOLVED` assessment; cannot authorize payout | If unavailable to validators, consensus can fail before contract state commits |
| Provider unilaterally removes subscribers | Subscribers only enrolled during `DRAFT`, frozen on exact funding | Provider chooses original beneficiaries; may register unrelated wallets |
| Replay/double payout | `claimed` wallet list, state update before transfer, explicit reserve reduction | Verify native-transfer implementation on Studio and network |
| Provider drains reserve while claims pending | No release until after frozen claim deadline | After deadline all unpaid claims expire |
| Underfunded escrow | Exact payable amount required, reserve per bond | Audit global balance liabilities after fee accounting |
| Unlimited input/CPU | Document, clause, ID, URL, bond and subscriber bounds | Need runtime gas and storage profiling |
| Wrong chain/contract | Frontend Studio Dev pin + empty address fails closed | Verify deployment source hash, contract address, SDK version |
| Rejected consensus | Validator agreement includes per-dimension status, witness source, exact normalized excerpt, and full SHA-256 of the cited baseline/current document; disagreement cannot authorize a breach | Real network may leave transaction undetermined; cannot force `UNRESOLVED` receipt. Studio's current read endpoint prevents independent verification of the finalized policy verdict |
| Claim after coverage closes | Claim deadline enforced with transaction-pinned timestamp | Long delay, clock semantics on target GenVM need verification |
| Arbitrary external links | Validated HTTPS URL and bounded fetch | DNS rebinding, redirects, web renderer trust require live tests |

## Launch blocking items

1. Run `genvm-lint check`, `validate`, `schema`, `typecheck` against the actual deployed SDK/GenVM runtime. Fix type/import/decorator discrepancies; no mocks or compatibility tricks in production.
2. Run native GenLayer Direct Mode and Studio integration tests for all state transitions, validator dissent, missing source, reentrancy risk, transfer finality, timestamp expiry and disputed decisions.
3. Verify auth/provenance of the baseline archive independently of hash value. External HTTPS source does not equal issuer signature.
4. Confirm numerical safety with 12 beneficiaries at maximum payout and fuzzing.
5. Verify strict separation of preview fixtures from actual contract data, and all required wallet actions in public browser.
6. Document real finalized receipt hashes and release a source-matched deployment manifest.
7. Publish an explicit operational model for policy-check scheduling; onchain code does **not** autonomously execute itself.
