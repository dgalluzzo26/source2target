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

        <!-- Join Conditions Section (if multi-table) -->
        <div v-if="selectedMapping.joins && selectedMapping.joins.length > 0" class="detail-section">
          <h3><i class="pi pi-share-alt"></i> Join Conditions</h3>
          <div class="joins-list">
            <div 
              v-for="(join, idx) in selectedMapping.joins" 
              :key="idx" 
              class="join-item"
            >
              <Badge :value="`${idx + 1}`" severity="info" class="join-order-badge" />
              <div class="join-details">
                <div class="join-sql">
                  <strong>{{ join.join_type }} JOIN</strong>
                  {{ join.right_table_name }} 
                  <span class="join-on">ON</span>
                  {{ join.left_table_name }}.{{ join.left_join_column }} = {{ join.right_table_name }}.{{ join.right_join_column }}
                </div>
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

    <!-- Edit Mapping Dialog -->
    <Dialog 
      v-model:visible="showEditDialog" 
      modal 
      header="Edit Mapping" 
      :style="{ width: '800px' }"
      :breakpoints="{ '1199px': '90vw', '575px': '95vw' }"
      @hide="resetEditForm"
    >
      <div v-if="editFormData" class="edit-mapping-form">
        
        <!-- Target Field (Read-Only) -->
        <div class="form-section">
          <div class="section-header">
            <i class="pi pi-map-marker"></i>
            <h3>Target Field (Read-Only)</h3>
          </div>
          <Message severity="info" :closable="false">
            To change the target field, you must delete this mapping and create a new one.
          </Message>
          <div class="readonly-field">
            <div class="field-item">
              <label>Table:</label>
              <span>{{ editFormData.target_table }}</span>
            </div>
            <div class="field-item">
              <label>Column:</label>
              <span>{{ editFormData.target_column }}</span>
            </div>
          </div>
        </div>

        <!-- Source Fields with Transformations -->
        <div class="form-section">
          <div class="section-header">
            <i class="pi pi-database"></i>
            <h3>Source Fields</h3>
          </div>
          <Message severity="warn" :closable="false">
            Cannot add, remove, or reorder source fields. Only transformations can be edited.
          </Message>
          
          <div v-for="(field, index) in editFormData.source_fields" :key="field.detail_id" class="source-field-edit">
            <div class="field-header">
              <Badge :value="field.field_order" severity="info" />
              <strong>{{ field.src_column_name }}</strong>
              <span class="table-name">({{ field.src_table_name }})</span>
            </div>
            
            <div class="field">
              <label :for="`transformation-${field.detail_id}`">Transformation</label>
              <Dropdown
                :id="`transformation-${field.detail_id}`"
                v-model="field.transformation_expr"
                :options="transformationOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Select transformation or enter custom"
                editable
                class="w-full"
              >
                <template #value="slotProps">
                  <span v-if="slotProps.value">{{ slotProps.value }}</span>
                  <span v-else class="placeholder-text">No transformation</span>
                </template>
              </Dropdown>
              <small class="field-hint">Choose from library or enter custom SQL expression</small>
            </div>
          </div>
        </div>

        <!-- Concatenation Strategy -->
        <div class="form-section">
          <div class="section-header">
            <i class="pi pi-link"></i>
            <h3>Concatenation</h3>
          </div>
          
          <div class="field">
            <label for="concat-strategy">Strategy</label>
            <Dropdown
              id="concat-strategy"
              v-model="editFormData.concat_strategy"
              :options="concatStrategyOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Select strategy"
              class="w-full"
            />
            <small class="field-hint">How to combine multiple source fields</small>
          </div>

          <div v-if="editFormData.concat_strategy === 'CUSTOM'" class="field">
            <label for="concat-separator">Custom Separator</label>
            <InputText
              id="concat-separator"
              v-model="editFormData.concat_separator"
              placeholder="Enter custom separator (e.g., ' - ', '|')"
              class="w-full"
            />
          </div>
        </div>

        <!-- Join Conditions -->
        <div class="form-section">
          <div class="section-header">
            <i class="pi pi-sitemap"></i>
            <h3>Join Conditions</h3>
            <Button 
              icon="pi pi-plus" 
              label="Add Join"
              size="small"
              @click="addJoinCondition"
            />
          </div>

          <div v-if="editFormData.joins && editFormData.joins.length > 0" class="joins-list">
            <div v-for="(join, index) in editFormData.joins" :key="index" class="join-item">
              <div class="join-fields">
                <div class="field">
                  <label>Left Table</label>
                  <InputText v-model="join.left_table" placeholder="table_name" class="w-full" />
                </div>
                <div class="field">
                  <label>Left Column</label>
                  <InputText v-model="join.left_column" placeholder="column_name" class="w-full" />
                </div>
                <div class="field">
                  <label>Join Type</label>
                  <Dropdown
                    v-model="join.join_type"
                    :options="['INNER', 'LEFT', 'RIGHT', 'FULL']"
                    placeholder="JOIN"
                    class="w-full"
                  />
                </div>
                <div class="field">
                  <label>Right Table</label>
                  <InputText v-model="join.right_table" placeholder="table_name" class="w-full" />
                </div>
                <div class="field">
                  <label>Right Column</label>
                  <InputText v-model="join.right_column" placeholder="column_name" class="w-full" />
                </div>
                <div class="field">
                  <label>&nbsp;</label>
                  <Button 
                    icon="pi pi-trash" 
                    severity="danger"
                    text
                    @click="removeJoinCondition(index)"
                  />
                </div>
              </div>
            </div>
          </div>
          
          <div v-else class="no-joins">
            <p>No join conditions defined. Click "Add Join" to create one.</p>
          </div>
        </div>

      </div>

      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="showEditDialog = false" 
          severity="secondary"
        />
        <Button 
          label="Save Changes" 
          icon="pi pi-check" 
          @click="saveEditedMapping"
          :loading="savingEdit"
        />
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
import Dropdown from 'primevue/dropdown'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Dialog from 'primevue/dialog'
import api from '@/services/api'

