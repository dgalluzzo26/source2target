<template>
  <div class="pattern-template-card">
    <div class="template-header">
      <div class="template-icon">
        <i class="pi pi-lightbulb"></i>
      </div>
      <div class="template-title">
        <h3>Pattern Match Found!</h3>
        <p class="subtitle">Based on similar past mappings, this field is typically combined with other fields.</p>
      </div>
      <Tag :value="pattern.source_relationship_type || 'COMBINED'" severity="warning" />
    </div>

    <div class="template-body">
      <!-- Pattern Summary -->
      <div class="pattern-summary">
        <div class="pattern-target">
          <label>Target Field:</label>
          <strong>{{ pattern.tgt_table_name }}.{{ pattern.tgt_column_name }}</strong>
        </div>
        <div v-if="pattern.transformations_applied" class="pattern-transforms">
          <label>Transformations:</label>
          <code>{{ pattern.transformations_applied }}</code>
        </div>
      </div>

      <!-- Template Slots - Show what fields are typically combined -->
      <div class="template-slots">
        <h4>
          <i class="pi pi-puzzle-piece"></i>
          Source Fields for This Pattern
        </h4>
        
        <div class="slots-list">
          <!-- Already selected field (green checkmark) -->
          <div 
            v-for="(slot, idx) in templateSlots" 
            :key="idx"
            class="slot-item"
            :class="{ filled: slot.selectedField, empty: !slot.selectedField }"
          >
            <div class="slot-header">
              <span class="slot-number">#{{ idx + 1 }}</span>
              <span class="slot-label">{{ slot.label }}</span>
              <i v-if="slot.selectedField" class="pi pi-check-circle slot-status filled"></i>
              <i v-else class="pi pi-circle slot-status empty"></i>
            </div>
            
            <div class="slot-content">
              <!-- Already filled slot -->
              <div v-if="slot.selectedField" class="filled-slot">
                <Tag severity="success" :value="slot.selectedField.src_column_name" />
                <span class="table-ref">{{ slot.selectedField.src_table_name }}</span>
              </div>
              
              <!-- Empty slot - show matching candidates -->
              <div v-else class="empty-slot">
                <Dropdown
                  v-model="slot.selectedFieldId"
                  :options="getMatchingFieldsForSlot(slot)"
                  optionLabel="label"
                  optionValue="id"
                  placeholder="Select matching field..."
                  class="slot-dropdown"
                  :showClear="true"
                  filter
                  filterPlaceholder="Search fields..."
                  @change="handleSlotSelection(slot, $event.value)"
                >
                  <template #option="{ option }">
                    <div class="dropdown-option">
                      <div class="option-main">
                        <Tag :value="option.datatype" severity="info" size="small" />
                        <strong>{{ option.column }}</strong>
                      </div>
                      <div class="option-details">
                        <span class="option-table">{{ option.table }}</span>
                        <span v-if="option.description" class="option-desc">{{ truncate(option.description, 50) }}</span>
                      </div>
                      <div v-if="option.matchScore" class="option-match">
                        <Tag 
                          :value="`${Math.round(option.matchScore * 100)}% match`" 
                          :severity="option.matchScore > 0.7 ? 'success' : option.matchScore > 0.4 ? 'warning' : 'secondary'" 
                          size="small"
                        />
                      </div>
                    </div>
                  </template>
                </Dropdown>
                
                <!-- Best match suggestion -->
                <div v-if="getBestMatchForSlot(slot)" class="best-match-hint">
                  <i class="pi pi-sparkles"></i>
                  <span>Best match: <strong>{{ getBestMatchForSlot(slot)?.src_column_name }}</strong></span>
                  <Button 
                    label="Use" 
                    size="small" 
                    severity="success" 
                    text
                    @click="autoFillSlot(slot, getBestMatchForSlot(slot))"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- SQL Preview (if all slots filled) -->
      <div v-if="allSlotsFilled" class="sql-preview">
        <h4>
          <i class="pi pi-code"></i>
          Generated SQL Expression
        </h4>
        <pre><code>{{ generatedSQL }}</code></pre>
      </div>
    </div>

    <div class="template-footer">
      <div class="footer-info">
        <i class="pi pi-info-circle"></i>
        <span v-if="!allSlotsFilled">Fill all slots to apply this pattern</span>
        <span v-else>Ready to apply template with {{ filledSlotCount }} fields</span>
      </div>
      <div class="footer-actions">
        <Button 
          label="Skip Template" 
          severity="secondary" 
          text
          icon="pi pi-times"
          @click="$emit('skip')"
        />
        <Button 
          label="Apply Template" 
          severity="success"
          icon="pi pi-check"
          :disabled="!allSlotsFilled"
          @click="handleApplyTemplate"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import Tag from 'primevue/tag'
