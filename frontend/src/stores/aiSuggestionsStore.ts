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
      
      // Transform target candidates into suggestion format
      suggestions.value = targetCandidates.map((candidate: any, idx: number) => {
        // Parse score - might be number, string, or undefined
        let score = 0
        if (candidate.search_score !== undefined && candidate.search_score !== null) {
          score = typeof candidate.search_score === 'string' 
            ? parseFloat(candidate.search_score) 
            : Number(candidate.search_score)
        }
        
        // Check if this is the LLM's best target (case-insensitive comparison)
        const candidateCol = (candidate.tgt_column_name || '').toLowerCase().trim()
        const bestTargetCol = (bestTarget.tgt_column_name || '').toLowerCase().trim()
        const isBestTarget = candidateCol === bestTargetCol && candidateCol !== ''
        
        // Also check table name match if available
        const candidateTable = (candidate.tgt_table_name || '').toLowerCase().trim()
        const bestTargetTable = (bestTarget.tgt_table_name || '').toLowerCase().trim()
        const isExactMatch = isBestTarget && (bestTargetTable === '' || candidateTable === bestTargetTable)
        
        // Debug first few candidates
        if (idx < 3) {
          console.log(`[AI Suggestions] Candidate ${idx + 1}:`, {
            column: candidate.tgt_column_name,
            score: candidate.search_score,
            parsedScore: score,
            isBestTarget: isExactMatch,
            bestTargetCol
          })
        }
        
        // Determine match quality
        const matchQuality = getMatchQuality(score, isExactMatch)
        
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
      
      // Process historical patterns with enhanced analysis
      const patternsFromApi = data.historical_patterns || []
      console.log('[AI Suggestions] Historical patterns received from API:', patternsFromApi.length)
      
      // Enhance patterns with analysis
      const enhancedPatterns = processPatterns(patternsFromApi, sourceFields)
      historicalPatterns.value = enhancedPatterns
      
      // Generate pattern templates for multi-column patterns
      const templates = generatePatternTemplates(enhancedPatterns, sourceFields, allAvailableFields || [])
      patternTemplates.value = templates
      
      console.log('[AI Suggestions] Enhanced patterns:', enhancedPatterns.length)
      console.log('[AI Suggestions] Pattern templates generated:', templates.length)
      
      // BOOST: If historical patterns strongly match target columns, boost those suggestions
      // This addresses the issue where vector search gives weak scores for combined fields
      // but historical patterns show what target should be used
      if (enhancedPatterns.length > 0 && suggestions.value.length > 0) {
        boostPatternMatchingSuggestions(enhancedPatterns)
      }
      
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
  
  // Helper: Convert score to match quality
  function getMatchQuality(score: number, isBestTarget: boolean): 'Excellent' | 'Strong' | 'Good' | 'Weak' | 'Unknown' {
    // LLM's best target always gets Excellent
    if (isBestTarget) return 'Excellent'
    
    // Handle invalid scores
    if (isNaN(score) || score === null || score === undefined) {
      console.warn('[AI Suggestions] Invalid score:', score)
      return 'Unknown'
    }
    
    // Vector search scores are typically 0-1
    // But some systems return 0-100, so normalize if needed
    const normalizedScore = score > 1 ? score / 100 : score
    
    if (normalizedScore >= 0.85) return 'Excellent'
    if (normalizedScore >= 0.70) return 'Strong'
    if (normalizedScore >= 0.50) return 'Good'
    if (normalizedScore >= 0.30) return 'Weak'
    if (normalizedScore > 0) return 'Weak'  // Any positive score is at least Weak
    return 'Unknown'
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
      
      return {
        ...p,
        isMultiColumn,
        columnCount: sourceCols.length,
        matchedToCurrentSelection: matchedCols > 0,
        templateRelevance: normalizedRelevance,
        search_score: typeof p.search_score === 'number' ? p.search_score : parseFloat(p.search_score) || 0,
        confidence_score: typeof p.confidence_score === 'number' ? p.confidence_score : parseFloat(p.confidence_score) || 0
      } as HistoricalPattern
    }).sort((a, b) => {
      // Sort by relevance first, then by search score
      if (b.templateRelevance !== a.templateRelevance) {
        return (b.templateRelevance || 0) - (a.templateRelevance || 0)
      }
      return (b.search_score || 0) - (a.search_score || 0)
    })
  }
  
  // Helper: Boost suggestions that match high-relevance historical patterns
  function boostPatternMatchingSuggestions(patterns: HistoricalPattern[]) {
    // Get patterns that are highly relevant to the user's selection
    const relevantPatterns = patterns.filter(p => (p.templateRelevance || 0) > 0.5)
    
    if (relevantPatterns.length === 0) {
      console.log('[AI Suggestions] No highly relevant patterns to boost from')
      return
    }
    
    console.log('[AI Suggestions] Checking', relevantPatterns.length, 'relevant patterns for boosting')
    
    // For each relevant pattern, find matching suggestions
    for (const pattern of relevantPatterns) {
      const patternTarget = (pattern.tgt_column_name || '').toLowerCase()
      const patternTable = (pattern.tgt_table_name || '').toLowerCase()
      
      const matchingIdx = suggestions.value.findIndex(s => {
        const sugTarget = (s.tgt_column_name || '').toLowerCase()
        const sugTable = (s.tgt_table_name || '').toLowerCase()
        return sugTarget === patternTarget && (patternTable === '' || sugTable === patternTable)
      })
      
      if (matchingIdx >= 0) {
        const suggestion = suggestions.value[matchingIdx]
        
        // Boost this suggestion
        const boosted = {
          ...suggestion,
          match_quality: 'Excellent' as const,
          ai_reasoning: `Historical pattern match (${Math.round((pattern.templateRelevance || 0) * 100)}% relevance): This target has been successfully mapped ${pattern.columnCount || 1} time(s) with similar source fields using ${pattern.transformations_applied || 'direct mapping'}.`,
          fromPattern: true,
          patternId: pattern.mapped_field_id
        }
        
        // If not already at top, move to position 0 or 1 (after LLM best if present)
        if (matchingIdx > 1) {
          suggestions.value.splice(matchingIdx, 1)
          // Insert at position 1 (after LLM best) or 0 if LLM best isn't excellent
          const insertIdx = suggestions.value[0]?.match_quality === 'Excellent' && !suggestions.value[0]?.fromPattern ? 1 : 0
          suggestions.value.splice(insertIdx, 0, boosted)
        } else {
          // Just update in place
          suggestions.value[matchingIdx] = boosted
        }
        
        // Re-rank all suggestions
        suggestions.value.forEach((s, i) => { s.rank = i + 1 })
        
        console.log('[AI Suggestions] Boosted pattern-matching suggestion:', patternTarget, 'to rank', suggestions.value.findIndex(s => s.tgt_column_name?.toLowerCase() === patternTarget) + 1)
      }
    }
  }
  
  // Helper: Generate pattern templates for incomplete multi-column patterns
  function generatePatternTemplates(
    patterns: HistoricalPattern[], 
    selectedFields: UnmappedField[],
    availableFields: UnmappedField[]
  ): PatternTemplate[] {
    const templates: PatternTemplate[] = []
    const selectedColNames = new Set(
      selectedFields.map(f => (f.src_column_physical_name || f.src_column_name || '').toLowerCase())
    )
    
    // Only consider multi-column patterns where user has selected some but not all fields
    patterns
      .filter(p => p.isMultiColumn && p.matchedToCurrentSelection)
      .forEach(pattern => {
        const sourceColsStr = pattern.source_columns || ''
        const sourceCols = sourceColsStr.split(/[|,]/).map(c => c.trim()).filter(c => c)
        
        if (sourceCols.length <= 1) return
        
        const selectedInPattern: string[] = []
        const missingInPattern: string[] = []
        
        sourceCols.forEach(col => {
          const colLower = col.toLowerCase()
          const colWords = colLower.split(/[_\s]+/)
          
          // Check if any selected field matches this column
          const isSelected = selectedFields.some(f => {
            const fCol = (f.src_column_physical_name || f.src_column_name || '').toLowerCase()
            const fWords = fCol.split(/[_\s]+/)
            
            // Direct match
            if (fCol === colLower) return true
            
            // Word overlap match (e.g., "street_num" matches "street_number")
            const overlap = fWords.filter(w => colWords.some(cw => cw.includes(w) || w.includes(cw))).length
            return overlap >= Math.min(fWords.length, colWords.length) * 0.6
          })
          
          if (isSelected) {
            selectedInPattern.push(col)
          } else {
            missingInPattern.push(col)
          }
        })
        
        // Only create template if user has some fields selected but not all
        if (selectedInPattern.length > 0 && missingInPattern.length > 0) {
          // Calculate how likely the missing fields exist in available fields
          const hasPossibleMatches = missingInPattern.some(missing => {
            const missingWords = missing.toLowerCase().split(/[_\s]+/)
            return availableFields.some(f => {
              const fCol = (f.src_column_physical_name || f.src_column_name || '').toLowerCase()
              const fWords = fCol.split(/[_\s]+/)
              const overlap = fWords.filter(w => missingWords.some(mw => mw.includes(w) || w.includes(mw))).length
              return overlap > 0
            })
          })
          
          templates.push({
            pattern,
            relevanceScore: pattern.templateRelevance || 0,
            selectedFields: selectedInPattern,
            missingFields: missingInPattern,
            isComplete: false,
            suggestedSQL: pattern.source_expression || ''
          })
        }
      })
    
    // Sort by relevance score
    return templates.sort((a, b) => b.relevanceScore - a.relevanceScore)
  }

  function selectSuggestion(suggestion: AISuggestion) {
    selectedSuggestion.value = suggestion
    console.log('[AI Suggestions] Selected:', suggestion.tgt_column_name)
  }

  function clearSuggestions() {
    suggestions.value = []
    sourceFieldsUsed.value = []
    selectedSuggestion.value = null
    historicalPatterns.value = []
    patternTemplates.value = []
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
    
    // Computed
    hasSuggestions,
    topSuggestion,
    hasRelevantTemplates,
    topTemplate,
    multiColumnPatterns,
    
    // Actions
    generateSuggestions,
    selectSuggestion,
    clearSuggestions,
    addSourceField,
    setSourceFields
  }
})

