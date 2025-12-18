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
          <Button 
            label="Approve"
            icon="pi pi-check"
            size="small"
            severity="success"
            @click="handleApprove(suggestion)"
          />
          <Button 
            label="Edit & Approve"
            icon="pi pi-pencil"
            size="small"
            severity="info"
            outlined
            @click="openEditDialog(suggestion)"
          />
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

    <!-- Edit Dialog -->
    <Dialog 
      v-model:visible="showEditDialog" 
      modal 
      header="Edit SQL Expression" 
      :style="{ width: '700px' }"
    >
      <div v-if="editingSuggestion" class="edit-dialog-content">
        <div class="edit-target-info">
          <label>Target Column:</label>
          <strong>{{ editingSuggestion.tgt_column_name }}</strong>
        </div>

        <div class="field">
          <label>SQL Expression:</label>
          <Textarea 
            v-model="editedSQL" 
            :rows="8"
            class="sql-editor w-full"
            placeholder="Enter the SQL expression..."
          />
        </div>

        <div class="field">
          <label>Notes (optional):</label>
          <InputText 
            v-model="editNotes" 
            class="w-full"
            placeholder="Explain your changes..."
          />
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" icon="pi pi-times" @click="showEditDialog = false" severity="secondary" />
        <Button label="Save & Approve" icon="pi pi-check" @click="handleEditApprove" :loading="saving" />
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
const editingSuggestion = ref<MappingSuggestion | null>(null)
const rejectingSuggestion = ref<MappingSuggestion | null>(null)
const editedSQL = ref('')
const editNotes = ref('')
const rejectReason = ref('')
const saving = ref(false)

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
  showEditDialog.value = true
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

/* Edit Dialog */
.edit-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.edit-target-info {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.edit-target-info label {
  color: var(--text-color-secondary);
}

.sql-editor {
  font-family: monospace;
  font-size: 0.9rem;
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

