# AI Mapping Approach Comparison

## Problem Statement

We need to map source columns to target columns where:

| Challenge | Description |
|-----------|-------------|
| **Different Names** | Source table/column names are completely different from target names |
| **Similar Descriptions** | Column descriptions ARE similar and can be used for matching |
| **Need Historical Learning** | Must detect transformations (TRIM, UPPER), single vs multi-field, joins vs unions from past mappings |
| **Avoid Past Mistakes** | Should not repeat previously rejected mappings |

**Example:**
```
Source: patient_data.mbr_ssn_num (Description: "Social security number of the patient")
Target: Member.SSN (Description: "Member social security number")

Names don't match, but descriptions are semantically similar!
```

---

## Approach 1: Sequential (Target-First)

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    APPROACH 1: SEQUENTIAL (TARGET-FIRST)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   SOURCE FIELDS                                                             │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │ • patient_data.mbr_ssn_num                                  │          │
│   │ • Description: "Social security number of the patient"      │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │  STEP 1: VECTOR SEARCH SEMANTIC_FIELDS                      │          │
│   │  ──────────────────────────────────────────────────         │          │
│   │  Query: Source description → Target semantic_field          │          │
│   │  Index: semantic_fields.semantic_field                      │          │
│   │                                                             │          │
│   │  Results:                                                   │          │
│   │  ┌───────────────────────────────────────────────────┐     │          │
│   │  │ 1. Member.SSN (0.94)                              │     │          │
│   │  │ 2. Member.Tax_ID (0.78)                           │     │          │
│   │  │ 3. Provider.Provider_SSN (0.65)                   │     │          │
│   │  └───────────────────────────────────────────────────┘     │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │  STEP 2: LOOKUP HISTORICAL PATTERNS (by Target Column)      │          │
│   │  ──────────────────────────────────────────────────         │          │
│   │  Query: WHERE tgt_column_name = 'SSN'                       │          │
│   │  Table: mapping_patterns (EXACT MATCH on target)            │          │
│   │                                                             │          │
│   │  Results:                                                   │          │
│   │  ┌───────────────────────────────────────────────────┐     │          │
│   │  │ • ssn_field → SSN (TRIM, REMOVE_DASHES) x 12     │     │          │
│   │  │ • social_sec → SSN (TRIM) x 8                    │     │          │
│   │  └───────────────────────────────────────────────────┘     │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │  STEP 3: LOOKUP REJECTIONS (by Target Column)               │          │
│   │  ──────────────────────────────────────────────────         │          │
│   │  Query: WHERE suggested_tgt_column = 'SSN'                  │          │
│   │         AND feedback_action = 'REJECTED'                    │          │
│   │  Table: mapping_feedback (EXACT MATCH on target)            │          │
│   │                                                             │          │
│   │  Results:                                                   │          │
│   │  ┌───────────────────────────────────────────────────┐     │          │
│   │  │ • member_id → SSN (REJECTED: "Not an SSN field") │     │          │
│   │  └───────────────────────────────────────────────────┘     │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │  STEP 4: LLM ANALYSIS                                       │          │
│   │  ──────────────────────────────────────────────────         │          │
│   │  Input:                                                     │          │
│   │  • Source field + description                               │          │
│   │  • Top target matches (from vector search)                  │          │
│   │  • Historical patterns (for those specific targets)         │          │
│   │  • Rejections (for those specific targets)                  │          │
│   │                                                             │          │
│   │  Output: Ranked recommendations with transformations        │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pros & Cons

| ✅ Pros | ❌ Cons |
|---------|---------|
| Simpler to implement | Sequential = slower (no parallelization) |
| Historical patterns are highly relevant (specific to suggested targets) | Misses patterns if best target wasn't in top N |
| Fewer vector search indexes needed | Historical context can't influence target selection |
| Lower infrastructure cost | If vector search suggests wrong target, history won't help |
| Exact match lookup is faster than vector search | Two-way dependency: need targets first to find history |

---

