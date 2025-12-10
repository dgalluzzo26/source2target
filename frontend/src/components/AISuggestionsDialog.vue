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

      <!-- UNIFIED RANKED LIST - All options in one place -->
      <div v-if="!aiStore.loading && aiStore.hasOptions" class="unified-options-section">
        <div class="section-header">
          <h3>
            <i class="pi pi-list"></i>
            Recommended Mappings
          </h3>
          <span class="options-count">{{ aiStore.unifiedOptions.length }} options found</span>
        </div>
        
        <!-- Options List -->
        <div class="options-list">
          <div 
            v-for="option in aiStore.unifiedOptions.slice(0, 15)" 
            :key="option.id"
            class="option-card"
            :class="[
              `source-${option.source}`,
              `quality-${option.matchQuality.toLowerCase()}`
            ]"
          >
            <!-- Card Header -->
            <div class="option-header">
              <div class="rank-badge" :class="`rank-${option.rank}`">
                #{{ option.rank }}
              </div>
              <div class="target-info">
                <div class="target-name">
                  {{ option.tgt_table_name }}.{{ option.tgt_column_name }}
                </div>
                <div class="target-physical">
                  {{ option.tgt_table_physical_name }}.{{ option.tgt_column_physical_name }}
                </div>
              </div>
              <div class="option-badges">
                <!-- Source badge -->
                <Tag 
                  v-if="option.source === 'ai_pick'"
                  value="AI Pick"
                  severity="success"
                  icon="pi pi-sparkles"
                />
                <Tag 
                  v-else-if="option.source === 'pattern'"
                  value="Pattern"
                  severity="warning"
                  icon="pi pi-history"
                />
                <Tag 
                  v-else
                  value="Vector"
                  severity="info"
                  icon="pi pi-search"
                />
                <!-- Quality badge -->
                <Tag 
                  :value="option.matchQuality"
                  :severity="getMatchQualitySeverity(option.matchQuality)"
                  :icon="getMatchQualityIcon(option.matchQuality)"
                />
                <!-- Multi-column indicator -->
                <Tag 
                  v-if="option.isMultiColumn"
                  value="Multi-Column"
                  severity="contrast"
                  icon="pi pi-table"
                />
              </div>
            </div>
            
            <!-- Card Body -->
            <div class="option-body">
              <!-- Description/Reasoning -->
              <div class="option-reasoning">
                <i class="pi pi-comment"></i>
                <span>{{ option.reasoning }}</span>
              </div>
              
              <!-- Target Comments (if available) -->
              <div v-if="option.tgt_comments" class="option-description">
                <i class="pi pi-info-circle"></i>
                <span>{{ option.tgt_comments }}</span>
              </div>
              
              <!-- Pattern transforms for TARGETS that have a matching pattern -->
              <div v-if="option.hasMatchingPattern && option.transformations" class="pattern-enrichment">
                <div class="enrichment-header">
                  <i class="pi pi-history"></i>
                  <span>Similar past mappings use:</span>
                </div>
                <div class="enrichment-transforms">
                  <Tag 
                    v-for="transform in option.transformations.split(',').map(t => t.trim())" 
                    :key="transform"
                    :value="transform"
                    severity="info"
                    size="small"
                    class="transform-tag"
                  />
                </div>
                <div v-if="option.generatedSQL" class="enrichment-sql">
                  <code>{{ truncateSQL(option.generatedSQL, 60) }}</code>
                </div>
              </div>
              
              <!-- Pattern details with suggested mappings (for pattern-only items) -->
              <div v-if="option.source === 'pattern' && option.pattern" class="pattern-info-enhanced">
                <!-- Suggested Field Mappings -->
                <div v-if="option.suggestedMappings && option.suggestedMappings.length > 0" class="suggested-mappings">
                  <div class="mappings-header">
                    <i class="pi pi-arrow-right-arrow-left"></i>
                    <span>Suggested Field Mapping:</span>
                    <Tag 
                      v-if="option.allFieldsMatched"
                      value="All Matched ✓"
                      severity="success"
                      size="small"
                    />
                    <Tag 
                      v-else
                      value="Partial Match"
                      severity="warning"
                      size="small"
                    />
                  </div>
                  <div class="mappings-table">
                    <div 
                      v-for="(mapping, idx) in option.suggestedMappings" 
                      :key="idx"
                      class="mapping-row"
                      :class="{ matched: mapping.isMatched, unmatched: !mapping.isMatched }"
                    >
                      <span class="pattern-col">{{ mapping.patternColumn }}</span>
                      <i class="pi pi-arrow-right mapping-arrow"></i>
                      <span v-if="mapping.isMatched" class="matched-field">
                        {{ mapping.suggestedField?.src_column_name }}
                        <i class="pi pi-check-circle match-icon"></i>
                      </span>
                      <span v-else class="unmatched-field">
                        <i class="pi pi-question-circle"></i>
                        No match found
                      </span>
                    </div>
                  </div>
                </div>
                
                <!-- Transforms -->
                <div v-if="option.transformations" class="pattern-transforms">
                  <span class="transforms-label">🔧 Transforms:</span>
                  <span class="transforms-value">{{ option.transformations }}</span>
                </div>
                
                <!-- Generated SQL Preview (only if all matched) -->
                <div v-if="option.allFieldsMatched && option.generatedSQL" class="sql-preview-mini">
                  <span class="sql-label">📝 SQL:</span>
                  <code class="sql-code">{{ truncateSQL(option.generatedSQL, 80) }}</code>
                </div>
              </div>
            </div>
            
            <!-- Card Actions -->
            <div class="option-actions">
              <!-- For patterns with suggested mappings -->
              <template v-if="option.source === 'pattern' && option.pattern">
                <!-- Primary action: Apply if all fields matched -->
                <Button
                  v-if="option.allFieldsMatched"
                  label="Apply Suggested Mapping"
                  icon="pi pi-check"
                  size="small"
                  severity="success"
                  @click="handleApplySuggestedMapping(option)"
                  v-tooltip.top="'Apply this pattern with the suggested field mappings'"
                />
                <Button
                  v-else
                  label="Complete Mapping"
                  icon="pi pi-pencil"
                  size="small"
                  severity="warning"
                  @click="handleUseAsTemplate(option.pattern)"
                  v-tooltip.top="'Some fields need to be matched manually'"
                />
                <!-- Secondary action: Customize -->
                <Button
                  label="Customize..."
                  icon="pi pi-cog"
                  size="small"
                  severity="secondary"
                  outlined
                  @click="handleUseAsTemplate(option.pattern)"
                  v-tooltip.top="'Open template dialog to customize field mappings'"
                />
              </template>
              
              <!-- For AI/Vector suggestions - Accept/Reject -->
              <template v-else>
                <!-- Show "Apply with Transforms" if target has matching pattern -->
                <Button
                  v-if="option.hasMatchingPattern && option.generatedSQL"
                  label="Apply with Transforms"
                  icon="pi pi-bolt"
                  size="small"
                  severity="success"
                  @click="handleApplyWithTransforms(option)"
                  v-tooltip.top="`Apply using: ${option.transformations}`"
                />
                <Button
                  :label="option.hasMatchingPattern ? 'Accept Only' : 'Accept'"
                  icon="pi pi-check"
                  size="small"
                  :severity="option.hasMatchingPattern ? 'secondary' : 'success'"
                  :outlined="option.hasMatchingPattern"
                  @click="handleAcceptFromOption(option)"
                  v-tooltip.top="option.hasMatchingPattern ? 'Accept without transforms' : 'Accept this suggestion'"
                />
                <Button
                  label="Reject"
                  icon="pi pi-times"
                  size="small"
                  severity="danger"
                  outlined
                  @click="handleRejectFromOption(option)"
                  v-tooltip.top="'Reject this suggestion and provide feedback'"
                />
              </template>
            </div>
          </div>
        </div>
        
        <!-- Tip Message -->
        <Message severity="info" :closable="false" class="tip-message">
          <div class="tip-content">
            <strong>💡 Tip:</strong> 
            <span class="tip-ai">AI Pick</span> = LLM's best recommendation, 
            <span class="tip-pattern">Pattern</span> = similar past mapping (can use as template), 
            <span class="tip-vector">Vector</span> = semantic similarity match
          </div>
        </Message>
      </div>

      <!-- No Options Found -->
      <div v-if="!aiStore.loading && !aiStore.hasOptions && !showManualSearch" class="no-suggestions">
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
import type { AISuggestion, HistoricalPattern, PatternTemplate, UnifiedMappingOption, SuggestedFieldMapping } from '@/stores/aiSuggestionsStore'
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

