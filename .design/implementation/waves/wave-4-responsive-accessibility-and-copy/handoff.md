# wave-4-responsive-accessibility-and-copy handoff

Status: complete
Wave number: 4

## Changed files

- `.design/quality/benchmark-2-feedback-and-friction-ledger.md`: changed; SHA-256 `eea9de79f4e56dcaf565c4581f44a00346605fb456069bbac713a1beddf0de83`. Records product feedback, observable build problems, completed repairs, evidence locators, and reusable workflow improvements while excluding private identities, local paths, credentials, prompts, private repository details, and internal fixtures.
- `.design/quality/wave-4-browser-accessibility.json`: changed; SHA-256 `ddff2cc0acc13ada167408c152256706022b14922362887e47ec492c541ea0ed`. Binds the final product hashes to 21 target scans, route smoke, keyboard flows, six responsive widths, contrast, touch targets, 200 percent zoom, WCAG text spacing, reduced motion, announcements, and focus restoration.
- `site/app.js`: changed; SHA-256 `cc4fac7ee7c5432467f0efebc27930871c789e06c9e4362f683aa7b799a64f14`. Implements exact catalog, case, package, comparison, and Method routes; controlled async recovery copy; live alerts; direct comparison hydration; keyboard focus preservation; package retry focus; and loopback-only diagnostic boundaries.
- `site/index.html`: changed; SHA-256 `3f178ebcfe0a61980fac86d1ad7d11eb3f9438c153ad7981bf8cbf72dbd0cdb1`. Provides the exact Method anchor, catalog recovery action, clear evidence-status copy, a case-record package description, a side-by-side comparison explanation, and the same complete information and actions at every planned screen.
- `site/styles.css`: changed; SHA-256 `a73c66965fc743f09f30dff05a1fde13e35b405ac057a84a6cbb4752324fafe1`. Recomposes filters, navigation, selection, and file details without page overflow; retains one labeled comparison scroll region; enforces 44 pixel primary controls; supports text spacing and reduced motion; and repairs functional-boundary and privacy-band contrast.
- `tests/test_wave11_site.py`: changed; SHA-256 `afbb812befc4ed325c192ea19306b36863c2d15002b7f9a4c1808c1a2bfd508c`. Adds regression checks for exact route hydration, catalog states, one-scroll-region composition, 44 pixel targets, announced errors, controlled reader copy, queued focus restoration, text-spacing wrapping, dynamic-control focus, and high-contrast privacy copy.

## Completed checks

- Run automated accessibility checks against every required target and record findings without treating the scanner as full acceptance.: pass. All 21 targets passed duplicate-ID, accessible-name, form-label, ARIA-reference, heading-order, hidden-focusable, dialog-label, console, and root-overflow checks. The receipt states that the scanner supports rather than replaces manual and rendered acceptance.
- Complete keyboard-only search, filtering, case detail, evidence tabs or sections, comparison, package selection, download, retry, return, and dialog close flows.: pass. Search, lane filtering, native Platform selection, case entry, package entry, verified download, two-case comparison, persistent and successful retry, return actions, Escape, close, and exact focus restoration all passed.
- Measure root overflow, bounded comparison overflow, primary touch targets, focus visibility, and content retention at 390, 600, 834, 960, 1280, and 1440 CSS pixels.: pass. The document root had no horizontal overflow at any width. Primary mobile controls met 44 by 44 CSS pixels. The labeled comparison region was the sole horizontal scroller at 390, 600, and 834 pixels and fit without scrolling at wider targets.
- Inspect 200 percent zoom, text-spacing overrides, reduced-motion mode, loading announcements, error announcements, and focus restoration.: pass. All five screens retained their information and actions at 200 percent scale, WCAG text spacing, and reduced motion. No root overflow remained. Loading and errors were announced, focus returned to the correct control, and the repaired privacy paragraph measured 14.2 to 1 contrast.

## Render targets

