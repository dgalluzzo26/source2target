/**
 * AI Suggestions Store V2 (Multi-Field)
 * 
 * Manages AI-powered mapping suggestions for multiple source fields.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UnmappedField } from './unmappedFieldsStore'

export interface AISuggestionV2 {
  semantic_field_id: number  // FK to semantic_fields table
  tgt_table_name: string
  tgt_table_physical_name: string
  tgt_column_name: string
  tgt_column_physical_name: string
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
      // TODO: Replace with real API call
      // const response = await fetch('/api/v2/ai-mapping/suggestions', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({
      //     source_fields: sourceFields.map(f => ({
      //       src_table_name: f.src_table_name,
      //       src_table_physical_name: f.src_table_physical_name,
      //       src_column_name: f.src_column_name,
      //       src_column_physical_name: f.src_column_physical_name,
      //       src_physical_datatype: f.src_physical_datatype,
      //       src_comments: f.src_comments
      //     })),
      //     num_results: 10
      //   })
      // })
      // suggestions.value = await response.json()

      // Mock: Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1500))

      // Generate mock suggestions based on source fields
      suggestions.value = generateMockSuggestions(sourceFields)
      
      // Add rank
      suggestions.value.forEach((sug, idx) => {
        sug.rank = idx + 1
      })

      console.log('[AI Suggestions V2] Generated', suggestions.value.length, 'suggestions for', sourceFields.length, 'fields')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to generate suggestions'
      console.error('[AI Suggestions V2] Error:', error.value)
    } finally {
      loading.value = false
    }
  }

  function generateMockSuggestions(sourceFields: UnmappedField[]): AISuggestionV2[] {
    // Single field suggestions
    if (sourceFields.length === 1) {
      const field = sourceFields[0]
      
      if (field.src_column_name === 'SSN') {
        return [
          {
            semantic_field_id: 1,
            tgt_table_name: 'slv_member',
            tgt_table_physical_name: 'slv_member',
            tgt_column_name: 'ssn_number',
            tgt_column_physical_name: 'ssn_number',
            search_score: 0.045,
            match_quality: 'Excellent',
            ai_reasoning: 'Strong semantic match for Social Security Number. This is the standard field name for SSN storage in the target schema.'
          },
          {
            semantic_field_id: 2,
            tgt_table_name: 'slv_member',
            tgt_table_physical_name: 'slv_member',
            tgt_column_name: 'member_ssn',
            tgt_column_physical_name: 'member_ssn',
            search_score: 0.039,
            match_quality: 'Strong',
            ai_reasoning: 'Common alternative field name for SSN storage. Used in 8 previous mappings.'
          },
          {
            semantic_field_id: 3,
            tgt_table_name: 'slv_person',
            tgt_table_physical_name: 'slv_person',
            tgt_column_name: 'social_security_number',
            tgt_column_physical_name: 'social_security_number',
            search_score: 0.042,
            match_quality: 'Strong',
            ai_reasoning: 'Full field name variant. Good match but less commonly used in this schema.'
          },
          {
            semantic_field_id: 4,
            tgt_table_name: 'slv_member',
            tgt_table_physical_name: 'slv_member',
            tgt_column_name: 'ssn',
            tgt_column_physical_name: 'ssn',
            search_score: 0.038,
            match_quality: 'Good',
            ai_reasoning: 'Abbreviated SSN field. Semantic similarity indicates reasonable match.'
          }
        ]
      } else if (field.src_column_name === 'NPI') {
        return [
          {
            semantic_field_id: 5,
            tgt_table_name: 'slv_provider',
            tgt_table_physical_name: 'slv_provider',
            tgt_column_name: 'npi_number',
            tgt_column_physical_name: 'npi_number',
            search_score: 0.048,
            match_quality: 'Excellent',
            ai_reasoning: 'Perfect match for National Provider Identifier. This is the standard NPI field in the provider table.'
          },
          {
            semantic_field_id: 6,
            tgt_table_name: 'slv_provider',
            tgt_table_physical_name: 'slv_provider',
            tgt_column_name: 'provider_npi',
            tgt_column_physical_name: 'provider_npi',
            search_score: 0.044,
            match_quality: 'Strong',
            ai_reasoning: 'Alternative NPI field name. Used in 5 previous provider mappings.'
          }
        ]
      }
    }

    // Multi-field suggestions
    const fieldNames = sourceFields.map(f => f.src_column_name).join(' + ')
    
    // FIRST_NAME + LAST_NAME
    if (fieldNames === 'FIRST_NAME + LAST_NAME') {
      return [
        {
          semantic_field_id: 7,
          tgt_table_name: 'slv_member',
          tgt_table_physical_name: 'slv_member',
          tgt_column_name: 'full_name',
          tgt_column_physical_name: 'full_name',
          search_score: 0.042,
          match_quality: 'Excellent',
          ai_reasoning: 'The combination of FIRST_NAME and LAST_NAME strongly correlates with full_name. This is the standard pattern confirmed by 15 historical mappings.'
        },
        {
          semantic_field_id: 8,
          tgt_table_name: 'slv_member',
          tgt_table_physical_name: 'slv_member',
          tgt_column_name: 'member_name',
          tgt_column_physical_name: 'member_name',
          search_score: 0.038,
          match_quality: 'Strong',
          ai_reasoning: 'Member name is a common alternative for storing combined first and last names. Used in 3 historical mappings.'
        },
        {
          semantic_field_id: 9,
          tgt_table_name: 'slv_person',
          tgt_table_physical_name: 'slv_person',
          tgt_column_name: 'person_full_name',
          tgt_column_physical_name: 'person_full_name',
          search_score: 0.035,
          match_quality: 'Good',
          ai_reasoning: 'Person table variant. Good semantic match but less commonly used in this schema.'
        },
        {
          semantic_field_id: 10,
          tgt_table_name: 'slv_member',
          tgt_table_physical_name: 'slv_member',
          tgt_column_name: 'first_last_name',
          tgt_column_physical_name: 'first_last_name',
          search_score: 0.029,
          match_quality: 'Good',
          ai_reasoning: 'Direct concatenation field. Moderate semantic similarity indicates reasonable match.'
        }
      ]
    }

    // ADDRESS_LINE1 + CITY + STATE + ZIP_CODE
    if (fieldNames.includes('ADDRESS') && fieldNames.includes('CITY')) {
      return [
        {
          semantic_field_id: 11,
          tgt_table_name: 'slv_member',
          tgt_table_physical_name: 'slv_member',
          tgt_column_name: 'full_address',
          tgt_column_physical_name: 'full_address',
          search_score: 0.041,
          match_quality: 'Excellent',
          ai_reasoning: 'The combination of address components (line1, city, state, zip) maps perfectly to full_address. This is the standard address concatenation pattern.'
        },
        {
          semantic_field_id: 12,
          tgt_table_name: 'slv_member',
          tgt_table_physical_name: 'slv_member',
          tgt_column_name: 'mailing_address',
          tgt_column_physical_name: 'mailing_address',
          search_score: 0.037,
          match_quality: 'Strong',
          ai_reasoning: 'Mailing address is a common variant for combined address fields. Good semantic match.'
        },
        {
          semantic_field_id: 13,
          tgt_table_name: 'slv_location',
          tgt_table_physical_name: 'slv_location',
          tgt_column_name: 'location_address',
          tgt_column_physical_name: 'location_address',
          search_score: 0.033,
          match_quality: 'Good',
          ai_reasoning: 'Location table address field. Reasonable match for address concatenation.'
        }
      ]
    }

    // Default: generic suggestions
    return [
      {
        semantic_field_id: 14,
        tgt_table_name: 'slv_member',
        tgt_table_physical_name: 'slv_member',
        tgt_column_name: 'combined_field',
        tgt_column_physical_name: 'combined_field',
        search_score: 0.025,
        match_quality: 'Good',
        ai_reasoning: `Moderate semantic similarity for the combination: ${fieldNames}. Review suggested target field carefully.`
      },
      {
        semantic_field_id: 15,
        tgt_table_name: 'slv_member',
        tgt_table_physical_name: 'slv_member',
        tgt_column_name: 'concatenated_value',
        tgt_column_physical_name: 'concatenated_value',
        search_score: 0.021,
        match_quality: 'Weak',
        ai_reasoning: 'Generic concatenation field. Lower confidence - manual verification recommended.'
      }
    ]
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

