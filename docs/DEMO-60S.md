# MLDoctor 60-second demo (copy-paste)

```bash
.venv/bin/mldoctor serve --port 8765   # copy the printed ?token= URL
```

1. **0:00** — Open the URL. The tour banner offers **Play full demo**: three real
   pipeline runs (repro → diverge → healthy), back to back.
2. **0:15** — Watch the pipeline stations light up: Reproduce → Classify →
   Investigate → Patch → Verify, all from real server events.
3. **0:35** — Open the Reproduce chapter: the before/after overlay shows the
   patched curves against the broken ones; hash glyphs fingerprint each run.
4. **0:45** — Read the plain-language patch story, then **Download patch
   (.patch)** and **Copy share link** in the Proof chapter.
5. **0:55** — Verdict moment: VERIFIED only when the server really verified it.
   A REJECTED patch gets the same drama — failure is a real result here.