- catalog-default-wide: pass. At 1440 by 1000, all 60 public cases, search, six lanes, six facets, sort, evidence boundary, and Method link rendered with zero root overflow.
- catalog-default-mobile: pass. At 390 by 844, catalog controls reflowed without hiding information, primary targets met 44 pixels, and the root did not overflow.
- catalog-default-tablet: pass. At 834 by 1112, catalog rows, filters, result status, and public boundary remained complete with zero root overflow.
- catalog-empty-mobile: pass. The exact no-match query preserved controls, named the empty state, and exposed Show all public cases without overflow.
- catalog-loading-mobile: pass. The exact loading route exposed four loading rows, role status, polite live text, aria-busy true, and all catalog context without overflow.
- catalog-error-wide: pass. The exact failure route removed case actions, set aria-busy false, announced controlled reader-safe copy, and exposed Retry public catalog.
- case-default-wide: pass. IBM Carbon opened with source context, analysis, evidence, limits, local navigation, package action, correct dialog entry focus, and zero overflow.
- case-default-tablet: pass. IBM Carbon retained all case sections, evidence, actions, and focus behavior at 834 by 1112 with zero root overflow.
- case-loading-mobile: pass. The exact loading route retained case identity, announced validation, and exposed Return to catalog at 390 by 844.
- case-error-mobile: pass. The exact missing-case route announced an alert, named the unavailable request, exposed Retry and Return to catalog, and exposed no package file.
- package-default-wide: pass. The exact package route retained context, contents, evidence boundary, provenance, limitations, exact files, verification, and two enabled downloads after validation.
- package-default-mobile: pass. The full package contract and both format choices remained readable at 390 by 844; file details stacked without a second horizontal scroller.
- package-default-tablet: pass. The full package contract, exact file table, and download actions fit at 834 by 1112 without page overflow.
- package-error-mobile: pass. The exact failure route kept package context, announced the blocked validation, exposed retry and return, disabled both files, and restored focus after retry.
- package-denied-wide: pass. The loopback-only sentinel exposed no private case, source, provenance, file, Blob, or download attribute and provided only Return to catalog.
- comparison-default-wide: pass. The exact direct route opened IBM Carbon and Vercel Geist side by side with one column per case and no horizontal scroll at 1440 pixels.
- comparison-default-mobile: pass. At 390 pixels, the comparison stayed concurrently inspectable through one labeled, keyboard-reachable 356 by 760 scroll region and no root overflow.
- comparison-default-tablet: pass. At 834 pixels, the comparison stayed in one labeled bounded region, retained open-case actions, and did not overflow the document root.
- method-default-wide: pass. The exact #method route reached truth classes, originality boundary, package use, and privacy boundary with repaired contrast and no overflow.
- method-default-mobile: pass. At 390 pixels, all Method definitions and the privacy boundary remained readable under default and WCAG text spacing with zero root overflow.
- method-default-tablet: pass. At 834 pixels, all Method content, headings, and boundaries remained in reading order with zero root overflow.

## Completion criteria

- Every required quality target renders with all approved information and actions present.: pass. The final-hash route matrix and automated scan passed all 21 exact targets with no missing target, console error, root-overflow failure, or removed information or action.
- Keyboard, focus, semantic, contrast, resize, reduced-motion, touch-target, and overflow checks have no unresolved blocking findings.: pass. The final receipt closes the native-select, lane-focus, retry-focus, text-spacing, and privacy-contrast findings and records complete PASS evidence for every named category.
- Comparison is concurrently inspectable at wide widths and uses one labeled bounded scroll region at narrow widths.: pass. Comparison fits without horizontal scrolling at 960 pixels and above and uses only the labeled, tabindex-zero comparison region at 390, 600, and 834 pixels.
- Copy identifies exact states and recovery actions without unsupported quality or completion claims.: pass. Controlled catalog, case, package, comparison, Method, retry, and download-request copy passed the final Unslop and public-safety review with no unsupported claim or private leakage.

## Review results

- independent-verifier by wave11_gate_verifier: pass. Verified all fixed hashes, 44 focused tests, 287 full tests on both supported Python versions, exact scope, all 21 targets, five-screen resize and motion evidence, keyboard flows, contrast, direction fidelity, and the Wave 5 token-source prerequisite.
- specialist by codex_install_verifier: pass. Produced and validated the final browser receipt, including 21 automated scans, 21 route smokes, computed contrast, six widths, all-five-screen zoom, text spacing, reduced motion, native keyboard selection, recovery focus, and zero unresolved blockers.
- unslop-reviewer by claude_install_verifier: pass. Verified all fixed hashes, closed the prior vague ledger phrases, passed interface and recovery copy, confirmed the feedback ledger is concrete and useful, and found no private leakage, unsupported completion claim, yellow cast, or remaining public-safety blocker.

## Known deviations

- The user-approved cool-neutral Site palette remains intentionally different from the earlier warm values in .design/system/tokens.source.json. The token source must be added to Wave 5's approved file scope and reconciled before Wave 5 acceptance without restoring the rejected yellow cast.

## New risks

- If Wave 5 updates the durable token source without checking the rendered Site, it could reintroduce the rejected warm palette or weaken the contrast values proved in this wave.
- Public deployment after Wave 5 must prove that loopback-only diagnostic states and the private sentinel remain inert on the public host and that anonymous visitors can load cases and download both formats.

## Next inputs

- Before preparing Wave 5, add .design/system/tokens.source.json to Wave 5's approved file scope through a recorded plan amendment based on the user's explicit neutral-palette correction.
- Reconcile the durable token source to the final cool-neutral CSS values, then validate token compilation and contrast without restoring the earlier warm yellow treatment.
- Use the final Wave 4 browser receipt and feedback ledger as Wave 5 acceptance inputs. Preserve the public-safe boundary and exact final hashes.
- Complete Wave 5 before publishing. After Wave 5 passes all three independent reviews, publish under the user's explicit approval and verify anonymous access, public-host diagnostic inertness, 60 public cases, and both download formats.

## Rollback notes

- If a Wave 5 token-source change alters the accepted rendering, restore the final Wave 4 neutral values and reopen only the token-parity work.
- If a Wave 5 integration check fails, preserve this complete Wave 4 boundary and repair only the owning corpus, package, Site, copy, or evidence artifact before requesting new reviews.

Ended at: 2026-09-02T03:19:09Z
