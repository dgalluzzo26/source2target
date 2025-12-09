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
        <!-- Loading Past Mappings -->
        <Card v-if="loadingPatterns" class="info-card patterns-card loading-patterns">
          <template #title>
            <div class="card-title">
              <i class="pi pi-history"></i>
              Similar Past Mappings
            </div>
          </template>
          <template #content>
            <div class="loading-patterns-content">
              <ProgressSpinner style="width: 30px; height: 30px;" />
              <span>Searching for similar past mappings...</span>
            </div>
          </template>
        </Card>

        <!-- Past Mappings Found -->
        <Card v-else-if="filteredHistoricalPatterns.length > 0" class="info-card patterns-card">
          <template #title>
            <div class="card-title">
              <i class="pi pi-history"></i>
              Similar Past Mappings ({{ filteredHistoricalPatterns.length }})
            </div>
          </template>
          <template #content>
            <p class="patterns-hint">
              Showing {{ hasMultipleFields ? (hasMultipleTables ? 'all' : 'SINGLE/UNION') : 'SINGLE' }} patterns for your selection
            </p>
            <div class="patterns-list">
              <div 
                v-for="(pattern, idx) in filteredHistoricalPatterns.slice(0, 3)" 
                :key="idx"
                class="pattern-item"
                @click="usePattern(pattern)"
              >
                <div class="pattern-header">
                  <span class="pattern-target">→ {{ pattern.tgt_column_name }}</span>
                  <Tag v-if="pattern.transformations_applied" :value="pattern.transformations_applied" size="small" severity="warning" />
                </div>
                <div class="pattern-info">
                  <span class="pattern-type">{{ pattern.source_relationship_type || 'SINGLE' }}</span>
                </div>
                <span class="pattern-hint">Click to apply transformations to your fields</span>
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
                :class="{ 'sql-error': !sqlValidation.valid && sourceExpression.trim() }"
                :placeholder="sqlPlaceholder"
                @input="updatePreview"
              />
              
              <!-- SQL Validation Error -->
              <Message 
                v-if="!sqlValidation.valid && sourceExpression.trim()" 
                severity="error" 
                :closable="false"
                class="sql-validation-error"
              >
                <i class="pi pi-exclamation-triangle"></i>
                <strong>Invalid SQL:</strong> {{ sqlValidation.error }}
              </Message>
              
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
                  optionDisabled="disabled"
                  @change="handleRelationshipChange"
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
            v-tooltip.top="saveButtonTooltip"
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
import ProgressSpinner from 'primevue/progressspinner'
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
const loadingPatterns = ref(false)
const saving = ref(false)

// SQL Expression state
const sourceExpression = ref('')
const relationshipType = ref<'SINGLE' | 'JOIN' | 'UNION'>('SINGLE')
const sourceTables = ref('')  // Logical names
const sourceColumns = ref('')  // Logical names
const sourceTablesPhysical = ref('')  // Physical names (for restore)
const sourceColumnsPhysical = ref('')  // Physical names (for restore)
const transformationsApplied = ref('')

// AI Helper state
const showAIHelper = ref(false)
const aiHelperRequest = ref('')
const aiGeneratedSQL = ref('')
const aiExplanation = ref('')
const generatingSQL = ref(false)

// Quick transformation dropdown
const selectedTransformation = ref<string | null>(null)

// Relationship options - computed based on source fields
const hasMultipleFields = computed(() => sourceFields.value.length > 1)
const hasMultipleTables = computed(() => {
  const tables = new Set(sourceFields.value.map(f => f.src_table_name || f.src_table_physical_name))
  return tables.size > 1
})

