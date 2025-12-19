<template>
  <div class="suggestion-review-panel">
    <!-- Summary Bar -->
    <div class="summary-bar">
      <div class="summary-stats">
        <div class="summary-stat">
          <span class="stat-num">{{ suggestions.length }}</span>
          <span class="stat-label">Total</span>
        </div>
        <div class="summary-stat pending">
          <span class="stat-num">{{ pendingCount }}</span>
          <span class="stat-label">Pending</span>
        </div>
        <div class="summary-stat approved">
          <span class="stat-num">{{ approvedCount }}</span>
          <span class="stat-label">Approved</span>
        </div>
        <div class="summary-stat rejected">
          <span class="stat-num">{{ noMatchCount }}</span>
          <span class="stat-label">No Match</span>
        </div>
      </div>
      <div class="summary-actions">
        <Button 
          label="Bulk Approve High Confidence"
          icon="pi pi-check-circle"
          size="small"
          severity="success"
          :disabled="highConfidenceCount === 0"
          @click="handleBulkApprove"
        />
        <Button 
          icon="pi pi-refresh"
          size="small"
          severity="secondary"
          @click="loadSuggestions"
          :loading="loading"
          v-tooltip.top="'Refresh'"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading && suggestions.length === 0" class="loading-container">
      <ProgressSpinner />
      <p>Loading suggestions...</p>
    </div>

    <!-- Suggestions List -->
    <div v-else class="suggestions-list">
      <div 
        v-for="suggestion in suggestions" 
        :key="suggestion.suggestion_id"
        class="suggestion-card"
        :class="{ 
          'approved': suggestion.suggestion_status === 'APPROVED' || suggestion.suggestion_status === 'EDITED',
          'rejected': suggestion.suggestion_status === 'REJECTED',
          'skipped': suggestion.suggestion_status === 'SKIPPED',
          'no-match': suggestion.suggestion_status === 'NO_MATCH' || suggestion.suggestion_status === 'NO_PATTERN'
        }"
      >
        <div class="suggestion-header">
          <div class="column-info">
            <i class="pi pi-arrow-circle-right"></i>
            <div class="column-names">
              <strong>{{ suggestion.tgt_column_name }}</strong>
              <span class="physical">{{ suggestion.tgt_column_physical_name }}</span>
            </div>
          </div>
          <div class="suggestion-meta">
            <Tag 
              :value="formatStatus(suggestion.suggestion_status)" 
              :severity="getStatusSeverity(suggestion.suggestion_status)"
              size="small"
            />
            <div v-if="suggestion.confidence_score" class="confidence-badge" :class="getConfidenceClass(suggestion.confidence_score)">
              {{ (suggestion.confidence_score * 100).toFixed(0) }}%
            </div>
          </div>
        </div>

        <div class="suggestion-description" v-if="suggestion.tgt_comments">
          {{ suggestion.tgt_comments }}
        </div>

        <!-- Pattern Info -->
        <div v-if="suggestion.pattern_type" class="pattern-info">
          <Tag :value="suggestion.pattern_type" severity="secondary" size="small" />
          <span class="pattern-label">Pattern from historical mapping</span>
        </div>

        <!-- Matched Source Fields -->
        <div v-if="getMatchedFields(suggestion).length > 0" class="matched-sources">
          <h4>Matched Source Fields:</h4>
          <div class="source-tags">
            <Tag 
              v-for="(field, idx) in getMatchedFields(suggestion).slice(0, 3)" 
              :key="idx"
              :value="`${field.src_table_physical_name}.${field.src_column_physical_name}`"
              severity="info"
              size="small"
            />
            <Badge 
              v-if="getMatchedFields(suggestion).length > 3"
              :value="`+${getMatchedFields(suggestion).length - 3}`"
              severity="secondary"
            />
          </div>
        </div>

        <!-- SQL Preview -->
        <div v-if="suggestion.suggested_sql" class="sql-preview">
          <div class="sql-header">
            <h4>SQL Expression:</h4>
            <Button 
              icon="pi pi-copy"
              text
              size="small"
              @click="copySQL(suggestion.suggested_sql)"
              v-tooltip.top="'Copy SQL'"
            />
          </div>
          <pre class="sql-code">{{ suggestion.suggested_sql }}</pre>
        </div>

        <!-- No Match Message -->
        <div v-if="suggestion.suggestion_status === 'NO_MATCH'" class="no-match-message">
          <i class="pi pi-exclamation-triangle"></i>
          <span>No matching source fields found. Manual mapping may be required.</span>
        </div>

        <!-- No Pattern Message -->
        <div v-if="suggestion.suggestion_status === 'NO_PATTERN'" class="no-pattern-message">
          <i class="pi pi-info-circle"></i>
          <span>No historical pattern found for this column. This will be the first mapping.</span>
        </div>

        <!-- Warnings -->
        <div v-if="getWarnings(suggestion).length > 0" class="warnings">
          <div v-for="(warning, idx) in getWarnings(suggestion)" :key="idx" class="warning-item">
            <i class="pi pi-exclamation-circle"></i>
            {{ warning }}
          </div>
        </div>

        <!-- Actions -->
        <div class="suggestion-actions" v-if="suggestion.suggestion_status === 'PENDING'">
          <!-- Show Edit first if there are warnings or low confidence -->
          <template v-if="hasWarningsOrIssues(suggestion)">
            <Button 
              label="Review & Edit"
              icon="pi pi-pencil"
              size="small"
              severity="warning"
              @click="openEditDialog(suggestion)"
            />
            <Button 
              label="Approve Anyway"
              icon="pi pi-check"
              size="small"
              severity="success"
              outlined
              @click="handleApprove(suggestion)"
            />
          </template>
          <!-- Show Approve first if clean (no warnings, high confidence) -->
          <template v-else>
            <Button 
              label="Approve"
              icon="pi pi-check"
              size="small"
              severity="success"
              @click="handleApprove(suggestion)"
            />
            <Button 
              label="Edit"
              icon="pi pi-pencil"
              size="small"
              severity="info"
              outlined
              @click="openEditDialog(suggestion)"
            />
          </template>
          <Button 
            label="Reject"
            icon="pi pi-times"
            size="small"
            severity="danger"
            outlined
            @click="openRejectDialog(suggestion)"
          />
          <Button 
            label="Skip"
            icon="pi pi-forward"
            size="small"
            severity="secondary"
            text
            @click="handleSkip(suggestion)"
          />
        </div>

        <!-- Manual Mapping Action for No Match -->
        <div class="suggestion-actions" v-if="suggestion.suggestion_status === 'NO_MATCH' || suggestion.suggestion_status === 'NO_PATTERN'">
          <Button 
            label="Create Manual Mapping"
            icon="pi pi-plus"
            size="small"
            @click="$emit('manual-mapping', suggestion)"
          />
          <Button 
            label="Skip"
            icon="pi pi-forward"
            size="small"
            severity="secondary"
            text
            @click="handleSkip(suggestion)"
          />
        </div>

        <!-- Reviewed Info -->
        <div v-if="suggestion.reviewed_by" class="reviewed-info">
          <i class="pi pi-user"></i>
          Reviewed by {{ suggestion.reviewed_by }} on {{ formatDate(suggestion.reviewed_ts) }}
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="suggestions.length === 0 && !loading" class="empty-state">
        <i class="pi pi-check-circle" style="font-size: 3rem; color: var(--green-500);"></i>
        <h3>All Caught Up!</h3>
        <p>No suggestions to review for this table.</p>
      </div>
    </div>

    <!-- Enhanced Edit Dialog -->
    <Dialog 
      v-model:visible="showEditDialog" 
      modal 
      header="Edit Mapping" 
      :style="{ width: '95vw', maxWidth: '1200px' }"
      maximizable
    >
      <div v-if="editingSuggestion" class="edit-dialog-content">
        <!-- Target Info Header -->
        <div class="edit-header">
          <div class="target-info">
            <Tag value="TARGET" severity="info" />
            <strong>{{ editingSuggestion.tgt_table_name }}.{{ editingSuggestion.tgt_column_name }}</strong>
            <span class="datatype">({{ editingSuggestion.tgt_physical_datatype || 'STRING' }})</span>
          </div>
          <div class="target-description" v-if="editingSuggestion.tgt_comments">
            {{ editingSuggestion.tgt_comments }}
          </div>
        </div>

        <!-- Two Column Layout -->
        <div class="edit-columns">
          <!-- Left: Source Fields -->
          <div class="source-panel">
            <div class="panel-header">
              <h4><i class="pi pi-table"></i> Available Source Fields</h4>
              <InputText 
                v-model="sourceFilter" 
                placeholder="Filter columns..." 
                size="small"
                class="source-filter"
              />
            </div>
            
            <div class="source-tables">
              <div v-for="table in groupedSourceFields" :key="table.tableName" class="source-table-group">
                <div class="table-header" @click="toggleTableExpand(table.tableName)">
                  <i :class="expandedTables.includes(table.tableName) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
                  <strong>{{ table.tableName }}</strong>
                  <Badge :value="table.columns.length" severity="secondary" />
                </div>
                <div v-if="expandedTables.includes(table.tableName)" class="table-columns">
                  <div 
                    v-for="col in filteredColumns(table.columns)" 
                    :key="col.unmapped_field_id"
                    class="column-item"
                    :class="{ 'matched': isMatchedColumn(col) }"
                    @click="insertColumnToSQL(col)"
                    v-tooltip.right="col.src_comments || 'Click to insert'"
                  >
                    <span class="col-name">{{ col.src_column_physical_name }}</span>
                    <span class="col-type">{{ col.src_physical_datatype || 'STRING' }}</span>
                    <i v-if="isMatchedColumn(col)" class="pi pi-check matched-icon"></i>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Right: SQL Editor -->
          <div class="sql-panel">
            <!-- Pattern Info & Warnings -->
            <div v-if="getChanges(editingSuggestion).length > 0 || getWarnings(editingSuggestion).length > 0" class="pattern-changes">
              <h4><i class="pi pi-info-circle"></i> AI Changes & Notes</h4>
              <div class="changes-list">
                <div v-for="(change, idx) in getChanges(editingSuggestion)" :key="'c'+idx" class="change-item">
                  <i class="pi pi-arrow-right"></i>
                  <span v-if="change.original">Replaced: <code>{{ change.original }}</code> → <code>{{ change.replacement }}</code></span>
                  <span v-else>{{ change.description || change }}</span>
                </div>
                <div v-for="(warning, idx) in getWarnings(editingSuggestion)" :key="'w'+idx" class="warning-item">
                  <i class="pi pi-exclamation-triangle"></i>
                  <span>{{ warning }}</span>
                </div>
              </div>
            </div>

            <!-- SQL Editor with AI Helper -->
            <div class="sql-editor-section">
              <div class="sql-header">
                <label>SQL Expression:</label>
                <div class="sql-actions">
                  <Button 
                    label="AI Assist" 
                    icon="pi pi-bolt" 
                    size="small"
                    severity="help"
                    outlined
                    @click="showAIAssist = true"
                    v-tooltip.top="'Get AI help with this expression'"
                  />
                  <Button 
                    icon="pi pi-copy" 
                    size="small"
                    text
                    @click="copySQL(editedSQL)"
                    v-tooltip.top="'Copy SQL'"
                  />
                </div>
              </div>
              <Textarea 
                v-model="editedSQL" 
                :rows="10"
                class="sql-editor w-full"
                placeholder="Enter the SQL expression..."
                spellcheck="false"
              />
            </div>

            <!-- Matched Source Summary -->
            <div class="matched-summary" v-if="getMatchedFields(editingSuggestion).length > 0">
              <h4>Matched Source Fields:</h4>
              <div class="matched-tags">
                <Tag 
                  v-for="field in getMatchedFields(editingSuggestion)" 
                  :key="field.unmapped_field_id"
                  :value="`${field.src_table_physical_name}.${field.src_column_physical_name} (${(field.match_score * 100).toFixed(0)}%)`"
                  severity="success"
                  size="small"
                />
              </div>
            </div>

            <!-- Edit Notes -->
            <div class="field">
              <label>Notes (optional):</label>
              <InputText 
                v-model="editNotes" 
                class="w-full"
                placeholder="Explain your changes..."
              />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" icon="pi pi-times" @click="showEditDialog = false" severity="secondary" />
        <Button label="Save & Approve" icon="pi pi-check" @click="handleEditApprove" :loading="saving" severity="success" />
      </template>
    </Dialog>

    <!-- AI Assist Dialog -->
    <Dialog 
      v-model:visible="showAIAssist" 
      modal 
      header="AI SQL Assistant" 
      :style="{ width: '600px' }"
    >
      <div class="ai-assist-content">
        <p>Describe what you need help with:</p>
        <Textarea 
          v-model="aiPrompt" 
          :rows="3"
          class="w-full"
          placeholder="e.g., Join recipient_master to member table on SAK_RECIP..."
        />
      </div>
      <template #footer>
        <Button label="Cancel" @click="showAIAssist = false" severity="secondary" />
        <Button label="Generate SQL" icon="pi pi-bolt" @click="handleAIAssist" :loading="aiGenerating" />
      </template>
    </Dialog>

    <!-- Reject Dialog -->
    <Dialog 
      v-model:visible="showRejectDialog" 
      modal 
      header="Reject Suggestion" 
      :style="{ width: '500px' }"
    >
      <div class="reject-dialog-content">
        <p>Why is this suggestion being rejected? This feedback helps improve future AI suggestions.</p>
        <Textarea 
          v-model="rejectReason" 
          :rows="4"
          class="w-full"
          placeholder="e.g., Wrong source table, incorrect transformation, missing join condition..."
        />
      </div>

      <template #footer>
        <Button label="Cancel" icon="pi pi-times" @click="showRejectDialog = false" severity="secondary" />
        <Button label="Reject" icon="pi pi-times" @click="handleReject" severity="danger" :loading="saving" :disabled="!rejectReason" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useProjectsStore, type MappingSuggestion, type MatchedSourceField } from '@/stores/projectsStore'
