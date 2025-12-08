/**
 * AI Suggestions Store
 * 
 * Manages AI-powered mapping suggestions for source fields.
 * Uses V3 API with dual vector search (semantic + historical patterns).
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
}

export const useAISuggestionsStore = defineStore('aiSuggestions', () => {
  // State
  const suggestions = ref<AISuggestion[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const sourceFieldsUsed = ref<UnmappedField[]>([])
  const selectedSuggestion = ref<AISuggestion | null>(null)
  const historicalPatterns = ref<any[]>([])

  // Computed
  const hasSuggestions = computed(() => suggestions.value.length > 0)
  const topSuggestion = computed(() => suggestions.value[0] || null)
  
  // Actions
  async function generateSuggestions(sourceFields: UnmappedField[]) {
    // IMPORTANT: Clear ALL previous state first
    console.log('[AI Suggestions] === Starting new suggestion request ===')
    console.log('[AI Suggestions] Clearing previous state...')
    
    loading.value = true
    error.value = null
    suggestions.value = []
    historicalPatterns.value = []  // Clear patterns BEFORE setting sourceFields
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
      
      // Store historical patterns from API response
      const patternsFromApi = data.historical_patterns || []
      console.log('[AI Suggestions] Historical patterns received from API:', patternsFromApi.length)
      if (patternsFromApi.length > 0) {
        console.log('[AI Suggestions] Pattern targets:', patternsFromApi.map((p: any) => p.tgt_column_name))
      }
      historicalPatterns.value = patternsFromApi
      
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

  function selectSuggestion(suggestion: AISuggestion) {
    selectedSuggestion.value = suggestion
    console.log('[AI Suggestions] Selected:', suggestion.tgt_column_name)
  }

  function clearSuggestions() {
    suggestions.value = []
    sourceFieldsUsed.value = []
    selectedSuggestion.value = null
    historicalPatterns.value = []
    error.value = null
    console.log('[AI Suggestions] Cleared suggestions')
  }

  return {
    // State
    suggestions,
    loading,
    error,
    sourceFieldsUsed,
    selectedSuggestion,
    historicalPatterns,
    
    // Computed
    hasSuggestions,
    topSuggestion,
    
    // Actions
    generateSuggestions,
    selectSuggestion,
    clearSuggestions
  }
})