// Handle accept from unified option
function handleAcceptFromOption(option: UnifiedMappingOption) {
  // "Accept Only" - explicitly clear any pre-filled SQL from prior runs
  // User chose NOT to use transforms, so start with blank SQL
  aiStore.recommendedExpression = ''
  sessionStorage.removeItem('templateGeneratedSQL')
  
  console.log('[AI Suggestions Dialog] Accept Only - cleared recommendedExpression and sessionStorage')
  
  // Convert unified option to AISuggestion format
  const suggestion: AISuggestion = {
    semantic_field_id: option.semantic_field_id || 0,
    tgt_table_name: option.tgt_table_name,
    tgt_table_physical_name: option.tgt_table_physical_name,
    tgt_column_name: option.tgt_column_name,
    tgt_column_physical_name: option.tgt_column_physical_name,
    tgt_comments: option.tgt_comments,
    search_score: option.score,
    match_quality: option.matchQuality,
    ai_reasoning: option.reasoning,
    rank: option.rank,
    fromPattern: option.source === 'pattern',
    patternId: option.pattern?.mapped_field_id
  }
  
  handleAccept(suggestion)
}

// Handle apply suggested mapping (for patterns with all fields matched)
function handleApplySuggestedMapping(option: UnifiedMappingOption) {
  if (!option.pattern || !option.suggestedMappings || !option.allFieldsMatched) {
    console.warn('[AI Suggestions Dialog] Cannot apply - missing data')
    return
  }
  
  console.log('[AI Suggestions Dialog] === Applying Suggested Mapping ===')
  console.log('[AI Suggestions Dialog] Pattern:', option.pattern.tgt_column_name)
  console.log('[AI Suggestions Dialog] Generated SQL:', option.generatedSQL)
  
  // Get all matched fields
  const selectedFields = option.suggestedMappings
    .filter(m => m.suggestedField)
    .map(m => m.suggestedField!)
  
  console.log('[AI Suggestions Dialog] Selected fields:', selectedFields.map(f => f.src_column_name))
  
  // Mark as accepting to prevent store clear
  acceptedSuggestion.value = true
  
  // Update stores with the matched fields
  aiStore.setSourceFields(selectedFields)
  unmappedStore.selectedFields = selectedFields
  
  // Create suggestion for navigation
  const suggestion: AISuggestion = {
    semantic_field_id: 0,
    tgt_table_name: option.tgt_table_name,
    tgt_table_physical_name: option.tgt_table_physical_name,
    tgt_column_name: option.tgt_column_name,
    tgt_column_physical_name: option.tgt_column_physical_name,
    tgt_comments: option.tgt_comments,
    search_score: option.score,
    match_quality: 'Excellent',
    ai_reasoning: `Applied pattern with ${selectedFields.length} fields`,
    rank: option.rank,
    fromPattern: true,
    patternId: option.pattern.mapped_field_id
  }
  
  aiStore.selectSuggestion(suggestion)
  
  // Store the generated SQL
  aiStore.recommendedExpression = option.generatedSQL || ''
  sessionStorage.setItem('templateGeneratedSQL', option.generatedSQL || '')
  
  console.log('[AI Suggestions Dialog] Stored SQL:', option.generatedSQL)
  
  toast.add({
    severity: 'success',
    summary: 'Pattern Applied',
    detail: `Mapping ${selectedFields.length} fields to ${option.tgt_column_name}`,
    life: 3000
  })
  
  // Close and navigate
  isVisible.value = false
  router.push({ name: 'mapping-config' })
}

