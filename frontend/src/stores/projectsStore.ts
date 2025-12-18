/**
 * Pinia store for V4 Target-First mapping projects.
 * 
 * Manages:
 * - Project list and CRUD
 * - Target tables within a project
 * - Mapping suggestions
 * - AI discovery process
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

// =============================================================================
// TYPES
// =============================================================================

export interface MappingProject {
  project_id: number
  project_name: string
  project_description?: string
  source_system?: string
  target_domains?: string
  project_status: 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'COMPLETE' | 'ARCHIVED'
  total_target_tables: number
  tables_complete: number
  tables_in_progress: number
  total_target_columns: number
  columns_mapped: number
  columns_pending_review: number
  created_by?: string
  created_ts?: string
  updated_ts?: string
}

export interface TargetTableStatus {
  target_table_status_id: number
  project_id: number
  tgt_table_name: string
  tgt_table_physical_name: string
  tgt_table_description?: string
  mapping_status: 'NOT_STARTED' | 'DISCOVERING' | 'SUGGESTIONS_READY' | 'IN_REVIEW' | 'COMPLETE' | 'SKIPPED'
  priority: 'HIGH' | 'MEDIUM' | 'LOW'
  total_columns: number
  columns_with_pattern: number
  columns_mapped: number
  columns_pending_review: number
  columns_no_match: number
  columns_skipped: number
  avg_confidence?: number
  min_confidence?: number
  progress_percent?: number
  ai_started_ts?: string
  ai_completed_ts?: string
  started_by?: string
}

export interface MappingSuggestion {
  suggestion_id: number
  project_id: number
  target_table_status_id: number
  semantic_field_id: number
  tgt_table_name: string
  tgt_table_physical_name: string
  tgt_column_name: string
  tgt_column_physical_name: string
  tgt_comments?: string
  tgt_physical_datatype?: string
  pattern_mapped_field_id?: number
  pattern_type?: string
  pattern_sql?: string
  matched_source_fields?: string  // JSON string
  suggested_sql?: string
  sql_changes?: string  // JSON string
  confidence_score?: number
  ai_reasoning?: string
  warnings?: string  // JSON string
  suggestion_status: 'PROCESSING' | 'PENDING' | 'APPROVED' | 'EDITED' | 'REJECTED' | 'SKIPPED' | 'NO_PATTERN' | 'NO_MATCH'
  edited_sql?: string
  edit_notes?: string
  rejection_reason?: string
  created_mapped_field_id?: number
  created_ts?: string
  reviewed_by?: string
  reviewed_ts?: string
}

export interface MatchedSourceField {
  unmapped_field_id: number
  src_table_name: string
  src_table_physical_name: string
  src_column_name: string
  src_column_physical_name: string
  src_comments?: string
  src_physical_datatype?: string
  match_score: number
}

// =============================================================================
// STORE
// =============================================================================

export const useProjectsStore = defineStore('projects', () => {
  // State
  const projects = ref<MappingProject[]>([])
  const currentProject = ref<MappingProject | null>(null)
  const targetTables = ref<TargetTableStatus[]>([])
  const currentTable = ref<TargetTableStatus | null>(null)
  const suggestions = ref<MappingSuggestion[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const activeProjects = computed(() => 
    projects.value.filter(p => p.project_status !== 'ARCHIVED')
  )

  const pendingSuggestions = computed(() =>
    suggestions.value.filter(s => s.suggestion_status === 'PENDING')
  )

  const highConfidenceSuggestions = computed(() =>
    suggestions.value.filter(s => 
      s.suggestion_status === 'PENDING' && 
      (s.confidence_score || 0) >= 0.8
    )
  )

  // =============================================================================
  // PROJECT ACTIONS
  // =============================================================================

  async function fetchProjects(includeArchived = false) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<MappingProject[]>(
        `/api/v4/projects/?include_archived=${includeArchived}`
      )
      projects.value = data
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch projects'
      console.error('[ProjectsStore] Fetch error:', e)
    } finally {
      loading.value = false
    }
  }

  async function createProject(data: {
    project_name: string
    project_description?: string
    source_system?: string
    target_domains?: string
    created_by: string
  }) {
    loading.value = true
    error.value = null
    try {
      const { data: result } = await api.post<{ project_id: number }>('/api/v4/projects/', data)
      await fetchProjects()
      return result
    } catch (e: any) {
      error.value = e.message || 'Failed to create project'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(projectId: number) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<MappingProject>(`/api/v4/projects/${projectId}`)
      currentProject.value = data
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch project'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateProject(projectId: number, updates: Partial<MappingProject>) {
    loading.value = true
    error.value = null
    try {
      await api.put(`/api/v4/projects/${projectId}`, updates)
      await fetchProjects()
    } catch (e: any) {
      error.value = e.message || 'Failed to update project'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteProject(projectId: number) {
    loading.value = true
    error.value = null
    try {
      await api.delete(`/api/v4/projects/${projectId}`)
      await fetchProjects()
    } catch (e: any) {
      error.value = e.message || 'Failed to delete project'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function initializeTargetTables(projectId: number, domain?: string) {
    loading.value = true
    error.value = null
    try {
      const params = domain ? `?domain=${encodeURIComponent(domain)}` : ''
      const { data } = await api.post<{ tables_initialized: number }>(
        `/api/v4/projects/${projectId}/initialize-tables${params}`,
        {}
      )
      await fetchProject(projectId)
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to initialize tables'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function uploadSourceFields(projectId: number, file: File) {
    loading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await fetch(`/api/v4/projects/${projectId}/source-fields`, {
        method: 'POST',
        body: formData
      })
      
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`)
      }
      
      const data = await response.json()
      await fetchProject(projectId)
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to upload source fields'
      throw e
    } finally {
      loading.value = false
    }
  }

  // =============================================================================
  // TARGET TABLE ACTIONS
  // =============================================================================

  async function fetchTargetTables(projectId: number) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<TargetTableStatus[]>(
        `/api/v4/projects/${projectId}/target-tables/`
      )
      targetTables.value = data
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch target tables'
      console.error('[ProjectsStore] Fetch tables error:', e)
    } finally {
      loading.value = false
    }
  }

  async function fetchTargetTable(projectId: number, tableId: number) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<TargetTableStatus>(
        `/api/v4/projects/${projectId}/target-tables/${tableId}`
      )
      currentTable.value = data
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch target table'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function startDiscovery(projectId: number, tableId: number, startedBy: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post(
        `/api/v4/projects/${projectId}/target-tables/${tableId}/discover`,
        { started_by: startedBy }
      )
      
      // Update local state
      const table = targetTables.value.find(t => t.target_table_status_id === tableId)
      if (table) {
        table.mapping_status = 'DISCOVERING'
      }
      
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to start discovery'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function startDiscoverySync(projectId: number, tableId: number, startedBy: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post(
        `/api/v4/projects/${projectId}/target-tables/${tableId}/discover/sync`,
        { started_by: startedBy }
      )
      
      // Refresh data after sync discovery
      await fetchTargetTables(projectId)
      
      return data
    } catch (e: any) {
      error.value = e.message || 'Discovery failed'
      throw e
    } finally {
      loading.value = false
    }
  }

  // =============================================================================
  // SUGGESTION ACTIONS
  // =============================================================================

  async function fetchSuggestions(projectId: number, tableId: number, statusFilter?: string) {
    loading.value = true
    error.value = null
    try {
      const params = statusFilter ? `?status=${statusFilter}` : ''
      const { data } = await api.get<MappingSuggestion[]>(
        `/api/v4/projects/${projectId}/target-tables/${tableId}/suggestions${params}`
      )
      suggestions.value = data
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch suggestions'
      console.error('[ProjectsStore] Fetch suggestions error:', e)
    } finally {
      loading.value = false
    }
  }

  async function approveSuggestion(suggestionId: number, reviewedBy: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post(
        `/api/v4/suggestions/${suggestionId}/approve`,
        { reviewed_by: reviewedBy }
      )
      
      // Update local state
      const idx = suggestions.value.findIndex(s => s.suggestion_id === suggestionId)
      if (idx >= 0) {
        suggestions.value[idx].suggestion_status = 'APPROVED'
        suggestions.value[idx].reviewed_by = reviewedBy
      }
      
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to approve suggestion'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function editAndApproveSuggestion(
    suggestionId: number, 
    reviewedBy: string,
    editedSql: string,
    editNotes?: string
  ) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post(
        `/api/v4/suggestions/${suggestionId}/edit`,
        { 
          reviewed_by: reviewedBy,
          edited_sql: editedSql,
          edit_notes: editNotes
        }
      )
      
      // Update local state
      const idx = suggestions.value.findIndex(s => s.suggestion_id === suggestionId)
      if (idx >= 0) {
        suggestions.value[idx].suggestion_status = 'EDITED'
        suggestions.value[idx].edited_sql = editedSql
        suggestions.value[idx].reviewed_by = reviewedBy
      }
      
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to edit suggestion'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function rejectSuggestion(suggestionId: number, reviewedBy: string, reason: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post(
        `/api/v4/suggestions/${suggestionId}/reject`,
        { 
          reviewed_by: reviewedBy,
          rejection_reason: reason
        }
      )
      
      // Update local state
      const idx = suggestions.value.findIndex(s => s.suggestion_id === suggestionId)
      if (idx >= 0) {
        suggestions.value[idx].suggestion_status = 'REJECTED'
        suggestions.value[idx].rejection_reason = reason
        suggestions.value[idx].reviewed_by = reviewedBy
      }
      
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to reject suggestion'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function skipSuggestion(suggestionId: number, reviewedBy: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post(
        `/api/v4/suggestions/${suggestionId}/skip`,
        { reviewed_by: reviewedBy }
      )
      
      // Update local state
      const idx = suggestions.value.findIndex(s => s.suggestion_id === suggestionId)
      if (idx >= 0) {
        suggestions.value[idx].suggestion_status = 'SKIPPED'
        suggestions.value[idx].reviewed_by = reviewedBy
      }
      
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to skip suggestion'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function bulkApprove(suggestionIds: number[], reviewedBy: string, minConfidence = 0.8) {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post(
        `/api/v4/suggestions/bulk-approve`,
        { 
          suggestion_ids: suggestionIds,
          reviewed_by: reviewedBy,
          min_confidence: minConfidence
        }
      )
      return data
    } catch (e: any) {
      error.value = e.message || 'Failed to bulk approve'
      throw e
    } finally {
      loading.value = false
    }
  }

  // =============================================================================
  // HELPERS
  // =============================================================================

  function parseMatchedSourceFields(jsonString?: string): MatchedSourceField[] {
    if (!jsonString) return []
    try {
      return JSON.parse(jsonString)
    } catch {
      return []
    }
  }

  function getConfidenceLevel(score?: number): 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW' {
    if (!score) return 'VERY_LOW'
    if (score >= 0.9) return 'HIGH'
    if (score >= 0.7) return 'MEDIUM'
    if (score >= 0.5) return 'LOW'
    return 'VERY_LOW'
  }

  function getConfidenceSeverity(score?: number): 'success' | 'info' | 'warning' | 'danger' {
    if (!score) return 'danger'
    if (score >= 0.9) return 'success'
    if (score >= 0.7) return 'info'
    if (score >= 0.5) return 'warning'
    return 'danger'
  }

  function clearCurrentProject() {
    currentProject.value = null
    targetTables.value = []
    currentTable.value = null
    suggestions.value = []
  }

  return {
    // State
    projects,
    currentProject,
    targetTables,
    currentTable,
    suggestions,
    loading,
    error,

    // Computed
    activeProjects,
    pendingSuggestions,
    highConfidenceSuggestions,

    // Project actions
    fetchProjects,
    createProject,
    fetchProject,
    updateProject,
    deleteProject,
    initializeTargetTables,
    uploadSourceFields,

    // Target table actions
    fetchTargetTables,
    fetchTargetTable,
    startDiscovery,
    startDiscoverySync,

    // Suggestion actions
    fetchSuggestions,
    approveSuggestion,
    editAndApproveSuggestion,
    rejectSuggestion,
    skipSuggestion,
    bulkApprove,

    // Helpers
    parseMatchedSourceFields,
    getConfidenceLevel,
    getConfidenceSeverity,
    clearCurrentProject
  }
})

