# V2.4.1 Independent Visual–Speech Alignment Verifier

Act as a strict reviewer who did not create the first-pass mapping. Re-open the original slide previews, region manifest, narration phrases, and timing JSON.

For every proposed matched phrase:
1. Confirm the slide number and phrase text are exact.
2. Confirm each region ID exists on the same slide and its bbox actually encloses the intended object.
3. Confirm the spoken phrase genuinely refers to that object, not merely a nearby or similarly named object.
4. Check whether the phrase should map to multiple regions, one region, or no region.
5. Verify each quoted evidence span appears verbatim in its source.
6. Reject stale, ambiguous, oversized, duplicated, or semantically weak regions.
7. Do not repair missing geometry by guessing.

Return the same JSON schema as the planner, changing status to review_required or unmatched whenever the mapping is uncertain. Use a distinct reviewer_pass value for this pass. Never increase confidence without a source-grounded reason. Do not invent region IDs, phrases, timestamps, hashes, or visual facts.
