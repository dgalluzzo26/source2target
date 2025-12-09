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
  source_columns?: string
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
    topSuggestion,
    hasRelevantTemplates,
    topTemplate,
    multiColumnPatterns,
    
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

