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
      <p class="subtitle">Define the SQL expression to map source fields to the target</p>
    </div>

    <div class="config-layout">
      <!-- Left Panel: Source & Target Info -->
      <div class="info-panel">
        <!-- Source Fields Card -->
        <Card class="info-card">
          <template #title>
            <div class="card-title">
              <i class="pi pi-database"></i>
              Source Fields ({{ sourceFields.length }})
            </div>
          </template>
          <template #content>
            <div class="source-fields-list">
              <div 
                v-for="(field, idx) in sourceFields" 
                :key="field.unmapped_field_id || idx"
                class="source-field-item"
              >
                <Badge :value="idx + 1" severity="info" />
                <div class="field-details">
                  <strong>{{ field.src_table_name }}.{{ field.src_column_name }}</strong>
                  <div class="field-meta">
                    <Tag :value="field.src_physical_datatype" size="small" severity="secondary" />
                    <span v-if="field.src_comments" class="field-comment">{{ field.src_comments }}</span>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </Card>

        <!-- Target Field Card -->
        <Card class="info-card target-card">
          <template #title>
            <div class="card-title">
              <i class="pi pi-arrow-circle-right"></i>
              Target Field
            </div>
          </template>
          <template #content>
            <div v-if="targetField" class="target-field-display">
              <Tag 
                :value="`${targetField.tgt_table_name}.${targetField.tgt_column_name}`"
                severity="success"
                icon="pi pi-check"
                class="target-tag"
              />
              <div class="target-meta">
                <div class="match-quality">
                  <Tag 
                    :value="targetField.match_quality" 
                    :severity="getMatchQualitySeverity(targetField.match_quality)" 
                    size="small"
                  />
                </div>
                <p v-if="targetField.ai_reasoning" class="ai-reasoning">{{ targetField.ai_reasoning }}</p>
              </div>
            </div>
          </template>
        </Card>

        <!-- AI Patterns Card (from historical mappings) -->
        <Card v-if="historicalPatterns.length > 0" class="info-card patterns-card">
          <template #title>
            <div class="card-title">
              <i class="pi pi-history"></i>
              Similar Past Mappings
            </div>
          </template>
          <template #content>
            <div class="patterns-list">
              <div 
                v-for="(pattern, idx) in historicalPatterns.slice(0, 3)" 
                :key="idx"
                class="pattern-item"
                @click="usePattern(pattern)"
              >
                <div class="pattern-header">
                  <strong>{{ pattern.source_columns }} → {{ pattern.tgt_column_name }}</strong>
                  <Tag v-if="pattern.transformations_applied" :value="pattern.transformations_applied" size="small" severity="warning" />
                </div>
                <code class="pattern-sql">{{ pattern.source_expression }}</code>
                <span class="pattern-hint">Click to use this pattern</span>
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Right Panel: SQL Editor -->
      <div class="editor-panel">
        <Card class="editor-card">
          <template #title>
            <div class="card-title-with-actions">
              <div class="card-title">
                <i class="pi pi-code"></i>
                SQL Expression
              </div>
              <div class="title-actions">
                <Button 
                  icon="pi pi-sparkles"
                  label="AI Helper"
                  size="small"
                  severity="info"
                  outlined
                  @click="showAIHelper = true"
                />
                <Dropdown
                  v-model="selectedTransformation"
                  :options="transformationOptions"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Quick Transform"
                  class="quick-transform"
                  @change="applyQuickTransform"
                />
              </div>
            </div>
          </template>
          <template #content>
            <div class="editor-content">
              <Textarea
                v-model="sourceExpression"
                :rows="8"
                class="sql-editor"
                :placeholder="sqlPlaceholder"
                @input="updatePreview"
              />
              
              <!-- SQL Preview -->
              <div class="sql-preview-section">
                <h4>Preview</h4>
                <pre class="sql-preview">{{ previewSQL }}</pre>
              </div>
              
              <!-- Relationship Type -->
              <div class="relationship-section">
                <label>Relationship Type</label>
                <SelectButton 
                  v-model="relationshipType" 
                  :options="relationshipOptions" 
                  optionLabel="label"
                  optionValue="value"
                  @change="updateSqlPlaceholder"
                />
                <div class="relationship-help">
                  <Message v-if="relationshipType === 'JOIN'" severity="info" :closable="false">
                    <strong>JOIN Example:</strong>
                    <pre>SELECT t1.field1, t2.field2 
