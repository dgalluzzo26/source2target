<template>
  <div class="mapping-config-view">
    <div class="view-header">
      <Button 
        icon="pi pi-arrow-left" 
        text 
        @click="handleBack"
        label="Back to Field Selection"
      />
      <h1>Configure Field Mapping</h1>
      <p class="subtitle">Configure how source fields map to the target field</p>
    </div>

    <!-- Progress Steps -->
    <Steps :model="steps" :activeIndex="activeStep" :readonly="false" class="mapping-steps" />

    <!-- Step 1: Review Selection -->
    <div v-if="activeStep === 0" class="step-content">
      <Card>
        <template #title>
          <i class="pi pi-check-circle"></i>
          Review Your Selection
        </template>
        <template #content>
          <div class="review-section">
            <div class="review-item">
              <h3>Source Fields ({{ sourceFields.length }})</h3>
              <div class="field-list">
                <Tag 
                  v-for="(field, idx) in sourceFields" 
                  :key="field.unmapped_field_id || idx"
                  :value="`${idx + 1}. ${field.src_table_name}.${field.src_column_name}`"
                  severity="info"
                  icon="pi pi-arrow-right"
                />
              </div>
            </div>

            <div class="arrow-separator">
              <i class="pi pi-arrow-down"></i>
            </div>

            <div class="review-item" v-if="targetField">
              <h3>Target Field</h3>
              <div class="target-preview">
                <Tag 
                  :value="`${targetField.tgt_table_name}.${targetField.tgt_column_name}`"
                  severity="success"
                  icon="pi pi-check"
                  style="font-size: 1.1rem;"
                />
                <div class="match-info">
                  <Tag :value="targetField.match_quality" :severity="getMatchQualitySeverity(targetField.match_quality)" />
                  <span class="ai-reasoning">{{ targetField.ai_reasoning }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Step 2: Field Ordering (Multi-field only) -->
    <div v-if="activeStep === 1 && sourceFields.length > 1" class="step-content">
      <Card>
        <template #title>
          <i class="pi pi-sort-alt"></i>
          Order Source Fields
        </template>
        <template #subtitle>
          Drag and drop to reorder fields. The order determines how fields are concatenated.
        </template>
        <template #content>
          <FieldOrderEditor 
            v-model:fields="orderedFields"
          />
        </template>
      </Card>
    </div>

    <!-- Step 2: Single Field Message -->
    <div v-if="activeStep === 1 && sourceFields.length === 1" class="step-content">
      <Card>
        <template #content>
          <Message severity="info" :closable="false">
            <strong>Single Field Mapping:</strong> Field ordering is not needed for single field mappings.
            Click "Next" to continue.
          </Message>
        </template>
      </Card>
    </div>

    <!-- Step 3: Define Joins (Multi-table only) -->
    <div v-if="activeStep === 2 && hasMultipleTables" class="step-content">
      <Card>
        <template #title>
          <i class="pi pi-link"></i>
          Define Table Joins
        </template>
        <template #subtitle>
          Specify how tables should be joined for the transformation query
        </template>
        <template #content>
          <JoinConfigurator 
            :source-fields="sourceFields"
            v-model:joins="joinDefinitions"
          />
        </template>
      </Card>
    </div>

    <!-- Step 3: Single Table Skip -->
    <div v-if="activeStep === 2 && !hasMultipleTables" class="step-content">
      <Card>
        <template #content>
          <Message severity="info" :closable="false">
            <strong>Single Table Mapping:</strong> All fields come from the same table. No joins needed.
            Click "Next" to continue to concatenation.
          </Message>
        </template>
      </Card>
    </div>

    <!-- Step 4: Concatenation Strategy (Multi-field only) -->
    <div v-if="activeStep === 3 && sourceFields.length > 1" class="step-content">
      <Card>
        <template #title>
          <i class="pi pi-link"></i>
          Concatenation Strategy
        </template>
        <template #subtitle>
          Choose how to combine multiple fields
        </template>
        <template #content>
          <ConcatStrategySelector 
            v-model:strategy="concatStrategy"
            v-model:customValue="customConcatValue"
            @update:strategy="updateSQLPreview"
            @update:customValue="updateSQLPreview"
          />
        </template>
      </Card>
    </div>

    <!-- Step 4: Single Field Skip -->
    <div v-if="activeStep === 3 && sourceFields.length === 1" class="step-content">
      <Card>
        <template #content>
          <Message severity="info" :closable="false">
            <strong>Single Field Mapping:</strong> Concatenation is not needed for single field mappings.
            Click "Next" to continue to transformations.
          </Message>
        </template>
      </Card>
    </div>

    <!-- Step 5: Transformations -->
    <div v-if="activeStep === 4" class="step-content">
      <Card>
        <template #title>
          <i class="pi pi-wrench"></i>
          Apply Transformations
        </template>
        <template #subtitle>
          Optional: Apply SQL transformations to each field
        </template>
        <template #content>
          <TransformationSelector 
            v-model:fields="orderedFields"
            @update:fields="updateSQLPreview"
          />
        </template>
      </Card>
    </div>

    <!-- Step 6: Review & Save -->
    <div v-if="activeStep === 5" class="step-content">
      <Card>
        <template #title>
          <i class="pi pi-eye"></i>
          Review & Save
        </template>
        <template #content>
          <div class="final-review">
            <!-- Mapping Summary -->
            <div class="summary-section">
              <h3>Mapping Summary</h3>
              <div class="summary-grid">
                <div class="summary-item">
                  <label>Source Fields:</label>
                  <span>{{ sourceFields.length }} field{{ sourceFields.length !== 1 ? 's' : '' }}</span>
                </div>
                <div class="summary-item" v-if="targetField">
                  <label>Target Field:</label>
                  <span>{{ targetField.tgt_table_name }}.{{ targetField.tgt_column_name }}</span>
                </div>
                <div class="summary-item" v-if="sourceFields.length > 1">
                  <label>Concatenation:</label>
                  <span>{{ getConcatStrategyLabel(concatStrategy) }}</span>
                </div>
                <div class="summary-item">
                  <label>Transformations:</label>
                  <span>{{ getTransformationCount() }} applied</span>
                </div>
              </div>
            </div>

            <!-- SQL Preview -->
            <div class="sql-preview-section">
              <h3>
                <i class="pi pi-code"></i>
                SQL Expression
              </h3>
              <div class="sql-preview">
                <code>{{ finalSQLExpression }}</code>
              </div>
            </div>

            <!-- Field Details -->
            <div class="field-details-section">
              <h3>Field Mapping Details</h3>
              <DataTable :value="orderedFields" class="field-details-table">
                <Column header="Order" style="width: 5rem">
                  <template #body="{ index }">
                    <Tag :value="`${index + 1}`" severity="info" />
                  </template>
                </Column>
                <Column header="Source Field">
                  <template #body="{ data }">
                    <strong>{{ data.src_table_name }}.{{ data.src_column_name }}</strong>
                  </template>
                </Column>
                <Column header="Transformation">
                  <template #body="{ data }">
                    <code v-if="data.transformation_expr">{{ data.transformation_expr }}</code>
                    <span v-else class="no-transform">None</span>
                  </template>
                </Column>
              </DataTable>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Navigation Footer -->
    <div class="navigation-footer">
      <Button 
        label="Previous" 
        icon="pi pi-chevron-left" 
        @click="handlePrevious"
        :disabled="activeStep === 0"
        severity="secondary"
      />
      <Button 
        v-if="activeStep < 5"
        label="Next" 
        icon="pi pi-chevron-right" 
        iconPos="right"
        @click="handleNext"
      />
      <Button 
        v-if="activeStep === 5"
        label="Save Mapping" 
        icon="pi pi-save" 
        @click="handleSave"
        :loading="saving"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMappingsStoreV2 } from '@/stores/mappingsStoreV2'
