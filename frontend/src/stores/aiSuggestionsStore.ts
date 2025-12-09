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
  source_relationship_type?: string
  transformations_applied?: string
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
  
  // Track top score for relative quality calculation (used by getMatchQuality)
  let topVectorScore = 0

  // Computed
  const hasSuggestions = computed(() => suggestions.value.length > 0)
  const topSuggestion = computed(() => suggestions.value[0] || null)
  
  // Pattern templates that suggest the user should add more fields
  const hasRelevantTemplates = computed(() => patternTemplates.value.length > 0)
  const topTemplate = computed(() => patternTemplates.value[0] || null)
  
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
  
  // Unified ranked list combining AI suggestions and historical patterns
  const unifiedOptions = computed((): UnifiedMappingOption[] => {
    const options: UnifiedMappingOption[] = []
    
    // Add AI suggestions (from vector search on semantic_fields)
    suggestions.value.forEach((s, idx) => {
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
    
    // Add historical patterns that aren't already in suggestions
    // (patterns are from vector search on mapped_fields - similar SOURCE mappings)
    historicalPatterns.value.forEach((p) => {
      // Check if this pattern's target is already in options
      const alreadyExists = options.some(o => 
        o.tgt_column_name.toLowerCase() === p.tgt_column_name.toLowerCase() &&
        o.tgt_table_name.toLowerCase() === p.tgt_table_name.toLowerCase()
      )
      
      if (!alreadyExists) {
        // Use normalized search_score (already x100 from processPatterns)
        // Combined with templateRelevance for better ranking
        const score = Math.max(p.search_score || 0, p.templateRelevance || 0)
        
        // Auto-match pattern fields to user's selected fields
        const { mappings, allMatched, generatedSQL } = autoMatchPatternFields(p)
        
        console.log(`[Unified Options] Adding pattern ${p.tgt_column_name}:`, {
          search_score: p.search_score,
          templateRelevance: p.templateRelevance,
          finalScore: score,
          mappingsCount: mappings.length,
          allMatched,
          generatedSQL: generatedSQL?.substring(0, 50)
        })
        
        options.push({
          id: `pattern-${p.mapped_field_id}`,
          rank: 0,
          source: 'pattern',
          tgt_table_name: p.tgt_table_name,
          tgt_table_physical_name: p.tgt_table_physical_name || p.tgt_table_name,
          tgt_column_name: p.tgt_column_name,
          tgt_column_physical_name: p.tgt_column_physical_name || p.tgt_column_name,
          tgt_comments: '',
          matchQuality: 'Unknown',  // Will be set after sorting by rank
          score: score,
          suggestedMappings: mappings,
          allFieldsMatched: allMatched,
          generatedSQL: generatedSQL,
          reasoning: p.transformations_applied 
            ? `Historical pattern using ${p.transformations_applied}`
            : 'Based on similar past mapping',
          pattern: p,
          sourceColumns: p.source_columns,
          transformations: p.transformations_applied,
          isMultiColumn: p.isMultiColumn
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
      
      // If quality wasn't already set (patterns come in as Unknown), set by rank
      if (opt.matchQuality === 'Unknown') {
        // Rank-based quality for consistency
        if (opt.rank === 1) opt.matchQuality = 'Excellent'
        else if (opt.rank <= 3) opt.matchQuality = 'Strong'
        else if (opt.rank <= 6) opt.matchQuality = 'Good'
        else opt.matchQuality = 'Weak'
      }
      
      // Boost pattern quality if it's in top 5 (patterns are valuable context)
      if (opt.source === 'pattern' && opt.rank <= 5 && opt.matchQuality === 'Weak') {
        opt.matchQuality = 'Good'
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
        topVectorScore = normalizeScore(rawTop)
        console.log('[AI Suggestions] Top vector score (normalized):', topVectorScore)
      }
      
      // Transform target candidates into suggestion format
      suggestions.value = targetCandidates.map((candidate: any, idx: number) => {
        // Parse score - might be number, string, or undefined
        // Databricks vector search returns raw cosine similarity scores (typically 0.001-0.01 range)
        // Multiply by 100 to get a more intuitive 0-1 scale (e.g., 0.00576 -> 0.576)
        let score = 0
        if (candidate.search_score !== undefined && candidate.search_score !== null) {
          const rawScore = typeof candidate.search_score === 'string' 
            ? parseFloat(candidate.search_score) 
            : Number(candidate.search_score)
          
          // If score is very small (< 0.1), multiply by 100 to normalize
          // This handles Databricks vector search raw scores
          score = rawScore < 0.1 ? rawScore * 100 : rawScore
        }
        
        // Check if this is the LLM's best target (case-insensitive comparison)
        const candidateCol = (candidate.tgt_column_name || '').toLowerCase().trim()
        const bestTargetCol = (bestTarget.tgt_column_name || '').toLowerCase().trim()
        const isBestTarget = candidateCol === bestTargetCol && candidateCol !== ''
        
        // Also check table name match if available
        const candidateTable = (candidate.tgt_table_name || '').toLowerCase().trim()
        const bestTargetTable = (bestTarget.tgt_table_name || '').toLowerCase().trim()
        const isExactMatch = isBestTarget && (bestTargetTable === '' || candidateTable === bestTargetTable)
        
        // Determine match quality FIRST (before logging)
        // Pass rank (idx + 1) for rank-based quality since vector scores are compressed
        const matchQuality = getMatchQuality(score, isExactMatch, idx + 1)
        
        // Debug first few candidates
        if (idx < 5) {
          const rawScore = candidate.search_score
          console.log(`[AI Suggestions] Candidate ${idx + 1}:`, {
            column: candidate.tgt_column_name,
            rawScore: rawScore,
            normalizedScore: score,
            wasNormalized: rawScore < 0.02,
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
          // Score is 0-1 similarity, display as decimal (e.g., 0.85) not percentage
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
  
  // Helper: Normalize Databricks vector search scores
  // Raw scores from Databricks are typically in 0.001-0.01 range
  // We multiply by 100 to get a more intuitive 0-1 scale
  // BUT only for very small scores that are clearly raw Databricks scores
  function normalizeScore(rawScore: number): number {
    if (!rawScore || isNaN(rawScore)) return 0
    // Only normalize if score is VERY small (< 0.02) - clearly a raw Databricks score
    // Scores >= 0.02 are likely already in a reasonable range
    if (rawScore < 0.02) {
      return rawScore * 100
    }
    return rawScore
  }
  
  // Helper: Convert score to match quality using HYBRID scoring
  // Combines:
  // 1. ABSOLUTE threshold - if top score is low, cap quality levels
  // 2. RELATIVE position - distance from top score determines tier within cap
  function getMatchQuality(score: number, isBestTarget: boolean, rank?: number): 'Excellent' | 'Strong' | 'Good' | 'Weak' | 'Unknown' {
    // LLM's best target always gets Excellent (AI validated this match)
    if (isBestTarget) return 'Excellent'
    
    // Handle invalid scores
    if (isNaN(score) || score === null || score === undefined) {
      console.warn('[AI Suggestions] Invalid score:', score)
      return 'Unknown'
    }
    
    // Determine the quality CAP based on the absolute top score
    // This ensures weak vector search results don't show misleading "Strong" ratings
    let maxQuality: 'Strong' | 'Good' | 'Weak' = 'Weak'
    if (topVectorScore >= 0.50) {
      maxQuality = 'Strong'  // Top score is solid - allow Strong for rank 1
    } else if (topVectorScore >= 0.35) {
      maxQuality = 'Good'    // Top score is moderate - cap at Good
    } else {
      maxQuality = 'Weak'    // Top score is weak - all results are Weak
    }
    
    // Now determine quality within the cap using rank
    let quality: 'Strong' | 'Good' | 'Weak' = 'Weak'
    
    if (rank !== undefined) {
      // Rank-based quality (relative positioning)
      if (rank === 1) {
        quality = 'Strong'
      } else if (rank <= 3) {
        quality = 'Good'
      } else {
        quality = 'Weak'
      }
    } else if (topVectorScore > 0 && score > 0) {
      // Fallback: Use score ratio
      const relativeScore = score / topVectorScore
      if (relativeScore >= 0.98) {
        quality = 'Strong'
      } else if (relativeScore >= 0.90) {
        quality = 'Good'
      } else {
        quality = 'Weak'
      }
    }
    
    // Apply the cap - quality cannot exceed maxQuality
    const qualityOrder = ['Weak', 'Good', 'Strong'] as const
    const qualityIdx = qualityOrder.indexOf(quality)
    const maxIdx = qualityOrder.indexOf(maxQuality)
    const cappedQuality = qualityOrder[Math.min(qualityIdx, maxIdx)]
    
    // Debug log for first few
    if (rank && rank <= 3) {
      console.log(`[AI Suggestions] Quality for rank ${rank}: topScore=${topVectorScore.toFixed(3)}, maxQuality=${maxQuality}, rawQuality=${quality}, capped=${cappedQuality}`)
    }
    
    return cappedQuality
  }
  
  // Helper: Process historical patterns to detect multi-column mappings
  function processPatterns(patterns: any[], selectedFields: UnmappedField[]): HistoricalPattern[] {
    const selectedColNames = new Set(
      selectedFields.map(f => (f.src_column_physical_name || f.src_column_name || '').toLowerCase())
    )
    const selectedColWords = new Set<string>()
    selectedFields.forEach(f => {
      const words = (f.src_column_physical_name || f.src_column_name || '').toLowerCase().split(/[_\s]+/)
      words.forEach(w => selectedColWords.add(w))
    })
    
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
      
      // Calculate how well this pattern matches the current selection
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
      
      // Log relevance calculation for debugging
      if (isMultiColumn) {
        console.log(`[AI Suggestions] Pattern relevance calc for ${p.tgt_column_name}:`, {
          sourceCols,
          selectedCols: Array.from(selectedColNames),
          matchedCols,
          rawRelevance: relevance,
          normalizedRelevance: normalizedRelevance.toFixed(3),
          isMultiColumn
        })
      }
      
      return {
        ...p,
        isMultiColumn,
        columnCount: sourceCols.length,
        matchedToCurrentSelection: matchedCols > 0,
        templateRelevance: normalizedRelevance,
        // Normalize search scores - Databricks returns raw scores that need x100
        search_score: normalizeScore(typeof p.search_score === 'number' ? p.search_score : parseFloat(p.search_score) || 0),
        confidence_score: normalizeScore(typeof p.confidence_score === 'number' ? p.confidence_score : parseFloat(p.confidence_score) || 0)
      } as HistoricalPattern
    }).sort((a, b) => {
      // Sort by relevance first, then by search score
      if (b.templateRelevance !== a.templateRelevance) {
        return (b.templateRelevance || 0) - (a.templateRelevance || 0)
      }
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

