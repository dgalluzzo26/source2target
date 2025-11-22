<template>
  <div class="join-configurator">
    <Message severity="info" :closable="false" class="info-message">
      <i class="pi pi-info-circle"></i>
      <strong>Join Configuration Required:</strong> Your selected fields come from {{ uniqueTables.length }} different tables.
      Please define how these tables should be joined to create the transformation query.
    </Message>

    <div class="tables-summary">
      <h4>
        <i class="pi pi-table"></i>
        Tables Involved
      </h4>
      <div class="table-list">
        <Tag 
          v-for="(table, idx) in uniqueTables" 
          :key="table"
          :value="`${idx + 1}. ${table}`"
          severity="info"
          icon="pi pi-database"
        />
      </div>
    </div>

    <Divider />

    <div class="joins-section">
      <div class="section-header">
        <h4>
          <i class="pi pi-link"></i>
          Join Definitions
        </h4>
        <Button 
          label="Add Join" 
          icon="pi pi-plus" 
          size="small"
          @click="addJoin"
        />
      </div>

      <Message v-if="localJoins.length === 0" severity="warn" :closable="false">
        No joins defined yet. Click "Add Join" to define how tables should be joined.
      </Message>

      <div v-for="(join, index) in localJoins" :key="index" class="join-item">
        <Card>
          <template #title>
            <div class="join-header">
              <span>Join {{ index + 1 }}</span>
              <Button 
                icon="pi pi-trash" 
                severity="danger" 
                text 
                size="small"
                @click="removeJoin(index)"
              />
            </div>
          </template>
          <template #content>
            <div class="join-config-grid">
              <!-- Left Table -->
              <div class="join-side">
                <label>Left Table</label>
                <Dropdown 
                  v-model="join.left_table_name" 
                  :options="uniqueTables"
                  placeholder="Select left table"
                  @change="onTableChange(join, 'left')"
                  class="w-full"
                />
              </div>

              <!-- Left Column -->
              <div class="join-side">
                <label>Left Join Column</label>
                <Dropdown 
                  v-model="join.left_join_column" 
                  :options="getColumnsForTable(join.left_table_name)"
                  placeholder="Select join column"
                  :disabled="!join.left_table_name"
                  class="w-full"
                />
              </div>

              <!-- Join Type -->
              <div class="join-type">
                <label>Join Type</label>
                <Dropdown 
                  v-model="join.join_type" 
                  :options="joinTypes"
                  class="w-full"
                />
              </div>

              <!-- Right Table -->
              <div class="join-side">
                <label>Right Table</label>
                <Dropdown 
                  v-model="join.right_table_name" 
                  :options="uniqueTables.filter(t => t !== join.left_table_name)"
                  placeholder="Select right table"
                  @change="onTableChange(join, 'right')"
                  class="w-full"
                />
              </div>

              <!-- Right Column -->
              <div class="join-side">
                <label>Right Join Column</label>
                <Dropdown 
                  v-model="join.right_join_column" 
                  :options="getColumnsForTable(join.right_table_name)"
                  placeholder="Select join column"
                  :disabled="!join.right_table_name"
                  class="w-full"
                />
              </div>
            </div>

            <!-- SQL Preview -->
            <div v-if="join.left_table_name && join.left_join_column && join.right_table_name && join.right_join_column" class="sql-preview">
              <label>SQL Preview:</label>
              <code>{{ getJoinSQL(join) }}</code>
            </div>
          </template>
        </Card>
      </div>
    </div>

    <Divider />

    <div class="full-sql-preview">
      <h4>
        <i class="pi pi-code"></i>
        Complete JOIN Query Preview
      </h4>
      <Message v-if="localJoins.length === 0" severity="info" :closable="false">
        Define at least one join to see the complete query preview.
      </Message>
      <pre v-else class="sql-code">{{ getFullJoinSQL() }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import Message from 'primevue/message'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Dropdown from 'primevue/dropdown'
import Divider from 'primevue/divider'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'

interface SourceField {
  src_table_name: string
  src_table_physical_name: string
  src_column_name: string
  src_column_physical_name: string
}

interface JoinDefinition {
  left_table_name: string
  left_table_physical_name: string
  left_join_column: string
  right_table_name: string
  right_table_physical_name: string
  right_join_column: string
  join_type: 'INNER' | 'LEFT' | 'RIGHT' | 'FULL'
  join_order: number
}

const props = defineProps<{
  sourceFields: SourceField[]
  joins: JoinDefinition[]
}>()

const emit = defineEmits<{
  (e: 'update:joins', joins: JoinDefinition[]): void
}>()

const toast = useToast()
const localJoins = ref<JoinDefinition[]>([...props.joins])
const allColumnsByTable = ref<Record<string, string[]>>({})
const loadingColumns = ref(false)

const joinTypes = ['INNER', 'LEFT', 'RIGHT', 'FULL']

// Get unique tables from source fields
const uniqueTables = computed(() => {
  const tables = new Set(props.sourceFields.map(f => f.src_table_name))
  return Array.from(tables).sort()
})

// Get unique table to physical name mapping
const tablePhysicalNames = computed(() => {
  const mapping: Record<string, string> = {}
  props.sourceFields.forEach(f => {
    mapping[f.src_table_name] = f.src_table_physical_name
  })
  return mapping
})

// Fetch all columns for all tables from the backend
async function fetchAllColumns() {
  loadingColumns.value = true
  try {
    const response = await fetch('/api/v2/unmapped-fields/columns-by-table')
    if (!response.ok) {
      throw new Error('Failed to fetch columns')
    }
    const data = await response.json()
    allColumnsByTable.value = data
    console.log('[Join Configurator] Fetched columns for tables:', Object.keys(data))
  } catch (error) {
    console.error('[Join Configurator] Error fetching columns:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load available columns for join configuration',
      life: 5000
    })
  } finally {
    loadingColumns.value = false
  }
}