## Approach 2: Parallel (All Vector Search)

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    APPROACH 2: PARALLEL (ALL VECTOR SEARCH)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   SOURCE FIELDS                                                             │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │ • patient_data.mbr_ssn_num                                  │          │
│   │ • Description: "Social security number of the patient"      │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                              │                                              │
│              ┌───────────────┼───────────────┐                             │
│              │               │               │                             │
│              ▼               ▼               ▼                             │
│   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             │
│   │  VECTOR SEARCH  │ │  VECTOR SEARCH  │ │  VECTOR SEARCH  │             │
│   │  semantic_      │ │  mapping_       │ │  mapping_       │             │
│   │  fields         │ │  patterns       │ │  feedback       │             │
│   │  ─────────────  │ │  ─────────────  │ │  ─────────────  │             │
│   │  Query: src     │ │  Query: src     │ │  Query: src     │             │
│   │  description    │ │  description    │ │  description    │             │
│   │                 │ │                 │ │  (rejections)   │             │
│   │  Index:         │ │  Index:         │ │  Index:         │             │
│   │  semantic_field │ │  source_        │ │  source_        │             │
│   │                 │ │  semantic_field │ │  semantic_field │             │
│   └─────────────────┘ └─────────────────┘ └─────────────────┘             │
│          │                   │                   │                         │
│          ▼                   ▼                   ▼                         │
│   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             │
│   │ Target Matches  │ │ Similar Past    │ │ Similar         │             │
│   │ (by desc)       │ │ Mappings        │ │ Rejections      │             │
│   │                 │ │ (by src desc)   │ │ (by src desc)   │             │
│   │ • Member.SSN    │ │ • ssn→SSN       │ │ • id→SSN ❌     │             │
│   │ • Member.Tax_ID │ │ • ss_num→SSN    │ │   (rejected)    │             │
│   │ • ...           │ │ • TRIM,UPPER    │ │                 │             │
│   └─────────────────┘ └─────────────────┘ └─────────────────┘             │
│          │                   │                   │                         │
│          └───────────────────┴───────────────────┘                         │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │  LLM ANALYSIS                                               │          │
│   │  ──────────────────────────────────────────────────         │          │
│   │  Input:                                                     │          │
│   │  • Source field + description                               │          │
│   │  • Target matches (vector search by description)            │          │
│   │  • Historical patterns (vector search by SOURCE description)│          │
│   │  • Rejections (vector search by SOURCE description)         │          │
│   │                                                             │          │
│   │  Key Difference: History found by source similarity,        │          │
│   │  not by target name. Can find patterns where similar        │          │
│   │  sources mapped to DIFFERENT targets!                       │          │
│   │                                                             │          │
│   │  Output: Ranked recommendations with transformations        │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pros & Cons

| ✅ Pros | ❌ Cons |
|---------|---------|
| All searches run in parallel (faster) | More vector indexes to maintain |
| Historical patterns influence target selection | History may be noisy (mixed target contexts) |
| Finds patterns by source similarity (cross-target learning) | Requires source descriptions in all tables |
| More holistic view for LLM | Higher infrastructure cost |
| Can discover unexpected patterns | More complex to implement |
| Better for diverse source systems | Vector search on 3 tables = more compute |

---

