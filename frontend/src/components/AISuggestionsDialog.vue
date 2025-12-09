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

      <!-- Loading State with Stages -->
      <div v-if="aiStore.loading" class="loading-container">
        <ProgressSpinner />
        <h3>Analyzing Your Fields</h3>
        <div class="loading-stages">
          <div class="loading-stage" :class="{ active: loadingStage >= 1, completed: loadingStage > 1 }">
            <i :class="loadingStage > 1 ? 'pi pi-check-circle' : 'pi pi-search'"></i>
            <span>Searching target field matches...</span>
          </div>
          <div class="loading-stage" :class="{ active: loadingStage >= 2, completed: loadingStage > 2 }">
            <i :class="loadingStage > 2 ? 'pi pi-check-circle' : 'pi pi-history'"></i>
            <span>Finding similar past mappings...</span>
          </div>
          <div class="loading-stage" :class="{ active: loadingStage >= 3 }">
            <i class="pi pi-sparkles"></i>
            <span>AI analyzing best matches...</span>
          </div>
        </div>
        <p class="loading-hint">This may take a few seconds</p>
      </div>

      <!-- Error State -->
      <Message v-if="aiStore.error" severity="error" :closable="true">
        {{ aiStore.error }}
      </Message>

      <!-- PATTERN TEMPLATE DIALOG (shown when user clicks "Use as Template") -->
      <Dialog
        v-model:visible="showTemplateDialog"
        modal
        header="Apply Historical Pattern as Template"
        :style="{ width: '80vw', maxWidth: '900px' }"
        @hide="handleCloseTemplateDialog"
      >
        <PatternTemplateCard
          v-if="aiStore.selectedTemplatePattern"
          :pattern="aiStore.selectedTemplatePattern"
          :currently-selected-fields="aiStore.sourceFieldsUsed"
          :available-fields="availableUnmappedFields"
          @skip="handleCloseTemplateDialog"
          @apply="handleApplyTemplate"
        />
      </Dialog>

      <!-- Multi-Column Pattern Alert (informational only) -->
      <div v-if="!aiStore.loading && relevantMultiColumnPatterns.length > 0" class="multi-column-alert">
        <Message severity="warn" :closable="false">
          <template #icon>
            <i class="pi pi-exclamation-triangle" style="font-size: 1.5rem;"></i>
          </template>
          <div class="alert-content">
            <strong>Multi-Column Mapping Pattern Found!</strong>
            <p>Based on similar past mappings, this target field typically uses <strong>multiple source columns</strong>.</p>
            <div class="pattern-examples">
              <div v-for="(pattern, idx) in relevantMultiColumnPatterns.slice(0, 2)" :key="idx" class="pattern-example">
                <i class="pi pi-history"></i>
                <span>
                  <strong>{{ pattern.tgt_column_name }}</strong> used: 
                  <code>{{ pattern.source_columns }}</code>
                  <span v-if="pattern.source_relationship_type" class="relationship-type">
                    ({{ pattern.source_relationship_type }})
                  </span>
                </span>
              </div>
            </div>
            <p class="action-hint">
              <i class="pi pi-lightbulb"></i>
              Consider selecting additional source fields before mapping, or use the SQL helper to combine fields.
            </p>
          </div>
        </Message>
      </div>

      <!-- Historical Patterns Summary - User can choose to use any as template -->
      <div v-if="!aiStore.loading && aiStore.historicalPatterns.length > 0" class="historical-patterns-section">
        <h3 @click="showPatternDetails = !showPatternDetails" class="collapsible-header">
          <i class="pi pi-history"></i>
          Similar Past Mappings ({{ aiStore.historicalPatterns.length }})
          <i :class="showPatternDetails ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="toggle-icon"></i>
        </h3>
        <p class="patterns-hint">
          <i class="pi pi-info-circle"></i>
          Click "Use as Template" to apply a past mapping pattern to your current fields
        </p>
        <div v-if="showPatternDetails" class="patterns-list">
          <div v-for="(pattern, idx) in aiStore.historicalPatterns.slice(0, 8)" :key="idx" class="pattern-card">
            <div class="pattern-header">
              <Tag :value="pattern.source_relationship_type || 'SINGLE'" 
                   :severity="pattern.source_relationship_type === 'SINGLE' ? 'info' : 'warning'" 
                   size="small" />
              <span class="target-name">→ {{ pattern.tgt_table_name }}.{{ pattern.tgt_column_name }}</span>
              <Tag 
                v-if="pattern.isMultiColumn" 
                value="Multi-Column" 
                severity="warning" 
                size="small" 
                icon="pi pi-table"
              />
            </div>
            <div class="pattern-details">
              <div v-if="pattern.source_columns" class="detail-item">
                <label>Source Columns:</label>
                <code>{{ pattern.source_columns }}</code>
              </div>
              <div v-if="pattern.transformations_applied" class="detail-item">
                <label>Transforms:</label>
                <span class="transforms">{{ pattern.transformations_applied }}</span>
              </div>
            </div>
            <div class="pattern-actions">
              <Button
                label="Use as Template"
                icon="pi pi-copy"
                size="small"
                severity="secondary"
                @click="handleUseAsTemplate(pattern)"
                v-tooltip.top="'Apply this pattern to your selected fields'"
              />
            </div>
          </div>
        </div>
      </div>

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
          <Column header="Match Quality" style="min-width: 12rem">
            <template #body="{ data }">
              <div class="match-quality">
                <Tag 
                  :value="data.match_quality" 
                  :severity="getMatchQualitySeverity(data.match_quality)"
                  :icon="getMatchQualityIcon(data.match_quality)"
                />
                <Tag 
                  v-if="data.fromPattern" 
                  value="Pattern" 
                  severity="warning" 
                  icon="pi pi-history"
                  class="pattern-tag"
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
      <div v-if="!aiStore.loading && !aiStore.hasSuggestions && !showManualSearch" class="no-suggestions">
        <i class="pi pi-inbox" style="font-size: 3rem; color: var(--text-color-secondary);"></i>
        <h3>No Suggestions Available</h3>
        <p>The AI could not generate suggestions for the selected fields.</p>
        <p>Try using Manual Search to browse all available target fields.</p>
      </div>

      <!-- Manual Search Section -->
      <div v-if="showManualSearch" class="manual-search-section">
        <h3>
          <i class="pi pi-search"></i>
          Manual Search - Browse Target Fields
        </h3>

        <div class="search-controls">
          <div class="search-input-group">
            <InputText
              v-model="manualSearchTerm"
              placeholder="Search by table name, column name, or description..."
              class="search-input"
              @keyup.enter="performManualSearch"
            />
            <Button
              label="Search"
              icon="pi pi-search"
              @click="performManualSearch"
              :loading="manualSearchLoading"
              :disabled="!manualSearchTerm.trim()"
            />
            <Button
              label="Clear"
              icon="pi pi-times"
              @click="clearManualSearch"
              severity="secondary"
              outlined
            />
          </div>
          <small class="search-hint">
            <i class="pi pi-info-circle"></i>
            Enter keywords to search across all target fields. Results are limited to 50 matches.
          </small>
        </div>

        <!-- Manual Search Results -->
        <div v-if="manualSearchResults.length > 0" class="search-results">
          <p class="results-count">Found {{ manualSearchResults.length }} matching target field(s)</p>
          
          <DataTable
            :value="manualSearchResults"
            dataKey="tgt_column_name"
            :paginator="true"
            :rows="10"
            class="manual-search-table"
            stripedRows
          >
            <!-- Target Field -->
            <Column header="Target Field" style="min-width: 15rem">
              <template #body="{ data }">
                <div class="target-field">
                  <strong>{{ data.tgt_table_name }}.{{ data.tgt_column_name }}</strong>
                  <span class="physical-name">{{ data.tgt_table_physical_name }}.{{ data.tgt_column_physical_name }}</span>
                </div>
              </template>
            </Column>

            <!-- Datatype -->
            <Column header="Datatype" style="width: 10rem">
              <template #body="{ data }">
                <Tag :value="data.tgt_physical_datatype" severity="info" />
              </template>
            </Column>

            <!-- Nullable -->
            <Column header="Nullable" style="width: 8rem">
              <template #body="{ data }">
                <Tag 
                  :value="data.tgt_nullable" 
                  :severity="data.tgt_nullable === 'Null' ? 'warning' : 'success'"
                />
              </template>
            </Column>

            <!-- Description -->
            <Column header="Description" style="min-width: 20rem">
              <template #body="{ data }">
                <span class="field-description">{{ data.tgt_comments || 'No description' }}</span>
              </template>
            </Column>

            <!-- Actions -->
            <Column header="Action" style="width: 10rem">
              <template #body="{ data }">
                <Button
                  label="Select"
                  icon="pi pi-check"
                  size="small"
                  severity="success"
                  @click="handleManualSelect(data)"
                  v-tooltip.top="'Use this target field for mapping'"
                />
              </template>
            </Column>
          </DataTable>
        </div>

        <!-- No Results -->
        <div v-if="!manualSearchLoading && manualSearchResults.length === 0 && manualSearchTerm" class="no-results">
          <i class="pi pi-search" style="font-size: 2.5rem; color: var(--text-color-secondary);"></i>
          <h4>No matching target fields found</h4>
          <p>Try different keywords or check your search term</p>
        </div>
      </div>
    </div>

    <template #footer>
      <Button label="Cancel" icon="pi pi-times" @click="handleClose" text />
      <Button 
        v-if="!showManualSearch"
        label="Manual Search" 
        icon="pi pi-search" 
        @click="handleManualSearch"
        severity="secondary"
        v-tooltip.top="'Search for target fields manually'"
      />
      <Button 
        v-else
        label="Back to AI Suggestions" 
        icon="pi pi-arrow-left" 
        @click="hideManualSearch"
        severity="secondary"
        v-tooltip.top="'Return to AI suggestions'"
      />
    </template>
  </Dialog>

  <!-- Rejection Feedback Dialog -->
  <Dialog
    v-model:visible="showRejectionDialog"
    modal
    header="Provide Feedback on Rejected Suggestion"
    :style="{ width: '700px' }"
    class="rejection-feedback-dialog"
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
        <label for="rejection-comment" class="feedback-label">
          <i class="pi pi-comment"></i>
          Why is this suggestion incorrect? <span class="required">*</span>
        </label>
        <Textarea
          id="rejection-comment"
          v-model="rejectionComment"
          rows="6"
          placeholder="Example: Wrong data type, different business meaning, already mapped elsewhere..."
          class="w-full feedback-textarea"
          autofocus
          autoResize
        />
        <small class="feedback-hint">Please provide specific details to help improve future suggestions</small>
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
import { ref, computed, watch, onUnmounted } from 'vue'
import { useAISuggestionsStore } from '@/stores/aiSuggestionsStore'
import { useUnmappedFieldsStore } from '@/stores/unmappedFieldsStore'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'
import ProgressBar from 'primevue/progressbar'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import PatternTemplateCard from '@/components/PatternTemplateCard.vue'
import type { AISuggestion, HistoricalPattern, PatternTemplate } from '@/stores/aiSuggestionsStore'
import type { UnmappedField } from '@/stores/unmappedFieldsStore'