FROM table1 t1 
JOIN table2 t2 ON t1.id = t2.id</pre>
                  </Message>
                  <Message v-else-if="relationshipType === 'UNION'" severity="info" :closable="false">
                    <strong>UNION Example:</strong>
                    <pre>SELECT field1 FROM table1
UNION ALL
SELECT field1 FROM table2</pre>
                  </Message>
                  <small v-else class="help-text">Single source field, optionally with transformations</small>
                </div>
              </div>

              <!-- Metadata (auto-populated, read-only) -->
              <div class="metadata-section">
                <h4><i class="pi pi-info-circle"></i> Mapping Metadata <small>(auto-populated)</small></h4>
                <div class="metadata-grid">
                  <div class="field">
                    <label>Source Tables</label>
                    <InputText v-model="sourceTables" disabled class="readonly-field" />
                  </div>
                  <div class="field">
                    <label>Source Columns</label>
                    <InputText v-model="sourceColumns" disabled class="readonly-field" />
                  </div>
                  <div class="field">
                    <label>Detected Transformations</label>
                    <InputText v-model="transformationsApplied" disabled class="readonly-field" placeholder="Auto-detected from SQL" />
                  </div>
                </div>
                <small class="metadata-hint">These fields are auto-populated from your selected source fields. Edit the SQL Expression above to define the actual mapping logic.</small>
              </div>
            </div>
          </template>
        </Card>

        <!-- Action Footer -->
        <div class="action-footer">
          <Button 
            label="Cancel" 
            icon="pi pi-times" 
            severity="secondary"
            @click="handleBack"
          />
          <Button 
            label="Save Mapping" 
            icon="pi pi-save" 
            @click="handleSave"
            :loading="saving"
            :disabled="!isValid"
          />
        </div>
      </div>
    </div>

    <!-- AI Helper Dialog -->
    <Dialog 
      v-model:visible="showAIHelper" 
      modal 
      header="AI SQL Helper" 
      :style="{ width: '700px' }"
      :breakpoints="{ '960px': '90vw' }"
    >
      <div class="ai-helper-content">
        <Message severity="info" :closable="false">
          <strong>Describe what you want in plain language.</strong>
          The AI will generate appropriate Databricks SQL.
        </Message>
        
        <div class="ai-examples">
          <span>Try:</span>
          <Tag 
            v-for="example in aiExamples" 
            :key="example"
            :value="example"
            class="example-tag"
            @click="aiHelperRequest = example"
          />
        </div>
        
        <Textarea
          v-model="aiHelperRequest"
          :rows="4"
          class="ai-input w-full"
          placeholder="e.g., 'Combine first_name and last_name with a space, convert to uppercase'"
        />
        
        <div v-if="aiGeneratedSQL" class="ai-result">
          <h4><i class="pi pi-sparkles"></i> Generated SQL</h4>
          <pre class="generated-sql">{{ aiGeneratedSQL }}</pre>
          <p v-if="aiExplanation" class="ai-explanation">
            <i class="pi pi-info-circle"></i> {{ aiExplanation }}
          </p>
        </div>
      </div>

      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="showAIHelper = false" 
          severity="secondary"
        />
        <Button 
          label="Generate SQL" 
          icon="pi pi-sparkles" 
          @click="generateSQL"
          :loading="generatingSQL"
          :disabled="!aiHelperRequest.trim()"
        />
        <Button 
          v-if="aiGeneratedSQL"
          label="Use This SQL" 
          icon="pi pi-check" 
          severity="success"
          @click="useGeneratedSQL"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMappingsStoreV3 } from '@/stores/mappingsStoreV3'
import { useUnmappedFieldsStore } from '@/stores/unmappedFieldsStore'
import { useAISuggestionsStore } from '@/stores/aiSuggestionsStore'
import { useUserStore } from '@/stores/user'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import Textarea from 'primevue/textarea'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import SelectButton from 'primevue/selectbutton'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import type { UnmappedField } from '@/stores/unmappedFieldsStore'
import type { AISuggestion } from '@/stores/aiSuggestionsStore'
import api from '@/services/api'

const router = useRouter()
const mappingsStore = useMappingsStoreV3()
const unmappedStore = useUnmappedFieldsStore()
const aiStore = useAISuggestionsStore()
const userStore = useUserStore()
const toast = useToast()

// State
const sourceFields = ref<UnmappedField[]>([])
const targetField = ref<AISuggestion | null>(null)
const historicalPatterns = ref<any[]>([])
const saving = ref(false)

