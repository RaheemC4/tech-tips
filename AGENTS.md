# Release completion

After app changes, review `TechLoungeTweaks/README.md` and update affected
behaviour/instructions. Update `RELEASE-NOTES.md`. Review screenshot fixtures
when UI changes; do not pass stale fixtures off as current screenshots.

Using `TechLoungeTweaks/.build-venv/Scripts/python.exe`, run
`tools/release.py --record-doc-review` only after actually reviewing docs, then
`tools/release.py --prepare`. This runs checks, regenerates screenshots, syncs
README copies and rebuilds/verifies the distribution ZIP. Deliver that ZIP.

Keep both BAT workflows working. Do not push without a user request to publish;
preparing scripts or a release does not imply a push. Never run real Windows
activation or edition changes in tests. Do not publish caches, environments,
build output directories, logs or scratch files.
