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
            unmapped_field_id: f.unmapped_field_id,
            src_table_name: f.src_table_name,
            src_table_physical_name: f.src_table_physical_name,
            src_column_name: f.src_column_name,
            src_column_physical_name: f.src_column_physical_name,
            src_physical_datatype: f.src_physical_datatype,
            src_comments: f.src_comments || ''
          })),
          num_suggestions: 10
        })
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`API error: ${response.status} - ${errorText}`)
      }

      const data = await response.json()
      
      // Handle response format - might be suggestions array or object with suggestions + patterns
      if (Array.isArray(data)) {
        suggestions.value = data
      } else {
        suggestions.value = data.suggestions || []
        historicalPatterns.value = data.historical_patterns || []
      }
      
      // Debug: Check response
      if (suggestions.value.length > 0) {
        console.log('[AI Suggestions] Sample suggestion:', suggestions.value[0])
      }
      
      // Add rank to each suggestion
      suggestions.value.forEach((sug, idx) => {
        sug.rank = idx + 1
      })

      console.log('[AI Suggestions] Generated', suggestions.value.length, 'suggestions')
      if (historicalPatterns.value.length > 0) {
        console.log('[AI Suggestions] Found', historicalPatterns.value.length, 'historical patterns')
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate suggestions'
      console.error('[AI Suggestions] Error:', error.value)
      suggestions.value = []
    } finally {
      loading.value = false
    }
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

