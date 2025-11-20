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
  custom_concat_value?: string
  final_sql_expression?: string
  mapped_at?: string
  mapped_by?: string
  mapping_confidence_score?: number
  ai_reasoning?: string
  source_fields: MappingDetailV2[]
}

export interface Transformation {
  transform_id: number
  transform_name: string
  transform_code: string
  description: string
  category: string
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
      transform_id: 1,
      transform_name: 'Trim Whitespace',
      transform_code: 'TRIM({field})',
      description: 'Remove leading and trailing whitespace',
      category: 'STRING'
    },
    {
      transform_id: 2,
      transform_name: 'Upper Case',
      transform_code: 'UPPER({field})',
      description: 'Convert to uppercase',
      category: 'STRING'
    },
    {
      transform_id: 3,
      transform_name: 'Lower Case',
      transform_code: 'LOWER({field})',
      description: 'Convert to lowercase',
      category: 'STRING'
    },
    {
      transform_id: 4,
      transform_name: 'Initial Caps',
      transform_code: 'INITCAP({field})',
      description: 'Capitalize first letter of each word',
      category: 'STRING'
    },
    {
      transform_id: 5,
      transform_name: 'Cast to String',
      transform_code: 'CAST({field} AS STRING)',
      description: 'Convert to string data type',
      category: 'CONVERSION'
    },
    {
      transform_id: 6,
      transform_name: 'Cast to Integer',
      transform_code: 'CAST({field} AS INT)',
      description: 'Convert to integer data type',
      category: 'CONVERSION'
    },
    {
      transform_id: 7,
      transform_name: 'Cast to Date',
      transform_code: 'CAST({field} AS DATE)',
      description: 'Convert to date data type',
      category: 'DATE'
    },
    {
      transform_id: 8,
      transform_name: 'Replace Nulls',
      transform_code: 'COALESCE({field}, \'\')',
      description: 'Replace NULL values with empty string',
      category: 'NULL_HANDLING'
    }
  ]

  // Computed
  const mappingCount = computed(() => mappings.value.length)

  // Actions
  async function fetchMappings() {
    loading.value = true
    error.value = null

    try {
      // TODO: Replace with real API call
      // const response = await fetch('/api/v2/mappings/')
      // mappings.value = await response.json()

      // Mock: Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 300))
      mappings.value = []

      console.log('[Mappings V2 Store] Loaded', mappings.value.length, 'mappings')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch mappings'
      console.error('[Mappings V2 Store] Error:', error.value)
    } finally {
      loading.value = false
    }
  }

  async function fetchTransformations() {
    loading.value = true
    error.value = null

    try {
      // TODO: Replace with real API call
      // const response = await fetch('/api/v2/transformations/')
      // transformations.value = await response.json()

      // Mock: Use mock data
      await new Promise(resolve => setTimeout(resolve, 200))
      transformations.value = [...mockTransformations]

      console.log('[Mappings V2 Store] Loaded', transformations.value.length, 'transformations')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch transformations'
      console.error('[Mappings V2 Store] Error:', error.value)
    } finally {
      loading.value = false
    }
  }

  async function createMapping(mappedField: MappedFieldV2) {
    loading.value = true
    error.value = null

    try {
      // TODO: Replace with real API call
      // const response = await fetch('/api/v2/mappings/', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({
      //     mapped_field: mappedField,
      //     mapping_details: mappedField.source_fields
      //   })
      // })
      // const result = await response.json()

      // Mock: Add to local array with generated ID
      await new Promise(resolve => setTimeout(resolve, 500))
      const newMapping: MappedFieldV2 = {
        ...mappedField,
        mapping_id: mappings.value.length + 1,
        mapped_at: new Date().toISOString(),
        mapped_by: 'john.doe@example.com'
      }
      mappings.value.push(newMapping)

      console.log('[Mappings V2 Store] Created mapping:', newMapping.mapping_id)
      return newMapping.mapping_id
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
      // TODO: Replace with real API call
      // await fetch(`/api/v2/mappings/${mappingId}`, { method: 'DELETE' })

      // Mock: Remove from local array
      await new Promise(resolve => setTimeout(resolve, 300))
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