interface Props {
  visible: boolean
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'suggestion-selected', suggestion: AISuggestion): void
  (e: 'template-applied', data: { pattern: HistoricalPattern, selectedFields: UnmappedField[], generatedSQL: string }): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const router = useRouter()
const aiStore = useAISuggestionsStore()
const unmappedStore = useUnmappedFieldsStore()
const userStore = useUserStore()
const toast = useToast()

// Available unmapped fields for template slot filling
const availableUnmappedFields = computed(() => {
  return unmappedStore.unmappedFields
})

// Multi-column patterns that are relevant to current selection
// Only show patterns that actually match the user's selected fields
const relevantMultiColumnPatterns = computed(() => {
  return aiStore.multiColumnPatterns.filter(p => p.matchedToCurrentSelection)
})

// Rejection dialog state
const showRejectionDialog = ref(false)
const rejectedSuggestion = ref<AISuggestion | null>(null)
const rejectionComment = ref('')

// Manual search state
const showManualSearch = ref(false)
const manualSearchTerm = ref('')
const manualSearchResults = ref<any[]>([])
const manualSearchLoading = ref(false)

// Historical patterns state
const showPatternDetails = ref(true)  // Default to expanded for better UX

// Template dialog state
const showTemplateDialog = ref(false)

// Loading stage simulation (1=targets, 2=patterns, 3=LLM)
const loadingStage = ref(1)
let loadingInterval: ReturnType<typeof setInterval> | null = null