## Approach 3: Hybrid (Two-Stage with Verification)

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    APPROACH 3: HYBRID (TWO-STAGE)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   SOURCE FIELDS                                                             │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │ • patient_data.mbr_ssn_num                                  │          │
│   │ • Description: "Social security number of the patient"      │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                              │                                              │
│   ════════════════════════════════════════════════════════════════         │
│   STAGE 1: PARALLEL DISCOVERY (Vector Search)                               │
│   ════════════════════════════════════════════════════════════════         │
│                              │                                              │
│              ┌───────────────┴───────────────┐                             │
│              │                               │                             │
│              ▼                               ▼                             │
│   ┌─────────────────────────┐   ┌─────────────────────────┐               │
│   │  VECTOR SEARCH          │   │  VECTOR SEARCH          │               │
│   │  semantic_fields        │   │  mapping_patterns       │               │
│   │  ─────────────────      │   │  ─────────────────      │               │
│   │  Find target candidates │   │  Find similar sources   │               │
│   │  by description match   │   │  that were mapped       │               │
│   │                         │   │                         │               │
│   │  → Member.SSN (0.94)    │   │  → ssn_col→SSN (0.91)  │               │
│   │  → Tax_ID (0.78)        │   │  → ss_num→SSN (0.88)   │               │
│   │  → ...                  │   │  → social→Tax_ID (0.72)│               │
│   └─────────────────────────┘   └─────────────────────────┘               │
│              │                               │                             │
│              └───────────────┬───────────────┘                             │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │  MERGE & RANK TARGET CANDIDATES                             │          │
│   │  ─────────────────────────────────────────────────          │          │
│   │  Combine targets from:                                      │          │
│   │  • Direct vector search (by description)                    │          │
│   │  • Historical patterns (what similar sources mapped to)     │          │
│   │                                                             │          │
│   │  Top Candidates: SSN, Tax_ID, Provider_SSN                  │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                              │                                              │
│   ════════════════════════════════════════════════════════════════         │
│   STAGE 2: TARGETED LOOKUP (Exact Match for Top Candidates)                 │
│   ════════════════════════════════════════════════════════════════         │
│                              │                                              │
│              ┌───────────────┴───────────────┐                             │
│              │                               │                             │
│              ▼                               ▼                             │
│   ┌─────────────────────────┐   ┌─────────────────────────┐               │
│   │  EXACT LOOKUP           │   │  EXACT LOOKUP           │               │
│   │  Historical Patterns    │   │  Rejections             │               │
│   │  ─────────────────      │   │  ─────────────────      │               │
│   │  For each top target:   │   │  For each top target:   │               │
│   │  • SSN patterns         │   │  • SSN rejections       │               │
│   │  • Tax_ID patterns      │   │  • Tax_ID rejections    │               │
│   │                         │   │                         │               │
│   │  → Transformations used │   │  → What to avoid        │               │
│   │  → Multi-field combos   │   │  → User feedback        │               │
│   └─────────────────────────┘   └─────────────────────────┘               │
│              │                               │                             │
│              └───────────────┬───────────────┘                             │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │  LLM ANALYSIS                                               │          │
│   │  ──────────────────────────────────────────────────         │          │
│   │  Input:                                                     │          │
│   │  • Source field + description                               │          │
│   │  • Target candidates (from both vector searches)            │          │
│   │  • Historical patterns (exact match for top targets)        │          │
│   │  • Rejections (exact match for top targets)                 │          │
│   │                                                             │          │
│   │  Benefits:                                                  │          │
│   │  • History influences target discovery (Stage 1)            │          │
│   │  • But final context is targeted (Stage 2)                  │          │
│   │                                                             │          │
│   │  Output: Ranked recommendations with transformations        │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pros & Cons

| ✅ Pros | ❌ Cons |
|---------|---------|
| History influences target discovery | More complex than Approach 1 |
| Final context is targeted (less noise) | Requires 2 vector indexes |
| Balanced: vector search where it helps, exact match where precise | Two stages = some sequential delay |
| Can find targets through historical similarity | Stage 2 still depends on Stage 1 results |
| Lower cost than Approach 2 (only 2 vector indexes) | Need to tune candidate count between stages |
| Best of both worlds | More code to maintain |

---

## Approach 4: LLM-Guided Discovery (New Option)

### Concept

Let the LLM help determine the best search strategy based on the source field context.

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    APPROACH 4: LLM-GUIDED DISCOVERY                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   SOURCE FIELDS                                                             │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │ • patient_data.mbr_ssn_num                                  │          │
│   │ • Description: "Social security number of the patient"      │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                              │                                              │
│   ════════════════════════════════════════════════════════════════         │
│   STEP 1: LLM PRE-ANALYSIS (Quick Classification)                           │
│   ════════════════════════════════════════════════════════════════         │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │  LLM CLASSIFICATION                                         │          │
│   │  ──────────────────────────────────────────────────         │          │
│   │  "Given this source field, classify:                        │          │
│   │   - Is this a common field type? (name, date, ID, address)  │          │
│   │   - What target domain? (member, provider, claims)          │          │
│   │   - Likely transformations? (TRIM, UPPER, FORMAT)           │          │
│   │   - Single or multi-field? (standalone or needs combining)" │          │
│   │                                                             │          │
│   │  Output: { domain: "member", type: "identifier",            │          │
│   │           likely_targets: ["SSN", "Tax_ID"],                │          │
│   │           search_strategy: "EXACT_LOOKUP" }                 │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                              │                                              │
│   ════════════════════════════════════════════════════════════════         │
│   STEP 2: ADAPTIVE SEARCH (Based on LLM Classification)                     │
│   ════════════════════════════════════════════════════════════════         │
│                              │                                              │
│              ┌───────────────┼───────────────┐                             │
│              │               │               │                             │
│      If common field   If ambiguous    If unique/rare                      │
│              │               │               │                             │
│              ▼               ▼               ▼                             │
│   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             │
│   │  EXACT LOOKUP   │ │  VECTOR SEARCH  │ │  FULL VECTOR    │             │
│   │  By likely      │ │  On targets +   │ │  SEARCH (all 3) │             │
│   │  targets from   │ │  patterns       │ │                 │             │
│   │  LLM            │ │                 │ │  + Manual       │             │
│   │                 │ │                 │ │    review flag  │             │
│   │  Fast path for  │ │  Moderate path  │ │                 │             │
│   │  common fields  │ │  for unclear    │ │  Slow path for  │             │
│   │                 │ │  cases          │ │  unusual fields │             │
│   └─────────────────┘ └─────────────────┘ └─────────────────┘             │
│              │               │               │                             │
│              └───────────────┴───────────────┘                             │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │  STEP 3: LLM FINAL RECOMMENDATION                           │          │
│   │  ──────────────────────────────────────────────────         │          │
│   │  Combine search results with LLM analysis                   │          │
│   │                                                             │          │
│   │  Output: Ranked recommendations with confidence             │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pros & Cons

