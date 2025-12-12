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

      <!-- JOIN Fields Section (for source-to-source joins) -->
      <div v-if="isSourceJoinPattern && joinFieldSlots.length > 0" class="join-fields-section">
        <h4>
          <i class="pi pi-link"></i>
          Join Fields Required
          <Tag :value="parsedJoinMetadata?.join_type || 'JOIN'" severity="warning" size="small" class="ml-2" />
        </h4>
        <p class="join-help-text">
          This pattern joins multiple source tables. Select the fields to use for each join condition.
        </p>
        
        <div class="join-conditions-list">
          <div 
            v-for="(cond, condIdx) in parsedJoinMetadata?.join_conditions || []" 
            :key="condIdx"
            class="join-condition-row"
          >
            <div class="join-condition-header">
              <Tag :value="`Join ${condIdx + 1}`" severity="secondary" size="small" />
              <span class="join-arrow">
                {{ cond.left_table }} <i class="pi pi-arrow-right"></i> {{ cond.right_table }}
              </span>
            </div>
            
            <div class="join-fields-row">
              <!-- Left side field -->
              <div class="join-field-slot">
                <label>{{ cond.left_table }}.{{ cond.left_column }}</label>
                <Dropdown
                  v-model="getJoinSlot(condIdx, 'left')!.selectedFieldId"
                  :options="getMatchingFieldsForJoinSlot(getJoinSlot(condIdx, 'left')!)"
                  optionLabel="label"
                  optionValue="id"
                  placeholder="Select join key..."
                  class="join-dropdown"
                  :showClear="true"
                  filter
                  @change="handleJoinFieldSelection(getJoinSlot(condIdx, 'left')!, $event.value)"
                >
                  <template #option="{ option }">
                    <div class="dropdown-option">
                      <div class="option-main">
                        <Tag :value="option.datatype" severity="info" size="small" />
                        <strong>{{ option.column }}</strong>
                      </div>
                      <div class="option-details">
                        <span class="option-table">{{ option.table }}</span>
                      </div>
                      <div v-if="option.matchScore > 0" class="option-match">
                        <Tag 
                          :value="`${Math.round(option.matchScore * 100)}%`" 
                          :severity="option.matchScore > 0.5 ? 'success' : 'secondary'" 
                          size="small"
                        />
                      </div>
                    </div>
                  </template>
                </Dropdown>
              </div>
              
              <div class="join-equals">=</div>
              
              <!-- Right side field -->
              <div class="join-field-slot">
                <label>{{ cond.right_table }}.{{ cond.right_column }}</label>
                <Dropdown
                  v-model="getJoinSlot(condIdx, 'right')!.selectedFieldId"
                  :options="getMatchingFieldsForJoinSlot(getJoinSlot(condIdx, 'right')!)"
                  optionLabel="label"
                  optionValue="id"
                  placeholder="Select join key..."
                  class="join-dropdown"
                  :showClear="true"
                  filter
                  @change="handleJoinFieldSelection(getJoinSlot(condIdx, 'right')!, $event.value)"
                >
                  <template #option="{ option }">
                    <div class="dropdown-option">
                      <div class="option-main">
                        <Tag :value="option.datatype" severity="info" size="small" />
                        <strong>{{ option.column }}</strong>
                      </div>
                      <div class="option-details">
                        <span class="option-table">{{ option.table }}</span>
                      </div>
                      <div v-if="option.matchScore > 0" class="option-match">
                        <Tag 
                          :value="`${Math.round(option.matchScore * 100)}%`" 
                          :severity="option.matchScore > 0.5 ? 'success' : 'secondary'" 
                          size="small"
                        />
                      </div>
                    </div>
                  </template>
                </Dropdown>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- SQL Preview (if all slots filled) -->
      <div v-if="allSlotsFilled && allJoinFieldsFilled" class="sql-preview">
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
        <span v-if="!allSlotsFilled">Fill all source field slots to apply this pattern</span>
        <span v-else-if="isSourceJoinPattern && !allJoinFieldsFilled">Select all join fields to apply this pattern</span>
        <span v-else>Ready to apply template with {{ filledSlotCount }} fields{{ isSourceJoinPattern ? ' + JOIN' : '' }}</span>
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
          :disabled="!allSlotsFilled || (isSourceJoinPattern && !allJoinFieldsFilled)"
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
  source_columns_physical?: string
  source_tables?: string
  source_tables_physical?: string
  source_expression?: string
  source_relationship_type?: string
  transformations_applied?: string
  search_score?: number
  join_metadata?: string  // JSON for source-to-source joins
}