import { useUserStore } from '@/stores/user'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import ProgressSpinner from 'primevue/progressspinner'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'
import InputText from 'primevue/inputtext'

const props = defineProps<{
  projectId: number
  tableId: number
  tableName: string
}>()

const emit = defineEmits(['suggestion-updated', 'manual-mapping'])

const toast = useToast()
const projectsStore = useProjectsStore()
const userStore = useUserStore()

// State
const showEditDialog = ref(false)
const showRejectDialog = ref(false)
const showAIAssist = ref(false)
const editingSuggestion = ref<MappingSuggestion | null>(null)
const rejectingSuggestion = ref<MappingSuggestion | null>(null)
const editedSQL = ref('')
const editNotes = ref('')
const rejectReason = ref('')
const saving = ref(false)
const aiGenerating = ref(false)
const aiPrompt = ref('')
const sourceFilter = ref('')
const expandedTables = ref<string[]>([])
const sourceFields = ref<any[]>([])

// Computed
const suggestions = computed(() => projectsStore.suggestions)
const loading = computed(() => projectsStore.loading)

const pendingCount = computed(() => 
  suggestions.value.filter(s => s.suggestion_status === 'PENDING').length
)
const approvedCount = computed(() => 
  suggestions.value.filter(s => s.suggestion_status === 'APPROVED' || s.suggestion_status === 'EDITED').length
)
const noMatchCount = computed(() => 
  suggestions.value.filter(s => s.suggestion_status === 'NO_MATCH' || s.suggestion_status === 'NO_PATTERN').length
)
const highConfidenceCount = computed(() => 
  suggestions.value.filter(s => 
    s.suggestion_status === 'PENDING' && 
    (s.confidence_score || 0) >= 0.8
  ).length
)

