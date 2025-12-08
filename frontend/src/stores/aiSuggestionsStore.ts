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
    loading.value = true
    error.value = null
    suggestions.value = []
    sourceFieldsUsed.value = [...sourceFields]
    historicalPatterns.value = []

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
      console.log('[AI Suggestions] V3 API response:', data)
      
      // V3 API returns target_candidates, historical_patterns, best_target, etc.
      // Transform target_candidates into AISuggestion format
      const targetCandidates = data.target_candidates || []
      const bestTarget = data.best_target || {}
      const llmReasoning = bestTarget.reasoning || data.recommended_expression || ''
      
      // Transform target candidates into suggestion format
      suggestions.value = targetCandidates.map((candidate: any, idx: number) => {
        const score = candidate.search_score || 0
        const isBestTarget = bestTarget.tgt_column_name === candidate.tgt_column_name
        
        return {
          semantic_field_id: candidate.semantic_field_id || 0,
          tgt_table_name: candidate.tgt_table_name || '',
          tgt_table_physical_name: candidate.tgt_table_physical_name || candidate.tgt_table_name || '',
          tgt_column_name: candidate.tgt_column_name || '',
          tgt_column_physical_name: candidate.tgt_column_physical_name || candidate.tgt_column_name || '',
          tgt_comments: candidate.tgt_comments || '',
          search_score: score,
          match_quality: getMatchQuality(score, isBestTarget),
          ai_reasoning: isBestTarget ? llmReasoning : (candidate.tgt_comments || `Vector search match (${Math.round(score * 100)}%)`),
          rank: idx + 1
        } as AISuggestion
      })
      
      // Store historical patterns
      historicalPatterns.value = data.historical_patterns || []
      
      // Debug output
      console.log('[AI Suggestions] Transformed', suggestions.value.length, 'suggestions')
      if (suggestions.value.length > 0) {
        console.log('[AI Suggestions] Top suggestion:', suggestions.value[0])
      }
      if (historicalPatterns.value.length > 0) {
        console.log('[AI Suggestions] Found', historicalPatterns.value.length, 'historical patterns')
      }
      if (bestTarget.tgt_column_name) {
        console.log('[AI Suggestions] LLM best target:', bestTarget.tgt_column_name, 'confidence:', bestTarget.confidence)
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
    if (isBestTarget) return 'Excellent'
    if (score >= 0.85) return 'Excellent'
    if (score >= 0.70) return 'Strong'
    if (score >= 0.50) return 'Good'
    if (score >= 0.30) return 'Weak'
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