const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const mappingsStore = useMappingsStoreV2()

// State
const searchQuery = ref('')
const showDetailsDialog = ref(false)
const selectedMapping = ref<any>(null)
const showEditDialog = ref(false)
const editFormData = ref<any>(null)
const savingEdit = ref(false)
const transformations = ref<any[]>([])

// Concat strategy options
const concatStrategyOptions = [
  { label: 'Space ( )', value: 'SPACE' },
  { label: 'Comma (,)', value: 'COMMA' },
  { label: 'Pipe (|)', value: 'PIPE' },
  { label: 'Custom', value: 'CUSTOM' },
  { label: 'None (no concat)', value: 'NONE' }
]

// Computed transformation options for dropdown
const transformationOptions = computed(() => {
  const options = transformations.value.map(t => ({
    label: `${t.transformation_name} - ${t.transformation_expression}`,
    value: t.transformation_expression
  }))
  // Add "No transformation" option
  options.unshift({ label: 'No transformation', value: '' })
  return options
})

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
    sql_expression: m.transformation_expression,
    joins: m.mapping_joins || []
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
  await Promise.all([
    fetchMappings(),
    loadTransformations()
  ])
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
  // Close details dialog if open
  showDetailsDialog.value = false
  
  // Clone the mapping data for editing
  editFormData.value = {
    mapping_id: mapping.id,
    target_table: mapping.target_table,
    target_column: mapping.target_column,
    concat_strategy: mapping.concat_strategy || 'SPACE',
    concat_separator: mapping.concat_separator || '',
    source_fields: mapping.source_fields.map((sf: any) => ({
      detail_id: sf.detail_id,
      src_table_name: sf.src_table_name,
      src_column_name: sf.src_column_name,
      field_order: sf.field_order,
      transformation_expr: sf.transformation_expr || ''
    })),
    joins: mapping.mapping_joins ? mapping.mapping_joins.map((j: any) => ({
      left_table: j.left_table,
      left_column: j.left_column,
      right_table: j.right_table,
      right_column: j.right_column,
      join_type: j.join_type
    })) : []
  }
  
  showEditDialog.value = true
}