// Handle apply with transforms (for targets that have matching patterns)
function handleApplyWithTransforms(option: UnifiedMappingOption) {
  console.log('[AI Suggestions Dialog] === Applying Target with Transforms ===')
  console.log('[AI Suggestions Dialog] Target:', option.tgt_column_name)
  console.log('[AI Suggestions Dialog] Transforms:', option.transformations)
  console.log('[AI Suggestions Dialog] Generated SQL:', option.generatedSQL)
  
  // Mark as accepting to prevent store clear
  acceptedSuggestion.value = true
  
  // Create suggestion with transform info
  const suggestion: AISuggestion = {
    semantic_field_id: option.semantic_field_id || 0,
    tgt_table_name: option.tgt_table_name,
    tgt_table_physical_name: option.tgt_table_physical_name,
    tgt_column_name: option.tgt_column_name,
    tgt_column_physical_name: option.tgt_column_physical_name,
    tgt_comments: option.tgt_comments,
    search_score: option.score,
    match_quality: option.matchQuality,
    ai_reasoning: `${option.reasoning} | Transforms: ${option.transformations}`,
    rank: option.rank,
    fromPattern: true
  }
  
  aiStore.selectSuggestion(suggestion)
  
  // Store the generated SQL from the pattern
  aiStore.recommendedExpression = option.generatedSQL || ''
  sessionStorage.setItem('templateGeneratedSQL', option.generatedSQL || '')
  
  console.log('[AI Suggestions Dialog] Stored SQL:', option.generatedSQL)
  
  toast.add({
    severity: 'success',
    summary: 'Transforms Applied',
    detail: `Using: ${option.transformations}`,
    life: 3000
  })
  
  // Close and navigate
  isVisible.value = false
  router.push({ name: 'mapping-config' })
}