// SQL Expression state
const sourceExpression = ref('')
const relationshipType = ref<'SINGLE' | 'JOIN' | 'UNION'>('SINGLE')
const sourceTables = ref('')
const sourceColumns = ref('')
const transformationsApplied = ref('')

// AI Helper state
const showAIHelper = ref(false)
const aiHelperRequest = ref('')
const aiGeneratedSQL = ref('')
const aiExplanation = ref('')
const generatingSQL = ref(false)

// Quick transformation dropdown
const selectedTransformation = ref<string | null>(null)

// Relationship options
const relationshipOptions = [
  { label: 'Single', value: 'SINGLE' },
  { label: 'Join', value: 'JOIN' },
  { label: 'Union', value: 'UNION' }
]

// AI examples
const aiExamples = [
  'Trim whitespace',
  'Convert to uppercase',
  'Combine with space',
  'Format as date',
  'Remove special characters'
]

// Transformation options
const transformationOptions = computed(() => {
  const transforms = mappingsStore.transformations.map(t => ({
    label: t.transformation_name,
    value: t.transformation_expression
  }))
  transforms.unshift({ label: 'Select transformation...', value: null as any })
  return transforms
})

// SQL placeholder
const sqlPlaceholder = computed(() => {
  const fields = sourceFields.value
  if (fields.length === 0) {
    return 'Enter SQL expression...'
  }
  
  const col1 = fields[0]?.src_column_physical_name || 'column1'
  const cols = fields.map(f => f.src_column_physical_name).join(', ')
  
  if (relationshipType.value === 'JOIN') {
    return `-- JOIN Example:\nSELECT t1.${col1}, t2.field2\nFROM table1 t1\nJOIN table2 t2 ON t1.id = t2.id`
  } else if (relationshipType.value === 'UNION') {
    return `-- UNION Example:\nSELECT ${col1} FROM table1\nUNION ALL\nSELECT ${col1} FROM table2`
  } else if (fields.length === 1) {
    return `Enter SQL expression, e.g.:\n  ${col1}\n  TRIM(${col1})\n  UPPER(TRIM(${col1}))`
  } else {
    return `Enter SQL expression, e.g.:\n  CONCAT(${cols})\n  CONCAT_WS(' ', ${cols})`
  }
})

// Preview SQL
const previewSQL = computed(() => {
  if (!sourceExpression.value) {
    return '-- Enter SQL expression above'
  }
  
  const targetCol = targetField.value?.tgt_column_physical_name || 'target_column'
  return `SELECT ${sourceExpression.value} AS ${targetCol}`
})

// Validation
const isValid = computed(() => {
  return sourceExpression.value.trim().length > 0 && targetField.value !== null
})

onMounted(async () => {
  console.log('[Mapping Config V3] === Mounting ===')
  console.log('[Mapping Config V3] aiStore.selectedSuggestion:', aiStore.selectedSuggestion)
  console.log('[Mapping Config V3] aiStore.sourceFieldsUsed:', aiStore.sourceFieldsUsed)
  console.log('[Mapping Config V3] aiStore.sourceFieldsUsed.length:', aiStore.sourceFieldsUsed?.length)
  
  // Load from AI store
  if (aiStore.selectedSuggestion && aiStore.sourceFieldsUsed?.length > 0) {
    console.log('[Mapping Config V3] Found data in AI store, loading...')
    sourceFields.value = aiStore.sourceFieldsUsed
    targetField.value = aiStore.selectedSuggestion
    
    console.log('[Mapping Config V3] Target field:', targetField.value?.tgt_column_name)
    console.log('[Mapping Config V3] Source fields:', sourceFields.value.map((f: any) => f.src_column_name))
    
    // Auto-populate metadata
    initializeMetadata()
    
    // Generate default expression
    generateDefaultExpression()
    
    // Fetch historical patterns
    await fetchHistoricalPatterns()
    
    console.log('[Mapping Config V3] Loaded', sourceFields.value.length, 'source fields')
  } else {
    console.warn('[Mapping Config V3] No data in AI store!')
    console.warn('[Mapping Config V3] selectedSuggestion:', aiStore.selectedSuggestion)
    console.warn('[Mapping Config V3] sourceFieldsUsed:', aiStore.sourceFieldsUsed)
    toast.add({
      severity: 'warn',
      summary: 'No Selection',
      detail: 'Please select fields and generate AI suggestions first',
      life: 3000
    })
    router.push({ name: 'unmapped-fields' })
  }
  
  // Load transformations
  await mappingsStore.fetchTransformations()
})

