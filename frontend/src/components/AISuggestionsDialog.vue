<template>
  <Dialog
    v-model:visible="isVisible"
    modal
    :header="dialogTitle"
    :style="{ width: '90vw', maxWidth: '1200px' }"
    :closable="true"
    @hide="handleClose"
  >
    <div class="ai-suggestions-content">
      <!-- Source Fields Summary -->
      <div class="source-fields-summary">
        <h3>
          <i class="pi pi-arrow-right"></i>
          Selected Source Fields ({{ aiStore.sourceFieldsUsed.length }})
        </h3>
        <div class="source-fields-list">
          <div 
            v-for="field in aiStore.sourceFieldsUsed" 
            :key="field.id"
            class="source-field-card"
          >
            <div class="field-name">
              <Tag 
                :value="`${field.src_table_name}.${field.src_column_name}`"
                severity="info"
              />
              <span class="datatype-badge">{{ field.src_physical_datatype }}</span>
            </div>
            <div v-if="field.src_comments" class="field-description">
              <i class="pi pi-info-circle"></i>
              <span>{{ field.src_comments }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="aiStore.loading" class="loading-container">
        <ProgressSpinner />
        <p>Analyzing fields and generating AI suggestions...</p>
        <p class="loading-hint">This may take a few seconds</p>
      </div>

      <!-- Error State -->
      <Message v-if="aiStore.error" severity="error" :closable="true">
        {{ aiStore.error }}
      </Message>

      <!-- AI Suggestions Table -->
      <div v-if="!aiStore.loading && aiStore.hasSuggestions" class="suggestions-section">
        <h3>
          <i class="pi pi-sparkles"></i>
          AI Suggested Target Fields
        </h3>
        
        <DataTable
          :value="aiStore.suggestions"
          dataKey="tgt_column_name"
          :paginator="false"
          class="suggestions-table"
          stripedRows
          @row-click="handleRowClick"
          :rowClass="getRowClass"
        >
          <!-- Rank -->
          <Column header="Rank" style="width: 5rem">
            <template #body="{ data }">
              <div class="rank-badge" :class="`rank-${data.rank}`">
                #{{ data.rank }}
              </div>
            </template>
          </Column>

          <!-- Target Field -->
          <Column header="Target Field" style="min-width: 15rem">
            <template #body="{ data }">
              <div class="target-field">
                <strong>{{ data.tgt_table_name }}.{{ data.tgt_column_name }}</strong>
                <span class="physical-name">{{ data.tgt_column_physical_name }}</span>
              </div>
            </template>
          </Column>

          <!-- Description -->
          <Column header="Description" style="min-width: 18rem">
            <template #body="{ data }">
              <div class="target-description">
                <i v-if="data.tgt_comments" class="pi pi-info-circle"></i>
                <span>{{ data.tgt_comments || 'No description available' }}</span>
              </div>
            </template>
          </Column>

          <!-- Match Quality -->
          <Column header="Match Quality" style="min-width: 10rem">
            <template #body="{ data }">
              <div class="match-quality">
                <Tag 
                  :value="data.match_quality" 
                  :severity="getMatchQualitySeverity(data.match_quality)"
                  :icon="getMatchQualityIcon(data.match_quality)"
                />
              </div>
            </template>
          </Column>

          <!-- AI Reasoning -->
          <Column header="AI Reasoning" style="min-width: 20rem">
            <template #body="{ data }">
              <div class="ai-reasoning">
                <i class="pi pi-comment"></i>
                <span>{{ data.ai_reasoning }}</span>
              </div>
            </template>
          </Column>

          <!-- Actions -->
          <Column header="Actions" style="width: 15rem">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  label="Accept"
                  icon="pi pi-check"
                  size="small"
                  severity="success"
                  @click.stop="handleAccept(data)"
                  v-tooltip.top="'Accept this suggestion and continue with mapping'"
                />
                <Button
                  label="Reject"
                  icon="pi pi-times"
                  size="small"
                  severity="danger"
                  outlined
                  @click.stop="handleReject(data)"
                  v-tooltip.top="'Reject this suggestion and provide feedback'"
                />
              </div>
            </template>
          </Column>
        </DataTable>

        <!-- Info Message -->
        <Message severity="info" :closable="false" class="info-message">
          <strong>Tip:</strong> Accept a suggestion to proceed with mapping configuration, or reject with comments to help improve future AI suggestions.
        </Message>
      </div>

      <!-- No Suggestions -->
      <div v-if="!aiStore.loading && !aiStore.hasSuggestions" class="no-suggestions">
        <i class="pi pi-inbox" style="font-size: 3rem; color: var(--text-color-secondary);"></i>
        <h3>No Suggestions Available</h3>
        <p>The AI could not generate suggestions for the selected fields.</p>
      </div>
    </div>

    <template #footer>
      <Button label="Cancel" icon="pi pi-times" @click="handleClose" text />
      <Button 
        label="Manual Search" 
        icon="pi pi-search" 
        @click="handleManualSearch"
        severity="secondary"
        v-tooltip.top="'Search for target fields manually'"
      />
    </template>
  </Dialog>

  <!-- Rejection Feedback Dialog -->
  <Dialog
    v-model:visible="showRejectionDialog"
    modal
    header="Provide Feedback on Rejected Suggestion"
    :style="{ width: '600px' }"
  >
    <div class="rejection-content">
      <Message severity="info" :closable="false">
        Your feedback helps improve AI suggestions for everyone. Please explain why this suggestion wasn't suitable.
      </Message>

      <div v-if="rejectedSuggestion" class="rejected-suggestion-summary">
        <h4>Rejected Suggestion:</h4>
        <div class="suggestion-details">
          <div class="detail-row">
            <label>Target Field:</label>
            <span><strong>{{ rejectedSuggestion.tgt_table_name }}.{{ rejectedSuggestion.tgt_column_name }}</strong></span>
          </div>
          <div class="detail-row">
            <label>Match Quality:</label>
            <Tag 
              :value="rejectedSuggestion.match_quality" 
              :severity="getMatchQualitySeverity(rejectedSuggestion.match_quality)"
            />
          </div>
          <div class="detail-row">
            <label>AI Reasoning:</label>
            <span class="ai-reason-text">{{ rejectedSuggestion.ai_reasoning }}</span>
          </div>
        </div>
      </div>

      <div class="feedback-form">
        <label for="rejection-comment">
          <i class="pi pi-comment"></i>
          Why is this suggestion incorrect? <span class="required">*</span>
        </label>
        <Textarea
          id="rejection-comment"
          v-model="rejectionComment"
          rows="5"
          placeholder="Example: Wrong data type, different business meaning, already mapped elsewhere..."
          class="w-full"
          autofocus
        />
        <small>Please provide specific details to help improve future suggestions</small>
      </div>
    </div>

    <template #footer>
      <Button label="Cancel" icon="pi pi-times" @click="closeRejectionDialog" text />
      <Button 
        label="Submit Feedback" 
        icon="pi pi-check" 
        @click="submitRejectionFeedback"
        :disabled="!rejectionComment.trim()"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAISuggestionsStoreV2 } from '@/stores/aiSuggestionsStoreV2'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import type { AISuggestionV2 } from '@/stores/aiSuggestionsStoreV2'

