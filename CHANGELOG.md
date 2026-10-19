# Changelog

## 0.2.0 (published 2026-10-19)

First published edition, released at the owner's request after the final reviewed runtime correction.
An existing non-symlink `current` is rejected under the target lock before release/state creation,
backup or migration; activation retains its final guard. Real file/directory regressions preserve
existing data and invoke no mutation commands; subsequent delivery through an owned symlink still
succeeds. This corrects the implementation of the existing contract and adds verification bindings;
it introduces no further normative obligation or edition increment within the unpublished draft.

Public jobs on Linux, Windows and macOS now exclusively use compatible standard GitHub-hosted
runners. This removes a permitted public Blacksmith route and therefore increments the normative
minor edition under STD-0000 R-0012. Private execution and the zero-additional-spend contract remain.

The implementation validates complete native deployment inputs and selected payloads before any
backup/migration/activation, terminates remaining owned descendants after timeout/cancellation, and
uses Android SDK apkanalyzer/bundletool for APK/AAB validation. Signing and store submission remain
separate. An optional SSH transport transfers the exact verified artifact and canonical runtime,
then executes the native adapter and shared target lock on the remote host. Pinned host keys,
concurrent callers and partial recovery are covered against an isolated SSH server.
Optional public security, native verified-payload release/SBOM/signature, OCI archive publication,
web/browser/accessibility and bounded native fuzz/mutation/benchmark capabilities restore useful
archived behavior through the shared implementation. Recursive checkout identities are checked before
and after validation. Regression and native fixture outcomes are recorded by the actual PR jobs.

## 0.1.0 (draft)

Initial owner-directed combined CI/CD contract, with modular execution, PR-only source validation,
zero-additional-spend routing, architecture/documentation feedback and artifact delivery.
Shared native CI/reporting, admission, artifact, cache and typed delivery operations now back composite actions. Native fixtures and bounded pilot integration are tracked separately from normative acceptance.
The publication license is the existing explicit NDDev AGPL-3.0-only template choice.

Finite native SDK/profile fixtures and isolated native delivery targets now execute positive/failure
scenarios. Partial verification bindings name their actual targets and leave account policy, authority,
prose truth and unselected hardware as review. The integration remains draft pending owner acceptance.