// Group source fields by table
const groupedSourceFields = computed(() => {
  const groups: { tableName: string; columns: any[] }[] = []
  const tableMap = new Map<string, any[]>()
  
  for (const field of sourceFields.value) {
    const tableName = field.src_table_physical_name || 'Unknown'
    if (!tableMap.has(tableName)) {
      tableMap.set(tableName, [])
    }
    tableMap.get(tableName)!.push(field)
  }
  
  tableMap.forEach((columns, tableName) => {
    groups.push({ tableName, columns })
  })
  
  return groups.sort((a, b) => a.tableName.localeCompare(b.tableName))
})

// Lifecycle
onMounted(() => {
  loadSuggestions()
})

watch(() => props.tableId, () => {
  loadSuggestions()
})

// Methods
async function loadSuggestions() {
  await projectsStore.fetchSuggestions(props.projectId, props.tableId)
}

function getMatchedFields(suggestion: MappingSuggestion): MatchedSourceField[] {
  return projectsStore.parseMatchedSourceFields(suggestion.matched_source_fields)
}

function getWarnings(suggestion: MappingSuggestion): string[] {
  if (!suggestion.warnings) return []
  try {
    return JSON.parse(suggestion.warnings)
  } catch {
    return []
  }
}

async function handleApprove(suggestion: MappingSuggestion) {
  try {
    await projectsStore.approveSuggestion(suggestion.suggestion_id, userStore.userEmail || 'unknown')
    toast.add({ severity: 'success', summary: 'Approved', detail: 'Mapping created', life: 2000 })
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  }
}

