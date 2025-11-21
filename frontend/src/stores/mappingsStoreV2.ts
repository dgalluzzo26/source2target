/**
 * Mappings Store V2 (Multi-Field)
 * 
 * Manages completed multi-field mappings.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface MappingDetailV2 {
  detail_id?: number
  src_table_name: string
  src_table_physical_name: string
  src_column_name: string
  src_column_physical_name: string
  field_order: number
  transformation_expr?: string
  added_at?: string
}

export interface MappedFieldV2 {
  mapping_id?: number
  tgt_table_name: string
  tgt_table_physical_name: string
  tgt_column_name: string
  tgt_column_physical_name: string
  concat_strategy: 'SPACE' | 'COMMA' | 'PIPE' | 'CUSTOM' | 'NONE'
  concat_separator?: string
  transformation_expression?: string
  confidence_score?: number
  mapping_source?: string
  ai_reasoning?: string
  mapping_status?: string
  mapped_at?: string
  mapped_by?: string
  source_fields: MappingDetailV2[]
}

export interface Transformation {
  transformation_id: number
  transformation_name: string
  transformation_code: string
  transformation_expression: string
  transformation_description: string
  category: string
  is_system?: boolean
}

export const useMappingsStoreV2 = defineStore('mappingsV2', () => {
  // State
  const mappings = ref<MappedFieldV2[]>([])
  const transformations = ref<Transformation[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Mock transformations
  const mockTransformations: Transformation[] = [
    {
      transformation_id: 1,
      transformation_name: 'Trim Whitespace',
      transformation_code: 'TRIM',
      transformation_expression: 'TRIM({field})',
      transformation_description: 'Remove leading and trailing whitespace',
      category: 'STRING',
      is_system: true
    },
    {
      transformation_id: 2,
      transformation_name: 'Upper Case',
      transformation_code: 'UPPER',
      transformation_expression: 'UPPER({field})',
      transformation_description: 'Convert to uppercase',
      category: 'STRING',
      is_system: true
    },
    {
      transformation_id: 3,
      transformation_name: 'Lower Case',
      transformation_code: 'LOWER',
      transformation_expression: 'LOWER({field})',
      transformation_description: 'Convert to lowercase',
      category: 'STRING',
      is_system: true
    },
    {
      transformation_id: 4,
      transformation_name: 'Initial Caps',
      transformation_code: 'INITCAP',
      transformation_expression: 'INITCAP({field})',
      transformation_description: 'Capitalize first letter of each word',
      category: 'STRING',
      is_system: true
    },
    {
      transformation_id: 5,
      transformation_name: 'Cast to String',
      transformation_code: 'CAST_STRING',
      transformation_expression: 'CAST({field} AS STRING)',
      transformation_description: 'Convert to string data type',
      category: 'CONVERSION',
      is_system: true
    },
    {
      transformation_id: 6,
      transformation_name: 'Cast to Integer',
      transformation_code: 'CAST_INT',
      transformation_expression: 'CAST({field} AS INT)',
      transformation_description: 'Convert to integer data type',
      category: 'CONVERSION',
      is_system: true
    },
    {
      transformation_id: 7,
      transformation_name: 'Cast to Date',
      transformation_code: 'CAST_DATE',
      transformation_expression: 'CAST({field} AS DATE)',
      transformation_description: 'Convert to date data type',
      category: 'DATE',
      is_system: true
    },
    {
      transformation_id: 8,
      transformation_name: 'Replace Nulls',
      transformation_code: 'COALESCE',
      transformation_expression: 'COALESCE({field}, \'\')',
      transformation_description: 'Replace NULL values with empty string',
      category: 'NULL_HANDLING',
      is_system: true
    }
  ]

  // Computed
  const mappingCount = computed(() => mappings.value.length)

  // Actions
  async function fetchMappings() {
    loading.value = true
    error.value = null

    try {
      console.log('[Mappings V2 Store] Fetching mappings from API...')
      
      const response = await fetch('/api/v2/mappings/', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      mappings.value = data

      console.log('[Mappings V2 Store] Loaded', mappings.value.length, 'mappings')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch mappings'
      console.error('[Mappings V2 Store] Error:', error.value)
      // Return empty array on error (not mock data)
      mappings.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchTransformations() {
    loading.value = true
    error.value = null

    try {
      console.log('[Mappings V2 Store] Fetching transformations from API...')
      
      const response = await fetch('/api/v2/transformations/', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      transformations.value = data

      console.log('[Mappings V2 Store] Loaded', transformations.value.length, 'transformations')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch transformations'
      console.error('[Mappings V2 Store] Error:', error.value)
      // Fallback to mock transformations if API fails
      console.log('[Mappings V2 Store] Falling back to mock transformations')
      transformations.value = [...mockTransformations]
    } finally {
      loading.value = false
    }
  }

  async function createMapping(mappedField: MappedFieldV2) {
    loading.value = true
    error.value = null

    try {
      console.log('[Mappings V2 Store] Creating mapping:', mappedField.tgt_column_name)
      
      const response = await fetch('/api/v2/mappings/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          mapped_field: {
            tgt_table_name: mappedField.tgt_table_name,
            tgt_table_physical_name: mappedField.tgt_table_physical_name,
            tgt_column_name: mappedField.tgt_column_name,
            tgt_column_physical_name: mappedField.tgt_column_physical_name,
            concat_strategy: mappedField.concat_strategy,
            concat_separator: mappedField.concat_separator,
            transformation_expression: mappedField.transformation_expression,
            mapped_by: mappedField.mapped_by,
            confidence_score: mappedField.confidence_score,
            mapping_source: mappedField.mapping_source,
            ai_reasoning: mappedField.ai_reasoning,
            mapping_status: mappedField.mapping_status
          },
          mapping_details: mappedField.source_fields.map(sf => ({
            src_table_name: sf.src_table_name,
            src_table_physical_name: sf.src_table_physical_name,
            src_column_name: sf.src_column_name,
            src_column_physical_name: sf.src_column_physical_name,
            field_order: sf.field_order,
            transformation_expr: sf.transformation_expr
          }))
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()
      const mappingId = result.mapping_id

      // Add to local array with returned ID
      const newMapping: MappedFieldV2 = {
        ...mappedField,
        mapping_id: mappingId,
        mapped_at: new Date().toISOString()
      }
      mappings.value.push(newMapping)

      console.log('[Mappings V2 Store] Created mapping:', mappingId)
      return mappingId
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create mapping'
      console.error('[Mappings V2 Store] Error:', error.value)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteMapping(mappingId: number) {
    loading.value = true
    error.value = null

    try {
      console.log('[Mappings V2 Store] Deleting mapping:', mappingId)
      
      const response = await fetch(`/api/v2/mappings/${mappingId}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
      }

      // Remove from local array
      const index = mappings.value.findIndex(m => m.mapping_id === mappingId)
      if (index >= 0) {
        mappings.value.splice(index, 1)
      }

      console.log('[Mappings V2 Store] Deleted mapping:', mappingId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete mapping'
      console.error('[Mappings V2 Store] Error:', error.value)
      throw e
    } finally {
      loading.value = false
    }
  }

  function buildSQLExpression(
    sourceFields: MappingDetailV2[],
    concatStrategy: string,
    customConcatValue?: string
  ): string {
    if (sourceFields.length === 0) {
      return ''
    }

    if (sourceFields.length === 1) {
      // Single field: just use transformation or field name
      const field = sourceFields[0]
      return field.transformation_expr || field.src_column_physical_name
    }

    // Multi-field: build CONCAT expression
    const separator = getConcatSeparator(concatStrategy, customConcatValue)
    const fieldExprs = sourceFields
      .sort((a, b) => a.field_order - b.field_order)
      .map(f => f.transformation_expr || f.src_column_physical_name)

    if (separator) {
      // CONCAT with separator
      return `CONCAT(${fieldExprs.join(`, '${separator}', `)})`
    } else {
      // CONCAT without separator
      return `CONCAT(${fieldExprs.join(', ')})`
    }
  }

  function getConcatSeparator(strategy: string, customValue?: string): string {
    switch (strategy) {
      case 'SPACE':
        return ' '
      case 'COMMA':
        return ', '
      case 'PIPE':
        return ' | '
      case 'CUSTOM':
        return customValue || ''
      case 'NONE':
      default:
        return ''
    }
  }

  return {
    // State
    mappings,
    transformations,
    loading,
    error,
    
    // Computed
    mappingCount,
    
    // Actions
    fetchMappings,
    fetchTransformations,
    createMapping,
    deleteMapping,
    buildSQLExpression,
    getConcatSeparator
  }
})

