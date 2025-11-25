# Match Quality Score Thresholds

## Updated Ranges (Calibrated for Vector Search)

The match quality badges in AI suggestions are now calculated using the following thresholds, calibrated for typical vector search similarity scores:

### Score Ranges:
- **Excellent**: Score ≥ 0.010 (1.0%+)
- **Strong**: Score ≥ 0.006 (0.6%+)
- **Good**: Score ≥ 0.003 (0.3%+)
- **Weak**: Score < 0.003 (< 0.3%)

### Previous Ranges (Too High):
- Excellent: ≥ 0.040 (4.0%+)
- Strong: ≥ 0.025 (2.5%+)
- Good: ≥ 0.015 (1.5%+)
- Weak: < 0.015

## Why the Change?

Vector search similarity scores from Databricks Vector Search are typically very small decimal numbers (0.001 to 0.02 range), not 0-100 percentages. The previous thresholds were too high, causing nearly all matches to be classified as "Weak" even when they were semantically strong matches.

## Implementation Details

The match quality calculation is **deterministic** and based purely on the `search_score` from the vector search results. It is **not** affected by the LLM's reasoning text. This ensures consistency - the badge always accurately reflects the similarity score.

### Location:
`backend/services/ai_mapping_service_v2.py` - Lines 400-407, 417-427, 482-489

### Logic:
```python
if score >= 0.010:
    match_quality = 'Excellent'
elif score >= 0.006:
    match_quality = 'Strong'
elif score >= 0.003:
    match_quality = 'Good'
else:
    match_quality = 'Weak'
```

## Frontend Display

The match quality is shown as color-coded badges in the AI Suggestions dialog:
- **Excellent**: Green badge
- **Strong**: Blue badge
- **Good**: Gray badge
- **Weak**: Orange badge

Results are sorted first by match quality (Excellent > Strong > Good > Weak), then by score within each tier.