// Filter historical patterns based on current selection
// - 1 column: show SINGLE patterns and any pattern with transformations (user wants to see what transforms were used)
// - Multiple columns, same table: show SINGLE, UNION, CONCAT
// - Multiple columns, different tables: show all types
const filteredHistoricalPatterns = computed(() => {
  if (!historicalPatterns.value || historicalPatterns.value.length === 0) {
    console.log('[Mapping Config] No historical patterns to filter')
    return []
  }
  
  console.log('[Mapping Config] Filtering', historicalPatterns.value.length, 'patterns')
  console.log('[Mapping Config] hasMultipleFields:', hasMultipleFields.value)
  console.log('[Mapping Config] hasMultipleTables:', hasMultipleTables.value)
  
  const filtered = historicalPatterns.value.filter(pattern => {
    const patternType = (pattern.source_relationship_type || 'SINGLE').toUpperCase()
    const hasTransformations = pattern.transformations_applied && pattern.transformations_applied.trim() !== ''
    
    // Single column selected:
    // - Show SINGLE patterns
    // - Show CONCAT patterns (might be combining later, useful to see transformations)
    // - Show ANY pattern that has transformations (user wants to see what transforms are commonly used)
    if (!hasMultipleFields.value) {
      const show = patternType === 'SINGLE' || patternType === 'CONCAT' || hasTransformations
      if (show) {
        console.log('[Mapping Config] Including pattern:', pattern.tgt_column_name, 'type:', patternType, 'transforms:', pattern.transformations_applied)
      }
      return show
    }
    
    // Multiple columns from different tables - show all types
    if (hasMultipleTables.value) {
      return true // SINGLE, JOIN, UNION, CONCAT all allowed
    }
    
    // Multiple columns from same table - show SINGLE, UNION, CONCAT (no JOIN since same table)
    return patternType === 'SINGLE' || patternType === 'UNION' || patternType === 'CONCAT'
  })
  
  console.log('[Mapping Config] Filtered to', filtered.length, 'patterns')
  return filtered
})

const relationshipOptions = computed(() => [
  { label: 'Single', value: 'SINGLE', disabled: false },
  { 
    label: hasMultipleTables.value ? 'Join' : 'Join (need multiple tables)', 
    value: 'JOIN', 
    disabled: !hasMultipleTables.value 
  },
  { 
    label: hasMultipleFields.value ? 'Union' : 'Union (need multiple fields)', 
    value: 'UNION', 
    disabled: !hasMultipleFields.value 
  }
])

// AI examples
const aiExamples = [
  'Trim whitespace',
  'Convert to uppercase',
  'Combine with space',
  'Format as date',
  'Remove special characters'
]

// Transformation options
// Simple built-in transformations (no database needed)
const transformationOptions = [
  { label: 'Select transformation...', value: null },
  { label: 'TRIM', value: 'TRIM({field})' },
  { label: 'UPPER', value: 'UPPER({field})' },
  { label: 'LOWER', value: 'LOWER({field})' },
  { label: 'INITCAP', value: 'INITCAP({field})' },
  { label: 'TRIM + UPPER', value: 'TRIM(UPPER({field}))' },
  { label: 'TRIM + INITCAP', value: 'TRIM(INITCAP({field}))' },
  { label: 'COALESCE (null handling)', value: "COALESCE({field}, '')" },
  { label: 'CAST to STRING', value: 'CAST({field} AS STRING)' },
  { label: 'CAST to DATE', value: "TO_DATE({field}, 'yyyy-MM-dd')" },
  { label: 'CONCAT (2 fields)', value: "CONCAT({field}, ' ', {field2})" }
]

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

// Validation - includes SQL validation
const isValid = computed(() => {
  const hasExpression = sourceExpression.value.trim().length > 0
  const hasTarget = targetField.value !== null
  const sqlIsValid = sqlValidation.value.valid
  
  return hasExpression && hasTarget && sqlIsValid
})

// Save button tooltip - explains why disabled
const saveButtonTooltip = computed(() => {
  if (!targetField.value) {
    return 'Select a target field first'
  }
  if (!sourceExpression.value.trim()) {
    return 'Enter a SQL expression'
  }
  if (!sqlValidation.value.valid) {
    return `Fix SQL error: ${sqlValidation.value.error}`
  }
  return 'Save this mapping'
})

