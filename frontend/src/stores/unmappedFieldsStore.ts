/**
 * Unmapped Fields Store (V2)
 * 
 * Manages source fields awaiting mapping in the V2 multi-field mapping workflow.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface UnmappedField {
  id: number
  src_table_name: string
  src_table_physical_name: string
  src_column_name: string
  src_column_physical_name: string
  src_nullable: string
  src_physical_datatype: string
  src_comments: string
  uploaded_at?: string
  uploaded_by?: string
  selected?: boolean  // UI-only field for multi-selection
}

export const useUnmappedFieldsStore = defineStore('unmappedFields', () => {
  // State
  const unmappedFields = ref<UnmappedField[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedFields = ref<UnmappedField[]>([])

  // Mock data for development
  const mockData: UnmappedField[] = [
    {
      id: 1,
      src_table_name: 'T_MEMBER',
      src_table_physical_name: 't_member',
      src_column_name: 'FIRST_NAME',
      src_column_physical_name: 'first_name',
      src_nullable: 'NO',
      src_physical_datatype: 'STRING',
      src_comments: 'First name of the member',
      uploaded_at: '2025-01-15T10:00:00',
      uploaded_by: 'john.doe@example.com',
      selected: false
    },
    {
      id: 2,
      src_table_name: 'T_MEMBER',
      src_table_physical_name: 't_member',
      src_column_name: 'LAST_NAME',
      src_column_physical_name: 'last_name',
      src_nullable: 'NO',
      src_physical_datatype: 'STRING',
      src_comments: 'Last name of the member',
      uploaded_at: '2025-01-15T10:00:00',
      uploaded_by: 'john.doe@example.com',
      selected: false
    },
    {
      id: 3,
      src_table_name: 'T_MEMBER',
      src_table_physical_name: 't_member',
      src_column_name: 'SSN',
      src_column_physical_name: 'ssn',
      src_nullable: 'YES',
      src_physical_datatype: 'STRING',
      src_comments: 'Social Security Number',
      uploaded_at: '2025-01-15T10:00:00',
      uploaded_by: 'john.doe@example.com',
      selected: false
    },
    {
      id: 4,
      src_table_name: 'T_MEMBER',
      src_table_physical_name: 't_member',
      src_column_name: 'DATE_OF_BIRTH',
      src_column_physical_name: 'date_of_birth',
      src_nullable: 'YES',
      src_physical_datatype: 'DATE',
      src_comments: 'Member date of birth',
      uploaded_at: '2025-01-15T10:00:00',
      uploaded_by: 'john.doe@example.com',
      selected: false
    },
    {
      id: 5,
      src_table_name: 'T_MEMBER',
      src_table_physical_name: 't_member',
      src_column_name: 'ADDRESS_LINE1',
      src_column_physical_name: 'address_line1',
      src_nullable: 'YES',
      src_physical_datatype: 'STRING',
      src_comments: 'Primary address line 1',
      uploaded_at: '2025-01-15T10:00:00',
      uploaded_by: 'john.doe@example.com',
      selected: false
    },
    {
      id: 6,
      src_table_name: 'T_MEMBER',
      src_table_physical_name: 't_member',
      src_column_name: 'CITY',
      src_column_physical_name: 'city',
      src_nullable: 'YES',
      src_physical_datatype: 'STRING',
      src_comments: 'City name',
      uploaded_at: '2025-01-15T10:00:00',
      uploaded_by: 'john.doe@example.com',
      selected: false
    },
    {
      id: 7,
      src_table_name: 'T_MEMBER',
      src_table_physical_name: 't_member',
      src_column_name: 'STATE',
      src_column_physical_name: 'state',
      src_nullable: 'YES',
      src_physical_datatype: 'STRING',
      src_comments: 'State code (2 characters)',
      uploaded_at: '2025-01-15T10:00:00',
      uploaded_by: 'john.doe@example.com',
      selected: false
    },
    {
      id: 8,
      src_table_name: 'T_MEMBER',
      src_table_physical_name: 't_member',
      src_column_name: 'ZIP_CODE',
      src_column_physical_name: 'zip_code',
      src_nullable: 'YES',
      src_physical_datatype: 'STRING',
      src_comments: 'ZIP code (5 or 9 digits)',
      uploaded_at: '2025-01-15T10:00:00',
      uploaded_by: 'john.doe@example.com',
      selected: false
    },
    {
      id: 9,
      src_table_name: 'T_PROVIDER',
      src_table_physical_name: 't_provider',
      src_column_name: 'NPI',
      src_column_physical_name: 'npi',
      src_nullable: 'NO',
      src_physical_datatype: 'STRING',
      src_comments: 'National Provider Identifier',
      uploaded_at: '2025-01-15T10:00:00',
      uploaded_by: 'john.doe@example.com',
      selected: false
    },
    {
      id: 10,
      src_table_name: 'T_PROVIDER',
      src_table_physical_name: 't_provider',
      src_column_name: 'PROVIDER_NAME',
      src_column_physical_name: 'provider_name',
      src_nullable: 'NO',
      src_physical_datatype: 'STRING',
      src_comments: 'Provider full name',
      uploaded_at: '2025-01-15T10:00:00',
      uploaded_by: 'john.doe@example.com',
      selected: false
    }
  ]

  // Computed
  const selectedCount = computed(() => selectedFields.value.length)
  const hasSelection = computed(() => selectedCount.value > 0)
  const isSingleSelection = computed(() => selectedCount.value === 1)
  const isMultiSelection = computed(() => selectedCount.value > 1)

  // Group fields by table for display
  const fieldsByTable = computed(() => {
    const grouped: Record<string, UnmappedField[]> = {}
    unmappedFields.value.forEach(field => {
      if (!grouped[field.src_table_name]) {
        grouped[field.src_table_name] = []
      }
      grouped[field.src_table_name].push(field)
    })
    return grouped
  })

  // Actions
  async function fetchUnmappedFields() {
    loading.value = true
    error.value = null

    try {
      // TODO: Replace with real API call
      // const response = await fetch('/api/v2/unmapped-fields/')
      // unmappedFields.value = await response.json()

      // Mock: Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 300))
      unmappedFields.value = [...mockData]
      
      console.log('[Unmapped Fields Store] Loaded', unmappedFields.value.length, 'fields')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch unmapped fields'
      console.error('[Unmapped Fields Store] Error:', error.value)
    } finally {
      loading.value = false
    }
  }

  function toggleFieldSelection(field: UnmappedField) {
    const index = selectedFields.value.findIndex(f => f.id === field.id)
    
    if (index >= 0) {
      // Deselect
      selectedFields.value.splice(index, 1)
      field.selected = false
    } else {
      // Select
      selectedFields.value.push(field)
      field.selected = true
    }

    console.log('[Unmapped Fields Store] Selected:', selectedFields.value.length, 'fields')
  }

  function selectField(field: UnmappedField) {
    if (!selectedFields.value.find(f => f.id === field.id)) {
      selectedFields.value.push(field)
      field.selected = true
    }
  }

  function deselectField(field: UnmappedField) {
    const index = selectedFields.value.findIndex(f => f.id === field.id)
    if (index >= 0) {
      selectedFields.value.splice(index, 1)
      field.selected = false
    }
  }

  function clearSelection() {
    selectedFields.value.forEach(field => {
      field.selected = false
    })
    selectedFields.value = []
    console.log('[Unmapped Fields Store] Selection cleared')
  }

  async function deleteUnmappedField(fieldId: number) {
    loading.value = true
    error.value = null

    try {
      // TODO: Replace with real API call
      // await fetch(`/api/v2/unmapped-fields/${fieldId}`, { method: 'DELETE' })

      // Mock: Remove from local array
      await new Promise(resolve => setTimeout(resolve, 200))
      const index = unmappedFields.value.findIndex(f => f.id === fieldId)
      if (index >= 0) {
        unmappedFields.value.splice(index, 1)
      }

      // Remove from selection if selected
      const selIndex = selectedFields.value.findIndex(f => f.id === fieldId)
      if (selIndex >= 0) {
        selectedFields.value.splice(selIndex, 1)
      }

      console.log('[Unmapped Fields Store] Deleted field:', fieldId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete field'
      console.error('[Unmapped Fields Store] Error:', error.value)
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    unmappedFields,
    loading,
    error,
    selectedFields,
    
    // Computed
    selectedCount,
    hasSelection,
    isSingleSelection,
    isMultiSelection,
    fieldsByTable,
    
    // Actions
    fetchUnmappedFields,
    toggleFieldSelection,
    selectField,
    deselectField,
    clearSelection,
    deleteUnmappedField
  }
})