// Watch for loading state changes
watch(() => aiStore.loading, (isLoading) => {
  if (isLoading) {
    // Start stage animation
    loadingStage.value = 1
    loadingInterval = setInterval(() => {
      if (loadingStage.value < 3) {
        loadingStage.value++
      }
    }, 1200) // Advance every 1.2 seconds
  } else {
    // Stop animation
    if (loadingInterval) {
      clearInterval(loadingInterval)
      loadingInterval = null
    }
    loadingStage.value = 1
  }
})

onUnmounted(() => {
  if (loadingInterval) {
    clearInterval(loadingInterval)
  }
})

// Template handling - User-driven approach
function handleUseAsTemplate(pattern: HistoricalPattern) {
  console.log('[AI Suggestions Dialog] User selected pattern as template:', pattern.tgt_column_name)
  aiStore.selectPatternAsTemplate(pattern)
  showTemplateDialog.value = true
}

function handleCloseTemplateDialog() {
  console.log('[AI Suggestions Dialog] Closing template dialog')
  showTemplateDialog.value = false
  aiStore.clearSelectedTemplate()
}

function handleSkipTemplate() {
  console.log('[AI Suggestions Dialog] User skipped template')
  handleCloseTemplateDialog()
}

function handleApplyTemplate(data: { pattern: HistoricalPattern, selectedFields: UnmappedField[], generatedSQL: string }) {
  console.log('[AI Suggestions Dialog] ========== APPLYING TEMPLATE ==========')
  console.log('[AI Suggestions Dialog] Pattern:', data.pattern.tgt_column_name)
  console.log('[AI Suggestions Dialog] Selected fields:', data.selectedFields.map(f => ({
    name: f.src_column_name,
    physical: f.src_column_physical_name
  })))
  console.log('[AI Suggestions Dialog] Generated SQL received:', data.generatedSQL)
  console.log('[AI Suggestions Dialog] SQL length:', data.generatedSQL?.length || 0)
  
  // Mark as accepting to prevent store clear
  acceptedSuggestion.value = true
  
  // Update the source fields in the store to include all template fields
  aiStore.setSourceFields(data.selectedFields)
  
  // Also update the unmapped store selection
  unmappedStore.selectedFields = data.selectedFields
  
  // Create a suggestion from the pattern for navigation
  const suggestion: AISuggestion = {
    semantic_field_id: 0, // Will need to look this up
    tgt_table_name: data.pattern.tgt_table_name,
    tgt_table_physical_name: data.pattern.tgt_table_physical_name || data.pattern.tgt_table_name,
    tgt_column_name: data.pattern.tgt_column_name,
    tgt_column_physical_name: data.pattern.tgt_column_physical_name || data.pattern.tgt_column_name,
    tgt_comments: '',
    search_score: data.pattern.search_score || 0.9,
    match_quality: 'Excellent',
    ai_reasoning: `Applied from historical pattern with ${data.selectedFields.length} fields`,
    rank: 1,
    fromPattern: true,
    patternId: data.pattern.mapped_field_id
  }
  
  aiStore.selectSuggestion(suggestion)
  
  // Store the generated SQL in multiple places to ensure it's available
  // 1. In the aiStore for direct access
  aiStore.recommendedExpression = data.generatedSQL || ''
  console.log('[AI Suggestions Dialog] Set aiStore.recommendedExpression to:', aiStore.recommendedExpression)
  
  // 2. In sessionStorage as backup (ALWAYS set, even if empty, for debugging)
  const sqlToStore = data.generatedSQL || ''
  sessionStorage.setItem('templateGeneratedSQL', sqlToStore)
  console.log('[AI Suggestions Dialog] Stored in sessionStorage:', sqlToStore)
  console.log('[AI Suggestions Dialog] Verify sessionStorage:', sessionStorage.getItem('templateGeneratedSQL'))
  
  // 3. Emit to parent
  emit('template-applied', data)
  
  toast.add({
    severity: 'success',
    summary: 'Template Applied',
    detail: `Using pattern with ${data.selectedFields.length} source fields`,
    life: 3000
  })
  
  // Close dialog and navigate
  isVisible.value = false
  router.push({ name: 'mapping-config' })
}