function openEditDialog(suggestion: MappingSuggestion) {
  editingSuggestion.value = suggestion
  editedSQL.value = suggestion.suggested_sql || ''
  editNotes.value = ''
  sourceFilter.value = ''
  expandedTables.value = []
  showEditDialog.value = true
  
  // Load source fields for the project
  loadSourceFields()
}

async function loadSourceFields() {
  try {
    const response = await fetch(`/api/v4/projects/${props.projectId}/source-fields`)
    if (response.ok) {
      sourceFields.value = await response.json()
      // Auto-expand first table
      if (groupedSourceFields.value.length > 0) {
        expandedTables.value = [groupedSourceFields.value[0].tableName]
      }
    }
  } catch (e) {
    console.error('Error loading source fields:', e)
  }
}

function toggleTableExpand(tableName: string) {
  if (expandedTables.value.includes(tableName)) {
    expandedTables.value = expandedTables.value.filter(t => t !== tableName)
  } else {
    expandedTables.value.push(tableName)
  }
}

function filteredColumns(columns: any[]) {
  if (!sourceFilter.value) return columns
  const filter = sourceFilter.value.toLowerCase()
  return columns.filter(c => 
    c.src_column_physical_name?.toLowerCase().includes(filter) ||
    c.src_comments?.toLowerCase().includes(filter)
  )
}