function initializeMetadata() {
  // Auto-populate metadata from source fields
  const tables = [...new Set(sourceFields.value.map(f => f.src_table_name))]
  const columns = sourceFields.value.map(f => f.src_column_name)
  
  sourceTables.value = tables.join(', ')
  sourceColumns.value = columns.join(', ')
  
  // Determine relationship type
  if (tables.length > 1) {
    relationshipType.value = 'JOIN'
  } else {
    relationshipType.value = 'SINGLE'
  }
}

function generateDefaultExpression() {
  if (sourceFields.value.length === 1) {
    // Single field: just the column name
    sourceExpression.value = sourceFields.value[0].src_column_physical_name
  } else {
    // Multi-field: CONCAT with space
    const cols = sourceFields.value.map(f => f.src_column_physical_name)
    sourceExpression.value = `CONCAT_WS(' ', ${cols.join(', ')})`
  }
}

async function fetchHistoricalPatterns() {
  try {
    // Build search query from source fields
    const descriptions = sourceFields.value
      .map(f => f.src_comments || f.src_column_name)
      .join(' | ')
    
    // Call AI suggestions endpoint to get patterns
    const response = await api.post('/api/v3/ai/suggestions', {
      source_fields: sourceFields.value.map(f => ({
        unmapped_field_id: f.unmapped_field_id,
        src_table_name: f.src_table_name,
        src_table_physical_name: f.src_table_physical_name,
        src_column_name: f.src_column_name,
        src_column_physical_name: f.src_column_physical_name,
        src_physical_datatype: f.src_physical_datatype,
        src_comments: f.src_comments
      })),
      num_suggestions: 3
    })
    
    // Extract historical patterns from response
    if (response.data?.historical_patterns) {
      historicalPatterns.value = response.data.historical_patterns
    }
    
  } catch (e) {
    console.warn('[Mapping Config V3] Could not fetch historical patterns:', e)
  }
}

function usePattern(pattern: any) {
  sourceExpression.value = pattern.source_expression
  if (pattern.transformations_applied) {
    transformationsApplied.value = pattern.transformations_applied
  }
  if (pattern.source_relationship_type) {
    relationshipType.value = pattern.source_relationship_type
  }
  
  toast.add({
    severity: 'success',
    summary: 'Pattern Applied',
    detail: 'Historical pattern applied to expression',
    life: 2000
  })
}