// Helper: truncate long expressions
function truncateExpression(expr: string, maxLen: number = 80): string {
  if (!expr) return ''
  return expr.length > maxLen ? expr.substring(0, maxLen) + '...' : expr
}

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

function getRowClass(data: AISuggestion) {
  if (data.rank === 1) return 'top-suggestion'
  if (data.fromPattern) return 'pattern-suggestion'
  return ''
}

function handleRowClick(event: any) {
  // Disabled for now - users should use explicit Accept/Reject buttons
  // handleAccept(event.data)
}

// Track if we're closing due to an accepted suggestion (don't clear store in that case)
const acceptedSuggestion = ref(false)

function handleAccept(suggestion: AISuggestion) {
  console.log('[AI Suggestions Dialog] === Accepting Suggestion ===')
  
  // Mark that we're accepting FIRST (don't clear store on close)
  acceptedSuggestion.value = true
  console.log('[AI Suggestions Dialog] acceptedSuggestion flag set to:', acceptedSuggestion.value)
  
  // Store the suggestion for mapping configuration
  aiStore.selectSuggestion(suggestion)
  
  console.log('[AI Suggestions Dialog] Accepted suggestion:', suggestion.tgt_column_name)
  console.log('[AI Suggestions Dialog] aiStore.selectedSuggestion:', aiStore.selectedSuggestion?.tgt_column_name)
  console.log('[AI Suggestions Dialog] aiStore.sourceFieldsUsed length:', aiStore.sourceFieldsUsed?.length)
  
  // Show toast
  toast.add({
    severity: 'success',
    summary: 'Suggestion Accepted',
    detail: `Proceeding with mapping to ${suggestion.tgt_table_name}.${suggestion.tgt_column_name}`,
    life: 3000
  })
  
  // Record acceptance feedback (non-blocking, fire and forget)
  recordFeedback(suggestion, 'accepted', 'User accepted this AI suggestion').catch(err => {
    console.warn('[AI Suggestions] Feedback recording failed (non-critical):', err)
  })
  
  // IMPORTANT: Emit to parent FIRST (this triggers navigation)
  // The parent will navigate to mapping-config, which will read from aiStore
  console.log('[AI Suggestions Dialog] Emitting suggestion-selected to parent')
  emit('suggestion-selected', suggestion)
  
  // Then close dialog (triggers handleClose, but flag prevents clearing)
  isVisible.value = false
}