| ✅ Pros | ❌ Cons |
|---------|---------|
| Adaptive to field complexity | Two LLM calls = higher latency |
| Fast path for common fields | More expensive (2 LLM calls) |
| Handles edge cases with full search | Complex routing logic |
| Can flag ambiguous cases for review | LLM classification could be wrong |
| Reduces unnecessary searches | Harder to debug/explain |

---

## Comparison Summary

| Aspect | Approach 1 (Sequential) | Approach 2 (Parallel) | Approach 3 (Hybrid) | Approach 4 (LLM-Guided) |
|--------|------------------------|----------------------|---------------------|------------------------|
| **Vector Indexes** | 1 | 3 | 2 | 1-3 (adaptive) |
| **Latency** | Medium (sequential) | Low (parallel) | Medium (2 stages) | Variable |
| **Cost** | Low | High | Medium | High (2 LLM calls) |
| **History Influence on Target** | ❌ After target selected | ✅ Before target selected | ✅ In Stage 1 | ✅ Via classification |
| **Noise in Results** | Low (targeted) | High (broad search) | Medium (balanced) | Low (adaptive) |
| **Cross-Target Learning** | ❌ | ✅ | Partial | ✅ |
| **Implementation Complexity** | Low | Medium | Medium-High | High |
| **Best For** | Simple, well-defined mappings | Diverse source systems | General purpose | High-value, complex mappings |

---

## Recommendation

### For Initial Implementation: **Approach 3 (Hybrid)**

**Rationale:**
1. Gets the benefits of historical learning influencing target discovery (unlike Approach 1)
2. Keeps final context targeted and less noisy (unlike Approach 2)
3. Only requires 2 vector indexes (semantic_fields + mapping_patterns)
4. Rejections can use exact lookup (doesn't need vector search)
5. Good balance of accuracy, performance, and cost

### Implementation Order:
1. **Phase 1**: Implement Approach 1 (simplest, get working end-to-end)
2. **Phase 2**: Upgrade to Approach 3 (add mapping_patterns vector search)
3. **Phase 3**: Consider Approach 2 or 4 if accuracy needs improvement

---

## Visual Comparison

```
                    COMPLEXITY
                        ↑
                        │
      Approach 4        │           
      (LLM-Guided)      │     Approach 2
           ●            │     (All Vector)
                        │          ●
                        │
                        │     Approach 3
                        │     (Hybrid)
                        │          ●
                        │
      Approach 1        │
      (Sequential)      │
           ●            │
                        │
    ────────────────────┼────────────────────→ ACCURACY
                        │
                       Low                    High
```

---

## Key Insight

The fundamental trade-off is:

> **Targeted History (by target name)** vs **Semantic History (by source description)**

- **Approach 1** finds history AFTER target is determined → More precise but may miss opportunities
- **Approach 2** finds history BY source similarity → More comprehensive but may be noisy
- **Approach 3** does BOTH → Best of both worlds with moderate complexity
- **Approach 4** lets LLM decide → Most adaptive but most expensive

