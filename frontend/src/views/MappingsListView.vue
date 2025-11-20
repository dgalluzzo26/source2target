<template>
  <div class="mappings-list-view">
    <div class="view-header">
      <h1>Current Mappings</h1>
      <p class="subtitle">View and manage all source-to-target field mappings</p>
    </div>

    <!-- Filters and Actions -->
    <div class="toolbar">
      <div class="toolbar-left">
        <IconField iconPosition="left">
          <InputIcon class="pi pi-search" />
          <InputText 
            v-model="searchQuery" 
            placeholder="Search mappings..." 
            class="search-input"
          />
        </IconField>
      </div>
      <div class="toolbar-right">
        <Button 
          label="Export Mappings" 
          icon="pi pi-download" 
          severity="secondary"
          @click="handleExport"
        />
        <Button 
          label="Create New Mapping" 
          icon="pi pi-plus" 
          @click="handleCreateNew"
        />
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <ProgressSpinner />
      <p>Loading mappings...</p>
    </div>

    <!-- Error State -->
    <Message v-if="error" severity="error" :closable="true">
      {{ error }}
    </Message>

    <!-- Mappings Table -->
    <div v-if="!loading && mappings.length > 0" class="mappings-table-container">
      <DataTable 
        :value="filteredMappings" 
        :paginator="true"
        :rows="20"
        :rowsPerPageOptions="[10, 20, 50, 100]"
        paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
        currentPageReportTemplate="Showing {first} to {last} of {totalRecords} mappings"
        class="mappings-table"
        stripedRows
        removableSort
        :rowClass="getRowClass"
      >
        <!-- Target Field -->
        <Column header="Target Field" :sortable="true" style="min-width: 15rem">
          <template #body="{ data }">
            <div class="target-field-cell">
              <i class="pi pi-arrow-circle-right target-icon"></i>
              <div class="field-info">
                <strong>{{ data.target_table }}.{{ data.target_column }}</strong>
                <span class="physical-name">{{ data.target_physical_name }}</span>
              </div>
            </div>
          </template>
        </Column>

        <!-- Source Fields -->
        <Column header="Source Field(s)" style="min-width: 20rem">
          <template #body="{ data }">
            <div class="source-fields-cell">
              <Tag 
                v-for="(source, idx) in data.source_fields" 
                :key="idx"
                :value="`${source.table}.${source.column}`"
                severity="info"
                :icon="data.source_fields.length > 1 ? `pi pi-sort-numeric-up-alt` : undefined"
              />
              <Badge 
                v-if="data.source_fields.length > 1" 
                :value="`${data.source_fields.length} fields`" 
                severity="info"
              />
            </div>
          </template>
        </Column>

        <!-- Concatenation -->
        <Column header="Concatenation" :sortable="true" style="min-width: 10rem">
          <template #body="{ data }">
            <Tag 
              v-if="data.concat_strategy !== 'NONE'" 
              :value="getConcatLabel(data.concat_strategy)" 
              severity="secondary"
            />
            <span v-else class="no-concat">Single field</span>
          </template>
        </Column>

        <!-- Transformations -->
        <Column header="Transformations" style="min-width: 12rem">
          <template #body="{ data }">
            <div v-if="data.has_transformations" class="transformations-cell">
              <Tag value="With Transforms" severity="warning" icon="pi pi-code" />
            </div>
            <span v-else class="no-transform">None</span>
          </template>
        </Column>

        <!-- Status -->
        <Column header="Status" :sortable="true" style="min-width: 8rem">
          <template #body="{ data }">
            <Tag 
              :value="data.status" 
              :severity="getStatusSeverity(data.status)"
              :icon="getStatusIcon(data.status)"
            />
          </template>
        </Column>

        <!-- Created Date -->
        <Column field="created_at" header="Created" :sortable="true" style="min-width: 10rem">
          <template #body="{ data }">
            <span class="date-cell">{{ formatDate(data.created_at) }}</span>
          </template>
        </Column>

        <!-- Actions -->
        <Column :exportable="false" style="min-width: 10rem">
          <template #body="{ data }">
            <div class="action-buttons">
              <Button 
                icon="pi pi-eye" 
                severity="info" 
                text 
                rounded 
                @click="handleView(data)"
                v-tooltip.top="'View Details'"
              />
              <Button 
                icon="pi pi-pencil" 
                severity="secondary" 
                text 
                rounded 
                @click="handleEdit(data)"
                v-tooltip.top="'Edit Mapping'"
              />
              <Button 
                icon="pi pi-trash" 
                severity="danger" 
                text 
                rounded 
                @click="handleDelete(data)"
                v-tooltip.top="'Delete Mapping'"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && mappings.length === 0" class="empty-state">
      <i class="pi pi-inbox" style="font-size: 4rem; color: var(--text-color-secondary);"></i>
      <h3>No Mappings Yet</h3>
      <p>Start creating field mappings to see them here.</p>
      <Button label="Create First Mapping" icon="pi pi-plus" @click="handleCreateNew" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'

const router = useRouter()
const confirm = useConfirm()
const toast = useToast()