// Helper: Truncate SQL for preview
function truncateSQL(sql: string, maxLen: number): string {
  if (!sql) return ''
  return sql.length > maxLen ? sql.substring(0, maxLen) + '...' : sql
}

// Handle reject from unified option
function handleRejectFromOption(option: UnifiedMappingOption) {
  // Convert to AISuggestion format for rejection dialog
  const suggestion: AISuggestion = {
    semantic_field_id: option.semantic_field_id || 0,
    tgt_table_name: option.tgt_table_name,
    tgt_table_physical_name: option.tgt_table_physical_name,
    tgt_column_name: option.tgt_column_name,
    tgt_column_physical_name: option.tgt_column_physical_name,
    tgt_comments: option.tgt_comments,
    search_score: option.score,
    match_quality: option.matchQuality,
    ai_reasoning: option.reasoning,
    rank: option.rank
  }
  
  handleReject(suggestion)
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

/* ============================================
   UNIFIED OPTIONS SECTION
   ============================================ */
.unified-options-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.unified-options-section .section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--surface-200);
}

.unified-options-section .section-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--gainwell-dark);
  font-size: 1.25rem;
}

.unified-options-section .section-header h3 i {
  color: var(--gainwell-primary);
}

.unified-options-section .options-count {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Option Card - Base */
.option-card {
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 12px;
  border: 2px solid var(--surface-200);
  overflow: hidden;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.option-card:hover {
  border-color: var(--gainwell-primary);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

/* Option Card - Source Variants */
.option-card.source-ai_pick {
  border-color: var(--green-400);
  background: linear-gradient(135deg, #f0fdf4, white);
}

.option-card.source-ai_pick:hover {
  border-color: var(--green-600);
}

.option-card.source-pattern {
  border-color: var(--yellow-400);
  background: linear-gradient(135deg, #fefce8, white);
}

.option-card.source-pattern:hover {
  border-color: var(--yellow-600);
}

.option-card.source-vector {
  border-color: var(--blue-200);
  background: linear-gradient(135deg, #eff6ff, white);
}

.option-card.source-vector:hover {
  border-color: var(--blue-500);
}

/* Option Card - Quality Accents */
.option-card.quality-excellent {
  border-left: 5px solid var(--green-500);
}

.option-card.quality-strong {
  border-left: 5px solid var(--blue-500);
}

.option-card.quality-good {
  border-left: 5px solid var(--yellow-500);
}

.option-card.quality-weak {
  border-left: 5px solid var(--gray-400);
}

/* Option Header */
.option-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: rgba(0, 0, 0, 0.02);
  border-bottom: 1px solid var(--surface-100);
}

.option-header .rank-badge {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.option-header .rank-badge.rank-1 {
  background: linear-gradient(135deg, #fde047, #facc15);
  color: #713f12;
  box-shadow: 0 2px 8px rgba(250, 204, 21, 0.4);
}

.option-header .rank-badge.rank-2 {
  background: linear-gradient(135deg, #e5e7eb, #d1d5db);
  color: #374151;
}

.option-header .rank-badge.rank-3 {
  background: linear-gradient(135deg, #fed7aa, #fdba74);
  color: #9a3412;
}

.option-header .rank-badge:not(.rank-1):not(.rank-2):not(.rank-3) {
  background: var(--surface-100);
  color: var(--text-color-secondary);
}

.option-header .target-info {
  flex: 1;
  min-width: 0;
}

.option-header .target-name {
  font-weight: 600;
  font-size: 1.1rem;
  color: var(--gainwell-dark);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.option-header .target-physical {
  font-family: 'Fira Code', 'Monaco', monospace;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.option-header .option-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  flex-shrink: 0;
}

/* Option Body */
.option-body {
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.option-reasoning {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  color: var(--text-color-secondary);
  font-size: 0.95rem;
  line-height: 1.5;
}

.option-reasoning i {
  color: var(--gainwell-primary);
  margin-top: 0.2rem;
  flex-shrink: 0;
}

.option-description {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
  font-size: 0.9rem;
  color: var(--text-color);
  line-height: 1.4;
}

.option-description i {
  color: var(--gainwell-secondary);
  margin-top: 0.15rem;
  flex-shrink: 0;
}

/* Pattern Enrichment for Targets with matching patterns */
.pattern-enrichment {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #f0fdf4, #dcfce7);
  border-radius: 8px;
  border: 1px solid #86efac;
  margin-top: 0.5rem;
}

.enrichment-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: #166534;
  font-weight: 500;
}

.enrichment-header i {
  color: #22c55e;
}

.enrichment-transforms {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.enrichment-transforms .transform-tag {
  background: #22c55e;
  color: white;
}

.enrichment-sql {
  margin-top: 0.25rem;
}

.enrichment-sql code {
  display: block;
  background: rgba(255, 255, 255, 0.8);
  padding: 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-family: 'JetBrains Mono', monospace;
  color: #166534;
  border: 1px solid #bbf7d0;
}

/* Enhanced Pattern Info with Suggested Mappings */
.pattern-info-enhanced {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
  border-radius: 8px;
  border: 1px solid #fcd34d;
}

.suggested-mappings {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.mappings-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #92400e;
  font-size: 0.9rem;
}

.mappings-header i {
  color: #f59e0b;
}

.mappings-table {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  background: white;
  border-radius: 6px;
  padding: 0.5rem;
  border: 1px solid #fde68a;
}

.mapping-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

.mapping-row.matched {
  background: #f0fdf4;
}

.mapping-row.unmatched {
  background: #fef2f2;
}

.mapping-row .pattern-col {
  font-family: 'Fira Code', monospace;
  color: #78716c;
  min-width: 120px;
}

.mapping-row .mapping-arrow {
  color: #a8a29e;
  font-size: 0.8rem;
}

.mapping-row .matched-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #166534;
}

.mapping-row .match-icon {
  color: #22c55e;
  font-size: 0.9rem;
}

.mapping-row .unmatched-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #dc2626;
  font-style: italic;
}

.mapping-row .unmatched-field i {
  color: #f87171;
}

.pattern-transforms {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.pattern-transforms .transforms-label {
  color: #78716c;
}

.pattern-transforms .transforms-value {
  color: #ea580c;
  font-weight: 600;
}

.sql-preview-mini {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #1e1e1e;
  border-radius: 4px;
  font-size: 0.8rem;
}

.sql-preview-mini .sql-label {
  color: #a3e635;
  flex-shrink: 0;
}

.sql-preview-mini .sql-code {
  color: #f0abfc;
  font-family: 'Fira Code', monospace;
  word-break: break-all;
}

/* Legacy pattern-info (for backward compatibility) */
.pattern-info {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 0.75rem;
  background: #fffbeb;
  border-radius: 6px;
  border: 1px dashed #fcd34d;
}

.pattern-detail {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.pattern-detail .detail-label {
  font-weight: 600;
  color: #92400e;
}

.pattern-detail code {
  background: rgba(0, 0, 0, 0.05);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

.pattern-detail .transforms-value {
  color: #ea580c;
  font-weight: 500;
}

/* Option Actions */
.option-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 0.75rem 1.25rem;
  background: var(--surface-50);
  border-top: 1px solid var(--surface-100);
}

/* Tip Message */
.tip-message {
  margin-top: 0.5rem;
}

.tip-content {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.tip-ai {
  background: var(--green-100);
  color: var(--green-700);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
}

.tip-pattern {
  background: var(--yellow-100);
  color: var(--yellow-700);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
}

.tip-vector {
  background: var(--blue-100);
  color: var(--blue-700);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
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