import { useUnmappedFieldsStore } from '@/stores/unmappedFieldsStore'
import { useAISuggestionsStoreV2 } from '@/stores/aiSuggestionsStoreV2'
import { useToast } from 'primevue/usetoast'
import Steps from 'primevue/steps'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import FieldOrderEditor from '@/components/FieldOrderEditor.vue'
import ConcatStrategySelector from '@/components/ConcatStrategySelector.vue'
import TransformationSelector from '@/components/TransformationSelector.vue'
import JoinConfigurator from '@/components/JoinConfigurator.vue'
import type { UnmappedField } from '@/stores/unmappedFieldsStore'
import type { AISuggestionV2 } from '@/stores/aiSuggestionsStoreV2'
import type { MappingDetailV2 } from '@/stores/mappingsStoreV2'

const route = useRoute()
const router = useRouter()
const mappingsStore = useMappingsStoreV2()
const unmappedStore = useUnmappedFieldsStore()
const aiStore = useAISuggestionsStoreV2()
const toast = useToast()

// State
const activeStep = ref(0)
const saving = ref(false)
const sourceFields = ref<UnmappedField[]>([])
const targetField = ref<AISuggestionV2 | null>(null)
const orderedFields = ref<MappingDetailV2[]>([])
const concatStrategy = ref<'SPACE' | 'COMMA' | 'PIPE' | 'CUSTOM' | 'NONE'>('SPACE')
const customConcatValue = ref('')
const finalSQLExpression = ref('')

