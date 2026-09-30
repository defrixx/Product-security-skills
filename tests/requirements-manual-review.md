# Requirements change evaluation

Evaluation date: 2026-09-29. Method: manually guided specification walkthrough against synthetic contrasting designs, not execution of a target product or independent agent evaluation. Source snapshot: the skill fingerprints in the accompanying regression run. Outcomes below concern instruction consistency only. Runtime evidence is separately recorded in `requirement-evidence.json` by the regression runner.

## Applicability contrasts (RQ-010)

| Condition | Valid design and observed instruction outcome | Invalid or different design and observed instruction outcome |
| --- | --- | --- |
| SD-CICD-001.C04 | A narrowly required capability is justified in the normal privilege inventory; no exception is demanded merely because it is required. | An unjustified host-control socket violates least privilege; deliberately retaining that violation requires a scoped exception with compensating controls, owner and review date. |
| SD-PY-001 | A closed mutation DTO rejects extra fields; an intentionally extensible contract validates its documented extension namespace. Both are selectable. | An extension cannot assign an unauthorized privilege field. Generic extra-field rejection is not imposed on the approved extensible contract. |
| SD-PY-004 | Exclusive-create rejects existing destinations; authorized replacement checks the selected replacement boundary. | Replacement without authorization or path confinement fails. A legitimate replacement is not falsely failed for overwriting alone. |
| SD-API-001.C02 | A supported GET-only read works without mutation; the mutation route accepts its configured method. | GET cannot invoke a protected mutation; an unsupported method is rejected. The text no longer expects 405 for every GET. |
| SD-CRYPTO-001.C01 | A fixed profile verifies its configured implementation; no new profile selector is required. | A selectable profile rejects unknown/prohibited selections. Fixed configuration does not exempt the actual primitive from verification. |

All five walkthroughs resolve the original contradictory branches. These observations do not measure autonomous control selection.

## Profile semantics (RQ-012)

Reviewed all 12 profile controls against their complete individual condition mappings. Python request contracts map to INPUT C01/AUTHZ C04; response output to SECRET C02 and API C05 for failures, SQL values/dynamic syntax to INPUT C02/C03, file publication to FILES conditions, and diagnostics to SECRET C03/API failures. TypeScript operation/object checks map to authorization/API, browser rendering to WEB, and response versus diagnostic disclosure to SECRET C02 versus C03. Compose listener/database exposure, secret delivery, image build exposure and runtime privilege map to their corresponding API/DATASTORE, SECRET and CICD conditions. Redundant parent lists have been removed.

An unintended stored credential in a successful Python or TypeScript response is now SECRET C02 in both profiles. An authorized issuance response to its intended recipient remains valid; diagnostic disclosure is separately C03. The structural validator rejects mapped IDs absent from the catalog; this semantic walkthrough supplies the applicability assessment that ID existence cannot establish.

## Unexecuted branches at the original requirements review

OAuth/OIDC/JWT exchanges, password enrollment, MongoDB operators, Jinja execution, browser framing/response policies and Next.js cache integrations were source-reviewed but were not executed in this change. Their new conditions have explicit `not_exercised_in_this_run` evidence status (API cache has partial synthetic evidence only). Existing optional integration results are not relabeled as results of this run. New boundary tests deliberately use local HTTP, SQLite and HMAC; injected identities/resolution and omitted production boundaries are listed for each case in [the manifest](requirement_coverage.json).

Primary sources and actual verification dates are in each changed topic; unchanged source dates remain historical. TLS guidance separates RFC implementation/negotiation requirements from the chosen web deployment profile. Terraform feature minimums replace the unsupported inference from a historical version selector. NIST password text was checked through its July 2025 PDF after the HTML endpoint became unavailable.

## Subsequent integration expansion

The original unexecuted status above is historical. Subsequent [optional integrations](integration/README.md) exercise selected Authlib/PyJWT, MongoDB/Jinja, Next.js Data Cache and Chromium CSP/framing clauses. Their separate run reports and [integration manifest](integration/coverage.json) record exact evidence and limitations; they do not change the original run or establish full-condition coverage. Password enrollment and independent agent evaluation remain unexecuted.