function resetEditForm() {
  editFormData.value = null
}

function addJoinCondition() {
  if (!editFormData.value.joins) {
    editFormData.value.joins = []
  }
  editFormData.value.joins.push({
    left_table: '',
    left_column: '',
    right_table: '',
    right_column: '',
    join_type: 'LEFT'
  })
}

function removeJoinCondition(index: number) {
  editFormData.value.joins.splice(index, 1)
}

async function saveEditedMapping() {
  if (!editFormData.value) return
  
  savingEdit.value = true
  
  try {
    // Build transformation updates object (detail_id -> transformation_expr)
    const transformation_updates: Record<number, string> = {}
    editFormData.value.source_fields.forEach((field: any) => {
      transformation_updates[field.detail_id] = field.transformation_expr || ''
    })
    
    // Build request body
    const updateRequest = {
      concat_strategy: editFormData.value.concat_strategy,
      concat_separator: editFormData.value.concat_strategy === 'CUSTOM' ? editFormData.value.concat_separator : null,
      transformation_updates,
      mapping_joins: editFormData.value.joins.length > 0 ? editFormData.value.joins : []
    }
    
    console.log('Updating mapping:', editFormData.value.mapping_id, updateRequest)
    
    // Call API
    await api.put(`/api/v2/mappings/${editFormData.value.mapping_id}`, updateRequest)
    
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Mapping updated successfully',
      life: 3000
    })
    
    // Close dialog and refresh
    showEditDialog.value = false
    await fetchMappings()
    
  } catch (error: any) {
    console.error('Error updating mapping:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.response?.data?.detail || 'Failed to update mapping',
      life: 5000
    })
  } finally {
    savingEdit.value = false
  }
}

async function loadTransformations() {
  try {
    const response = await api.get('/api/v2/transformations/')
    transformations.value = response.data
    console.log(`Loaded ${transformations.value.length} transformations`)
  } catch (error) {
    console.error('Error loading transformations:', error)
    // Non-critical error, user can still enter custom transformations
  }
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

/* Join Conditions Styles */
.joins-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.join-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: var(--blue-50);
  border-left: 3px solid var(--blue-500);
  border-radius: 6px;
}

.join-order-badge {
  flex-shrink: 0;
}

.join-details {
  flex: 1;
}

.join-sql {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.6;
}

.join-sql strong {
  color: var(--blue-600);
  font-weight: 700;
}

.join-sql .join-on {
  color: var(--blue-700);
  font-weight: 600;
  padding: 0 0.25rem;
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

/* Edit Mapping Dialog Styles */
.edit-mapping-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-section {
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 1rem;
  background: var(--surface-50);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--surface-border);
}

.section-header h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 1.1rem;
  color: var(--text-color);
}

.section-header i {
  color: var(--primary-color);
}

.readonly-field {
  display: flex;
  gap: 2rem;
  margin-top: 1rem;
  padding: 1rem;
  background: var(--surface-100);
  border-radius: 6px;
}

.field-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.field-item label {
  font-weight: 600;
  color: var(--text-color-secondary);
}

.field-item span {
  font-weight: 500;
  color: var(--text-color);
}

.source-field-edit {
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 0.75rem;
  background: white;
}

.field-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  font-size: 1rem;
}

.table-name {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.field:last-child {
  margin-bottom: 0;
}

.field label {
  font-weight: 500;
  color: var(--text-color);
  font-size: 0.95rem;
}

.field-hint {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
  margin-top: -0.25rem;
}

.w-full {
  width: 100%;
}

.placeholder-text {
  color: var(--text-color-secondary);
  font-style: italic;
}

.joins-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.join-item {
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 1rem;
  background: white;
}

.join-fields {
  display: grid;
  grid-template-columns: 1fr 1fr auto 1fr 1fr auto;
  gap: 0.75rem;
  align-items: end;
}

.no-joins {
  text-align: center;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.no-joins p {
  margin: 0;
}

@media (max-width: 968px) {
  .join-fields {
    grid-template-columns: 1fr 1fr;
  }
  
  .readonly-field {
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>