function isMatchedColumn(col: any): boolean {
  if (!editingSuggestion.value) return false
  const matched = getMatchedFields(editingSuggestion.value)
  return matched.some(m => m.unmapped_field_id === col.unmapped_field_id)
}

function insertColumnToSQL(col: any) {
  const insertion = `${col.src_table_physical_name}.${col.src_column_physical_name}`
  editedSQL.value += (editedSQL.value ? ' ' : '') + insertion
}

function getChanges(suggestion: MappingSuggestion): any[] {
  if (!suggestion.sql_changes) return []
  try {
    return JSON.parse(suggestion.sql_changes)
  } catch {
    return []
  }
}

function hasWarningsOrIssues(suggestion: MappingSuggestion): boolean {
  const warnings = getWarnings(suggestion)
  const confidence = suggestion.confidence_score || 0
  // Has issues if: warnings exist, low confidence, or no matched sources
  return warnings.length > 0 || confidence < 0.9 || !suggestion.matched_source_fields || suggestion.matched_source_fields === '[]'
}

async function handleAIAssist() {
  if (!aiPrompt.value) return
  
  aiGenerating.value = true
  try {
    const response = await fetch('/api/v3/ai/generate-sql', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: aiPrompt.value,
        context: {
          target_column: editingSuggestion.value?.tgt_column_name,
          target_table: editingSuggestion.value?.tgt_table_name,
          current_sql: editedSQL.value
        }
      })
    })
    
    if (response.ok) {
      const result = await response.json()
      if (result.sql) {
        editedSQL.value = result.sql
        toast.add({ severity: 'success', summary: 'SQL Generated', detail: 'AI generated SQL expression', life: 2000 })
      }
    } else {
      toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to generate SQL', life: 3000 })
    }
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'AI service unavailable', life: 3000 })
  } finally {
    aiGenerating.value = false
    showAIAssist.value = false
    aiPrompt.value = ''
  }
}

async function handleEditApprove() {
  if (!editingSuggestion.value || !editedSQL.value) return
  
  saving.value = true
  try {
    await projectsStore.editAndApproveSuggestion(
      editingSuggestion.value.suggestion_id,
      userStore.userEmail || 'unknown',
      editedSQL.value,
      editNotes.value || undefined
    )
    toast.add({ severity: 'success', summary: 'Saved', detail: 'Edited mapping created', life: 2000 })
    showEditDialog.value = false
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  } finally {
    saving.value = false
  }
}