function handleReject(suggestion: AISuggestion) {
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

async function recordFeedback(suggestion: AISuggestion, action: 'accepted' | 'rejected', comment: string) {
  try {
    // For multi-field mappings, create one feedback record per source field
    const feedbackAction = action === 'accepted' ? 'ACCEPTED' : 'REJECTED'
    
    // Get current user email from user store
    const currentUser = userStore.userEmail || 'demo.user@gainwell.com'
    
    for (const sourceField of aiStore.sourceFieldsUsed) {
      const feedbackPayload = {
        suggested_src_table: sourceField.src_table_name || '',
        suggested_src_column: sourceField.src_column_name || '',
        suggested_tgt_table: suggestion.tgt_table_name,
        suggested_tgt_column: suggestion.tgt_column_name,
        feedback_action: feedbackAction,
        user_comments: comment || null,
        ai_confidence_score: suggestion.search_score || null,
        ai_reasoning: suggestion.ai_reasoning || null,
        vector_search_score: suggestion.search_score || null,
        suggestion_rank: suggestion.rank || null,
        feedback_by: currentUser
      }
      
      console.log('[AI Suggestions] Recording feedback:', feedbackPayload)
      
      // Call feedback API (non-blocking)
      const response = await fetch('/api/v2/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(feedbackPayload)
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        console.warn('[AI Suggestions] Feedback recording failed:', response.statusText, errorText)
      } else {
        console.log('[AI Suggestions] Feedback recorded successfully for', sourceField.src_column_name)
      }
    }
  } catch (error) {
    console.error('[AI Suggestions] Error recording feedback:', error)
    // Don't block the user flow if feedback fails
  }
}

function handleManualSearch() {
  console.log('[AI Suggestions Dialog] Manual search requested')
  showManualSearch.value = true
}

function hideManualSearch() {
  showManualSearch.value = false
  manualSearchTerm.value = ''
  manualSearchResults.value = []
}

async function performManualSearch() {
  if (!manualSearchTerm.value.trim()) {
    return
  }

  manualSearchLoading.value = true
  
  try {
    const response = await fetch(`/api/mapping/search-semantic-table?search_term=${encodeURIComponent(manualSearchTerm.value.trim())}`)
    
    if (!response.ok) {
      throw new Error('Search failed')
    }
    
    const results = await response.json()
    manualSearchResults.value = results || []
    
    console.log('[AI Suggestions Dialog] Manual search returned', results.length, 'results')
    
    if (results.length === 0) {
      toast.add({
        severity: 'info',
        summary: 'No Results',
        detail: 'No matching target fields found. Try different keywords.',
        life: 3000
      })
    }
  } catch (error) {
    console.error('[AI Suggestions Dialog] Manual search error:', error)
    toast.add({
      severity: 'error',
      summary: 'Search Failed',
      detail: 'Failed to search target fields. Please try again.',
      life: 5000
    })
  } finally {
    manualSearchLoading.value = false
  }
}

function clearManualSearch() {
  manualSearchTerm.value = ''
  manualSearchResults.value = []
}

function handleManualSelect(targetField: any) {
  // Convert manual search result to suggestion format
  const manualSuggestion: AISuggestion = {
    semantic_field_id: targetField.semantic_field_id || 0,
    tgt_table_name: targetField.tgt_table_name,
    tgt_column_name: targetField.tgt_column_name,
    tgt_table_physical_name: targetField.tgt_table_physical_name,
    tgt_column_physical_name: targetField.tgt_column_physical_name,
    tgt_comments: targetField.tgt_comments,
    search_score: 0,
    match_quality: 'Manual',
    ai_reasoning: 'Manually selected by user',
    rank: 0
  }
  
  console.log('[AI Suggestions Dialog] Manual selection:', targetField)
  
  // Use the same accept flow as AI suggestions
  handleAccept(manualSuggestion)
}

function handleClose() {
  console.log('[AI Suggestions Dialog] === handleClose called ===')
  console.log('[AI Suggestions Dialog] acceptedSuggestion flag:', acceptedSuggestion.value)
  
  isVisible.value = false
  showManualSearch.value = false
  manualSearchTerm.value = ''
  manualSearchResults.value = []
  showPatternDetails.value = false
  
  // Only clear AI store if we're NOT closing due to accepting a suggestion
  // (We need to preserve the selected suggestion for the mapping workflow)
  if (acceptedSuggestion.value) {
    console.log('[AI Suggestions Dialog] Closed after accepting - keeping store data for workflow')
    console.log('[AI Suggestions Dialog] Store data preserved:', aiStore.selectedSuggestion?.tgt_column_name)
    acceptedSuggestion.value = false  // Reset for next time
  } else {
    // Clear AI store to prevent stale data showing on next open
    console.log('[AI Suggestions Dialog] Closed without selection - clearing state')
    aiStore.clearSuggestions()
  }
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

.loading-container h3 {
  margin: 0;
  color: var(--gainwell-dark);
}

.loading-stages {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  min-width: 300px;
}

.loading-stage {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  opacity: 0.5;
  transition: opacity 0.3s ease;
}

.loading-stage.active {
  opacity: 1;
  color: var(--gainwell-primary);
  font-weight: 600;
}

.loading-stage.completed {
  opacity: 1;
  color: var(--green-600);
}

.loading-stage.completed i {
  color: var(--green-600);
}

.loading-stage i {
  font-size: 1.1rem;
}

.loading-hint {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

/* Multi-Column Pattern Alert */
.multi-column-alert {
  margin-bottom: 1rem;
}

.multi-column-alert .alert-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.multi-column-alert .alert-content strong {
  font-size: 1.1rem;
  color: #856404;
}

.multi-column-alert .alert-content p {
  margin: 0;
  line-height: 1.5;
}

.pattern-examples {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(255, 193, 7, 0.1);
  border-radius: 6px;
  margin: 0.5rem 0;
}

.pattern-example {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.pattern-example i {
  color: #856404;
}

.pattern-example code {
  background: rgba(0,0,0,0.05);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

.relationship-type {
  color: var(--orange-700);
  font-weight: 600;
  font-size: 0.8rem;
}

.action-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-style: italic;
  color: #6c757d;
}

.action-hint i {
  color: #ffc107;
}

/* Historical Patterns Section */
.historical-patterns-section {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  border-left: 4px solid var(--gainwell-secondary);
}

.historical-patterns-section .collapsible-header {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--gainwell-dark);
  cursor: pointer;
  user-select: none;
}

.historical-patterns-section .collapsible-header:hover {
  color: var(--gainwell-primary);
}

.historical-patterns-section .toggle-icon {
  margin-left: auto;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.patterns-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}

.pattern-card {
  padding: 0.75rem;
  background: white;
  border-radius: 6px;
  border: 1px solid var(--surface-border);
}

.pattern-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.pattern-header .target-name {
  font-weight: 600;
  color: var(--gainwell-dark);
}

.pattern-details {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding-left: 0.5rem;
  font-size: 0.85rem;
}

.pattern-details .detail-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.pattern-details .detail-item label {
  font-weight: 600;
  color: var(--text-color-secondary);
  min-width: 100px;
}

.pattern-details .detail-item code {
  background: var(--surface-100);
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.8rem;
  word-break: break-all;
}

.pattern-details .transforms {
  color: var(--gainwell-accent);
}

.patterns-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0.5rem 0 0 0;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
  font-style: italic;
}

.patterns-hint i {
  color: var(--gainwell-secondary);
}

.pattern-actions {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-border);
  display: flex;
  justify-content: flex-end;
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
  flex-wrap: wrap;
}

.match-quality .pattern-tag {
  margin-top: 0.25rem;
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

/* Pattern-based suggestion highlighting */
:deep(.pattern-suggestion) {
  background: #fffbeb !important;
  border-left: 3px solid #f59e0b;
}

:deep(.pattern-suggestion:hover) {
  background: #fef3c7 !important;
}

/* Row hover effect */
:deep(.p-datatable-tbody > tr:hover) {
  background: var(--surface-hover);
  cursor: pointer;
}

/* Rejection Feedback Dialog Styles */
.rejection-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 0.5rem 0;
}

.rejected-suggestion-summary {
  background: linear-gradient(135deg, #fff3cd, #ffe8a1);
  padding: 1.25rem;
  border-radius: 8px;
  border-left: 4px solid #ffc107;
}

.rejected-suggestion-summary h4 {
  margin: 0 0 1rem 0;
  color: #856404;
  font-size: 1rem;
  font-weight: 600;
}

.suggestion-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-row {
  display: grid;
  grid-template-columns: 120px 1fr;
  align-items: flex-start;
  gap: 0.75rem;
}

.detail-row label {
  font-weight: 600;
  color: #6c757d;
  font-size: 0.9rem;
}

.detail-row span {
  color: #212529;
}

.ai-reason-text {
  line-height: 1.5;
  font-size: 0.9rem;
}

.feedback-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.feedback-label {
  display: block;
  font-weight: 600;
  color: #4a5568;
  font-size: 1rem;
  margin-bottom: 0.5rem;
}

.feedback-label i {
  margin-right: 0.5rem;
  color: #38a169;
}

.feedback-label .required {
  color: #dc3545;
  margin-left: 0.25rem;
}

.feedback-textarea {
  font-size: 0.95rem;
  line-height: 1.6;
  border: 2px solid #dee2e6;
  border-radius: 6px;
  padding: 0.75rem;
}

.feedback-textarea:focus {
  border-color: #38a169;
  box-shadow: 0 0 0 0.2rem rgba(56, 161, 105, 0.25);
}

.feedback-hint {
  color: #6c757d;
  font-size: 0.85rem;
  font-style: italic;
  margin-top: -0.25rem;
}

.rejection-feedback-dialog :deep(.p-dialog-content) {
  overflow-y: auto;
  max-height: 70vh;
}

/* Manual Search Section Styles */
.manual-search-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem 0;
}

.manual-search-section h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--gainwell-dark);
  font-size: 1.25rem;
}

.manual-search-section h3 i {
  color: var(--gainwell-accent);
}

.search-controls {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.search-input-group {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.search-input {
  flex: 1;
  font-size: 1rem;
}

.search-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.search-hint i {
  color: var(--gainwell-secondary);
}

.search-results {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.results-count {
  font-weight: 600;
  color: var(--gainwell-primary);
  margin: 0;
}

.manual-search-table {
  border: 1px solid var(--surface-border);
  border-radius: 6px;
}

.manual-search-table .field-description {
  font-size: 0.9rem;
  color: var(--text-color-secondary);
  line-height: 1.5;
}

.no-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  gap: 1rem;
  text-align: center;
  background: var(--surface-50);
  border-radius: 8px;
}

.no-results h4 {
  margin: 0;
  color: var(--text-color);
}

.no-results p {
  margin: 0;
  color: var(--text-color-secondary);
}
</style>