// Watch source fields and reset relationship type if invalid
watch(sourceFields, () => {
  // If JOIN is selected but we no longer have multiple tables, reset to SINGLE
  if (relationshipType.value === 'JOIN' && !hasMultipleTables.value) {
    relationshipType.value = 'SINGLE'
  }
  // If UNION is selected but we no longer have multiple fields, reset to SINGLE
  if (relationshipType.value === 'UNION' && !hasMultipleFields.value) {
    relationshipType.value = 'SINGLE'
  }
}, { deep: true })

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
    
    // Check for template-generated SQL from multiple sources
    // 1. First check aiStore.recommendedExpression (set by template or AI)
    // 2. Then check sessionStorage as backup
    console.log('[Mapping Config V3] ========== CHECKING FOR TEMPLATE SQL ==========')
    const aiStoreSQL = aiStore.recommendedExpression
    const sessionSQL = sessionStorage.getItem('templateGeneratedSQL')
    console.log('[Mapping Config V3] aiStore.recommendedExpression:', aiStoreSQL)
    console.log('[Mapping Config V3] sessionStorage templateGeneratedSQL:', sessionSQL)
    
    const templateSQL = aiStoreSQL || sessionSQL
    
    if (templateSQL && templateSQL.trim()) {
      console.log('[Mapping Config V3] ✓ Using template-generated SQL:', templateSQL)
      sourceExpression.value = templateSQL
      
      // Clear sources
      sessionStorage.removeItem('templateGeneratedSQL')
      
      // Parse transformations from the SQL (updatePreview does this)
      updatePreview()
    } else {
      console.log('[Mapping Config V3] ✗ No template SQL found, generating default')
      // Generate default expression
      generateDefaultExpression()
    }
    console.log('[Mapping Config V3] Final sourceExpression.value:', sourceExpression.value)
    console.log('[Mapping Config V3] ========== END TEMPLATE SQL CHECK ==========')
    
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
  
  // Note: Quick transforms are now hardcoded, no database fetch needed
})

function initializeMetadata() {
  // Auto-populate metadata from source fields
  // Logical names (for display)
  const tables = [...new Set(sourceFields.value.map(f => f.src_table_name))]
  const columns = sourceFields.value.map(f => f.src_column_name)
  
  // Physical names (for database and restore)
  const tablesPhysical = [...new Set(sourceFields.value.map(f => f.src_table_physical_name || f.src_table_name))]
  const columnsPhysical = sourceFields.value.map(f => f.src_column_physical_name || f.src_column_name)
  
  // Use pipe delimiter for CSV-friendly export
  sourceTables.value = tables.join(' | ')
  sourceColumns.value = columns.join(' | ')
  sourceTablesPhysical.value = tablesPhysical.join(' | ')
  sourceColumnsPhysical.value = columnsPhysical.join(' | ')
  
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
  loadingPatterns.value = true
  console.log('[Mapping Config V3] ========== FETCHING HISTORICAL PATTERNS ==========')
  
  try {
    // Build search query from source fields
    const descriptions = sourceFields.value
      .map(f => f.src_comments || f.src_column_name)
      .join(' | ')
    
    console.log('[Mapping Config V3] Source fields for pattern search:', sourceFields.value.map(f => f.src_column_name))
    
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
      num_suggestions: 5  // Get more patterns
    })
    
    console.log('[Mapping Config V3] API Response:', response.data)
    
    // Extract historical patterns from response
    if (response.data?.historical_patterns) {
      historicalPatterns.value = response.data.historical_patterns
      console.log('[Mapping Config V3] ✓ Received', historicalPatterns.value.length, 'historical patterns')
      
      // Log details of each pattern
      historicalPatterns.value.forEach((p, i) => {
        console.log(`[Mapping Config V3] Pattern ${i + 1}:`, {
          target: p.tgt_column_name,
          type: p.source_relationship_type,
          transforms: p.transformations_applied,
          expression: p.source_expression?.substring(0, 50)
        })
      })
    } else {
      console.log('[Mapping Config V3] ✗ No historical_patterns in response')
    }
    
  } catch (e) {
    console.warn('[Mapping Config V3] Could not fetch historical patterns:', e)
  } finally {
    loadingPatterns.value = false
    console.log('[Mapping Config V3] ========== END FETCH PATTERNS ==========')
  }
}

