/**
 * AI Suggestions Store V2 (Multi-Field)
 * 
 * Manages AI-powered mapping suggestions for multiple source fields.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UnmappedField } from './unmappedFieldsStore'

export interface AISuggestionV2 {
  semantic_field_id?: number  // FK to semantic_fields table (optional)
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

export const useAISuggestionsStoreV2 = defineStore('aiSuggestionsV2', () => {
  // State
  const suggestions = ref<AISuggestionV2[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const sourceFieldsUsed = ref<UnmappedField[]>([])
  const selectedSuggestion = ref<AISuggestionV2 | null>(null)

  // Computed
  const hasSuggestions = computed(() => suggestions.value.length > 0)
  const topSuggestion = computed(() => suggestions.value[0] || null)
  
  // Actions
  async function generateSuggestions(sourceFields: UnmappedField[]) {
    loading.value = true
    error.value = null
    suggestions.value = []
    sourceFieldsUsed.value = [...sourceFields]

    try {
      console.log('[AI Suggestions V2] Calling real API for', sourceFields.length, 'source fields')
      
      const response = await fetch('/api/v2/ai-mapping/suggestions', {
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

      suggestions.value = await response.json()
      
      // Add rank to each suggestion
      suggestions.value.forEach((sug, idx) => {
        sug.rank = idx + 1
      })

      console.log('[AI Suggestions V2] Generated', suggestions.value.length, 'suggestions for', sourceFields.length, 'fields')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate suggestions'
      console.error('[AI Suggestions V2] Error:', error.value)
      suggestions.value = []
    } finally {
      loading.value = false
    }
  }

  function selectSuggestion(suggestion: AISuggestionV2) {
    selectedSuggestion.value = suggestion
    console.log('[AI Suggestions V2] Selected:', suggestion.tgt_column_name)
  }

  function clearSuggestions() {
    suggestions.value = []
    sourceFieldsUsed.value = []
    selectedSuggestion.value = null
    error.value = null
    console.log('[AI Suggestions V2] Cleared suggestions')
  }

  return {
    // State
    suggestions,
    loading,
    error,
    sourceFieldsUsed,
    selectedSuggestion,
    
    // Computed
    hasSuggestions,
    topSuggestion,
    
    // Actions
    generateSuggestions,
    selectSuggestion,
    clearSuggestions
  }
})