import Dropdown from 'primevue/dropdown'
import Button from 'primevue/button'
import type { UnmappedField } from '@/stores/unmappedFieldsStore'

interface HistoricalPattern {
  mapped_field_id?: number
  tgt_table_name: string
  tgt_column_name: string
  tgt_table_physical_name?: string
  tgt_column_physical_name?: string
  source_columns?: string
  source_tables?: string
  source_expression?: string
  source_relationship_type?: string
  transformations_applied?: string
  search_score?: number
}

interface TemplateSlot {
  label: string
  originalColumn: string
  originalTable?: string
  selectedField: UnmappedField | null
  selectedFieldId: number | null
}

interface Props {
  pattern: HistoricalPattern
  currentlySelectedFields: UnmappedField[]
  availableFields: UnmappedField[]
}

interface Emits {
  (e: 'skip'): void
  (e: 'apply', data: { 
    pattern: HistoricalPattern, 
    selectedFields: UnmappedField[],
    generatedSQL: string
  }): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Parse pattern to extract slot information
const templateSlots = ref<TemplateSlot[]>([])

function parsePatternSlots() {
  const slots: TemplateSlot[] = []
  
  // Get source columns from pattern
  const columnsStr = props.pattern.source_columns || ''
  const tablesStr = props.pattern.source_tables || ''
  
  // Parse columns - support both | and , delimiters
  const columns = columnsStr.split(/[|,]/).map(c => c.trim()).filter(c => c)
  const tables = tablesStr.split(/[|,]/).map(t => t.trim()).filter(t => t)
  
  // Create slots for each column in the pattern
  columns.forEach((col, idx) => {
    // Check if this column is already selected by the user
    const alreadySelected = props.currentlySelectedFields.find(
      f => matchesColumn(f, col, tables[idx])
    )
    
    // Generate a descriptive label from the column name
    const label = generateLabel(col)
    
    slots.push({
      label,
      originalColumn: col,
      originalTable: tables[idx] || '',
      selectedField: alreadySelected || null,
      selectedFieldId: alreadySelected?.id || null
    })
  })
  
  // If no columns parsed, create generic slots based on relationship type
  if (slots.length === 0 && props.pattern.source_relationship_type) {
    // Create slots for the currently selected field
    props.currentlySelectedFields.forEach((field, idx) => {
      slots.push({
        label: generateLabel(field.src_column_name),
        originalColumn: field.src_column_physical_name || field.src_column_name,
        originalTable: field.src_table_physical_name || field.src_table_name,
        selectedField: field,
        selectedFieldId: field.id
      })
    })
    
    // Add an empty slot for additional field
    slots.push({
      label: 'Additional Field',
      originalColumn: '',
      originalTable: '',
      selectedField: null,
      selectedFieldId: null
    })
  }
  
  templateSlots.value = slots
}

function matchesColumn(field: UnmappedField, column: string, table?: string): boolean {
  const fieldCol = (field.src_column_physical_name || field.src_column_name || '').toLowerCase()
  const fieldColDisplay = (field.src_column_name || '').toLowerCase()
  const colLower = column.toLowerCase()
  
  // Check exact or fuzzy match
  if (fieldCol === colLower || fieldColDisplay === colLower) return true
  
  // Check partial match (e.g., "street_num" matches "street_number")
  const fieldWords = fieldCol.split(/[_\s]+/)
  const colWords = colLower.split(/[_\s]+/)
  const commonWords = fieldWords.filter(w => colWords.some(cw => cw.includes(w) || w.includes(cw)))
  
  return commonWords.length >= Math.min(fieldWords.length, colWords.length) * 0.6
}

function generateLabel(column: string): string {
  // Convert column_name to "Column Name" style label
  return column
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace(/\s+/g, ' ')
    .trim() || 'Field'
}

// Get available fields that might match a slot
function getMatchingFieldsForSlot(slot: TemplateSlot) {
  const alreadySelectedIds = new Set(
    templateSlots.value
      .filter(s => s.selectedFieldId)
      .map(s => s.selectedFieldId)
  )
  
  return props.availableFields
    .filter(f => !alreadySelectedIds.has(f.id))
    .map(field => {
      const matchScore = calculateMatchScore(field, slot)
      return {
        id: field.id,
        column: field.src_column_name,
        table: field.src_table_name,
        datatype: field.src_physical_datatype,
        description: field.src_comments,
        label: `${field.src_table_name}.${field.src_column_name}`,
        matchScore,
        field
      }
    })
    .sort((a, b) => b.matchScore - a.matchScore)
}

function calculateMatchScore(field: UnmappedField, slot: TemplateSlot): number {
  let score = 0
  const fieldCol = (field.src_column_physical_name || field.src_column_name || '').toLowerCase()
  const slotCol = slot.originalColumn.toLowerCase()
  const slotLabel = slot.label.toLowerCase()
  
  // Exact match
  if (fieldCol === slotCol) return 1.0
  
  // Word overlap
  const fieldWords = new Set(fieldCol.split(/[_\s]+/))
  const slotWords = new Set(slotCol.split(/[_\s]+/).concat(slotLabel.split(/\s+/)))
  
  let overlap = 0
  fieldWords.forEach(w => {
    slotWords.forEach(sw => {
      if (w === sw) overlap += 1
      else if (w.includes(sw) || sw.includes(w)) overlap += 0.5
    })
  })
  
  score = Math.min(overlap / Math.max(fieldWords.size, slotWords.size), 0.9)
  
  // Boost if description contains relevant keywords
  const desc = (field.src_comments || '').toLowerCase()
  slotWords.forEach(sw => {
    if (desc.includes(sw)) score += 0.1
  })
  
  return Math.min(score, 0.99)
}

function getBestMatchForSlot(slot: TemplateSlot) {
  const matches = getMatchingFieldsForSlot(slot)
  const best = matches.find(m => m.matchScore > 0.4)
  return best?.field || null
}

function autoFillSlot(slot: TemplateSlot, field: UnmappedField | null) {
  if (!field) return
  slot.selectedField = field
  slot.selectedFieldId = field.id
}

function handleSlotSelection(slot: TemplateSlot, fieldId: number | null) {
  if (fieldId) {
    const field = props.availableFields.find(f => f.id === fieldId)
    slot.selectedField = field || null
  } else {
    slot.selectedField = null
  }
}

// Computed: Check if all slots are filled
const allSlotsFilled = computed(() => {
  return templateSlots.value.length > 0 && 
         templateSlots.value.every(slot => slot.selectedField !== null)
})

const filledSlotCount = computed(() => {
  return templateSlots.value.filter(s => s.selectedField).length
})

// Generate SQL based on filled slots and pattern transformations
const generatedSQL = computed(() => {
  if (!allSlotsFilled.value) return ''
  
  const transforms = props.pattern.transformations_applied || ''
  const fields = templateSlots.value.map(s => 
    s.selectedField?.src_column_physical_name || s.selectedField?.src_column_name || ''
  )
  
  // Parse transforms (e.g., "TRIM, INITCAP, CONCAT")
  const transformList = transforms.split(/[,\s]+/).map(t => t.trim().toUpperCase()).filter(t => t)
  
  // Build expression based on relationship type and transforms
  const relType = props.pattern.source_relationship_type?.toUpperCase() || 'SINGLE'
  
  if (relType === 'CONCAT' || transformList.includes('CONCAT') || fields.length > 1) {
    // Concatenation pattern
    const fieldExpressions = fields.map(f => {
      let expr = f
      // Apply transforms to each field
      transformList.filter(t => t !== 'CONCAT').forEach(t => {
        if (['TRIM', 'UPPER', 'LOWER', 'INITCAP'].includes(t)) {
          expr = `${t}(${expr})`
        }
      })
      return expr
    })
    return `CONCAT(${fieldExpressions.join(", ' ', ")})`
  } else {
    // Single field with transforms
    let expr = fields[0]
    transformList.forEach(t => {
      if (['TRIM', 'UPPER', 'LOWER', 'INITCAP', 'COALESCE'].includes(t)) {
        expr = `${t}(${expr})`
      }
    })
    return expr
  }
})

function truncate(str: string, maxLen: number): string {
  if (!str) return ''
  return str.length > maxLen ? str.substring(0, maxLen) + '...' : str
}

function handleApplyTemplate() {
  if (!allSlotsFilled.value) return
  
  const selectedFields = templateSlots.value
    .filter(s => s.selectedField)
    .map(s => s.selectedField as UnmappedField)
  
  emit('apply', {
    pattern: props.pattern,
    selectedFields,
    generatedSQL: generatedSQL.value
  })
}

// Initialize on mount and when pattern changes
onMounted(() => {
  parsePatternSlots()
})

watch(() => props.pattern, () => {
  parsePatternSlots()
}, { deep: true })

watch(() => props.currentlySelectedFields, () => {
  parsePatternSlots()
}, { deep: true })
</script>

<style scoped>
.pattern-template-card {
  background: linear-gradient(135deg, #fefce8, #fef9c3);
  border: 2px solid #facc15;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(250, 204, 21, 0.2);
}

.template-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
  background: linear-gradient(135deg, #fde047, #facc15);
  border-bottom: 1px solid #eab308;
}

.template-icon {
  width: 48px;
  height: 48px;
  background: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.template-icon i {
  font-size: 1.5rem;
  color: #ca8a04;
}

.template-title {
  flex: 1;
}

.template-title h3 {
  margin: 0;
  font-size: 1.25rem;
  color: #713f12;
}

.template-title .subtitle {
  margin: 0.25rem 0 0 0;
  font-size: 0.9rem;
  color: #854d0e;
}

.template-body {
  padding: 1.5rem;
}

.pattern-summary {
  display: flex;
  gap: 2rem;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.pattern-target,
.pattern-transforms {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.pattern-target label,
.pattern-transforms label {
  font-size: 0.8rem;
  color: #78716c;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.pattern-target strong {
  color: #292524;
  font-size: 1rem;
}

.pattern-transforms code {
  background: #f5f5f4;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.85rem;
  color: #ea580c;
}

.template-slots h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem 0;
  color: #44403c;
  font-size: 1rem;
}

.template-slots h4 i {
  color: #ca8a04;
}

.slots-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.slot-item {
  background: white;
  border-radius: 8px;
  border: 2px dashed #d6d3d1;
  overflow: hidden;
  transition: all 0.2s ease;
}

.slot-item.filled {
  border-style: solid;
  border-color: #22c55e;
  background: #f0fdf4;
}

.slot-item.empty:hover {
  border-color: #ca8a04;
}

.slot-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: #fafaf9;
  border-bottom: 1px solid #e7e5e4;
}

.slot-item.filled .slot-header {
  background: #dcfce7;
  border-bottom-color: #bbf7d0;
}

.slot-number {
  width: 24px;
  height: 24px;
  background: #78716c;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
}

.slot-item.filled .slot-number {
  background: #22c55e;
}

.slot-label {
  flex: 1;
  font-weight: 500;
  color: #44403c;
}

.slot-status {
  font-size: 1.25rem;
}

.slot-status.filled {
  color: #22c55e;
}

.slot-status.empty {
  color: #d6d3d1;
}

.slot-content {
  padding: 1rem;
}

.filled-slot {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.filled-slot .table-ref {
  color: #78716c;
  font-size: 0.85rem;
}

.empty-slot {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.slot-dropdown {
  width: 100%;
}

.dropdown-option {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.25rem 0;
}

.option-main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.option-details {
  display: flex;
  gap: 1rem;
  font-size: 0.8rem;
  color: #78716c;
  padding-left: 2rem;
}

.option-desc {
  color: #a8a29e;
  font-style: italic;
}

.option-match {
  padding-left: 2rem;
}

.best-match-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #fef9c3;
  border-radius: 6px;
  font-size: 0.85rem;
  color: #713f12;
}

.best-match-hint i {
  color: #ca8a04;
}

.sql-preview {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #1e1e1e;
  border-radius: 8px;
}

.sql-preview h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.75rem 0;
  color: #a3e635;
  font-size: 0.9rem;
}

.sql-preview pre {
  margin: 0;
  padding: 0.75rem;
  background: #292929;
  border-radius: 4px;
  overflow-x: auto;
}

.sql-preview code {
  color: #f0abfc;
  font-size: 0.9rem;
  font-family: 'Fira Code', 'Monaco', monospace;
}

.template-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: #fefce8;
  border-top: 1px solid #fde047;
}

.footer-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #854d0e;
  font-size: 0.9rem;
}

.footer-info i {
  color: #ca8a04;
}

.footer-actions {
  display: flex;
  gap: 0.75rem;
}

/* Responsive */
@media (max-width: 768px) {
  .pattern-summary {
    flex-direction: column;
    gap: 1rem;
  }
  
  .template-footer {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .footer-actions {
    justify-content: flex-end;
  }
}
</style>

