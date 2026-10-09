# Code review, 9 October 2026

Code Quality Trio's Pstack, Ponytail and Thermo-Nuclear stages were performed
by the same agent. This was a targeted review of startup, hardware caching,
app installation, progress/cancellation, update download/replacement and native
window lifecycle paths. It was not an independent audit of every bundled tool.

## Findings repaired

| Priority | Finding | Repair and evidence |
|---|---|---|
| P1 | All app jobs downloaded into one folder. A completed job deleted other jobs' files, potentially interrupting a concurrent install. | Each job now owns a temporary directory. A two-thread regression holds one installer open while another completes; the first file and an unrelated sentinel survive, and both jobs finish successfully. Failed-job cleanup is also covered. |
| P2 | The Home summary read six hardware sections directly, a second summary read repeated them, then prefetch read the sections again. | Summary reads now use the existing section cache. Tests verify one read per section across the repeated-summary/prefetch sequence and new reads after explicit refresh. |
| P2 | Direct installers wrote to a PIPE that nobody drained while waiting for exit. Sufficient output could block the installer. | Unused output now goes to DEVNULL. A real harmless Python child writes two million characters and exits successfully under a bounded test timeout. |

## Performance evidence

A read-only before/after comparison ran two summary reads followed by all System
Information sections, matching the repeated work in startup. The baseline was
repository commit `659a1fa`; the changed code ran on the same Windows PC.

| Hardware sequence | PowerShell queries | Elapsed time |
|---|---:|---:|
| Before | 31 | 12.56 s |
| After | 11 | 4.36 s |

The resulting hardware summary was identical. Query count is deterministic for
this sequence; timings are one local sample and can benefit from Windows caches.
These numbers do not measure full GUI launch, tweak detection or NVIDIA scans.

## Integration and quality checks

- ConvtPersonal remains a direct, pinned download, available without winget.
  Size and SHA-256 must match before its NSIS `/S` installer can run.
- Matching, truncated and same-length-corrupt payloads, cancellation, existing
  Discord/OpenAsar behaviour, concurrent jobs and refresh behaviour are covered.
- The Apps UI was exercised with the real catalogue: Install dispatch, progress
  completion and Cancel dispatch worked. README screenshots were regenerated
  and the Apps screenshot was visually reviewed.
- The published ConvtPersonal asset was downloaded through the real installer
  code, verified and silently reinstalled on the development PC. Uninstall
  registration and all six engines were present. A real TXT-to-PDF conversion
  passed, with the original preserved.
- The release preparation runs the full Python suites, JavaScript/UI checks,
  native window smoke checks, screenshot generation, executable build and ZIP
  integrity/hash checks. Publication verifies the uploaded ZIP's GitHub digest.

## Limits and further work

The large `main.py` and frontend files remain candidates for gradual separation
by feature when those areas next change. Splitting them now would add regression
risk without a demonstrated runtime improvement. Existing update rendering
already caches unchanged row content; native movement uses window events, so
neither was rewritten speculatively.

Fresh ConvtPersonal installation on a second PC was not tested in this task.
Its installer is unsigned. Review and runtime checks do not establish the safety
of the separately supplied modified Driver Booster or TreeSize binaries.