function usePattern(pattern: any) {
  // Get current field names (not the old ones from the pattern!)
  const currentFields = sourceFields.value.map(f => f.src_column_physical_name || f.src_column_name)
  
  // Extract transformations from the pattern
  const transforms = pattern.transformations_applied?.split(',').map((t: string) => t.trim()) || []
  
  // Build new expression using CURRENT field names with the pattern's transformations
  let newExpression = ''
  
  if (currentFields.length === 1) {
    // Single field - apply transformations in order
    newExpression = currentFields[0]
    for (const transform of transforms.reverse()) {
      newExpression = `${transform}(${newExpression})`
    }
  } else if (pattern.source_relationship_type === 'JOIN') {
    // Multiple fields with JOIN - user needs to customize
    const fieldsStr = currentFields.join(', ')
    newExpression = `-- Apply ${transforms.join(', ')} to: ${fieldsStr}\n-- Customize the JOIN expression below:\nSELECT ${currentFields[0]}\nFROM ${sourceFields.value[0]?.src_table_physical_name || 'table1'}\nJOIN table2 ON condition`
  } else if (pattern.source_relationship_type === 'UNION') {
    // UNION pattern
    newExpression = currentFields.map((f, i) => `SELECT ${transforms.length > 0 ? `${transforms[0]}(${f})` : f} FROM table${i + 1}`).join('\nUNION ALL\n')
  } else {
    // Multiple fields - concatenate with transformations
    const transformedFields = currentFields.map(f => {
      let expr = f
      for (const transform of [...transforms].reverse()) {
        expr = `${transform}(${expr})`
      }
      return expr
    })
    newExpression = `CONCAT_WS(' ', ${transformedFields.join(', ')})`
  }
  
  sourceExpression.value = newExpression
  
  if (pattern.transformations_applied) {
    transformationsApplied.value = pattern.transformations_applied
  }
  if (pattern.source_relationship_type) {
    relationshipType.value = pattern.source_relationship_type
  }
  
  updatePreview()
  
  toast.add({
    severity: 'success',
    summary: 'Pattern Applied',
    detail: `Applied ${transforms.join(', ') || 'pattern'} to current fields`,
    life: 3000
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

function handleRelationshipChange() {
  // Validate the selection
  if (relationshipType.value === 'JOIN' && !hasMultipleTables.value) {
    relationshipType.value = 'SINGLE'
    toast.add({
      severity: 'warn',
      summary: 'Invalid Selection',
      detail: 'JOIN requires source fields from multiple tables',
      life: 3000
    })
    return
  }
  
  if (relationshipType.value === 'UNION' && !hasMultipleFields.value) {
    relationshipType.value = 'SINGLE'
    toast.add({
      severity: 'warn',
      summary: 'Invalid Selection',
      detail: 'UNION requires multiple source fields',
      life: 3000
    })
    return
  }
  
  console.log('[Mapping Config] Relationship type changed to:', relationshipType.value)
  
  // Update placeholder via computed
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
        datatype: f.src_physical_datatype,
        // CRITICAL: Pass physical names for SQL generation
        physical_table: f.src_table_physical_name || f.src_table_name,
        physical_column: f.src_column_physical_name || f.src_column_name,
        comments: f.src_comments
      })),
      {
        table: targetField.value?.tgt_table_name || '',
        column: targetField.value?.tgt_column_name || '',
        datatype: targetField.value?.tgt_physical_datatype || 'STRING',
        physical_table: targetField.value?.tgt_table_physical_name || targetField.value?.tgt_table_name || '',
        physical_column: targetField.value?.tgt_column_physical_name || targetField.value?.tgt_column_name || ''
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

// Known valid Databricks SQL functions
const VALID_SQL_FUNCTIONS = new Set([
  // String functions
  'TRIM', 'LTRIM', 'RTRIM', 'UPPER', 'LOWER', 'INITCAP', 'LENGTH', 'LEN',
  'CONCAT', 'CONCAT_WS', 'SUBSTRING', 'SUBSTR', 'LEFT', 'RIGHT',
  'REPLACE', 'REGEXP_REPLACE', 'REGEXP_EXTRACT', 'SPLIT', 'SPLIT_PART',
  'LPAD', 'RPAD', 'REVERSE', 'REPEAT', 'TRANSLATE', 'SOUNDEX',
  'ASCII', 'CHR', 'CHAR', 'INSTR', 'LOCATE', 'POSITION',
  'FORMAT_STRING', 'PRINTF', 'OVERLAY', 'LEVENSHTEIN',
  // Null handling
  'COALESCE', 'NVL', 'NVL2', 'NULLIF', 'IFNULL', 'ISNULL',
  // Type conversion
  'CAST', 'CONVERT', 'TRY_CAST', 'TO_CHAR', 'TO_NUMBER',
  // Date/Time functions
  'DATE', 'TO_DATE', 'DATE_FORMAT', 'DATE_ADD', 'DATE_SUB', 'DATEDIFF',
  'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND', 'DAYOFWEEK', 'DAYOFYEAR',
  'CURRENT_DATE', 'CURRENT_TIMESTAMP', 'NOW', 'GETDATE', 'SYSDATE',
  'TIMESTAMP', 'TO_TIMESTAMP', 'FROM_UNIXTIME', 'UNIX_TIMESTAMP',
  'ADD_MONTHS', 'MONTHS_BETWEEN', 'LAST_DAY', 'NEXT_DAY', 'TRUNC',
  'DATE_TRUNC', 'EXTRACT', 'DATEPART', 'TIMESTAMPADD', 'TIMESTAMPDIFF',
  // Numeric functions
  'ROUND', 'FLOOR', 'CEIL', 'CEILING', 'ABS', 'MOD', 'POWER', 'POW',
  'SQRT', 'EXP', 'LOG', 'LOG10', 'LN', 'SIGN', 'RAND', 'RANDOM',
  'GREATEST', 'LEAST', 'TRUNCATE',
  // Aggregate functions
  'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COLLECT_LIST', 'COLLECT_SET',
  'FIRST', 'LAST', 'STDDEV', 'VARIANCE', 'PERCENTILE', 'APPROX_COUNT_DISTINCT',
  // Conditional functions
  'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'IF', 'IIF', 'DECODE', 'NULLIF',
  // Array/Map functions
  'ARRAY', 'MAP', 'STRUCT', 'NAMED_STRUCT', 'SIZE', 'EXPLODE', 'POSEXPLODE',
  'ARRAY_CONTAINS', 'ELEMENT_AT', 'SLICE', 'SEQUENCE', 'FLATTEN',
  // Window functions
  'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'NTILE', 'LAG', 'LEAD',
  'FIRST_VALUE', 'LAST_VALUE', 'OVER', 'PARTITION', 'ORDER',
  // JSON functions
  'GET_JSON_OBJECT', 'JSON_TUPLE', 'TO_JSON', 'FROM_JSON', 'SCHEMA_OF_JSON',
  // Other
  'HASH', 'MD5', 'SHA1', 'SHA2', 'BASE64', 'UNBASE64', 'CRC32',
  'UUID', 'MONOTONICALLY_INCREASING_ID',
  // SQL keywords that might appear like functions
  'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER',
  'ON', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'UNION', 'ALL',
  'GROUP', 'BY', 'HAVING', 'ORDER', 'ASC', 'DESC', 'LIMIT', 'AS', 'DISTINCT'
])

// Common typos and their corrections
const COMMON_TYPOS: Record<string, string> = {
  'INITCA': 'INITCAP',
  'INTCAP': 'INITCAP',
  'INITCP': 'INITCAP',
  'INTICAP': 'INITCAP',
  'UPPPER': 'UPPER',
  'UPER': 'UPPER',
  'LOWWER': 'LOWER',
  'LOWEER': 'LOWER',
  'TRIN': 'TRIM',
  'TIRM': 'TRIM',
  'TRIIM': 'TRIM',
  'CONACT': 'CONCAT',
  'CONCATE': 'CONCAT',
  'COALESE': 'COALESCE',
  'COLASCE': 'COALESCE',
  'COLAESCE': 'COALESCE',
  'SUBSTING': 'SUBSTRING',
  'SUBSTRIG': 'SUBSTRING',
  'REPLCE': 'REPLACE',
  'RPLACE': 'REPLACE',
  'LENGHT': 'LENGTH',
  'LEGTH': 'LENGTH',
  'ROUNG': 'ROUND',
  'ROUD': 'ROUND',
}

// SQL Validation - checks for common syntax issues and invalid functions
function validateSQLExpression(sql: string): { valid: boolean; error?: string; warning?: string } {
  const trimmedSql = sql.trim()
  
  // Check for empty expression
  if (!trimmedSql) {
    return { valid: false, error: 'SQL expression cannot be empty' }
  }
  
  // Check for balanced parentheses
  let parenCount = 0
  for (const char of trimmedSql) {
    if (char === '(') parenCount++
    if (char === ')') parenCount--
    if (parenCount < 0) {
      return { valid: false, error: 'Unbalanced parentheses: extra closing parenthesis' }
    }
  }
  if (parenCount !== 0) {
    return { valid: false, error: 'Unbalanced parentheses: missing closing parenthesis' }
  }
  
  // Check for balanced quotes
  const singleQuotes = (trimmedSql.match(/'/g) || []).length
  if (singleQuotes % 2 !== 0) {
    return { valid: false, error: 'Unbalanced single quotes' }
  }
  
  // Check for common SQL injection patterns (basic)
  const dangerousPatterns = [/;\s*DROP/i, /;\s*DELETE/i, /;\s*TRUNCATE/i, /;\s*INSERT\s+INTO/i, /;\s*UPDATE\s+\w+\s+SET/i]
  for (const pattern of dangerousPatterns) {
    if (pattern.test(trimmedSql)) {
      return { valid: false, error: 'Expression contains potentially dangerous SQL commands' }
    }
  }
  
  // Extract all function-like patterns (word followed by parenthesis)
  const functionMatches = trimmedSql.match(/\b([A-Za-z_][A-Za-z0-9_]*)\s*\(/g) || []
  
  for (const match of functionMatches) {
    // Extract just the function name
    const fnName = match.replace(/\s*\($/, '').toUpperCase()
    
    // Skip if it looks like a table.column pattern or field name
    if (fnName.includes('.')) continue
    
    // Check for common typos first
    if (COMMON_TYPOS[fnName]) {
      return { 
        valid: false, 
        error: `Invalid function "${fnName}" - did you mean "${COMMON_TYPOS[fnName]}"?` 
      }
    }
    
    // Check if it's a known SQL function
    if (!VALID_SQL_FUNCTIONS.has(fnName)) {
      // Check for similar functions (Levenshtein-like match)
      const suggestions = Array.from(VALID_SQL_FUNCTIONS).filter(validFn => {
        // Simple similarity check: same first 2-3 letters
        return validFn.startsWith(fnName.substring(0, 2)) || 
               fnName.startsWith(validFn.substring(0, 2))
      }).slice(0, 3)
      
      if (suggestions.length > 0) {
        return { 
          valid: false, 
          error: `Unknown function "${fnName}" - did you mean: ${suggestions.join(', ')}?` 
        }
      }
      
      return { 
        valid: false, 
        error: `Unknown function "${fnName}" - please use valid Databricks SQL functions` 
      }
    }
  }
  
  // Check for empty function calls (except no-arg functions)
  const noArgFunctions = /CURRENT_TIMESTAMP|CURRENT_DATE|NOW|GETDATE|SYSDATE|UUID/i
  if (/\(\s*\)/.test(trimmedSql)) {
    // Find which function has empty args
    const emptyFnMatch = trimmedSql.match(/\b(\w+)\s*\(\s*\)/i)
    if (emptyFnMatch && !noArgFunctions.test(emptyFnMatch[1])) {
      return { valid: false, error: `Function ${emptyFnMatch[1]}() requires arguments` }
    }
  }
  
  // Check that known functions have proper syntax
  for (const fn of ['TRIM', 'UPPER', 'LOWER', 'INITCAP', 'CONCAT', 'COALESCE']) {
    const fnRegex = new RegExp(`\\b${fn}\\s*\\(`, 'i')
    if (fnRegex.test(trimmedSql)) {
      const fnWithArgs = new RegExp(`\\b${fn}\\s*\\([^)]+\\)`, 'i')
      if (!fnWithArgs.test(trimmedSql)) {
        return { valid: false, error: `${fn} function appears to be malformed - check syntax` }
      }
    }
  }
  
  console.log('[SQL Validation] Expression passed validation:', trimmedSql.substring(0, 100))
  
  return { valid: true }
}

// Reactive validation state
const sqlValidation = computed(() => {
  if (!sourceExpression.value.trim()) {
    return { valid: true, error: undefined } // Empty is ok until save
  }
  return validateSQLExpression(sourceExpression.value)
})

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
  
  // Validate SQL expression
  const validationResult = validateSQLExpression(sourceExpression.value)
  if (!validationResult.valid) {
    toast.add({
      severity: 'error',
      summary: 'SQL Validation Error',
      detail: validationResult.error,
      life: 5000
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
    
    // Build source datatypes (use pipe delimiter for CSV-friendly export)
    const datatypes = sourceFields.value
      .map(f => f.src_physical_datatype)
      .join(' | ')
    
    // Get domain from source fields (use first non-null domain)
    const sourceDomain = sourceFields.value
      .map(f => (f as any).domain)
      .find(d => d) || undefined
    
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
        source_tables_physical: sourceTablesPhysical.value || undefined,
        source_columns: sourceColumns.value || undefined,
        source_columns_physical: sourceColumnsPhysical.value || undefined,
        source_descriptions: descriptions || undefined,
        source_datatypes: datatypes || undefined,
        source_domain: sourceDomain,
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

.loading-patterns-content {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  color: var(--text-color-secondary);
  font-style: italic;
}

.patterns-hint {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  margin-bottom: 0.75rem;
  font-style: italic;
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
  border: 1px solid transparent;
}

.pattern-item:hover {
  background: var(--blue-50);
  transform: translateX(4px);
  border-color: var(--blue-300);
}

.pattern-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.pattern-target {
  font-weight: 600;
  color: var(--gainwell-primary);
}

.pattern-info {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.pattern-type {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  background: var(--surface-200);
  padding: 0.15rem 0.5rem;
  border-radius: 3px;
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

/* SQL Editor error state */
.sql-editor.sql-error {
  border-color: var(--red-500) !important;
  background-color: rgba(239, 68, 68, 0.05);
}

.sql-editor.sql-error:deep(textarea) {
  border-color: var(--red-500) !important;
}

/* SQL Validation Error Message */
.sql-validation-error {
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}

.sql-validation-error i {
  margin-right: 0.5rem;
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

