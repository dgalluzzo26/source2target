/**
 * AI Suggestions Store
 * 
 * Manages AI-powered mapping suggestions for source fields.
 * Uses V3 API with dual vector search (semantic + historical patterns).
 * 
 * Enhanced with pattern template detection for multi-field mappings.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UnmappedField } from './unmappedFieldsStore'

export interface AISuggestion {
  semantic_field_id: number  // FK to semantic_fields table (REQUIRED for mapping creation)
  tgt_table_name: string
  tgt_table_physical_name: string
  tgt_column_name: string
  tgt_column_physical_name: string
  tgt_comments?: string  // Target field description/comments
  search_score: number
  match_quality: 'Excellent' | 'Strong' | 'Good' | 'Weak' | 'Unknown'
  ai_reasoning: string
  rank?: number  // UI-only: 1, 2, 3...
  fromPattern?: boolean  // True if this suggestion comes from a pattern match
  patternId?: number  // ID of the matching pattern if applicable
}

export interface HistoricalPattern {
  mapped_field_id: number
  tgt_table_name: string
  tgt_column_name: string
  tgt_table_physical_name?: string
  tgt_column_physical_name?: string
  source_expression?: string
  source_tables?: string
  source_tables_physical?: string
  source_columns?: string
  source_columns_physical?: string
  source_descriptions?: string
  source_datatypes?: string
  source_domain?: string
  target_domain?: string
  source_relationship_type?: string
  transformations_applied?: string
  join_metadata?: string  // JSON metadata for JOIN/UNION patterns
  confidence_score?: number
  search_score?: number
  ai_reasoning?: string
  // Enhanced properties for template matching
  isMultiColumn?: boolean
  columnCount?: number
  matchedToCurrentSelection?: boolean
  templateRelevance?: number  // 0-1 score of how well this pattern matches user's selection
}

export interface PatternTemplate {
  pattern: HistoricalPattern
  relevanceScore: number
  missingFields: string[]  // Column names that user hasn't selected yet
  selectedFields: string[]  // Column names user has selected
  isComplete: boolean
  suggestedSQL?: string
}

// Suggested field mapping for patterns
export interface SuggestedFieldMapping {
  patternColumn: string  // Original column name from pattern
  suggestedField: UnmappedField | null  // Matched field from user's selection
  matchConfidence: number  // 0-1 confidence of the match
  isMatched: boolean
}

// Unified item for combined ranked list
export interface UnifiedMappingOption {
  id: string  // Unique identifier
  rank: number
  source: 'ai_pick' | 'pattern' | 'vector'  // Where this option came from
  
  // Target info
  tgt_table_name: string
  tgt_table_physical_name: string
  tgt_column_name: string
  tgt_column_physical_name: string
  tgt_comments?: string
  
  // Quality/relevance
  matchQuality: 'Excellent' | 'Strong' | 'Good' | 'Weak' | 'Unknown'
  score: number  // Normalized 0-1 score for ranking
  reasoning: string
  
  // For AI suggestions
  semantic_field_id?: number
  
  // For patterns (template usage)
  pattern?: HistoricalPattern
  sourceColumns?: string
  transformations?: string
  isMultiColumn?: boolean
  
  // Suggested field mappings (for patterns)
  suggestedMappings?: SuggestedFieldMapping[]
  allFieldsMatched?: boolean
  generatedSQL?: string
  
  // Flag when a semantic target also has a matching pattern with transforms
  hasMatchingPattern?: boolean
  
  // Frequency boosting info
  patternCount?: number  // How many similar patterns were aggregated
  frequencyBoost?: number  // The boost multiplier applied
}

// Aggregated pattern group - patterns grouped by target + column count
export interface AggregatedPatternGroup {
  // Grouping key
  targetKey: string  // "TABLE.COLUMN"
  columnCount: number
  
  // Aggregated info
  patterns: HistoricalPattern[]
  patternCount: number
  
  // Best pattern in group (highest score)
  bestPattern: HistoricalPattern
  aggregatedScore: number
  
  // Voted transformations (majority wins)
  votedTransformations: string[]
  transformationVotes: Map<string, number>
  
  // Boost multiplier based on frequency
  frequencyBoost: number
  boostedScore: number
}

export const useAISuggestionsStore = defineStore('aiSuggestions', () => {
  // State
  const suggestions = ref<AISuggestion[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const sourceFieldsUsed = ref<UnmappedField[]>([])
  const selectedSuggestion = ref<AISuggestion | null>(null)
  const historicalPatterns = ref<HistoricalPattern[]>([])
  const patternTemplates = ref<PatternTemplate[]>([])  // Templates that need additional fields
  const recommendedExpression = ref<string>('')
  const detectedPatternType = ref<string>('SINGLE')
  const selectedTemplatePattern = ref<HistoricalPattern | null>(null)  // User-selected pattern to use as template
  
  // Hybrid filtering thresholds
  // 1. Absolute minimum - filter obvious noise
  // 2. Relative threshold - filter results too far from top score
  const ABSOLUTE_MIN_SCORE = 0.003  // Minimum score to show
  const RELATIVE_THRESHOLD = 0.25   // Must be at least 25% of top score
  
  // Base combo boost: when a target has BOTH semantic match AND historical pattern
  // This rewards validated mappings with semantic relevance
  const BASE_COMBO_BOOST = 1.5  // Base 50% score boost for combo matches
  
  // Frequency boost constants
  // Formula: BASE_COMBO_BOOST * (1 + min(1.0, log2(count) * FREQUENCY_BOOST_FACTOR))
  const FREQUENCY_BOOST_FACTOR = 0.3  // How much each doubling of patterns adds
  const MAX_FREQUENCY_BOOST = 1.0     // Cap the frequency component at +100%
  
  // Match quality thresholds (calibrated for observed score ranges)
  // Raised thresholds to reduce noise - fewer Strong/Good, more Weak
  const QUALITY_THRESHOLDS = {
    excellent: 0.010,  // Top-tier match (combo boosted or very high semantic)
    strong: 0.007,     // Clear semantic match
    good: 0.005,       // Related/secondary match
    weak: 0.003        // Distant match (borderline)
  }
  
  // Track top score for relative quality calculation (used by getMatchQuality)
  let topVectorScore = 0

  // Computed (thresholds are applied in unifiedOptions)
  const hasSuggestions = computed(() => suggestions.value.length > 0)
  const topSuggestion = computed(() => suggestions.value[0] || null)
  
  // Pattern templates that suggest the user should add more fields
  const hasRelevantTemplates = computed(() => patternTemplates.value.length > 0)
  const topTemplate = computed(() => patternTemplates.value[0] || null)
  
  // Hybrid filtering is automatic - no manual threshold setters needed
  // Constants ABSOLUTE_MIN_SCORE (0.003) and RELATIVE_THRESHOLD (0.25) control filtering
  
  // Multi-column patterns from historical data
  const multiColumnPatterns = computed(() => {
    return historicalPatterns.value.filter(p => p.isMultiColumn)
  })
  
  // Helper: Auto-match pattern columns to user's selected fields
  function autoMatchPatternFields(pattern: HistoricalPattern): {
    mappings: SuggestedFieldMapping[],
    allMatched: boolean,
    generatedSQL: string
  } {
    const mappings: SuggestedFieldMapping[] = []
    const selectedFields = sourceFieldsUsed.value
    
    // Parse pattern columns
    const patternColsPhysical = (pattern.source_columns_physical || pattern.source_columns || '').split(/[|,]/).map(c => c.trim()).filter(c => c)
    const patternCols = (pattern.source_columns || '').split(/[|,]/).map(c => c.trim()).filter(c => c)
    
    // Use physical names if available, fall back to display names
    const columnsToMatch = patternColsPhysical.length > 0 ? patternColsPhysical : patternCols
    
    // Track which selected fields have been used
    const usedFieldIds = new Set<number>()
    
    columnsToMatch.forEach((patternCol, idx) => {
      const patternColLower = patternCol.toLowerCase()
      const patternWords = new Set(patternColLower.split(/[_\s]+/).filter(w => w.length > 1))
      
      // Find best matching field from user's selection
      let bestMatch: UnmappedField | null = null
      let bestScore = 0
      
      selectedFields.forEach(field => {
        if (usedFieldIds.has(field.id)) return // Already used
        
        const fieldColLower = (field.src_column_physical_name || field.src_column_name || '').toLowerCase()
        const fieldWords = new Set(fieldColLower.split(/[_\s]+/).filter(w => w.length > 1))
        
        // Calculate match score
        let score = 0
        
        // Exact match
        if (fieldColLower === patternColLower) {
          score = 1.0
        } else {
          // Word overlap
          let overlap = 0
          fieldWords.forEach(fw => {
            patternWords.forEach(pw => {
              if (fw === pw) overlap += 1
              else if (fw.includes(pw) || pw.includes(fw)) overlap += 0.5
            })
          })
          score = overlap / Math.max(fieldWords.size, patternWords.size)
        }
        
        if (score > bestScore) {
          bestScore = score
          bestMatch = field
        }
      })
      
      // Accept match if score is reasonable (> 0.3)
      if (bestMatch && bestScore > 0.3) {
        usedFieldIds.add(bestMatch.id)
        mappings.push({
          patternColumn: patternCols[idx] || patternCol, // Use display name for UI
          suggestedField: bestMatch,
          matchConfidence: bestScore,
          isMatched: true
        })
      } else {
        mappings.push({
          patternColumn: patternCols[idx] || patternCol,
          suggestedField: null,
          matchConfidence: 0,
          isMatched: false
        })
      }
    })
    
    const allMatched = mappings.length > 0 && mappings.every(m => m.isMatched)
    
    // Generate SQL if all fields matched
    let generatedSQL = ''
    if (allMatched) {
      generatedSQL = generateSQLFromMappings(pattern, mappings)
    }
    
    return { mappings, allMatched, generatedSQL }
  }
  
  // Helper: Generate SQL directly from user's selected fields + transforms
  // Used when merging pattern transforms onto a semantic target
  function generateSQLForUserFields(userFields: UnmappedField[], transforms: string): string {
    const fields = userFields.map(f => 
      (f.src_column_physical_name || f.src_column_name || '').toLowerCase().replace(/\s+/g, '_')
    ).filter(f => f)
    
    if (fields.length === 0) return ''
    
    const transformList = transforms.split(/[,\s]+/).map(t => t.trim().toUpperCase()).filter(t => t)
    
    console.log('[generateSQLForUserFields]', { fields, transformList })
    
    if (fields.length > 1 || transformList.includes('CONCAT')) {
      // Multi-field: CONCAT
      const fieldExpressions = fields.map(f => {
        let expr = f
        const appliedTransforms = transformList.filter(t => t !== 'CONCAT')
        if (appliedTransforms.length === 0) {
          expr = `TRIM(${expr})`
        } else {
          appliedTransforms.forEach(t => {
            if (['TRIM', 'UPPER', 'LOWER', 'INITCAP'].includes(t)) {
              expr = `${t}(${expr})`
            }
          })
        }
        return expr
      })
      return `CONCAT_WS(' ', ${fieldExpressions.join(', ')})`
    } else {
      // Single field
      let expr = fields[0]
      if (transformList.length === 0) {
        expr = `TRIM(${expr})`
      } else {
        // Apply transforms in logical order: TRIM first, then case transforms
        const orderedTransforms = [...transformList].sort((a, b) => {
          if (a === 'TRIM') return -1
          if (b === 'TRIM') return 1
          return 0
        })
        orderedTransforms.forEach(t => {
          if (['TRIM', 'UPPER', 'LOWER', 'INITCAP'].includes(t)) {
            expr = `${t}(${expr})`
          }
        })
      }
      return expr
    }
  }
  
  // Helper: Generate SQL from matched fields
  function generateSQLFromMappings(pattern: HistoricalPattern, mappings: SuggestedFieldMapping[]): string {
    const fields = mappings
      .filter(m => m.suggestedField)
      .map(m => (m.suggestedField!.src_column_physical_name || m.suggestedField!.src_column_name || '').toLowerCase().replace(/\s+/g, '_'))
    
    if (fields.length === 0) return ''
    
    // If pattern has source_expression, adapt it
    if (pattern.source_expression && pattern.source_columns_physical) {
      let adaptedSQL = pattern.source_expression
      const oldColumns = (pattern.source_columns_physical || '').split(/[|,]/).map(c => c.trim()).filter(c => c)
      const oldTables = (pattern.source_tables_physical || '').split(/[|,]/).map(t => t.trim()).filter(t => t)
      
      // Get new table names
      const newTables = mappings
        .filter(m => m.suggestedField)
        .map(m => (m.suggestedField!.src_table_physical_name || m.suggestedField!.src_table_name || '').toLowerCase().replace(/\s+/g, '_'))
      
      oldColumns.forEach((oldCol, idx) => {
        if (fields[idx]) {
          const oldTable = oldTables[Math.min(idx, oldTables.length - 1)] || ''
          const newTable = newTables[idx] || newTables[0] || ''
          
          // Replace table-qualified names first
          if (oldTable) {
            const tableQualifiedRegex = new RegExp(`\\b${oldTable}\\.${oldCol}\\b`, 'gi')
            const newQualified = newTable ? `${newTable}.${fields[idx]}` : fields[idx]
            adaptedSQL = adaptedSQL.replace(tableQualifiedRegex, newQualified)
          }
          
          // Replace unqualified column names
          const unqualifiedRegex = new RegExp(`\\b${oldCol}\\b`, 'gi')
          adaptedSQL = adaptedSQL.replace(unqualifiedRegex, fields[idx])
        }
      })
      
      return adaptedSQL
    }
    
    // Build SQL from transformations
    const transforms = (pattern.transformations_applied || '').split(/[,\s]+/).map(t => t.trim().toUpperCase()).filter(t => t)
    
    if (fields.length > 1 || transforms.includes('CONCAT')) {
      // Multi-field: CONCAT
      const fieldExpressions = fields.map(f => {
        let expr = f
        const appliedTransforms = transforms.filter(t => t !== 'CONCAT')
        if (appliedTransforms.length === 0) {
          expr = `TRIM(${expr})`
        } else {
          appliedTransforms.forEach(t => {
            if (['TRIM', 'UPPER', 'LOWER', 'INITCAP'].includes(t)) {
              expr = `${t}(${expr})`
            }
          })
        }
        return expr
      })
      return `CONCAT_WS(' ', ${fieldExpressions.join(', ')})`
    } else {
      // Single field
      let expr = fields[0]
      if (transforms.length === 0) {
        expr = `TRIM(${expr})`
      } else {
        transforms.forEach(t => {
          if (['TRIM', 'UPPER', 'LOWER', 'INITCAP'].includes(t)) {
            expr = `${t}(${expr})`
          }
        })
      }
      return expr
    }
  }
  
  // Helper: Calculate frequency boost based on pattern count
  // Formula: BASE_COMBO_BOOST * (1 + min(MAX_FREQUENCY_BOOST, log2(count) * FREQUENCY_BOOST_FACTOR))
  // Examples: 1 pattern = 1.5x, 2 patterns = 1.8x, 3 patterns = 1.98x, 5 patterns = 2.2x
  function calculateFrequencyBoost(patternCount: number): number {
    if (patternCount <= 0) return 1.0
    if (patternCount === 1) return BASE_COMBO_BOOST
    
    const frequencyComponent = Math.min(MAX_FREQUENCY_BOOST, Math.log2(patternCount) * FREQUENCY_BOOST_FACTOR)
    const boost = BASE_COMBO_BOOST * (1 + frequencyComponent)
    
    console.log(`[Frequency Boost] ${patternCount} patterns -> ${boost.toFixed(2)}x boost`)
    return boost
  }
  
  // Helper: Vote on transformations within a pattern group
  // Returns transforms that appear in >50% of patterns
  function voteOnTransformations(patterns: HistoricalPattern[]): { 
    votedTransforms: string[], 
    votes: Map<string, number> 
  } {
    const votes = new Map<string, number>()
    const threshold = patterns.length / 2  // >50% required
    
    // Count votes for each transformation
    patterns.forEach(p => {
      const transforms = (p.transformations_applied || '')
        .split(/[,\s]+/)
        .map(t => t.trim().toUpperCase())
        .filter(t => t)
      
      const seen = new Set<string>()  // Avoid double-counting same transform in one pattern
      transforms.forEach(t => {
        if (!seen.has(t)) {
          seen.add(t)
          votes.set(t, (votes.get(t) || 0) + 1)
        }
      })
    })
    
    // Filter to transforms with >50% votes
    const votedTransforms: string[] = []
    votes.forEach((count, transform) => {
      if (count > threshold) {
        votedTransforms.push(transform)
      }
    })
    
    // Order: TRIM first, then case transforms
    const transformOrder = ['TRIM', 'UPPER', 'LOWER', 'INITCAP', 'PROPER_CASE', 'CONCAT']
    votedTransforms.sort((a, b) => {
      const aIdx = transformOrder.indexOf(a)
      const bIdx = transformOrder.indexOf(b)
      if (aIdx === -1 && bIdx === -1) return 0
      if (aIdx === -1) return 1
      if (bIdx === -1) return -1
      return aIdx - bIdx
    })
    
    console.log(`[Transform Voting] ${patterns.length} patterns, threshold=${threshold.toFixed(1)}`, 
      Object.fromEntries(votes), `-> Winners: [${votedTransforms.join(', ')}]`)
    
    return { votedTransforms, votes }
  }
  
  // Helper: Aggregate patterns into groups by target + column count
  function aggregatePatternGroups(patterns: HistoricalPattern[]): AggregatedPatternGroup[] {
    const groups = new Map<string, HistoricalPattern[]>()
    
    // Group patterns by target + column count
    patterns.forEach(p => {
      const targetKey = `${(p.tgt_table_name || '').toLowerCase()}.${(p.tgt_column_name || '').toLowerCase()}`
      const columnCount = p.columnCount || 1
      const groupKey = `${targetKey}|${columnCount}`
      
      if (!groups.has(groupKey)) {
        groups.set(groupKey, [])
      }
      groups.get(groupKey)!.push(p)
    })
    
    // Convert to AggregatedPatternGroup array
    const aggregatedGroups: AggregatedPatternGroup[] = []
    
    groups.forEach((groupPatterns, groupKey) => {
      const [targetKey, colCountStr] = groupKey.split('|')
      const columnCount = parseInt(colCountStr) || 1
      
      // Find best pattern (highest score)
      const sortedPatterns = [...groupPatterns].sort((a, b) => 
        (b.search_score || 0) - (a.search_score || 0)
      )
      const bestPattern = sortedPatterns[0]
      const aggregatedScore = bestPattern.search_score || 0
      
      // Vote on transformations
      const { votedTransforms, votes } = voteOnTransformations(groupPatterns)
      
      // Calculate frequency boost
      const frequencyBoost = calculateFrequencyBoost(groupPatterns.length)
      const boostedScore = aggregatedScore * frequencyBoost
      
      console.log(`[Pattern Group] ${targetKey} (${columnCount} cols): ${groupPatterns.length} patterns, ` +
        `score=${aggregatedScore.toFixed(4)} * ${frequencyBoost.toFixed(2)} = ${boostedScore.toFixed(4)}, ` +
        `transforms=[${votedTransforms.join(', ')}]`)
      
      aggregatedGroups.push({
        targetKey,
        columnCount,
        patterns: groupPatterns,
        patternCount: groupPatterns.length,
        bestPattern,
        aggregatedScore,
        votedTransformations: votedTransforms,
        transformationVotes: votes,
        frequencyBoost,
        boostedScore
      })
    })
    
    // Sort by boosted score descending
    aggregatedGroups.sort((a, b) => b.boostedScore - a.boostedScore)
    
    console.log(`[Pattern Aggregation] ${patterns.length} patterns -> ${aggregatedGroups.length} groups`)
    
    return aggregatedGroups
  }
  
  // Unified ranked list combining AI suggestions and historical patterns
  // Uses HYBRID filtering: absolute minimum + relative to top score
  const unifiedOptions = computed((): UnifiedMappingOption[] => {
    const options: UnifiedMappingOption[] = []
    
    // Log raw counts
    console.log(`[Unified Options] Raw suggestions: ${suggestions.value.length}, Raw patterns: ${historicalPatterns.value.length}`)
    
    // Find top scores for relative filtering
    const topTargetScore = suggestions.value.length > 0 
      ? Math.max(...suggestions.value.map(s => s.search_score ?? 0))
      : 0
    const topPatternScore = historicalPatterns.value.length > 0
      ? Math.max(...historicalPatterns.value.map(p => p.search_score ?? 0))
      : 0
    
    // Calculate relative thresholds (25% of top score)
    const targetRelativeThreshold = topTargetScore * RELATIVE_THRESHOLD
    const patternRelativeThreshold = topPatternScore * RELATIVE_THRESHOLD
    
    console.log(`[Unified Options] Top scores - Targets: ${topTargetScore.toFixed(4)}, Patterns: ${topPatternScore.toFixed(4)}`)
    console.log(`[Unified Options] Hybrid thresholds - Targets: max(${ABSOLUTE_MIN_SCORE}, ${targetRelativeThreshold.toFixed(4)}), Patterns: max(${ABSOLUTE_MIN_SCORE}, ${patternRelativeThreshold.toFixed(4)})`)
    
    // HYBRID filter for targets: must pass BOTH absolute minimum AND relative threshold
    const filteredSuggestionsList = suggestions.value.filter(s => {
      const score = s.search_score ?? 0
      const effectiveThreshold = Math.max(ABSOLUTE_MIN_SCORE, targetRelativeThreshold)
      const passes = !isNaN(score) && score >= effectiveThreshold
      if (!passes) {
        console.log(`[Unified Options] Filtered target: ${s.tgt_column_name}, score=${score.toFixed(4)} < threshold=${effectiveThreshold.toFixed(4)}`)
      }
      return passes
    })
    
    // HYBRID filter for patterns
    const filteredPatternsList = historicalPatterns.value.filter(p => {
      const score = p.search_score ?? 0
      const effectiveThreshold = Math.max(ABSOLUTE_MIN_SCORE, patternRelativeThreshold)
      const passes = !isNaN(score) && score >= effectiveThreshold
      if (!passes) {
        console.log(`[Unified Options] Filtered pattern: ${p.tgt_column_name}, score=${score.toFixed(4)} < threshold=${effectiveThreshold.toFixed(4)}`)
      }
      return passes
    })
    
    console.log(`[Unified Options] After hybrid filter - Targets: ${filteredSuggestionsList.length}, Patterns: ${filteredPatternsList.length}`)
    
    // Add AI suggestions (from vector search on semantic_fields)
    filteredSuggestionsList.forEach((s, idx) => {
      // Determine source type based on properties
      let source: 'ai_pick' | 'pattern' | 'vector' = 'vector'
      if (s.match_quality === 'Excellent' && idx === 0) {
        source = 'ai_pick'  // LLM's best pick
      } else if (s.fromPattern) {
        source = 'pattern'
      }
      
      options.push({
        id: `suggestion-${s.semantic_field_id}-${s.tgt_column_name}`,
        rank: 0,  // Will be set after sorting
        source,
        tgt_table_name: s.tgt_table_name,
        tgt_table_physical_name: s.tgt_table_physical_name,
        tgt_column_name: s.tgt_column_name,
        tgt_column_physical_name: s.tgt_column_physical_name,
        tgt_comments: s.tgt_comments,
        matchQuality: s.match_quality,
        score: s.search_score,
        reasoning: s.ai_reasoning,
        semantic_field_id: s.semantic_field_id
      })
    })
    
    // AGGREGATE historical patterns by target + column count
    // This groups similar patterns and applies frequency-based boosting
    const aggregatedGroups = aggregatePatternGroups(filteredPatternsList)
    
    console.log(`[Unified Options] Aggregated ${filteredPatternsList.length} patterns into ${aggregatedGroups.length} groups`)
    
    // Process each aggregated pattern group
    aggregatedGroups.forEach((group) => {
      const p = group.bestPattern  // Use best pattern in group as representative
      
      // Check if this pattern's target already exists as a semantic target
      const existingTargetIdx = options.findIndex(o => 
        o.tgt_column_name.toLowerCase() === p.tgt_column_name.toLowerCase() &&
        o.tgt_table_name.toLowerCase() === p.tgt_table_name.toLowerCase() &&
        o.source !== 'pattern'  // Only merge into non-pattern options (targets)
      )
      
      // Auto-match pattern fields to user's selected fields
      const { mappings, allMatched, generatedSQL } = autoMatchPatternFields(p)
      
      // Use voted transformations instead of single pattern's transforms
      const votedTransformsStr = group.votedTransformations.join(', ')
      
      if (existingTargetIdx >= 0) {
        // MERGE: Enrich the existing target with aggregated pattern info
        const existing = options[existingTargetIdx]
        
        // For merged targets, generate SQL using USER's selected fields + VOTED transforms
        let mergedSQL = ''
        if (sourceFieldsUsed.value.length > 0 && votedTransformsStr) {
          mergedSQL = generateSQLForUserFields(sourceFieldsUsed.value, votedTransformsStr)
        }
        
        // FREQUENCY BOOST: Apply boost based on pattern count
        // More patterns = higher confidence = bigger boost
        const originalScore = existing.score
        existing.score = existing.score * group.frequencyBoost
        
        console.log(`[Unified Options] MERGING ${group.patternCount} patterns into target ${p.tgt_column_name}:`, {
          existingSource: existing.source,
          originalScore: originalScore?.toFixed(4),
          boostedScore: existing.score?.toFixed(4),
          boostMultiplier: group.frequencyBoost.toFixed(2),
          patternCount: group.patternCount,
          votedTransforms: votedTransformsStr,
          userFields: sourceFieldsUsed.value.map(f => f.src_column_physical_name),
          generatedSQL: mergedSQL?.substring(0, 50)
        })
        
        // Add aggregated pattern info to the target
        existing.transformations = votedTransformsStr  // Use voted transforms
        existing.pattern = p
        existing.sourceColumns = p.source_columns
        existing.isMultiColumn = p.isMultiColumn || group.columnCount > 1
        existing.suggestedMappings = mappings
        existing.allFieldsMatched = allMatched || sourceFieldsUsed.value.length > 0
        existing.generatedSQL = mergedSQL || generatedSQL
        existing.hasMatchingPattern = true
        existing.patternCount = group.patternCount
        existing.frequencyBoost = group.frequencyBoost
        
        // Update reasoning to include pattern frequency info
        const patternInfo = group.patternCount > 1 
          ? `${group.patternCount} similar mappings typically use: ${votedTransformsStr}`
          : `Similar mapping uses: ${votedTransformsStr}`
        existing.reasoning = `${existing.reasoning || ''} | ${patternInfo}`.trim()
      } else {
        // ADD: New pattern-only option (no matching semantic target)
        // Use the boosted score from aggregation
        const score = group.boostedScore
        
        console.log(`[Unified Options] Adding NEW pattern group ${p.tgt_column_name}:`, {
          patternCount: group.patternCount,
          aggregatedScore: group.aggregatedScore.toFixed(4),
          frequencyBoost: group.frequencyBoost.toFixed(2),
          boostedScore: score.toFixed(4),
          columnCount: group.columnCount,
          votedTransforms: votedTransformsStr,
          mappingsCount: mappings.length,
          allMatched
        })
        
        // Try to get target description from vector search results if available
        const matchingTarget = suggestions.value.find(
          t => t.tgt_column_physical_name === (p.tgt_column_physical_name || p.tgt_column_name) &&
               t.tgt_table_physical_name === (p.tgt_table_physical_name || p.tgt_table_name)
        )
        const tgtComments = matchingTarget?.tgt_comments || ''
        
        const patternInfo = group.patternCount > 1 
          ? `${group.patternCount} similar mappings using ${votedTransformsStr}`
          : `Historical pattern using ${votedTransformsStr || 'direct mapping'}`
        
        options.push({
          id: `pattern-group-${group.targetKey}-${group.columnCount}`,
          rank: 0,
          source: 'pattern',
          tgt_table_name: p.tgt_table_name,
          tgt_table_physical_name: p.tgt_table_physical_name || p.tgt_table_name,
          tgt_column_name: p.tgt_column_name,
          tgt_column_physical_name: p.tgt_column_physical_name || p.tgt_column_name,
          tgt_comments: tgtComments,
          matchQuality: 'Unknown',  // Will be set after sorting by rank
          score: score,
          suggestedMappings: mappings,
          allFieldsMatched: allMatched,
          generatedSQL: generatedSQL,
          reasoning: patternInfo,
          pattern: p,
          sourceColumns: p.source_columns,
          transformations: votedTransformsStr,
          isMultiColumn: p.isMultiColumn || group.columnCount > 1,
          patternCount: group.patternCount,
          frequencyBoost: group.frequencyBoost
        })
      }
    })
    
    // Sort by: 1) ai_pick first, 2) score descending
    options.sort((a, b) => {
      // AI pick always first
      if (a.source === 'ai_pick' && b.source !== 'ai_pick') return -1
      if (b.source === 'ai_pick' && a.source !== 'ai_pick') return 1
      
      // Then by score
      return b.score - a.score
    })
    
    // Assign ranks AND quality based on final position
    // This ensures consistent quality regardless of source
    options.forEach((opt, idx) => {
      opt.rank = idx + 1
      
      // If quality wasn't already set (patterns come in as Unknown), set by score
      if (opt.matchQuality === 'Unknown') {
        // Score-based quality using new calibrated thresholds
        if (opt.score >= QUALITY_THRESHOLDS.excellent) opt.matchQuality = 'Excellent'
        else if (opt.score >= QUALITY_THRESHOLDS.strong) opt.matchQuality = 'Strong'
        else if (opt.score >= QUALITY_THRESHOLDS.good) opt.matchQuality = 'Good'
        else opt.matchQuality = 'Weak'
      }
    })
    
    return options
  })
  
  const hasOptions = computed(() => unifiedOptions.value.length > 0)
  
  // Actions
  async function generateSuggestions(sourceFields: UnmappedField[], allAvailableFields?: UnmappedField[]) {
    // IMPORTANT: Clear ALL previous state first
    console.log('[AI Suggestions] === Starting new suggestion request ===')
    console.log('[AI Suggestions] Clearing previous state...')
    
    loading.value = true
    error.value = null
    suggestions.value = []
    historicalPatterns.value = []
    patternTemplates.value = []
    recommendedExpression.value = ''
    detectedPatternType.value = 'SINGLE'
    sourceFieldsUsed.value = [...sourceFields]
    topVectorScore = 0  // Reset for new request
    
    console.log('[AI Suggestions] State cleared. Historical patterns:', historicalPatterns.value.length)
    console.log('[AI Suggestions] Source fields for this query:', sourceFields.map(f => f.src_column_name))

    try {
      console.log('[AI Suggestions] Calling V3 API for', sourceFields.length, 'source fields')
      
      const response = await fetch('/api/v3/ai/suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_fields: sourceFields.map(f => ({
            src_table_name: f.src_table_name,
            src_table_physical_name: f.src_table_physical_name,
            src_column_name: f.src_column_name,
            src_column_physical_name: f.src_column_physical_name,
            src_physical_datatype: f.src_physical_datatype,
            src_comments: f.src_comments || ''
          })),
          num_results: 10
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`API error: ${response.status} - ${errorText}`)
      }

      const data = await response.json()
      console.log('[AI Suggestions] V3 API response:', JSON.stringify(data, null, 2))
      
      // V3 API returns target_candidates, historical_patterns, best_target, etc.
      const targetCandidates = data.target_candidates || []
      const bestTarget = data.best_target || {}
      const llmReasoning = bestTarget.reasoning || data.recommended_expression || ''
      
      console.log('[AI Suggestions] Best target from LLM:', bestTarget)
      console.log('[AI Suggestions] Target candidates count:', targetCandidates.length)
      
      // Log ALL raw scores for calibration
      console.log('[AI Suggestions] === RAW VECTOR SEARCH SCORES ===')
      targetCandidates.forEach((c: any, i: number) => {
        console.log(`  ${i + 1}. ${c.tgt_column_name}: raw=${c.search_score}`)
      })
      console.log('[AI Suggestions] === END RAW SCORES ===')
      
      // Set top score for relative quality calculation
      if (targetCandidates.length > 0 && targetCandidates[0].search_score) {
        const rawTop = typeof targetCandidates[0].search_score === 'string' 
          ? parseFloat(targetCandidates[0].search_score) 
          : Number(targetCandidates[0].search_score)
        topVectorScore = parseScore(rawTop)
        console.log('[AI Suggestions] Top vector score (normalized):', topVectorScore)
      }
      
      // Transform target candidates into suggestion format
      // Backend already filters by minimum score threshold - just display what we get
      suggestions.value = targetCandidates.map((candidate: any, idx: number) => {
        // Parse score - might be number, string, or undefined
        // Databricks vector search returns raw cosine similarity scores (typically 0.001-0.01 range)
        // Multiply by 100 to get a more intuitive 0-1 scale (e.g., 0.00576 -> 0.576)
        let score = 0
        if (candidate.search_score !== undefined && candidate.search_score !== null) {
          const rawScore = typeof candidate.search_score === 'string' 
            ? parseFloat(candidate.search_score) 
            : Number(candidate.search_score)
          
          // No normalization needed - new format gives good scores (0.006-0.050)
          score = rawScore
        }
        
        // Check if this is the LLM's best target (case-insensitive comparison)
        const candidateCol = (candidate.tgt_column_name || '').toLowerCase().trim()
        const bestTargetCol = (bestTarget.tgt_column_name || '').toLowerCase().trim()
        const isBestTarget = candidateCol === bestTargetCol && candidateCol !== ''
        
        // Also check table name match if available
        const candidateTable = (candidate.tgt_table_name || '').toLowerCase().trim()
        const bestTargetTable = (bestTarget.tgt_table_name || '').toLowerCase().trim()
        const isExactMatch = isBestTarget && (bestTargetTable === '' || candidateTable === bestTargetTable)
        
        // Determine match quality based on rank (backend already sorted by score)
        const matchQuality = getMatchQuality(score, isExactMatch, idx + 1)
        
        // Debug first few candidates
        if (idx < 5) {
          console.log(`[AI Suggestions] Candidate ${idx + 1}:`, {
            column: candidate.tgt_column_name,
            rawScore: candidate.search_score,
            displayScore: score,
            matchQuality: matchQuality,
            isBestTarget: isExactMatch
          })
        }
        
        // Build reasoning
        let reasoning = ''
        if (isExactMatch && llmReasoning) {
          reasoning = llmReasoning
        } else if (candidate.tgt_comments) {
          reasoning = candidate.tgt_comments
        } else {
          reasoning = `Vector search similarity: ${score.toFixed(4)}`
        }
        
        return {
          semantic_field_id: candidate.semantic_field_id || 0,
          tgt_table_name: candidate.tgt_table_name || '',
          tgt_table_physical_name: candidate.tgt_table_physical_name || candidate.tgt_table_name || '',
          tgt_column_name: candidate.tgt_column_name || '',
          tgt_column_physical_name: candidate.tgt_column_physical_name || candidate.tgt_column_name || '',
          tgt_comments: candidate.tgt_comments || '',
          search_score: score,
          match_quality: matchQuality,
          ai_reasoning: reasoning,
          rank: idx + 1
        } as AISuggestion
      })
      
      console.log(`[AI Suggestions] Displaying ${suggestions.value.length} suggestions (backend already filtered)`)
      
      // If we have a best target but it's not in top candidates, move it to top
      if (bestTarget.tgt_column_name && suggestions.value.length > 0) {
        const bestIdx = suggestions.value.findIndex(
          s => s.tgt_column_name.toLowerCase() === bestTarget.tgt_column_name?.toLowerCase()
        )
        if (bestIdx > 0) {
          // Move best target to position 0
          const best = suggestions.value.splice(bestIdx, 1)[0]
          best.match_quality = 'Excellent'
          best.ai_reasoning = llmReasoning || best.ai_reasoning
          suggestions.value.unshift(best)
          // Re-rank
          suggestions.value.forEach((s, i) => { s.rank = i + 1 })
        }
      }
      
      // Store recommended expression and pattern type from LLM
      recommendedExpression.value = data.recommended_expression || ''
      detectedPatternType.value = data.detected_pattern || 'SINGLE'
      
      // Process historical patterns - just enhance with metadata, no auto-detection
      // User will choose which pattern to use as template
      const patternsFromApi = data.historical_patterns || []
      console.log('[AI Suggestions] Historical patterns received from API:', patternsFromApi.length)
      
      // Enhance patterns with basic analysis (multi-column detection, etc.)
      const enhancedPatterns = processPatterns(patternsFromApi, sourceFields)
      historicalPatterns.value = enhancedPatterns
      
      // Clear any previous template selection - user will choose
      patternTemplates.value = []
      selectedTemplatePattern.value = null
      
      console.log('[AI Suggestions] Enhanced patterns:', enhancedPatterns.length)
      
      // Debug output
      console.log('[AI Suggestions] === Results Summary ===')
      console.log('[AI Suggestions] Final suggestions:', suggestions.value.length)
      console.log('[AI Suggestions] Final historical patterns:', historicalPatterns.value.length)
      if (suggestions.value.length > 0) {
        console.log('[AI Suggestions] Top suggestion:', suggestions.value[0])
      }
      
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate suggestions'
      console.error('[AI Suggestions] Error:', error.value)
      suggestions.value = []
    } finally {
      loading.value = false
    }
  }
  
  // Helper: Parse and validate score (no normalization needed with new semantic_field format)
  // New format (DESCRIPTION + TYPE only) returns scores in 0.006-0.050 range
  // which is perfect for our thresholds (Excellent: 0.035+, Strong: 0.020+, etc.)
  function parseScore(rawScore: number | string | null | undefined): number {
    if (rawScore === null || rawScore === undefined) return 0
    const score = typeof rawScore === 'string' ? parseFloat(rawScore) : Number(rawScore)
    if (isNaN(score)) return 0
    return score
  }
  
  // Helper: Convert score to match quality using ABSOLUTE thresholds
  // Calibrated for NEW semantic_field format (DESCRIPTION + TYPE only)
  // Observed scores: top=0.043, 2nd=0.012, noise=0.006
  function getMatchQuality(score: number, isBestTarget: boolean, rank?: number): 'Excellent' | 'Strong' | 'Good' | 'Weak' | 'Unknown' {
    // LLM's best target always gets Excellent (AI validated this match)
    if (isBestTarget) return 'Excellent'
    
    // Handle invalid scores
    if (isNaN(score) || score === null || score === undefined) {
      console.warn('[AI Suggestions] Invalid score:', score)
      return 'Unknown'
    }
    
    // ABSOLUTE thresholds based on new semantic_field format
    // These are the RAW scores from vector search (not normalized)
    let quality: 'Excellent' | 'Strong' | 'Good' | 'Weak' = 'Weak'
    
    if (score >= QUALITY_THRESHOLDS.excellent) {
      quality = 'Excellent'  // 0.010+ = top-tier match (combo boosted or very high)
    } else if (score >= QUALITY_THRESHOLDS.strong) {
      quality = 'Strong'     // 0.007+ = clear semantic match
    } else if (score >= QUALITY_THRESHOLDS.good) {
      quality = 'Good'       // 0.005+ = related/secondary match
    } else if (score >= QUALITY_THRESHOLDS.weak) {
      quality = 'Weak'       // 0.003+ = distant match
    } else {
      quality = 'Weak'       // Below 0.003 = noise (should be filtered)
    }
    
    // Debug log for first few
    if (rank && rank <= 5) {
      console.log(`[AI Suggestions] Quality for rank ${rank}: score=${score.toFixed(4)}, quality=${quality}`)
    }
    
    return quality
  }
  
  // Helper: Process historical patterns to detect multi-column mappings
  // Backend already filters by minimum score threshold - just enhance with metadata
  function processPatterns(patterns: any[], selectedFields: UnmappedField[]): HistoricalPattern[] {
    const selectedColNames = new Set(
      selectedFields.map(f => (f.src_column_physical_name || f.src_column_name || '').toLowerCase())
    )
    const selectedColWords = new Set<string>()
    selectedFields.forEach(f => {
      const words = (f.src_column_physical_name || f.src_column_name || '').toLowerCase().split(/[_\s]+/)
      words.forEach(w => selectedColWords.add(w))
    })
    
    console.log('[AI Suggestions] Processing', patterns.length, 'patterns from backend (already filtered by score)')
    
    return patterns.map((p: any) => {
      // Parse source columns to determine if multi-column
      const sourceColsStr = p.source_columns || ''
      const sourceCols = sourceColsStr.split(/[|,]/).map((c: string) => c.trim()).filter((c: string) => c)
      const isMultiColumn = sourceCols.length > 1 || 
                           p.source_relationship_type === 'CONCAT' ||
                           p.source_relationship_type === 'JOIN' ||
                           p.source_relationship_type === 'UNION' ||
                           (p.source_expression && (
                             p.source_expression.includes('CONCAT') ||
                             p.source_expression.includes('||')
                           ))
      
      // Calculate how well this pattern matches the current selection (for template matching)
      let matchedCols = 0
      let relevance = 0
      
      sourceCols.forEach((col: string) => {
        const colLower = col.toLowerCase()
        const colWords = colLower.split(/[_\s]+/)
        
        // Check direct match
        if (selectedColNames.has(colLower)) {
          matchedCols++
          relevance += 1.0
        } else {
          // Check word overlap
          const overlap = colWords.filter((w: string) => selectedColWords.has(w)).length
          if (overlap > 0) {
            relevance += overlap / Math.max(colWords.length, 1) * 0.5
          }
        }
      })
      
      // Normalize relevance by total columns in pattern
      const normalizedRelevance = sourceCols.length > 0 ? relevance / sourceCols.length : 0
      
      return {
        ...p,
        isMultiColumn,
        columnCount: sourceCols.length,
        matchedToCurrentSelection: matchedCols > 0,
        templateRelevance: normalizedRelevance,
        // Parse search scores - no normalization needed with new semantic_field format
        search_score: parseScore(p.search_score),
        confidence_score: parseScore(p.confidence_score)
      } as HistoricalPattern
    }).sort((a, b) => {
      // Sort by search score (already filtered by backend)
      return (b.search_score || 0) - (a.search_score || 0)
    })
  }
  
  function selectSuggestion(suggestion: AISuggestion) {
    selectedSuggestion.value = suggestion
    console.log('[AI Suggestions] Selected:', suggestion.tgt_column_name)
  }

  // User explicitly chooses a historical pattern to use as template
  function selectPatternAsTemplate(pattern: HistoricalPattern) {
    selectedTemplatePattern.value = pattern
    console.log('[AI Suggestions] User selected pattern as template:', pattern.tgt_column_name, {
      sourceCols: pattern.source_columns,
      expression: pattern.source_expression,
      isMultiColumn: pattern.isMultiColumn
    })
  }
  
  // Clear the selected template
  function clearSelectedTemplate() {
    selectedTemplatePattern.value = null
  }

  function clearSuggestions() {
    suggestions.value = []
    sourceFieldsUsed.value = []
    selectedSuggestion.value = null
    historicalPatterns.value = []
    patternTemplates.value = []
    selectedTemplatePattern.value = null
    recommendedExpression.value = ''
    detectedPatternType.value = 'SINGLE'
    error.value = null
    console.log('[AI Suggestions] Cleared suggestions')
  }
  
  // Action: Update source fields (when user adds more fields via template)
  function addSourceField(field: UnmappedField) {
    if (!sourceFieldsUsed.value.find(f => f.id === field.id)) {
      sourceFieldsUsed.value.push(field)
      console.log('[AI Suggestions] Added source field:', field.src_column_name)
    }
  }
  
  // Action: Set multiple source fields (for template completion)
  function setSourceFields(fields: UnmappedField[]) {
    sourceFieldsUsed.value = [...fields]
    console.log('[AI Suggestions] Set source fields:', fields.map(f => f.src_column_name))
  }

  return {
    // State
    suggestions,
    loading,
    error,
    sourceFieldsUsed,
    selectedSuggestion,
    historicalPatterns,
    patternTemplates,
    recommendedExpression,
    detectedPatternType,
    selectedTemplatePattern,
    
    // Computed
    hasSuggestions,
    hasOptions,
    topSuggestion,
    hasRelevantTemplates,
    topTemplate,
    multiColumnPatterns,
    unifiedOptions,
    
    // Actions
    generateSuggestions,
    selectSuggestion,
    selectPatternAsTemplate,
    clearSelectedTemplate,
    clearSuggestions,
    addSourceField,
    setSourceFields
  }
})