// Steps configuration
const steps = ref([
  { label: 'Review' },
  { label: 'Order Fields' },
  { label: 'Define Joins' },
  { label: 'Concatenation' },
  { label: 'Transformations' },
  { label: 'Review & Save' }
])

// Join configuration
const joinDefinitions = ref<Array<{
  left_table: string
  left_table_physical: string
  left_column: string
  right_table: string
  right_table_physical: string
  right_column: string
  join_type: 'INNER' | 'LEFT' | 'RIGHT' | 'FULL'
  join_order: number
}>>([])

const hasMultipleTables = computed(() => {
  const tables = new Set(sourceFields.value.map(f => f.src_table_name))
  return tables.size > 1
})

onMounted(() => {
  // Load data from AI suggestions store
  if (aiStore.selectedSuggestion && aiStore.sourceFieldsUsed.length > 0) {
    sourceFields.value = aiStore.sourceFieldsUsed
    targetField.value = aiStore.selectedSuggestion
    
    // Initialize ordered fields
    orderedFields.value = sourceFields.value.map((field, index) => ({
      src_table_name: field.src_table_name,
      src_table_physical_name: field.src_table_physical_name,
      src_column_name: field.src_column_name,
      src_column_physical_name: field.src_column_physical_name,
      field_order: index + 1,
      transformation_expr: undefined
    }))

    // Set initial concat strategy
    if (sourceFields.value.length === 1) {
      concatStrategy.value = 'NONE'
    }

    updateSQLPreview()
    console.log('[Mapping Config] Loaded from AI store:', sourceFields.value.length, 'fields')
  } else {
    // No data in store - redirect back to field selection
    console.warn('[Mapping Config] No data in AI store, redirecting to unmapped fields')
    toast.add({
      severity: 'warn',
      summary: 'No Selection',
      detail: 'Please select fields and generate AI suggestions first',
      life: 3000
    })
    router.push({ name: 'unmapped-fields' })
  }
})

function getMatchQualitySeverity(quality: string): string {
  switch (quality) {
    case 'Excellent': return 'success'
    case 'Strong': return 'info'
    case 'Good': return 'warning'
    case 'Weak': return 'danger'
    default: return 'secondary'
  }
}

function getConcatStrategyLabel(strategy: string): string {
  switch (strategy) {
    case 'SPACE': return 'Space separator'
    case 'COMMA': return 'Comma separator'
    case 'PIPE': return 'Pipe separator'
    case 'CUSTOM': return `Custom: "${customConcatValue.value}"`
    case 'NONE': return 'No concatenation'
    default: return strategy
  }
}

function getTransformationCount(): number {
  return orderedFields.value.filter(f => f.transformation_expr).length
}

function updateSQLPreview() {
  finalSQLExpression.value = mappingsStore.buildSQLExpression(
    orderedFields.value,
    concatStrategy.value,
    customConcatValue.value
  )
}

