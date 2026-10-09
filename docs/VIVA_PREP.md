# Viva Questions & Answers

1. **Why use deterministic validation instead of just asking the LLM if it's correct?**
   *Answer:* LLMs are prone to hallucinations. They might confidently generate invalid YAML or expose sensitive ports. Deterministic validation (like running `docker build` or `trivy`) ensures actual correctness, which is critical for infrastructure.

2. **How does the AI Self-Correction loop work?**
   *Answer:* If validation fails, the exact error logs (e.g., mismatched ports) are fed back to the LLM as a repair prompt. The LLM generates a fix, and the validation runs again. This repeats up to 3 times to prevent infinite loops.

3. **How is the Readiness Score calculated?**
   *Answer:* It's a formula-based score starting at 100. It deducts points for validation failures, critical security findings, and suboptimal performance configs. It is entirely deterministic, avoiding LLM bias.
