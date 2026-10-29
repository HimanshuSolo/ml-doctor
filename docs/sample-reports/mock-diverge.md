# MLDoctor patch: diverge.py

Mode: MOCK (simulated)
Symptom: diverged
Hypothesis: LR = 5.0 with raw 0-16 pixel values, no normalization — lower LR to 0.05 and StandardScaler-normalize inputs
Verification: PASS — finite, sane losses on all seeds

Applied by hand only; never pushed automatically.
