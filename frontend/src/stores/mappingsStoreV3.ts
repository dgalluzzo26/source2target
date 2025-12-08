/**
 * Mappings Store V3 (Simplified Single-Table)
 * 
 * V3 KEY CHANGES:
 * - Single table structure - no more source_fields array
 * - source_expression contains the complete SQL
 * - Metadata fields for display: source_tables, source_columns
 * - AI-generated expressions supported
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export interface MappedFieldV3 {
  mapped_field_id?: number
  semantic_field_id: number
  
  // Target field info
  tgt_table_name: string
  tgt_table_physical_name: string
  tgt_column_name: string
  tgt_column_physical_name: string
  tgt_comments?: string
  
  // Source expression - THE KEY V3 FIELD
  source_expression: string
  
  // Source metadata for display
  source_tables?: string
  source_columns?: string
  source_descriptions?: string
  source_datatypes?: string
  source_relationship_type: 'SINGLE' | 'JOIN' | 'UNION'
  transformations_applied?: string
  
  // AI/Confidence metadata
  confidence_score?: number
  mapping_source: 'AI' | 'MANUAL' | 'BULK_UPLOAD'
  ai_reasoning?: string
  ai_generated: boolean
  
  // Status and audit
  mapping_status: 'ACTIVE' | 'INACTIVE' | 'PENDING_REVIEW'
  mapped_by?: string
  mapped_ts?: string
  updated_by?: string
  updated_ts?: string
  
  // Vector search field
  source_semantic_field?: string
}

export interface MappedFieldCreateV3 {
  semantic_field_id: number
  tgt_table_name: string
  tgt_table_physical_name: string
  tgt_column_name: string
  tgt_column_physical_name: string
  tgt_comments?: string
  source_expression: string
  source_tables?: string
  source_columns?: string
  source_descriptions?: string
  source_datatypes?: string
  source_domain?: string  // Preserve domain for restore on delete
  source_relationship_type?: string
  transformations_applied?: string
  confidence_score?: number
  mapping_source?: string
  ai_reasoning?: string
  ai_generated?: boolean
  mapped_by?: string
}

export interface MappedFieldUpdateV3 {
  source_expression?: string
  source_tables?: string
  source_columns?: string
  source_descriptions?: string
  source_datatypes?: string
  source_relationship_type?: string
  transformations_applied?: string
  ai_reasoning?: string
  ai_generated?: boolean
  mapping_status?: string
  updated_by?: string
}

export interface TransformationTemplate {
  transformation_id: number
  transformation_name: string
  transformation_code: string
  transformation_expression: string
  transformation_description: string
  category: string
  is_system?: boolean
}

export const useMappingsStoreV3 = defineStore('mappingsV3', () => {
  // State
  const mappings = ref<MappedFieldV3[]>([])
  const transformations = ref<TransformationTemplate[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const mappingCount = computed(() => mappings.value.length)
  const activeMappings = computed(() => 
    mappings.value.filter(m => m.mapping_status === 'ACTIVE')
  )

  // =========================================================================
  // FETCH MAPPINGS
  // =========================================================================
  async function fetchMappings(statusFilter?: string) {
    loading.value = true
    error.value = null

    try {
      console.log('[Mappings V3 Store] Fetching mappings...')
      
      let url = '/api/v3/mappings/'
      if (statusFilter) {
        url += `?status=${statusFilter}`
      }
      
      const response = await api.get(url)
      mappings.value = response.data

      console.log('[Mappings V3 Store] Loaded', mappings.value.length, 'mappings')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch mappings'
      console.error('[Mappings V3 Store] Error:', error.value)
      mappings.value = []
    } finally {
      loading.value = false
    }
  }

  // =========================================================================
  // GET SINGLE MAPPING
  // =========================================================================
  async function getMapping(mappingId: number): Promise<MappedFieldV3 | null> {
    try {
      console.log('[Mappings V3 Store] Fetching mapping:', mappingId)
      const response = await api.get(`/api/v3/mappings/${mappingId}`)
      return response.data
    } catch (e) {
      console.error('[Mappings V3 Store] Error getting mapping:', e)
      return null
    }
  }

  // =========================================================================
  // CREATE MAPPING
  // =========================================================================
  async function createMapping(
    data: MappedFieldCreateV3,
    unmappedFieldIds?: number[]
  ): Promise<number> {
    loading.value = true
    error.value = null

    try {
      console.log('[Mappings V3 Store] Creating mapping:', data.tgt_column_name)
      
      const response = await api.post('/api/v3/mappings/', {
        mapping: data,
        unmapped_field_ids: unmappedFieldIds || []
      })

      const mappingId = response.data.mapping_id

      // Add to local array
      const newMapping: MappedFieldV3 = {
        ...data,
        mapped_field_id: mappingId,
        source_relationship_type: (data.source_relationship_type as 'SINGLE' | 'JOIN' | 'UNION') || 'SINGLE',
        mapping_source: (data.mapping_source as 'AI' | 'MANUAL' | 'BULK_UPLOAD') || 'MANUAL',
        ai_generated: data.ai_generated || false,
        mapping_status: 'ACTIVE',
        mapped_ts: new Date().toISOString()
      }
      mappings.value.push(newMapping)

      console.log('[Mappings V3 Store] Created mapping:', mappingId)
      return mappingId
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to create mapping'
      console.error('[Mappings V3 Store] Error:', error.value)
      throw e
    } finally {
      loading.value = false
    }
  }

  // =========================================================================
  // UPDATE MAPPING
  // =========================================================================
  async function updateMapping(
    mappingId: number,
    data: MappedFieldUpdateV3
  ): Promise<void> {
    loading.value = true
    error.value = null

    try {
      console.log('[Mappings V3 Store] Updating mapping:', mappingId)
      
      await api.put(`/api/v3/mappings/${mappingId}`, data)

      // Update local array
      const index = mappings.value.findIndex(m => m.mapped_field_id === mappingId)
      if (index >= 0) {
        mappings.value[index] = {
          ...mappings.value[index],
          ...data,
          updated_ts: new Date().toISOString()
        } as MappedFieldV3
      }

      console.log('[Mappings V3 Store] Updated mapping:', mappingId)
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to update mapping'
      console.error('[Mappings V3 Store] Error:', error.value)
      throw e
    } finally {
      loading.value = false
    }
  }

  // =========================================================================
  // DELETE MAPPING
  // =========================================================================
  async function deleteMapping(
    mappingId: number,
    restoreToUnmapped: boolean = false
  ): Promise<void> {
    loading.value = true
    error.value = null

    try {
      console.log('[Mappings V3 Store] Deleting mapping:', mappingId)
      
      await api.delete(`/api/v3/mappings/${mappingId}?restore=${restoreToUnmapped}`)

      // Remove from local array
      const index = mappings.value.findIndex(m => m.mapped_field_id === mappingId)
      if (index >= 0) {
        mappings.value.splice(index, 1)
      }

      console.log('[Mappings V3 Store] Deleted mapping:', mappingId)
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to delete mapping'
      console.error('[Mappings V3 Store] Error:', error.value)
      throw e
    } finally {
      loading.value = false
    }
  }

  // =========================================================================
  // FETCH TRANSFORMATIONS
  // =========================================================================
  async function fetchTransformations() {
    try {
      console.log('[Mappings V3 Store] Fetching transformations...')
      
      const response = await api.get('/api/v3/mappings/transformations/library')
      transformations.value = response.data

      console.log('[Mappings V3 Store] Loaded', transformations.value.length, 'transformations')
    } catch (e) {
      console.error('[Mappings V3 Store] Error fetching transformations:', e)
      // Load fallback transformations
      transformations.value = getDefaultTransformations()
    }
  }

  // =========================================================================
  // GENERATE SQL WITH AI
  // =========================================================================
  async function generateSQLWithAI(
    userDescription: string,
    sourceColumns: Array<{ 
      table: string, 
      column: string, 
      datatype?: string,
      physical_table?: string,
      physical_column?: string,
      comments?: string 
    }>,
    targetColumn: { 
      table: string, 
      column: string, 
      datatype?: string,
      physical_table?: string,
      physical_column?: string 
    }
  ): Promise<{ sql: string, explanation: string }> {
    try {
      console.log('[Mappings V3 Store] Generating SQL with AI...')
      console.log('[Mappings V3 Store] User description:', userDescription)
      console.log('[Mappings V3 Store] Source columns:', sourceColumns)
      console.log('[Mappings V3 Store] Target column:', targetColumn)
      
      // Transform to API format
      const requestBody = {
        user_description: userDescription,
        source_fields: sourceColumns.map(col => ({
          src_table_name: col.table,
          src_table_physical_name: col.physical_table || col.table,
          src_column_name: col.column,
          src_column_physical_name: col.physical_column || col.column,
          src_physical_datatype: col.datatype || 'STRING',
          src_comments: col.comments || ''
        })),
        target_field: {
          tgt_table_name: targetColumn.table,
          tgt_table_physical_name: targetColumn.physical_table || targetColumn.table,
          tgt_column_name: targetColumn.column,
          tgt_column_physical_name: targetColumn.physical_column || targetColumn.column,
          tgt_physical_datatype: targetColumn.datatype || 'STRING'
        }
      }
      
      console.log('[Mappings V3 Store] Request body:', JSON.stringify(requestBody, null, 2))
      
      const response = await api.post('/api/v3/ai/generate-sql', requestBody)

      return {
        sql: response.data.sql_expression || response.data.generated_sql || '',
        explanation: response.data.explanation || ''
      }
    } catch (e: any) {
      console.error('[Mappings V3 Store] Error generating SQL:', e)
      console.error('[Mappings V3 Store] Response data:', e.response?.data)
      throw new Error(e.response?.data?.detail || 'Failed to generate SQL')
    }
  }

  // =========================================================================
  // HELPER: Default transformations if API fails
  // =========================================================================
  function getDefaultTransformations(): TransformationTemplate[] {
    return [
      {
        transformation_id: 1,
        transformation_name: 'Trim Whitespace',
        transformation_code: 'TRIM',
        transformation_expression: 'TRIM({field})',
        transformation_description: 'Remove leading and trailing whitespace',
        category: 'TEXT',
        is_system: true
      },
      {
        transformation_id: 2,
        transformation_name: 'Uppercase',
        transformation_code: 'UPPER',
        transformation_expression: 'UPPER({field})',
        transformation_description: 'Convert to uppercase',
        category: 'TEXT',
        is_system: true
      },
      {
        transformation_id: 3,
        transformation_name: 'Lowercase',
        transformation_code: 'LOWER',
        transformation_expression: 'LOWER({field})',
        transformation_description: 'Convert to lowercase',
        category: 'TEXT',
        is_system: true
      },
      {
        transformation_id: 4,
        transformation_name: 'Title Case',
        transformation_code: 'INITCAP',
        transformation_expression: 'INITCAP({field})',
        transformation_description: 'Convert to title case',
        category: 'TEXT',
        is_system: true
      },
      {
        transformation_id: 5,
        transformation_name: 'Trim and Upper',
        transformation_code: 'TRIM_UPPER',
        transformation_expression: 'TRIM(UPPER({field}))',
        transformation_description: 'Trim and convert to uppercase',
        category: 'TEXT',
        is_system: true
      },
      {
        transformation_id: 6,
        transformation_name: 'Replace Null with Empty',
        transformation_code: 'COALESCE_EMPTY',
        transformation_expression: "COALESCE({field}, '')",
        transformation_description: 'Replace NULL with empty string',
        category: 'TEXT',
        is_system: true
      },
      {
        transformation_id: 7,
        transformation_name: 'Cast to String',
        transformation_code: 'TO_STRING',
        transformation_expression: 'CAST({field} AS STRING)',
        transformation_description: 'Convert to string',
        category: 'NUMERIC',
        is_system: true
      },
      {
        transformation_id: 8,
        transformation_name: 'Date to String',
        transformation_code: 'DATE_TO_STR',
        transformation_expression: "DATE_FORMAT({field}, 'yyyy-MM-dd')",
        transformation_description: 'Format date as YYYY-MM-DD',
        category: 'DATE',
        is_system: true
      }
    ]
  }

  // =========================================================================
  // HELPER: Parse source columns from pipe-separated string (CSV-friendly)
  // Also handles legacy comma-separated for backward compatibility
  // =========================================================================
  function parseSourceColumns(sourceColumns: string | undefined): string[] {
    if (!sourceColumns) return []
    // Prefer pipe delimiter, fall back to comma for legacy data
    const delimiter = sourceColumns.includes(' | ') ? ' | ' : ','
    return sourceColumns.split(delimiter).map(s => s.trim())
  }

  // =========================================================================
  // HELPER: Parse source tables from pipe-separated string (CSV-friendly)
  // Also handles legacy comma-separated for backward compatibility
  // =========================================================================
  function parseSourceTables(sourceTables: string | undefined): string[] {
    if (!sourceTables) return []
    // Prefer pipe delimiter, fall back to comma for legacy data
    const delimiter = sourceTables.includes(' | ') ? ' | ' : ','
    return sourceTables.split(delimiter).map(s => s.trim())
  }

  // =========================================================================
  // HELPER: Get relationship type label
  // =========================================================================
  function getRelationshipTypeLabel(type: string): string {
    switch (type) {
      case 'SINGLE': return 'Single Table'
      case 'JOIN': return 'Joined Tables'
      case 'UNION': return 'Unioned Tables'
      default: return type
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
    activeMappings,
    
    // Actions
    fetchMappings,
    getMapping,
    createMapping,
    updateMapping,
    deleteMapping,
    fetchTransformations,
    generateSQLWithAI,
    
    // Helpers
    parseSourceColumns,
    parseSourceTables,
    getRelationshipTypeLabel
  }
})