interface Props {
  visible: boolean
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'suggestion-selected', suggestion: AISuggestionV2): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const aiStore = useAISuggestionsStoreV2()
const toast = useToast()

// Rejection dialog state
const showRejectionDialog = ref(false)
const rejectedSuggestion = ref<AISuggestionV2 | null>(null)
const rejectionComment = ref('')

const isVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const dialogTitle = computed(() => {
  const count = aiStore.sourceFieldsUsed.length
  if (count === 1) {
    return 'AI Mapping Suggestions (Single Field)'
  } else {
    return `AI Mapping Suggestions (${count} Fields Combined)`
  }
})

function getMatchQualitySeverity(quality: string): string {
  switch (quality) {
    case 'Excellent':
      return 'success'
    case 'Strong':
      return 'info'
    case 'Good':
      return 'warning'
    case 'Weak':
      return 'danger'
    default:
      return 'secondary'
  }
}

function getMatchQualityIcon(quality: string): string {
  switch (quality) {
    case 'Excellent':
      return 'pi pi-star-fill'
    case 'Strong':
      return 'pi pi-check-circle'
    case 'Good':
      return 'pi pi-check'
    case 'Weak':
      return 'pi pi-exclamation-triangle'
    default:
      return 'pi pi-question'
  }
}

function getRowClass(data: AISuggestionV2) {
  return data.rank === 1 ? 'top-suggestion' : ''
}

function handleRowClick(event: any) {
  // Disabled for now - users should use explicit Accept/Reject buttons
  // handleAccept(event.data)
}

function handleAccept(suggestion: AISuggestionV2) {
  // Store the suggestion for mapping configuration
  aiStore.selectSuggestion(suggestion)
  
  // Record acceptance feedback (non-blocking, fire and forget)
  recordFeedback(suggestion, 'accepted', 'User accepted this AI suggestion').catch(err => {
    console.warn('[AI Suggestions] Feedback recording failed (non-critical):', err)
  })
  
  // Emit event to parent to proceed with mapping
  emit('suggestion-selected', suggestion)
  isVisible.value = false
  
  toast.add({
    severity: 'success',
    summary: 'Suggestion Accepted',
    detail: `Proceeding with mapping to ${suggestion.tgt_table_name}.${suggestion.tgt_column_name}`,
    life: 3000
  })
}

function handleReject(suggestion: AISuggestionV2) {
  rejectedSuggestion.value = suggestion
  rejectionComment.value = ''
  showRejectionDialog.value = true
}

function closeRejectionDialog() {
  showRejectionDialog.value = false
  rejectedSuggestion.value = null
  rejectionComment.value = ''
}