// Parsed join metadata structure
interface JoinCondition {
  left_table: string
  left_alias: string
  left_column: string
  right_table: string
  right_alias: string
  right_column: string
}

interface ParsedJoinMetadata {
  is_source_join?: boolean
  join_type?: string
  source_tables?: string[]
  primary_table?: string
  join_conditions?: JoinCondition[]
  select_column?: { table: string; alias: string; column: string }
  select_columns?: { table: string; alias: string; column: string }[]
  default_value?: string
}

// Join field selection for user input
interface JoinFieldSlot {
  joinIndex: number
  side: 'left' | 'right'
  tableName: string
  originalColumn: string  // From the pattern
  selectedField: UnmappedField | null
  selectedFieldId: number | null
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

// Join field slots for source-to-source joins
const joinFieldSlots = ref<JoinFieldSlot[]>([])

// Parse join_metadata JSON
const parsedJoinMetadata = computed((): ParsedJoinMetadata | null => {
  if (!props.pattern.join_metadata) return null
  try {
    return JSON.parse(props.pattern.join_metadata)
  } catch (e) {
    console.error('[PatternTemplate] Failed to parse join_metadata:', e)
    return null
  }
})

// Is this a source-to-source join pattern?
const isSourceJoinPattern = computed(() => {
  return parsedJoinMetadata.value?.is_source_join === true
})

// Get the tables involved in the join
const joinTables = computed(() => {
  return parsedJoinMetadata.value?.source_tables || []
})

// Check if all join fields are filled
const allJoinFieldsFilled = computed(() => {
  if (!isSourceJoinPattern.value) return true
  return joinFieldSlots.value.every(slot => slot.selectedField !== null)
})

// Initialize join field slots from join_metadata
function parseJoinFieldSlots() {
  const slots: JoinFieldSlot[] = []
  const metadata = parsedJoinMetadata.value
  
  if (!metadata?.is_source_join || !metadata.join_conditions) {
    joinFieldSlots.value = []
    return
  }
  
  console.log('[PatternTemplate] Parsing JOIN conditions:', metadata.join_conditions)
  
  metadata.join_conditions.forEach((cond, idx) => {
    // Left side of join (e.g., employees.title_cd)
    slots.push({
      joinIndex: idx,
      side: 'left',
      tableName: cond.left_table,
      originalColumn: cond.left_column,
      selectedField: null,
      selectedFieldId: null
    })
    
    // Right side of join (e.g., title_ref.title_cd)
    slots.push({
      joinIndex: idx,
      side: 'right',
      tableName: cond.right_table,
      originalColumn: cond.right_column,
      selectedField: null,
      selectedFieldId: null
    })
  })
  
  // Try to auto-match join fields from available fields
  slots.forEach(slot => {
    const bestMatch = findBestJoinFieldMatch(slot)
    if (bestMatch && bestMatch.matchScore > 0.5) {
      slot.selectedField = bestMatch.field
      slot.selectedFieldId = bestMatch.field.id
      console.log('[PatternTemplate] Auto-matched join field:', slot.originalColumn, '->', bestMatch.field.src_column_name)
    }
  })
  
  joinFieldSlots.value = slots
}

// Find best matching field for a join slot
function findBestJoinFieldMatch(slot: JoinFieldSlot): { field: UnmappedField; matchScore: number } | null {
  let bestMatch: { field: UnmappedField; matchScore: number } | null = null
  
  for (const field of props.availableFields) {
    const score = calculateJoinFieldMatchScore(field, slot)
    if (score > (bestMatch?.matchScore || 0)) {
      bestMatch = { field, matchScore: score }
    }
  }
  
  return bestMatch
}

// Calculate match score for a field against a join slot
function calculateJoinFieldMatchScore(field: UnmappedField, slot: JoinFieldSlot): number {
  let score = 0
  
  const fieldCol = (field.src_column_physical_name || field.src_column_name || '').toLowerCase()
  const fieldTable = (field.src_table_physical_name || field.src_table_name || '').toLowerCase()
  const slotCol = slot.originalColumn.toLowerCase()
  const slotTable = slot.tableName.toLowerCase()
  
  // Exact column match
  if (fieldCol === slotCol) score += 0.5
  // Partial column match
  else if (fieldCol.includes(slotCol) || slotCol.includes(fieldCol)) score += 0.3
  
  // Table name match (soft signal)
  if (fieldTable === slotTable) score += 0.3
  else if (fieldTable.includes(slotTable) || slotTable.includes(fieldTable)) score += 0.1
  
  // Check for common join key patterns
  const joinKeyPatterns = ['_id', '_key', '_sk', '_cd', '_code', 'id_']
  if (joinKeyPatterns.some(p => fieldCol.includes(p) && slotCol.includes(p))) {
    score += 0.2
  }
  
  return Math.min(score, 1)
}

// Get matching fields for a join slot dropdown
function getMatchingFieldsForJoinSlot(slot: JoinFieldSlot) {
  return props.availableFields
    .map(f => {
      const score = calculateJoinFieldMatchScore(f, slot)
      return {
        id: f.id,
        label: `${f.src_column_name} (${f.src_table_name})`,
        column: f.src_column_name,
        table: f.src_table_name,
        datatype: f.src_physical_datatype,
        description: f.src_comments,
        matchScore: score,
        field: f
      }
    })
    .sort((a, b) => b.matchScore - a.matchScore)
}

// Handle join field selection
function handleJoinFieldSelection(slot: JoinFieldSlot, fieldId: number | null) {
  if (fieldId === null) {
    slot.selectedField = null
    return
  }
  
  const field = props.availableFields.find(f => f.id === fieldId)
  slot.selectedField = field || null
}

// Get a specific join slot by index and side
function getJoinSlot(condIdx: number, side: 'left' | 'right'): JoinFieldSlot | undefined {
  return joinFieldSlots.value.find(s => s.joinIndex === condIdx && s.side === side)
}

function parsePatternSlots() {
  const slots: TemplateSlot[] = []
  
  console.log('[PatternTemplate] Parsing slots for pattern:', props.pattern.tgt_column_name)
  console.log('[PatternTemplate] Currently selected fields:', props.currentlySelectedFields.map(f => f.src_column_name))
  
  // Get source columns from pattern
  const columnsStr = props.pattern.source_columns || ''
  const tablesStr = props.pattern.source_tables || ''
  
  // Parse columns - support both | and , delimiters
  let columns = columnsStr.split(/[|,]/).map(c => c.trim()).filter(c => c)
  const tables = tablesStr.split(/[|,]/).map(t => t.trim()).filter(t => t)
  
  console.log('[PatternTemplate] Pattern columns from history:', columns)
  
  // Track which currently-selected fields have been assigned to slots
  const assignedFieldIds = new Set<number>()
  
  // If pattern has columns defined, create slots for ONLY those columns
  // Try to match user's selected fields to each pattern slot
  if (columns.length > 0) {
    // SPECIAL CASE: For SINGLE field patterns with 1 slot and user has 1 selected field,
    // auto-assign the user's field regardless of name matching - they already chose what to map!
    const isSingleMapping = columns.length === 1 && props.currentlySelectedFields.length === 1
    const relationshipType = props.pattern.source_relationship_type?.toUpperCase() || ''
    const isSinglePattern = isSingleMapping || relationshipType === 'SINGLE'
    
    columns.forEach((col, idx) => {
      let alreadySelected: UnmappedField | undefined
      
      // For single-field patterns: use the user's selected field directly
      if (isSinglePattern && columns.length === 1 && props.currentlySelectedFields.length >= 1) {
        alreadySelected = props.currentlySelectedFields[0]
        console.log('[PatternTemplate] SINGLE pattern - auto-assigning user selected field:', alreadySelected.src_column_name)
      } else {
        // For multi-field patterns: try to match currently selected fields to this slot
        // Use broader matching to catch variations like "street_num" vs "Street Number"
        alreadySelected = props.currentlySelectedFields.find(
          f => !assignedFieldIds.has(f.id) && matchesColumn(f, col, tables[idx])
        )
      }
      
      if (alreadySelected) {
        assignedFieldIds.add(alreadySelected.id)
        console.log('[PatternTemplate] Matched user field', alreadySelected.src_column_name, 'to pattern slot', col)
      }
      
      const label = generateLabel(col)
      
      slots.push({
        label,
        originalColumn: col,
        originalTable: tables[idx] || '',
        selectedField: alreadySelected || null,
        selectedFieldId: alreadySelected?.id || null
      })
    })
    
    // DON'T add extra slots for unmatched selected fields - they might just not match
    // the pattern column names exactly. The user can select them in the empty slots.
  } else {
    // No pattern columns - create generic slots
    // First slot: the user's currently selected field
    props.currentlySelectedFields.forEach((field) => {
      slots.push({
        label: generateLabel(field.src_column_name),
        originalColumn: field.src_column_physical_name || field.src_column_name,
        originalTable: field.src_table_physical_name || field.src_table_name,
        selectedField: field,
        selectedFieldId: field.id
      })
      assignedFieldIds.add(field.id)
    })
    
    // Add one empty slot for the additional field
    slots.push({
      label: 'Additional Field',
      originalColumn: '',
      originalTable: '',
      selectedField: null,
      selectedFieldId: null
    })
  }
  
  console.log('[PatternTemplate] Created', slots.length, 'slots:', slots.map(s => ({
    label: s.label,
    filled: !!s.selectedField,
    fieldName: s.selectedField?.src_column_name
  })))
  
  templateSlots.value = slots
}

function matchesColumn(field: UnmappedField, column: string, table?: string): boolean {
  const fieldCol = (field.src_column_physical_name || field.src_column_name || '').toLowerCase()
  const fieldColDisplay = (field.src_column_name || '').toLowerCase()
  const colLower = column.toLowerCase()
  
  // Check exact match
  if (fieldCol === colLower || fieldColDisplay === colLower) {
    console.log('[PatternTemplate] Exact match:', fieldCol, '===', colLower)
    return true
  }
  
  // Normalize: remove underscores, spaces, and common abbreviations
  const normalize = (s: string) => s
    .replace(/[_\s-]+/g, '')  // Remove separators
    .replace(/number/g, 'num')  // Normalize abbreviations
    .replace(/street/g, 'st')
    .replace(/address/g, 'addr')
    .replace(/name/g, 'nm')
  
  const normalizedField = normalize(fieldCol)
  const normalizedCol = normalize(colLower)
  
  if (normalizedField === normalizedCol) {
    console.log('[PatternTemplate] Normalized match:', fieldCol, '~', colLower)
    return true
  }
  
  // Check word overlap (e.g., "street_num" vs "street_number")
  const fieldWords = fieldCol.split(/[_\s]+/).filter(w => w.length > 1)
  const colWords = colLower.split(/[_\s]+/).filter(w => w.length > 1)
  
  // Count matching words (with partial matching)
  let matchScore = 0
  for (const fw of fieldWords) {
    for (const cw of colWords) {
      if (fw === cw) {
        matchScore += 1
      } else if (fw.includes(cw) || cw.includes(fw)) {
        matchScore += 0.8  // Partial match (num vs number)
      } else if (fw.substring(0, 3) === cw.substring(0, 3) && fw.length > 2 && cw.length > 2) {
        matchScore += 0.5  // Same prefix (str vs street)
      }
    }
  }
  
  const maxWords = Math.max(fieldWords.length, colWords.length)
  const matchRatio = maxWords > 0 ? matchScore / maxWords : 0
  
  if (matchRatio >= 0.5) {
    console.log('[PatternTemplate] Word overlap match:', fieldCol, '~', colLower, 'ratio:', matchRatio.toFixed(2))
    return true
  }
  
  return false
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
function buildSQLExpression(): string {
  // Check for source-to-source JOIN pattern
  if (isSourceJoinPattern.value && allJoinFieldsFilled.value) {
    return buildJoinSQL()
  }
  
  // Get all filled fields (use physical names for SQL)
  const filledSlots = templateSlots.value.filter(s => s.selectedField)
  
  console.log('[PatternTemplate] ========== BUILDING SQL ==========')
  console.log('[PatternTemplate] Filled slots count:', filledSlots.length)
  console.log('[PatternTemplate] All slots:', templateSlots.value.map(s => ({
    label: s.label,
    hasFilled: !!s.selectedField,
    selectedFieldId: s.selectedFieldId
  })))
  
  if (filledSlots.length === 0) {
    console.log('[PatternTemplate] ERROR: No filled slots!')
    return ''
  }
  
  // Debug: log full field objects
  filledSlots.forEach((s, i) => {
    console.log(`[PatternTemplate] Slot ${i} field:`, JSON.stringify(s.selectedField, null, 2))
  })
  
  // Get field names - try multiple properties
  const fields: string[] = []
  
  for (const slot of filledSlots) {
    const field = slot.selectedField
    if (!field) continue
    
    // Try to get the column name from various sources
    let colName = ''
    
    // Check common property names
    if (field.src_column_physical_name && field.src_column_physical_name.trim()) {
      colName = field.src_column_physical_name.trim()
    } else if (field.src_column_name && field.src_column_name.trim()) {
      colName = field.src_column_name.trim()
    } else if ((field as any).column_name) {
      colName = (field as any).column_name
    } else if ((field as any).columnName) {
      colName = (field as any).columnName
    } else if ((field as any).name) {
      colName = (field as any).name
    }
    
    // Normalize: lowercase and replace spaces with underscores
    if (colName) {
      colName = colName.toLowerCase().replace(/\s+/g, '_')
      fields.push(colName)
      console.log(`[PatternTemplate] Found field name: ${colName}`)
    } else {
      // Ultimate fallback: use the slot label
      const fallback = slot.label.toLowerCase().replace(/\s+/g, '_')
      fields.push(fallback)
      console.log(`[PatternTemplate] Using slot label as fallback: ${fallback}`)
    }
  }
  
  console.log('[PatternTemplate] Final field names for SQL:', fields)
  
  if (fields.length === 0) {
    console.log('[PatternTemplate] ERROR: Could not extract any field names!')
    return ''
  }
  
  const sql = buildSQLForFields(fields)
  console.log('[PatternTemplate] Generated SQL:', sql)
  console.log('[PatternTemplate] ========== END BUILDING SQL ==========')
  
  return sql
}

function buildSQLForFields(fields: string[]): string {
  const transforms = props.pattern.transformations_applied || ''
  console.log('[PatternTemplate] Pattern transforms:', transforms)
  console.log('[PatternTemplate] Pattern expression:', props.pattern.source_expression)
  console.log('[PatternTemplate] New fields to use:', fields)
  
  // If pattern has a source_expression, try to adapt it to the new field names
  if (props.pattern.source_expression && props.pattern.source_columns) {
    let adaptedSQL = props.pattern.source_expression
    // Try physical names first (used in SQL expressions), fallback to display names
    const oldColumnsPhysical = props.pattern.source_columns_physical || props.pattern.source_columns || ''
    const oldColumns = oldColumnsPhysical.split(/[|,]/).map(c => c.trim()).filter(c => c)
    const oldTablesPhysical = props.pattern.source_tables_physical || props.pattern.source_tables || ''
    const oldTables = oldTablesPhysical.split(/[|,]/).map(t => t.trim()).filter(t => t)
    
    console.log('[PatternTemplate] Old columns:', oldColumns)
    console.log('[PatternTemplate] Old tables:', oldTables)
    
    // Get the new table names from the selected fields
    const newTables = templateSlots.value
      .filter(s => s.selectedField)
      .map(s => (s.selectedField?.src_table_physical_name || s.selectedField?.src_table_name || '').toLowerCase().replace(/\s+/g, '_'))
    
    console.log('[PatternTemplate] New tables:', newTables)
    
    oldColumns.forEach((oldCol, idx) => {
      if (fields[idx]) {
        const newCol = fields[idx]
        const oldTable = oldTables[Math.min(idx, oldTables.length - 1)] || ''
        const newTable = newTables[idx] || newTables[0] || ''
        
        // First, replace table-qualified names (table.column -> new_table.new_column)
        if (oldTable) {
          const tableQualifiedRegex = new RegExp(`\\b${escapeRegex(oldTable)}\\.${escapeRegex(oldCol)}\\b`, 'gi')
          const newQualified = newTable ? `${newTable}.${newCol}` : newCol
          adaptedSQL = adaptedSQL.replace(tableQualifiedRegex, newQualified)
          console.log(`[PatternTemplate] Replacing ${oldTable}.${oldCol} with ${newQualified}`)
        }
        
        // Then, replace any remaining unqualified column names
        const unqualifiedRegex = new RegExp(`\\b${escapeRegex(oldCol)}\\b`, 'gi')
        adaptedSQL = adaptedSQL.replace(unqualifiedRegex, newCol)
        console.log(`[PatternTemplate] Replacing ${oldCol} with ${newCol}`)
      }
    })
    
    console.log('[PatternTemplate] Adapted SQL from pattern:', adaptedSQL)
    return adaptedSQL
  }
  
  // Parse transforms (e.g., "TRIM, INITCAP, CONCAT")
  const transformList = transforms.split(/[,\s]+/).map(t => t.trim().toUpperCase()).filter(t => t)
  
  // Determine relationship type
  const relType = props.pattern.source_relationship_type?.toUpperCase() || 'SINGLE'
  
  // Multi-field: use CONCAT with transforms applied to each field
  if (relType === 'CONCAT' || transformList.includes('CONCAT') || fields.length > 1) {
    const fieldExpressions = fields.map(f => {
      let expr = f
      // Apply each transform (except CONCAT itself) - default to TRIM if none specified
      const appliedTransforms = transformList.filter(t => t !== 'CONCAT')
      if (appliedTransforms.length === 0) {
        expr = `TRIM(${expr})`
      } else {
        appliedTransforms.forEach(t => {
          if (['TRIM', 'UPPER', 'LOWER', 'INITCAP'].includes(t)) {
            expr = `${t}(${expr})`
          }
        })
      }
      return expr
    })
    
    // Use CONCAT_WS for cleaner syntax with separator
    const sql = `CONCAT_WS(' ', ${fieldExpressions.join(', ')})`
    console.log('[PatternTemplate] Generated CONCAT SQL:', sql)
    return sql
  } else {
    // Single field with transforms
    let expr = fields[0]
    
    // If no transforms specified, apply TRIM as default for strings
    if (transformList.length === 0) {
      expr = `TRIM(${expr})`
    } else {
      transformList.forEach(t => {
        if (['TRIM', 'UPPER', 'LOWER', 'INITCAP', 'COALESCE'].includes(t)) {
          expr = `${t}(${expr})`
        }
      })
    }
    console.log('[PatternTemplate] Generated single field SQL:', expr)
    return expr
  }
}

// Build SQL for source-to-source JOIN patterns
function buildJoinSQL(): string {
  const metadata = parsedJoinMetadata.value
  if (!metadata || !metadata.join_conditions) return ''
  
  console.log('[PatternTemplate] ========== BUILDING JOIN SQL ==========')
  
  // Get the first (primary) table from slots
  const primarySlot = templateSlots.value.find(s => s.selectedField)
  const primaryTable = primarySlot?.selectedField?.src_table_physical_name || 
                       primarySlot?.selectedField?.src_table_name || 'source_table'
  const primaryAlias = 'a'
  
  // Get the selected field for the SELECT clause
  const selectField = primarySlot?.selectedField
  let selectColumn = selectField?.src_column_physical_name || selectField?.src_column_name || 'column'
  
  // If pattern has a specific select column from a lookup table, use that
  if (metadata.select_column) {
    // Find the join slot for the right side of first join
    const lookupSlot = getJoinSlot(0, 'right')
    const lookupTable = lookupSlot?.selectedField?.src_table_physical_name || 
                        lookupSlot?.selectedField?.src_table_name || metadata.select_column.table
    const lookupAlias = 'b'
    
    // Find the actual column to select from the lookup table
    // We need to find an unmapped field from the lookup table that matches the select pattern
    const lookupField = props.availableFields.find(f => 
      (f.src_table_physical_name || f.src_table_name || '').toLowerCase() === lookupTable.toLowerCase() &&
      !joinFieldSlots.value.some(js => js.selectedField?.id === f.id) // Not used as join key
    )
    
    selectColumn = lookupField 
      ? `${lookupAlias}.${lookupField.src_column_physical_name || lookupField.src_column_name}`
      : `${lookupAlias}.${metadata.select_column.column}`
  }
  
  // Build the JOIN clauses
  const joinClauses: string[] = []
  let tableAliasMap: { [key: string]: string } = { [primaryTable.toLowerCase()]: primaryAlias }
  let aliasCounter = 1  // Start with 'b' for first join
  
  metadata.join_conditions.forEach((cond, idx) => {
    const leftSlot = getJoinSlot(idx, 'left')
    const rightSlot = getJoinSlot(idx, 'right')
    
    if (!leftSlot?.selectedField || !rightSlot?.selectedField) return
    
    const leftTable = leftSlot.selectedField.src_table_physical_name || 
                      leftSlot.selectedField.src_table_name || ''
    const leftCol = leftSlot.selectedField.src_column_physical_name || 
                    leftSlot.selectedField.src_column_name || ''
    
    const rightTable = rightSlot.selectedField.src_table_physical_name || 
                       rightSlot.selectedField.src_table_name || ''
    const rightCol = rightSlot.selectedField.src_column_physical_name || 
                     rightSlot.selectedField.src_column_name || ''
    
    // Assign alias for right table if not already assigned
    if (!tableAliasMap[rightTable.toLowerCase()]) {
      tableAliasMap[rightTable.toLowerCase()] = String.fromCharCode(97 + aliasCounter) // 'b', 'c', 'd', etc.
      aliasCounter++
    }
    
    const leftAlias = tableAliasMap[leftTable.toLowerCase()] || primaryAlias
    const rightAlias = tableAliasMap[rightTable.toLowerCase()]
    
    const joinType = metadata.join_type || 'LEFT'
    joinClauses.push(
      `${joinType} JOIN ${rightTable} ${rightAlias} ON ${leftAlias}.${leftCol} = ${rightAlias}.${rightCol}`
    )
  })
  
  // Apply transforms to select column if specified
  const transforms = props.pattern.transformations_applied || ''
  const transformList = transforms.split(/[,\s]+/).map(t => t.trim().toUpperCase()).filter(t => t)
  
  let selectExpr = selectColumn
  
  // Check for COALESCE with default value
  if (transformList.includes('COALESCE') && metadata.default_value) {
    selectExpr = `COALESCE(${selectExpr}, '${metadata.default_value}')`
  }
  
  // Apply other transforms
  transformList.filter(t => !['COALESCE', 'LOOKUP', 'JOIN'].includes(t)).forEach(t => {
    if (['TRIM', 'UPPER', 'LOWER', 'INITCAP'].includes(t)) {
      selectExpr = `${t}(${selectExpr})`
    }
  })
  
  // Get target column name
  const targetCol = props.pattern.tgt_column_physical_name || props.pattern.tgt_column_name || 'target'
  
  // Build final SQL
  const sql = `SELECT ${selectExpr} AS ${targetCol}\nFROM ${primaryTable} ${primaryAlias}\n${joinClauses.join('\n')}`
  
  console.log('[PatternTemplate] Generated JOIN SQL:', sql)
  console.log('[PatternTemplate] ========== END JOIN SQL ==========')
  
  return sql
}

// Helper to escape regex special characters
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// Computed for display (preview)
const generatedSQL = computed(() => {
  if (!allSlotsFilled.value) return ''
  return buildSQLExpression()
})

function truncate(str: string, maxLen: number): string {
  if (!str) return ''
  return str.length > maxLen ? str.substring(0, maxLen) + '...' : str
}

function handleApplyTemplate() {
  if (!allSlotsFilled.value) {
    console.log('[PatternTemplate] Cannot apply - not all slots filled')
    return
  }
  
  const selectedFields = templateSlots.value
    .filter(s => s.selectedField)
    .map(s => s.selectedField as UnmappedField)
  
  // Build SQL expression directly (don't rely on computed)
  const sql = buildSQLExpression()
  
  console.log('[PatternTemplate] === Applying Template ===')
  console.log('[PatternTemplate] Selected fields:', selectedFields.map(f => f.src_column_name))
  console.log('[PatternTemplate] Generated SQL:', sql)
  
  emit('apply', {
    pattern: props.pattern,
    selectedFields,
    generatedSQL: sql
  })
}

// Initialize on mount and when pattern changes
onMounted(() => {
  parsePatternSlots()
  parseJoinFieldSlots()
})

watch(() => props.pattern, () => {
  parsePatternSlots()
  parseJoinFieldSlots()
}, { deep: true })

watch(() => props.currentlySelectedFields, () => {
  parsePatternSlots()
  parseJoinFieldSlots()
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

/* Join Fields Section */
.join-fields-section {
  padding: 1rem;
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  border-radius: 8px;
  border: 1px solid #f59e0b;
}

.join-fields-section h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.5rem 0;
  color: #92400e;
  font-size: 0.95rem;
}

.join-fields-section h4 i {
  color: #f59e0b;
}

.join-help-text {
  font-size: 0.85rem;
  color: #78350f;
  margin-bottom: 1rem;
}

.join-conditions-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.join-condition-row {
  background: rgba(255, 255, 255, 0.8);
  border-radius: 6px;
  padding: 0.75rem;
}

.join-condition-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.join-arrow {
  font-size: 0.85rem;
  color: #92400e;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.join-arrow i {
  font-size: 0.75rem;
}

.join-fields-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.join-field-slot {
  flex: 1;
}

.join-field-slot label {
  display: block;
  font-size: 0.75rem;
  color: #78350f;
  margin-bottom: 0.25rem;
  font-family: 'JetBrains Mono', monospace;
}

.join-dropdown {
  width: 100%;
}

.join-equals {
  font-weight: bold;
  color: #92400e;
  padding: 0 0.5rem;
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