function applyQuickTransform() {
  if (!selectedTransformation.value) return
  
  const template = selectedTransformation.value
  
  if (sourceFields.value.length === 1) {
    // Single field: replace {field} with column name
    const col = sourceFields.value[0].src_column_physical_name
    sourceExpression.value = template.replace('{field}', col)
  } else {
    // Multi-field: apply to first field or show as example
    const col = sourceFields.value[0].src_column_physical_name
    sourceExpression.value = template.replace('{field}', col)
  }
  
  // Parse transformation name
  const match = template.match(/^(\w+)\(/)?.[1]
  if (match && !transformationsApplied.value.includes(match)) {
    transformationsApplied.value = transformationsApplied.value 
      ? `${transformationsApplied.value}, ${match}`
      : match
  }
  
  // Reset dropdown
  selectedTransformation.value = null
}

function updatePreview() {
  const expr = sourceExpression.value.toUpperCase()
  
  // Auto-detect transformations from expression
  const transforms: string[] = []
  
  if (expr.includes('TRIM')) transforms.push('TRIM')
  if (expr.includes('UPPER')) transforms.push('UPPER')
  if (expr.includes('LOWER')) transforms.push('LOWER')
  if (expr.includes('CONCAT')) transforms.push('CONCAT')
  if (expr.includes('CAST')) transforms.push('CAST')
  if (expr.includes('COALESCE')) transforms.push('COALESCE')
  if (expr.includes('NVL')) transforms.push('NVL')
  if (expr.includes('DATE_FORMAT')) transforms.push('DATE_FORMAT')
  if (expr.includes('TO_DATE')) transforms.push('TO_DATE')
  if (expr.includes('INITCAP')) transforms.push('INITCAP')
  if (expr.includes('SUBSTRING')) transforms.push('SUBSTRING')
  if (expr.includes('REPLACE')) transforms.push('REPLACE')
  if (expr.includes('REGEXP')) transforms.push('REGEXP')
  
  // Update transformations field
  transformationsApplied.value = transforms.length > 0 ? transforms.join(', ') : ''
  
  // Auto-detect relationship type from SQL
  if (expr.includes(' JOIN ')) {
    relationshipType.value = 'JOIN'
  } else if (expr.includes('UNION')) {
    relationshipType.value = 'UNION'
  }
}

function updateSqlPlaceholder() {
  // Called when relationship type changes - placeholder updates via computed
  console.log('[Mapping Config] Relationship type changed to:', relationshipType.value)
}

async function generateSQL() {
  if (!aiHelperRequest.value.trim()) return
  
  generatingSQL.value = true
  
  try {
    const result = await mappingsStore.generateSQLWithAI(
      aiHelperRequest.value,
      sourceFields.value.map(f => ({
        table: f.src_table_name,
        column: f.src_column_name,
        datatype: f.src_physical_datatype
      })),
      {
        table: targetField.value?.tgt_table_name || '',
        column: targetField.value?.tgt_column_name || '',
        datatype: 'STRING'
      }
    )
    
    aiGeneratedSQL.value = result.sql
    aiExplanation.value = result.explanation
    
  } catch (error: any) {
    console.error('Error generating SQL:', error)
    toast.add({
      severity: 'error',
      summary: 'AI Error',
      detail: error.message || 'Failed to generate SQL',
      life: 5000
    })
  } finally {
    generatingSQL.value = false
  }
}

function useGeneratedSQL() {
  if (aiGeneratedSQL.value) {
    sourceExpression.value = aiGeneratedSQL.value
    showAIHelper.value = false
    updatePreview()
    
    toast.add({
      severity: 'success',
      summary: 'SQL Applied',
      detail: 'AI-generated SQL has been applied',
      life: 3000
    })
  }
}

function getMatchQualitySeverity(quality: string): string {
  switch (quality) {
    case 'Excellent': return 'success'
    case 'Strong': return 'info'
    case 'Good': return 'warning'
    case 'Weak': return 'danger'
    default: return 'secondary'
  }
}

function handleBack() {
  router.push({ name: 'unmapped-fields' })
}

async function handleSave() {
  if (!targetField.value || !sourceExpression.value.trim()) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Please enter a SQL expression',
      life: 3000
    })
    return
  }
  
  saving.value = true
  
  try {
    // Build source descriptions
    const descriptions = sourceFields.value
      .map(f => f.src_comments || '')
      .filter(d => d)
      .join(' | ')
    
    // Build source datatypes
    const datatypes = sourceFields.value
      .map(f => f.src_physical_datatype)
      .join(', ')
    
    const mappingId = await mappingsStore.createMapping(
      {
        semantic_field_id: targetField.value.semantic_field_id,
        tgt_table_name: targetField.value.tgt_table_name,
        tgt_table_physical_name: targetField.value.tgt_table_physical_name,
        tgt_column_name: targetField.value.tgt_column_name,
        tgt_column_physical_name: targetField.value.tgt_column_physical_name,
        tgt_comments: targetField.value.tgt_comments,
        source_expression: sourceExpression.value,
        source_tables: sourceTables.value || undefined,
        source_columns: sourceColumns.value || undefined,
        source_descriptions: descriptions || undefined,
        source_datatypes: datatypes || undefined,
        source_relationship_type: relationshipType.value,
        transformations_applied: transformationsApplied.value || undefined,
        confidence_score: targetField.value.search_score,
        mapping_source: 'AI',
        ai_reasoning: targetField.value.ai_reasoning,
        ai_generated: false,
        mapped_by: userStore.userEmail || 'unknown'
      },
      sourceFields.value.map(f => (f as any).id || (f as any).unmapped_field_id).filter((id): id is number => id !== undefined && id > 0)
    )
    
    toast.add({
      severity: 'success',
      summary: 'Mapping Created',
      detail: `Successfully created mapping (ID: ${mappingId})`,
      life: 3000
    })
    
    // Clear selection and navigate
    unmappedStore.clearSelection()
    router.push({ name: 'unmapped-fields' })
    
  } catch (error: any) {
    console.error('Failed to save mapping:', error)
    toast.add({
      severity: 'error',
      summary: 'Save Failed',
      detail: error.message || 'Failed to create mapping',
      life: 5000
    })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.mapping-config-view {
  padding: 2rem;
  max-width: 1400px;
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

.config-layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 1.5rem;
}

/* Info Panel (Left) */
.info-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--gainwell-dark);
}

.card-title i {
  color: var(--primary-color);
}

.source-fields-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.source-field-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.field-details {
  flex: 1;
  min-width: 0;
}

.field-details strong {
  font-size: 0.95rem;
  word-break: break-word;
}

.field-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.25rem;
}

