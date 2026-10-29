# MLDoctor patch: leakage.py

Mode: MOCK (simulated)
Symptom: leakage
Hypothesis: duplicated rows land on both sides of train/test split — deduplicate rows before the train/test split
Verification: FAIL — masking: leakage masking (dedup after split)

Applied by hand only; never pushed automatically.
