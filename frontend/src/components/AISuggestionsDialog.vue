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
          <Tag 
            v-for="field in aiStore.sourceFieldsUsed" 
            :key="field.id"
            :value="`${field.src_table_name}.${field.src_column_name}`"
            severity="info"
          />
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

          <!-- Match Quality -->
          <Column header="Match Quality" style="min-width: 10rem">
            <template #body="{ data }">
              <div class="match-quality">
                <Tag 
                  :value="data.match_quality" 
                  :severity="getMatchQualitySeverity(data.match_quality)"
                  :icon="getMatchQualityIcon(data.match_quality)"
                />
                <div class="score-tooltip">
                  <i 
                    class="pi pi-info-circle" 
                    v-tooltip.right="{
                      value: getScoreTooltip(data.search_score),
                      escape: true
                    }"
                  ></i>
                </div>
              </div>
            </template>
          </Column>

          <!-- Search Score -->
          <Column header="Similarity" style="min-width: 8rem">
            <template #body="{ data }">
              <ProgressBar 
                :value="(data.search_score * 1000)" 
                :showValue="false"
                style="height: 0.5rem"
              />
              <span class="score-value">{{ (data.search_score * 1000).toFixed(1) }}</span>
            </template>
          </Column>

          <!-- AI Reasoning -->
          <Column header="AI Reasoning" style="min-width: 25rem">
            <template #body="{ data }">
              <div class="ai-reasoning">
                <i class="pi pi-comment"></i>
                <span>{{ data.ai_reasoning }}</span>
              </div>
            </template>
          </Column>

          <!-- Action -->
          <Column style="width: 8rem">
            <template #body="{ data }">
              <Button
                label="Select"
                icon="pi pi-check"
                size="small"
                @click.stop="handleSelect(data)"
              />
            </template>
          </Column>
        </DataTable>

        <!-- Info Message -->
        <Message severity="info" :closable="false" class="info-message">
          <strong>Tip:</strong> Click on a row or the "Select" button to choose a target field. 
          The system learns from your choices to improve future suggestions.
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
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAISuggestionsStoreV2 } from '@/stores/aiSuggestionsStoreV2'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
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

function getScoreTooltip(score: number): string {
  const normalized = (score * 1000).toFixed(1)
  return `Vector Similarity Score: ${normalized}\n\nScore Range:\n- 40+ = Excellent match\n- 20-40 = Good match\n- < 20 = Weak match\n\nThis score represents semantic similarity between source and target fields based on names, descriptions, and historical patterns.`
}

function getRowClass(data: AISuggestionV2) {
  return data.rank === 1 ? 'top-suggestion' : ''
}

function handleRowClick(event: any) {
  handleSelect(event.data)
}

function handleSelect(suggestion: AISuggestionV2) {
  aiStore.selectSuggestion(suggestion)
  emit('suggestion-selected', suggestion)
  isVisible.value = false
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
  flex-wrap: wrap;
  gap: 0.5rem;
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

.match-quality {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.score-tooltip i {
  color: var(--text-color-secondary);
  cursor: help;
}

.score-value {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  margin-top: 0.25rem;
  display: block;
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