async function submitRejectionFeedback() {
  if (!rejectedSuggestion.value || !rejectionComment.value.trim()) {
    return
  }
  
  // Record rejection feedback (with error handling)
  try {
    await recordFeedback(rejectedSuggestion.value, 'rejected', rejectionComment.value)
    
    toast.add({
      severity: 'info',
      summary: 'Feedback Recorded',
      detail: 'Thank you! Your feedback will help improve future suggestions.',
      life: 3000
    })
  } catch (error) {
    console.warn('[AI Suggestions] Feedback recording failed (non-critical):', error)
    toast.add({
      severity: 'warn',
      summary: 'Feedback Not Saved',
      detail: 'Your rejection was recorded, but feedback could not be saved.',
      life: 3000
    })
  }
  
  closeRejectionDialog()
}

async function recordFeedback(suggestion: AISuggestionV2, action: 'accepted' | 'rejected', comment: string) {
  try {
    // Build feedback payload
    const feedback = {
      // Source fields (can be multiple in V2)
      source_fields: aiStore.sourceFieldsUsed.map(f => ({
        src_table_name: f.src_table_name,
        src_column_name: f.src_column_name
      })),
      // Suggested target field
      suggested_tgt_table: suggestion.tgt_table_name,
      suggested_tgt_column: suggestion.tgt_column_name,
      // AI metadata
      search_score: suggestion.search_score,
      ai_reasoning: suggestion.ai_reasoning,
      match_quality: suggestion.match_quality,
      rank: suggestion.rank,
      // User feedback
      feedback_action: action,
      user_comment: comment
    }
    
    console.log('[AI Suggestions] Recording feedback:', feedback)
    
    // Call feedback API (non-blocking)
    const response = await fetch('/api/v2/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(feedback)
    })
    
    if (!response.ok) {
      console.warn('[AI Suggestions] Feedback recording failed:', response.statusText)
    }
  } catch (error) {
    console.error('[AI Suggestions] Error recording feedback:', error)
    // Don't block the user flow if feedback fails
  }
}

function handleManualSearch() {
  // TODO: Navigate to manual search
  console.log('[AI Suggestions Dialog] Manual search requested')
}

function handleClose() {
  isVisible.value = false
}
</script>

<style scoped>
.ai-suggestions-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.source-fields-summary {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
  border-left: 4px solid var(--gainwell-primary);
}

.source-fields-summary h3 {
  margin: 0 0 0.5rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--gainwell-dark);
}

.source-fields-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.source-field-card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.source-field-card .field-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.source-field-card .datatype-badge {
  font-family: 'Courier New', monospace;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  background: var(--surface-100);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.source-field-card .field-description {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding-left: 0.5rem;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
  line-height: 1.4;
}

.source-field-card .field-description i {
  color: var(--gainwell-secondary);
  margin-top: 0.15rem;
  flex-shrink: 0;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  gap: 1rem;
}

.loading-hint {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.suggestions-section h3 {
  margin: 0 0 1rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--gainwell-dark);
}

.suggestions-section h3 i {
  color: var(--gainwell-accent);
}

.suggestions-table {
  border: 1px solid var(--surface-border);
  border-radius: 6px;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  font-weight: bold;
  font-size: 0.9rem;
}

.rank-badge.rank-1 {
  background: var(--green-100);
  color: var(--green-900);
  border: 2px solid var(--green-500);
}

.rank-badge.rank-2 {
  background: var(--blue-100);
  color: var(--blue-900);
  border: 2px solid var(--blue-500);
}

.rank-badge.rank-3 {
  background: var(--orange-100);
  color: var(--orange-900);
  border: 2px solid var(--orange-500);
}

.target-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.target-field strong {
  color: var(--text-color);
}

.physical-name {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  font-family: 'Courier New', monospace;
}

.target-description {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  line-height: 1.4;
  padding: 0.5rem;
  background: var(--surface-50);
  border-radius: 4px;
}

.target-description i {
  color: var(--gainwell-secondary);
  margin-top: 0.15rem;
  flex-shrink: 0;
}

.match-quality {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.ai-reasoning {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.ai-reasoning i {
  color: var(--gainwell-primary);
  margin-top: 0.25rem;
  flex-shrink: 0;
}

.ai-reasoning span {
  color: var(--text-color-secondary);
  line-height: 1.5;
}

.info-message {
  margin-top: 1rem;
}

.no-suggestions {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  gap: 1rem;
  text-align: center;
}

.no-suggestions h3 {
  margin: 0;
  color: var(--text-color);
}

.no-suggestions p {
  margin: 0;
  color: var(--text-color-secondary);
}

/* Top suggestion highlighting */
:deep(.top-suggestion) {
  background: var(--green-50) !important;
  border-left: 3px solid var(--green-500);
}

:deep(.top-suggestion:hover) {
  background: var(--green-100) !important;
}

/* Row hover effect */
:deep(.p-datatable-tbody > tr:hover) {
  background: var(--surface-hover);
  cursor: pointer;
}
</style>