.field-comment {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  font-style: italic;
}

.target-card {
  border-left: 4px solid var(--green-500);
}

.target-field-display {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.target-tag {
  font-size: 1rem;
}

.target-meta {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.match-quality {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.confidence {
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.ai-reasoning {
  font-size: 0.9rem;
  color: var(--text-color-secondary);
  font-style: italic;
  margin: 0;
}

.patterns-card {
  border-left: 4px solid var(--blue-500);
}

.patterns-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.pattern-item {
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.pattern-item:hover {
  background: var(--blue-50);
  transform: translateX(4px);
}

.pattern-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.pattern-sql {
  display: block;
  font-size: 0.85rem;
  background: var(--surface-100);
  padding: 0.5rem;
  border-radius: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pattern-hint {
  display: block;
  font-size: 0.8rem;
  color: var(--blue-500);
  margin-top: 0.25rem;
  opacity: 0;
  transition: opacity 0.2s;
}

.pattern-item:hover .pattern-hint {
  opacity: 1;
}

/* Editor Panel (Right) */
.editor-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;  /* Allow flex item to shrink */
  overflow: hidden;
}

.editor-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  flex: 1;
  min-width: 0;  /* Allow card to shrink */
  overflow: hidden;
}

.editor-card :deep(.p-card-content) {
  overflow: hidden;
}

.card-title-with-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.title-actions {
  display: flex;
  gap: 0.5rem;
}

.quick-transform {
  width: 160px;
}

.editor-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-width: 0;
  overflow: hidden;
  max-width: 100%;
}

.sql-editor {
  font-family: 'Courier New', 'Monaco', monospace;
  font-size: 0.95rem;
  width: 100%;
  min-height: 150px;
  resize: vertical;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

/* Override PrimeVue Textarea to allow proper wrapping */
.sql-editor:deep(textarea) {
  white-space: pre-wrap !important;
  word-wrap: break-word !important;
  overflow-wrap: break-word !important;
}

.sql-preview-section {
  max-width: 100%;
  overflow: hidden;
}

.sql-preview-section h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.sql-preview {
  background: var(--surface-50);
  padding: 1rem;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  margin: 0;
  overflow-x: auto;
  overflow-y: auto;
  max-height: 200px;
  border: 1px solid var(--surface-border);
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
}

.relationship-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.relationship-section label {
  font-weight: 600;
  color: var(--text-color);
}

.relationship-help {
  margin-top: 0.5rem;
}

.relationship-help pre {
  background: var(--surface-100);
  padding: 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  margin: 0.5rem 0 0 0;
  white-space: pre-wrap;
  font-family: 'Courier New', monospace;
}

.help-text {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

.metadata-section {
  border-top: 1px solid var(--surface-border);
  padding-top: 1rem;
  background: var(--surface-50);
  padding: 1rem;
  border-radius: 6px;
  margin-top: 1rem;
}

.metadata-section h4 {
  margin: 0 0 0.75rem 0;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.metadata-section h4 small {
  font-weight: normal;
  color: var(--text-color-secondary);
}

.metadata-hint {
  display: block;
  margin-top: 0.75rem;
  color: var(--text-color-secondary);
  font-size: 0.8rem;
  font-style: italic;
}

.readonly-field {
  background: var(--surface-100) !important;
  opacity: 0.8;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-color);
}

.action-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* AI Helper Dialog */
.ai-helper-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.ai-examples {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.ai-examples span {
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.example-tag {
  cursor: pointer;
  transition: transform 0.2s;
}

.example-tag:hover {
  transform: scale(1.05);
}

.ai-input {
  font-size: 1rem;
}

.ai-result {
  padding: 1rem;
  background: var(--green-50);
  border-radius: 8px;
  border-left: 4px solid var(--green-500);
}

.ai-result h4 {
  margin: 0 0 0.5rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--green-700);
}

.generated-sql {
  background: white;
  padding: 1rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  margin: 0;
  overflow-x: auto;
  white-space: pre-wrap;
}

.ai-explanation {
  margin: 0.5rem 0 0 0;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.w-full {
  width: 100%;
}

/* Responsive */
@media (max-width: 1024px) {
  .config-layout {
    grid-template-columns: 1fr;
  }
  
  .info-panel {
    order: -1;
  }
  
  .metadata-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .mapping-config-view {
    padding: 1rem;
  }
  
  .card-title-with-actions {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .title-actions {
    width: 100%;
  }
  
  .quick-transform {
    width: 100%;
  }
}
</style>