// State
const mappings = ref<any[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')

// Mock data for now
const mockMappings = [
  {
    id: 1,
    target_table: 'slv_member',
    target_column: 'full_name',
    target_physical_name: 'full_name',
    source_fields: [
      { table: 'T_MEMBER', column: 'FIRST_NAME' },
      { table: 'T_MEMBER', column: 'LAST_NAME' }
    ],
    concat_strategy: 'SPACE',
    has_transformations: true,
    status: 'Active',
    created_at: '2025-11-15T10:30:00'
  },
  {
    id: 2,
    target_table: 'slv_member',
    target_column: 'ssn_number',
    target_physical_name: 'ssn_number',
    source_fields: [
      { table: 'T_MEMBER', column: 'SSN' }
    ],
    concat_strategy: 'NONE',
    has_transformations: false,
    status: 'Active',
    created_at: '2025-11-14T14:20:00'
  },
  {
    id: 3,
    target_table: 'slv_member',
    target_column: 'full_address',
    target_physical_name: 'full_address',
    source_fields: [
      { table: 'T_ADDRESS', column: 'ADDRESS_LINE1' },
      { table: 'T_ADDRESS', column: 'CITY' },
      { table: 'T_ADDRESS', column: 'STATE' },
      { table: 'T_ADDRESS', column: 'ZIP_CODE' }
    ],
    concat_strategy: 'COMMA',
    has_transformations: true,
    status: 'Active',
    created_at: '2025-11-13T09:15:00'
  }
]

// Computed
const filteredMappings = computed(() => {
  if (!searchQuery.value) return mappings.value
  
  const query = searchQuery.value.toLowerCase()
  return mappings.value.filter(m => 
    m.target_table.toLowerCase().includes(query) ||
    m.target_column.toLowerCase().includes(query) ||
    m.source_fields.some((s: any) => 
      s.table.toLowerCase().includes(query) || 
      s.column.toLowerCase().includes(query)
    )
  )
})

onMounted(async () => {
  await fetchMappings()
})

async function fetchMappings() {
  loading.value = true
  error.value = null
  
  try {
    // TODO: Replace with real API call
    // const response = await fetch('/api/v2/mappings')
    // mappings.value = await response.json()
    
    // Mock: Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500))
    mappings.value = mockMappings
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load mappings'
  } finally {
    loading.value = false
  }
}

function getConcatLabel(strategy: string): string {
  switch (strategy) {
    case 'SPACE': return 'Space'
    case 'COMMA': return 'Comma'
    case 'PIPE': return 'Pipe'
    case 'CUSTOM': return 'Custom'
    default: return strategy
  }
}

function getStatusSeverity(status: string): string {
  switch (status) {
    case 'Active': return 'success'
    case 'Inactive': return 'secondary'
    case 'Draft': return 'warning'
    case 'Error': return 'danger'
    default: return 'info'
  }
}

function getStatusIcon(status: string): string {
  switch (status) {
    case 'Active': return 'pi pi-check-circle'
    case 'Inactive': return 'pi pi-times-circle'
    case 'Draft': return 'pi pi-pencil'
    case 'Error': return 'pi pi-exclamation-triangle'
    default: return 'pi pi-info-circle'
  }
}

function getRowClass(data: any) {
  return data.status === 'Inactive' ? 'inactive-row' : ''
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function handleView(mapping: any) {
  toast.add({
    severity: 'info',
    summary: 'View Mapping',
    detail: `Viewing details for ${mapping.target_table}.${mapping.target_column}`,
    life: 3000
  })
  // TODO: Open details dialog
}

function handleEdit(mapping: any) {
  toast.add({
    severity: 'info',
    summary: 'Edit Mapping',
    detail: `Editing ${mapping.target_table}.${mapping.target_column}`,
    life: 3000
  })
  // TODO: Navigate to edit view
}

function handleDelete(mapping: any) {
  confirm.require({
    message: `Are you sure you want to delete the mapping for "${mapping.target_table}.${mapping.target_column}"?`,
    header: 'Confirm Deletion',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        // TODO: Call delete API
        toast.add({
          severity: 'success',
          summary: 'Deleted',
          detail: 'Mapping deleted successfully',
          life: 3000
        })
        await fetchMappings()
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to delete mapping',
          life: 3000
        })
      }
    }
  })
}

function handleExport() {
  toast.add({
    severity: 'info',
    summary: 'Export',
    detail: 'Exporting mappings to CSV...',
    life: 3000
  })
  // TODO: Implement export
}

function handleCreateNew() {
  router.push({ name: 'unmapped-fields' })
}
</script>

<style scoped>
.mappings-list-view {
  padding: 2rem;
  max-width: 1600px;
  margin: 0 auto;
}

.view-header {
  margin-bottom: 2rem;
}

.view-header h1 {
  margin: 0 0 0.5rem 0;
  color: var(--gainwell-dark);
}

.subtitle {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 1rem;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.toolbar-left {
  flex: 1;
  min-width: 300px;
}

.toolbar-right {
  display: flex;
  gap: 0.5rem;
}

.search-input {
  width: 100%;
  max-width: 400px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  gap: 1rem;
}

.mappings-table-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.target-field-cell {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.target-icon {
  color: var(--gainwell-secondary);
  font-size: 1.25rem;
  flex-shrink: 0;
}

.field-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.physical-name {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  font-family: 'Courier New', monospace;
}

.source-fields-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.transformations-cell {
  display: flex;
  gap: 0.5rem;
}

.no-concat,
.no-transform {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
  font-style: italic;
}

.date-cell {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  gap: 1rem;
  text-align: center;
}

.empty-state h3 {
  margin: 0;
  color: var(--text-color);
}

.empty-state p {
  margin: 0;
  color: var(--text-color-secondary);
}

/* Inactive row styling */
:deep(.inactive-row) {
  opacity: 0.6;
}

/* Responsive */
@media (max-width: 768px) {
  .mappings-list-view {
    padding: 1rem;
  }
  
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .toolbar-left,
  .toolbar-right {
    width: 100%;
  }
  
  .search-input {
    max-width: none;
  }
}
</style>