function openRejectDialog(suggestion: MappingSuggestion) {
  rejectingSuggestion.value = suggestion
  rejectReason.value = ''
  showRejectDialog.value = true
}

async function handleReject() {
  if (!rejectingSuggestion.value || !rejectReason.value) return
  
  saving.value = true
  try {
    await projectsStore.rejectSuggestion(
      rejectingSuggestion.value.suggestion_id,
      userStore.userEmail || 'unknown',
      rejectReason.value
    )
    toast.add({ severity: 'info', summary: 'Rejected', detail: 'Feedback recorded', life: 2000 })
    showRejectDialog.value = false
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  } finally {
    saving.value = false
  }
}

async function handleSkip(suggestion: MappingSuggestion) {
  try {
    await projectsStore.skipSuggestion(suggestion.suggestion_id, userStore.userEmail || 'unknown')
    toast.add({ severity: 'info', summary: 'Skipped', detail: 'Column skipped', life: 2000 })
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  }
}

async function handleBulkApprove() {
  const highConfidence = suggestions.value.filter(s => 
    s.suggestion_status === 'PENDING' && 
    (s.confidence_score || 0) >= 0.8
  )
  
  if (highConfidence.length === 0) return
  
  try {
    const result = await projectsStore.bulkApprove(
      highConfidence.map(s => s.suggestion_id),
      userStore.userEmail || 'unknown',
      0.8
    )
    
    toast.add({ 
      severity: 'success', 
      summary: 'Bulk Approve Complete', 
      detail: `Approved ${result.approved_count} suggestions`,
      life: 3000 
    })
    
    await loadSuggestions()
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  }
}

function copySQL(sql: string) {
  navigator.clipboard.writeText(sql)
  toast.add({ severity: 'info', summary: 'Copied', detail: 'SQL copied to clipboard', life: 2000 })
}

function formatStatus(status: string): string {
  return status.replace(/_/g, ' ')
}

function getStatusSeverity(status: string): 'success' | 'info' | 'warning' | 'danger' | 'secondary' {
  switch (status) {
    case 'APPROVED':
    case 'EDITED': return 'success'
    case 'PENDING': return 'warning'
    case 'REJECTED': return 'danger'
    case 'SKIPPED': return 'secondary'
    case 'NO_MATCH':
    case 'NO_PATTERN': return 'info'
    default: return 'secondary'
  }
}

function getConfidenceClass(score: number): string {
  if (score >= 0.8) return 'high'
  if (score >= 0.6) return 'medium'
  return 'low'
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.suggestion-review-panel {
  max-height: 70vh;
  overflow-y: auto;
}

/* Summary Bar */
.summary-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  margin-bottom: 1rem;
  position: sticky;
  top: 0;
  z-index: 10;
}

.summary-stats {
  display: flex;
  gap: 2rem;
}

.summary-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-num {
  font-size: 1.5rem;
  font-weight: 600;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
}

.summary-stat.pending .stat-num { color: var(--orange-500); }
.summary-stat.approved .stat-num { color: var(--green-500); }
.summary-stat.rejected .stat-num { color: var(--red-500); }

.summary-actions {
  display: flex;
  gap: 0.5rem;
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  gap: 1rem;
}

/* Suggestions List */
.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.suggestion-card {
  border: 1px solid var(--surface-border);
  border-radius: 10px;
  padding: 1.25rem;
  background: white;
  transition: all 0.2s;
}

.suggestion-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.suggestion-card.approved {
  border-left: 4px solid var(--green-500);
  background: #f1f8e9;
}

.suggestion-card.rejected {
  border-left: 4px solid var(--red-500);
  opacity: 0.7;
}

.suggestion-card.skipped {
  border-left: 4px solid var(--surface-400);
  opacity: 0.6;
}

.suggestion-card.no-match {
  border-left: 4px solid var(--orange-500);
  background: #fff8e1;
}

/* Card Header */
.suggestion-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.column-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.column-info i {
  color: var(--gainwell-secondary);
  font-size: 1.25rem;
}