// Get columns for a specific table (from all available columns, not just selected fields)
function getColumnsForTable(tableName: string): string[] {
  if (!tableName) return []
  
  // Use the fetched columns from backend if available
  if (allColumnsByTable.value[tableName]) {
    return allColumnsByTable.value[tableName]
  }
  
  // Fallback: use columns from current source fields
  return props.sourceFields
    .filter(f => f.src_table_name === tableName)
    .map(f => f.src_column_name)
}

// Handle table selection change
function onTableChange(join: JoinDefinition, side: 'left' | 'right') {
  if (side === 'left') {
    join.left_table_physical_name = tablePhysicalNames.value[join.left_table_name] || join.left_table_name
    join.left_join_column = '' // Reset column when table changes
  } else {
    join.right_table_physical_name = tablePhysicalNames.value[join.right_table_name] || join.right_table_name
    join.right_join_column = '' // Reset column when table changes
  }
}

function addJoin() {
  const newJoin: JoinDefinition = {
    left_table_name: '',
    left_table_physical_name: '',
    left_join_column: '',
    right_table_name: '',
    right_table_physical_name: '',
    right_join_column: '',
    join_type: 'INNER',
    join_order: localJoins.value.length + 1
  }
  localJoins.value.push(newJoin)
  emitJoins()
}

function removeJoin(index: number) {
  localJoins.value.splice(index, 1)
  // Reorder remaining joins
  localJoins.value.forEach((join, idx) => {
    join.join_order = idx + 1
  })
  emitJoins()
}

function emitJoins() {
  emit('update:joins', [...localJoins.value])
}

function getJoinSQL(join: JoinDefinition): string {
  const leftPhysical = join.left_table_physical_name || join.left_table_name
  const rightPhysical = join.right_table_physical_name || join.right_table_name
  return `${join.join_type} JOIN ${rightPhysical} ON ${leftPhysical}.${join.left_join_column} = ${rightPhysical}.${join.right_join_column}`
}

function getFullJoinSQL(): string {
  if (localJoins.value.length === 0) return ''
  
  // Start with first table
  const firstJoin = localJoins.value[0]
  const leftPhysical = firstJoin.left_table_physical_name || firstJoin.left_table_name
  
  let sql = `FROM ${leftPhysical}\n`
  
  localJoins.value.forEach(join => {
    sql += `  ${getJoinSQL(join)}\n`
  })
  
  return sql.trim()
}

// Watch for changes in dropdowns and emit (debounced to avoid loops)
let emitTimeout: ReturnType<typeof setTimeout> | null = null
watch(localJoins, () => {
  if (emitTimeout) clearTimeout(emitTimeout)
  emitTimeout = setTimeout(() => {
    emitJoins()
  }, 300)
}, { deep: true })

// Watch for external changes from parent
watch(() => props.joins, (newJoins) => {
  // Only update if the actual content has changed to prevent loops
  const currentJSON = JSON.stringify(localJoins.value)
  const newJSON = JSON.stringify(newJoins)
  
  if (currentJSON !== newJSON) {
    localJoins.value = [...newJoins]
  }
}, { deep: true })

// Fetch columns when component mounts
onMounted(() => {
  fetchAllColumns()
})
</script>

<style scoped>
.join-configurator {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.info-message {
  margin-bottom: 1rem;
}

.tables-summary h4 {
  margin: 0 0 1rem 0;
  color: var(--gainwell-dark);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.table-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.joins-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h4 {
  margin: 0;
  color: var(--gainwell-dark);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.join-item {
  margin-bottom: 1rem;
}

.join-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 1rem;
  font-weight: 600;
}

.join-config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr auto 1fr 1fr;
  gap: 1rem;
  align-items: end;
  margin-bottom: 1rem;
}

.join-side,
.join-type {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.join-side label,
.join-type label {
  font-weight: 600;
  color: var(--gainwell-text-primary);
  font-size: 0.9rem;
}

.join-type {
  min-width: 120px;
}

.sql-preview {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--surface-50);
  border-left: 4px solid var(--gainwell-secondary);
  border-radius: 6px;
}

.sql-preview label {
  font-weight: 600;
  color: var(--gainwell-text-secondary);
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
}

.sql-preview code {
  font-family: monospace;
  color: var(--gainwell-dark);
  font-size: 0.95rem;
}

.full-sql-preview h4 {
  margin: 0 0 1rem 0;
  color: var(--gainwell-dark);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sql-code {
  background: var(--surface-100);
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid var(--surface-border);
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  color: var(--gainwell-dark);
  overflow-x: auto;
  white-space: pre-wrap;
}
</style>

