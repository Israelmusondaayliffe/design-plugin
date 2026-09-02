# wave-3-download-behavior-and-recovery handoff

Status: complete
Wave number: 3

## Changed files

- `site/README.md`: changed; SHA-256 `33c3a590e3f197a81648ba2838674891fa2e518fe5d1daaaf6f7f7a71963554f`. Documents exact-byte browser validation, all loopback-only recovery hooks, the original approved render routes, the non-public sentinel boundary, local verification commands, and the separate publication gate.
- `site/app.js`: changed; SHA-256 `080bfc42fc7ee74fb8ff8ef56d578ceb590adbc74edc7978de83a8d1ef4eb0d7`. Fails closed on malformed manifests and unsafe files, verifies byte counts and SHA-256 before creating Blob URLs, preserves stable filenames, supplies exact loading and recovery states, and keeps approved route aliases loopback-only.
- `site/index.html`: changed; SHA-256 `ad69f9635e9937254b450e414c26460c51ce71d257976d1b7843c0fa5d63a2c5`. Keeps both downloads disabled by default, adds package retry and return controls, gives the case-loading state a visible catalog escape, and cache-busts the repaired Wave 3 assets.
- `site/styles.css`: changed; SHA-256 `c3d96405a2cdc2431de0cb49d7d6b283a4b4196844a9041a7c741cc2aa714238`. Applies the user-approved visual correction: cool neutral surfaces, graphite text, restrained rust and teal, squared status labels, tighter display type, and readable recovery layouts without page-level overflow.
- `tests/test_wave11_site.py`: changed; SHA-256 `37b99a1da080f55e79de40cd5eb155126e93d4c1e93d9a5c747016ff8b553d64`. Adds five Wave 3 tests for all 120 manifest-bound browser sources, verified-byte Blob delivery, fail-closed manifest handling, bounded recovery hooks, and exact approved quality-target route compatibility.

## Completed checks

- Test valid readable and structured downloads for a representative case and verify filename, media type, byte count, and SHA-256 against the manifest.: pass. All 120 generated files matched their manifests. The browser downloaded ibm-carbon-design-reference.md at 9,189 bytes with SHA-256 1ca2e4d928ec4709d76037d2e8a239ee66fe63d57222860dd05562b973215a41 and ibm-carbon-design-reference.json at 10,533 bytes with SHA-256 ad7448dc40708e2d0904db9d4820441bde74ee0a59c3941e59c55d61d4a6e9ed.
- Test missing files, invalid manifests, failed validation, unavailable cases, non-public cases, network failure, and browser download failure without clearing context.: pass. JavaScript syntax and all 39 focused tests passed. All 282 full tests passed on Python 3.9.6 and all 282 passed on Python 3.12.13 after the approved-route repair.
- Test that readable and structured package views expose the same normalized claims, evidence IDs, provenance, limitations, and unknowns.: pass. All 60 Markdown semantic traces matched normalized JSON leaf bindings, and mutation tests rejected missing, changed, extra, and incorrect bindings.
- Inspect every named failure target for exact case, format, problem, and recovery copy.: pass. All six exact approved routes rendered the named state with zero page or dialog overflow. Scope stayed inside five allowed files. Index and README passed the writing gate; the app finding on item.journey is structured field access, not human-facing prose.

## Render targets

- case-loading-mobile: pass. At 390 by 844, IBM Carbon retained its title, source context, preview, local navigation, an explicit validation message, and a visible Return to catalog action with zero overflow.
- case-error-mobile: pass. The exact missing-case route named the requested case, explained that it was missing, non-public, invalid, or unavailable, exposed Retry and Return to catalog, and exposed no package or file.
- package-default-wide: pass. At the exact #download-package route and 1440 by 1000, the validated IBM Carbon package opened directly with two manifest-matched Blob links and zero page or dialog overflow.
- package-default-mobile: pass. At the exact #download-package route and 390 by 844, the complete package contract remained readable and both links enabled only after filename, byte count, and SHA-256 verification.
- package-error-mobile: pass. The exact download-error route retained IBM Carbon and the affected format, named the SHA-256 mismatch, exposed Retry and Return to case, and left both file links inert.
- package-denied-wide: pass. The exact private-test-case route rendered a loopback-only permission boundary with no case-package request, source, provenance, file, Blob URL, download attribute, or retry action; Return to catalog restored search focus.