function handleNext() {
  // Validate current step before proceeding
  
  // Step 2: Define Joins - Require at least one join if multiple tables
  if (activeStep.value === 2 && hasMultipleTables.value) {
    if (joinDefinitions.value.length === 0) {
      toast.add({
        severity: 'warn',
        summary: 'Join Required',
        detail: 'Please define at least one join between tables or go back to select fields from a single table.',
        life: 5000
      })
      return
    }
    
    // Validate that all joins have required fields
    const incompleteJoins = joinDefinitions.value.filter(join => 
      !join.left_table || !join.left_column || !join.right_table || !join.right_column
    )
    
    if (incompleteJoins.length > 0) {
      toast.add({
        severity: 'warn',
        summary: 'Incomplete Join',
        detail: 'Please complete all join definitions (table and column selections).',
        life: 5000
      })
      return
    }
  }
  
  if (activeStep.value < 5) {
    activeStep.value++
  }
}

function handlePrevious() {
  if (activeStep.value > 0) {
    activeStep.value--
  }
}

function handleBack() {
  router.push({ name: 'unmapped-fields' })
}

async function handleSave() {
  if (!targetField.value) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No target field selected',
      life: 3000
    })
    return
  }

  saving.value = true

  try {
    const mappingId = await mappingsStore.createMapping({
      semantic_field_id: targetField.value.semantic_field_id,
      tgt_table_name: targetField.value.tgt_table_name,
      tgt_table_physical_name: targetField.value.tgt_table_physical_name,
      tgt_column_name: targetField.value.tgt_column_name,
      tgt_column_physical_name: targetField.value.tgt_column_physical_name,
      concat_strategy: concatStrategy.value,
      concat_separator: customConcatValue.value || undefined,
      transformation_expression: finalSQLExpression.value,
      confidence_score: targetField.value.search_score,
      mapping_source: 'AI',
      ai_reasoning: targetField.value.ai_reasoning,
      mapping_status: 'ACTIVE',
      source_fields: orderedFields.value,
      mapping_joins: joinDefinitions.value
    })

    toast.add({
      severity: 'success',
      summary: 'Mapping Created',
      detail: `Successfully created mapping (ID: ${mappingId})`,
      life: 3000
    })

    // Clear selection and navigate back
    unmappedStore.clearSelection()
    router.push({ name: 'unmapped-fields' })
  } catch (error) {
    console.error('Failed to save mapping:', error)
    toast.add({
      severity: 'error',
      summary: 'Save Failed',
      detail: 'Failed to create mapping. Please try again.',
      life: 3000
    })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.mapping-config-view {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.view-header {
  margin-bottom: 2rem;
}

.view-header h1 {
  margin: 0.5rem 0 0.5rem 0;
  color: var(--gainwell-dark);
}

.subtitle {
  margin: 0;
  color: var(--text-color-secondary);
}

.mapping-steps {
  margin-bottom: 2rem;
}

.step-content {
  margin-bottom: 2rem;
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.review-section {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.review-item h3 {
  margin: 0 0 1rem 0;
  color: var(--gainwell-dark);
}

.field-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.arrow-separator {
  text-align: center;
  color: var(--gainwell-primary);
  font-size: 2rem;
}

.target-preview {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.match-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.ai-reasoning {
  color: var(--text-color-secondary);
  font-style: italic;
}

.final-review {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.summary-section h3,
.sql-preview-section h3,
.field-details-section h3 {
  margin: 0 0 1rem 0;
  color: var(--gainwell-dark);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.summary-item label {
  font-weight: 600;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.summary-item span {
  color: var(--text-color);
}

.sql-preview {
  padding: 1rem;
  background: var(--surface-100);
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  overflow-x: auto;
}

.sql-preview code {
  color: var(--gainwell-dark);
  font-size: 0.95rem;
}

.no-transform {
  color: var(--text-color-secondary);
  font-style: italic;
}

.navigation-footer {
  display: flex;
  justify-content: space-between;
  padding: 1.5rem;
  background: white;
  border-top: 1px solid var(--surface-border);
  position: sticky;
  bottom: 0;
  z-index: 10;
}

/* Responsive */
@media (max-width: 768px) {
  .mapping-config-view {
    padding: 1rem;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>