.column-names {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.column-names strong {
  color: var(--text-color);
}

.column-names .physical {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  font-family: monospace;
}

.suggestion-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.confidence-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.confidence-badge.high {
  background: #c8e6c9;
  color: #2e7d32;
}

.confidence-badge.medium {
  background: #ffe0b2;
  color: #e65100;
}

.confidence-badge.low {
  background: #ffcdd2;
  color: #c62828;
}

.suggestion-description {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

/* Pattern Info */
.pattern-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.pattern-label {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

/* Matched Sources */
.matched-sources {
  margin-bottom: 0.75rem;
}

.matched-sources h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.source-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
}

/* SQL Preview */
.sql-preview {
  margin-bottom: 0.75rem;
}

.sql-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sql-header h4 {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.sql-code {
  background: var(--surface-50);
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 0.75rem;
  font-family: monospace;
  font-size: 0.85rem;
  overflow-x: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 150px;
  overflow-y: auto;
}

/* Messages */
.no-match-message,
.no-pattern-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

.no-match-message {
  background: #fff3e0;
  color: #e65100;
}

.no-pattern-message {
  background: #e3f2fd;
  color: #1565c0;
}

/* Warnings */
.warnings {
  margin-bottom: 0.75rem;
}

.warning-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #fff3e0;
  color: #e65100;
  border-radius: 4px;
  font-size: 0.85rem;
  margin-bottom: 0.35rem;
}

/* Actions */
.suggestion-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-border);
}

/* Reviewed Info */
.reviewed-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-border);
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  gap: 0.75rem;
  text-align: center;
}

.empty-state h3 {
  margin: 0;
  color: var(--text-color);
}

.empty-state p {
  margin: 0;
  color: var(--text-color-secondary);
}

/* Enhanced Edit Dialog */
.edit-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.edit-header {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  border-left: 4px solid var(--primary-color);
}

.target-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.target-info .datatype {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.target-description {
  margin-top: 0.5rem;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.edit-columns {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1.5rem;
  min-height: 400px;
}

/* Source Panel */
.source-panel {
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 0.75rem;
  background: var(--surface-100);
  border-bottom: 1px solid var(--surface-border);
}

.panel-header h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.source-filter {
  width: 100%;
}

.source-tables {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
}

.source-table-group {
  border-bottom: 1px solid var(--surface-border);
}

.table-header {
  padding: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  background: var(--surface-50);
  transition: background 0.2s;
}

.table-header:hover {
  background: var(--surface-100);
}

.table-header i {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.table-columns {
  padding: 0.25rem;
}

.column-item {
  padding: 0.5rem 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
}

.column-item:hover {
  background: var(--primary-50);
}

.column-item.matched {
  background: var(--green-50);
  border-left: 3px solid var(--green-500);
}

.col-name {
  flex: 1;
  font-family: monospace;
  font-size: 0.85rem;
}

.col-type {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.matched-icon {
  color: var(--green-500);
  font-size: 0.8rem;
}

/* SQL Panel */
.sql-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.pattern-changes {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  border: 1px solid var(--surface-border);
}

.pattern-changes h4 {
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--primary-color);
}

.changes-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.change-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.change-item i {
  color: var(--primary-color);
  margin-top: 2px;
}

.change-item code {
  background: var(--surface-200);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-size: 0.8rem;
}

.change-item .warning-item {
  color: var(--orange-600);
}

.change-item .warning-item i {
  color: var(--orange-500);
}

.sql-editor-section {
  flex: 1;
}

.sql-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.sql-header label {
  font-weight: 500;
}

.sql-actions {
  display: flex;
  gap: 0.25rem;
}

.sql-editor {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.9rem;
  background: var(--surface-900);
  color: var(--surface-50);
  border-radius: 8px;
}

.matched-summary {
  padding: 0.75rem;
  background: var(--green-50);
  border-radius: 6px;
  border: 1px solid var(--green-200);
}

.matched-summary h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  color: var(--green-700);
}

.matched-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

/* AI Assist Dialog */
.ai-assist-content p {
  margin: 0 0 1rem 0;
  color: var(--text-color-secondary);
}

/* Reject Dialog */
.reject-dialog-content p {
  margin: 0 0 1rem 0;
  color: var(--text-color-secondary);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  color: var(--text-color);
}

.w-full {
  width: 100%;
}
</style>