## Completion criteria

- Both formats download successfully for all 60 validated public cases and match their manifests.: pass. All 60 public cases contain one readable and one structured file with exact generator, route, filename, media-type, model-binding, byte-count, and SHA-256 parity. Representative real browser downloads matched exactly.
- No action can generate or expose a file for a non-public, invalid, missing, or failed package.: pass. Generator rejection tests, browser failures, unavailable cases, the exact permission sentinel, and invalid package paths all failed closed with inert links and no download attribute or private request.
- Every required loading and failure target retains case context and exposes a specific next action.: pass. All six approved targets named the case or package, described the current condition or problem, and offered an exact Retry, Return to case, or Return to catalog action.
- Tests prove semantic parity from the shared normalized model rather than from matching file counts.: pass. All 60 Markdown semantic traces matched normalized JSON leaf bindings, and mutation tests rejected missing, changed, extra, and incorrect bindings.

## Review results

- independent-verifier by wave11_gate_verifier: pass. Found the initial approved-route mismatch, then verified the repair across all six exact routes, zero overflow, scope fidelity, no private request or file exposure, and the required token-source and feedback-ledger obligations.
- specialist by codex_install_verifier: pass. Independently passed all 13 final hashes, syntax, manifest, scope, 39 focused and 282 full tests on both Python versions; verified all 60 packages, exact route behavior, no private sentinel fetch, and inert failure downloads.
- unslop-reviewer by claude_install_verifier: pass. Confirmed supported and plain public copy, exact permission-boundary language, no private leakage, no true style violations, no yellow cast or pill-heavy concept styling, and a safely bounded future ledger contract.

## Known deviations

- The user rejected the earlier yellow cast and AI concept-page feel. Wave 3 therefore uses a user-approved cool-neutral CSS palette, squared status labels, and tighter display typography while the frozen token source still records the earlier warm values. Preserve the corrected interface and reconcile the durable token source before Wave 5 acceptance.

## New risks

- A public feedback and friction ledger could leak private harness, account, identity, repository, fixture, log, URL, or credential details unless it is built from an explicit public allowlist.
- Future public hosting must keep all diagnostic states and the private-test-case sentinel inert outside the exact loopback host allowlist, then prove that behavior from the deployed anonymous route.

## Next inputs

- Prepare Wave 4 only from this verified handoff and the unchanged approved implementation plan.
- Before Wave 5 acceptance, reconcile the user-approved neutral interface into the durable design token source without restoring the rejected warm palette.
- Before Wave 5 acceptance, create a public-safe feedback and friction ledger. Record the user request for context, intent, value, quality, verified writing, a less AI-like neutral interface, and post-Wave-5 public publication. Record the repaired missing loading escape, approved-route drift, browser download-event timeout, and exact-byte filesystem proof. Include only public route, task, observable symptom, category, severity, status, and public evidence locator; exclude all private harness, account, identity, repository, fixture, log, private locator, and credential details.
- Do not publish before Wave 5 completion. After Wave 5 passes its independent reviews, publish the Site under the user's explicit approval and verify anonymous production access.

## Rollback notes

- Remove only the Wave 3 validation, Blob-delivery, recovery, route-alias, and loading-exit changes through a scoped patch while preserving the Wave 1 package generator and Wave 2 information structure.
- If the visual correction must be rolled back for diagnosis, preserve the current neutral values in evidence first and restore them after the diagnostic; do not reinstate the rejected yellow cast as the default.

Ended at: 2026-09-02T02:19:19Z
