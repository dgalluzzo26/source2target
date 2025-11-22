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

    <!-- Details Dialog -->
    <Dialog 
      v-model:visible="showDetailsDialog" 
      modal 
      header="Mapping Details" 
      :style="{ width: '50rem' }"
      :breakpoints="{ '1199px': '75vw', '575px': '90vw' }"
    >
      <div v-if="selectedMapping" class="mapping-details">
        <!-- Target Field Section -->
        <div class="detail-section">
          <h3><i class="pi pi-arrow-circle-right"></i> Target Field</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Table</label>
              <div class="detail-value">{{ selectedMapping.target_table }}</div>
            </div>
            <div class="detail-item">
              <label>Column</label>
              <div class="detail-value">{{ selectedMapping.target_column }}</div>
            </div>
            <div class="detail-item">
              <label>Physical Name</label>
              <div class="detail-value code">{{ selectedMapping.target_physical_name }}</div>
            </div>
            <div class="detail-item">
              <label>Status</label>
              <Tag 
                :value="selectedMapping.status" 
                :severity="getStatusSeverity(selectedMapping.status)"
              />
            </div>
          </div>
        </div>

        <!-- Source Fields Section -->
        <div class="detail-section">
          <h3><i class="pi pi-list"></i> Source Fields</h3>
          <div class="source-fields-list">
            <div 
              v-for="(field, idx) in selectedMapping.source_fields" 
              :key="idx" 
              class="source-field-item"
            >
              <Badge :value="`${idx + 1}`" class="field-order-badge" />
              <div class="field-details">
                <strong>{{ field.table }}.{{ field.column }}</strong>
                <span v-if="field.transformation" class="transformation">{{ field.transformation }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Concatenation Section -->
        <div class="detail-section">
          <h3><i class="pi pi-link"></i> Concatenation Strategy</h3>
          <Tag 
            :value="getConcatLabel(selectedMapping.concat_strategy)" 
            severity="secondary"
            size="large"
          />
        </div>

        <!-- SQL Expression Section -->
        <div v-if="selectedMapping.sql_expression" class="detail-section">
          <h3><i class="pi pi-code"></i> SQL Expression</h3>
          <pre class="sql-expression">{{ selectedMapping.sql_expression }}</pre>
        </div>

        <!-- Metadata Section -->
        <div class="detail-section">
          <h3><i class="pi pi-info-circle"></i> Metadata</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Created</label>
              <div class="detail-value">{{ formatDate(selectedMapping.created_at) }}</div>
            </div>
            <div class="detail-item">
              <label>Created By</label>
              <div class="detail-value">{{ selectedMapping.mapped_by || 'Unknown' }}</div>
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <Button label="Close" icon="pi pi-times" @click="showDetailsDialog = false" severity="secondary" />
        <Button label="Edit" icon="pi pi-pencil" @click="handleEdit(selectedMapping)" />
        <Button label="Delete" icon="pi pi-trash" @click="handleDelete(selectedMapping); showDetailsDialog = false" severity="danger" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useMappingsStoreV2 } from '@/stores/mappingsStoreV2'
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
import Dialog from 'primevue/dialog'

const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const mappingsStore = useMappingsStoreV2()

// State
const searchQuery = ref('')
const showDetailsDialog = ref(false)
const selectedMapping = ref<any>(null)

// Transform store mappings to view format
const mappings = computed(() => {
  return mappingsStore.mappings.map(m => ({
    id: m.mapping_id,
    target_table: m.tgt_table_name,
    target_column: m.tgt_column_name,
    target_physical_name: m.tgt_column_physical_name,
    source_fields: m.source_fields
      .sort((a, b) => a.field_order - b.field_order)
      .map(sf => ({
        table: sf.src_table_name,
        column: sf.src_column_name
      })),
    concat_strategy: m.concat_strategy,
    has_transformations: m.source_fields.some(sf => !!sf.transformation_expr),
    status: m.mapping_status || 'Active',
    created_at: m.mapped_at || new Date().toISOString(),
    mapped_by: m.mapped_by,
    sql_expression: m.transformation_expression
  }))
})

const loading = computed(() => mappingsStore.loading)
const error = computed(() => mappingsStore.error)

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
  try {
    await mappingsStore.fetchMappings()
  } catch (e) {
    console.error('[Mappings List View] Error:', e)
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
  selectedMapping.value = mapping
  showDetailsDialog.value = true
}

function handleEdit(mapping: any) {
  toast.add({
    severity: 'warn',
    summary: 'Not Yet Implemented',
    detail: 'Mapping edit functionality is coming soon',
    life: 3000
  })
  // TODO: Implement edit functionality - navigate to edit wizard
  // router.push({ name: 'mapping-edit', params: { id: mapping.id } })
}

function handleDelete(mapping: any) {
  confirm.require({
    message: `Are you sure you want to delete the mapping for "${mapping.target_table}.${mapping.target_column}"? This action cannot be undone.`,
    header: 'Confirm Deletion',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await mappingsStore.deleteMapping(mapping.id)
        toast.add({
          severity: 'success',
          summary: 'Deleted',
          detail: 'Mapping deleted successfully',
          life: 3000
        })
        // Refresh the list
        await fetchMappings()
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: error instanceof Error ? error.message : 'Failed to delete mapping',
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

/* Details Dialog Styles */
.mapping-details {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.detail-section {
  border-bottom: 1px solid var(--surface-border);
  padding-bottom: 1rem;
}

.detail-section:last-child {
  border-bottom: none;
}

.detail-section h3 {
  margin: 0 0 1rem 0;
  color: var(--primary-color);
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-item label {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-value {
  font-size: 1rem;
  color: var(--text-color);
}

.detail-value.code {
  font-family: 'Courier New', monospace;
  background: var(--surface-50);
  padding: 0.5rem;
  border-radius: 4px;
}

.source-fields-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.source-field-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.field-order-badge {
  flex-shrink: 0;
}

.field-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.field-details .transformation {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  font-family: 'Courier New', monospace;
}

.sql-expression {
  background: var(--surface-50);
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.5;
  margin: 0;
  border: 1px solid var(--surface-border);
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
  
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>

