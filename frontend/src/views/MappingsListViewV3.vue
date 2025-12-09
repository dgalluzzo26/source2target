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
        <Dropdown
          v-model="statusFilter"
          :options="statusOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="All Statuses"
          class="status-filter"
          @change="handleStatusChange"
        />
      </div>
      <div class="toolbar-right">
        <Button 
          label="Export CSV" 
          icon="pi pi-download" 
          severity="secondary"
          outlined
          @click="exportMappings"
        />
        <Button 
          label="Refresh" 
          icon="pi pi-refresh" 
          severity="secondary"
          @click="handleRefresh"
          :loading="loading"
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
                <strong>{{ data.tgt_table_name }}.{{ data.tgt_column_name }}</strong>
                <span class="physical-name">{{ data.tgt_column_physical_name }}</span>
              </div>
            </div>
          </template>
        </Column>

        <!-- Source Fields (from metadata) -->
        <Column header="Source Field(s)" style="min-width: 20rem">
          <template #body="{ data }">
            <div class="source-fields-cell">
              <Tag 
                v-for="(source, idx) in parseSourceInfo(data.source_tables, data.source_columns)" 
                :key="idx"
                :value="source"
                severity="info"
              />
              <Badge 
                v-if="getSourceCount(data.source_columns) > 1" 
                :value="`${getSourceCount(data.source_columns)} fields`" 
                severity="info"
              />
            </div>
          </template>
        </Column>

        <!-- Relationship Type -->
        <Column header="Type" :sortable="true" style="min-width: 8rem">
          <template #body="{ data }">
            <Tag 
              :value="data.source_relationship_type" 
              :severity="getRelationshipSeverity(data.source_relationship_type)"
              :icon="getRelationshipIcon(data.source_relationship_type)"
            />
          </template>
        </Column>

        <!-- Transformations -->
        <Column header="Transformations" style="min-width: 10rem">
          <template #body="{ data }">
            <div v-if="data.transformations_applied" class="transformations-cell">
              <Tag 
                v-for="(transform, idx) in parseTransformations(data.transformations_applied)" 
                :key="idx"
                :value="transform"
                severity="warning"
                size="small"
              />
            </div>
            <span v-else class="no-transform">None</span>
          </template>
        </Column>

        <!-- Mapping Source -->
        <Column header="Source" :sortable="true" style="min-width: 8rem">
          <template #body="{ data }">
            <Tag 
              :value="data.mapping_source" 
              :severity="getMappingSourceSeverity(data.mapping_source)"
              :icon="getMappingSourceIcon(data.mapping_source)"
            />
          </template>
        </Column>

        <!-- Status -->
        <Column header="Status" :sortable="true" style="min-width: 8rem">
          <template #body="{ data }">
            <Tag 
              :value="data.mapping_status" 
              :severity="getStatusSeverity(data.mapping_status)"
              :icon="getStatusIcon(data.mapping_status)"
            />
          </template>
        </Column>

        <!-- Created Date -->
        <Column field="mapped_ts" header="Created" :sortable="true" style="min-width: 10rem">
          <template #body="{ data }">
            <span class="date-cell">{{ formatDate(data.mapped_ts) }}</span>
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
      :style="{ width: '60rem' }"
      :breakpoints="{ '1199px': '75vw', '575px': '90vw' }"
    >
      <div v-if="selectedMapping" class="mapping-details">
        <!-- Target Field Section -->
        <div class="detail-section">
          <h3><i class="pi pi-arrow-circle-right"></i> Target Field</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Table</label>
              <div class="detail-value">{{ selectedMapping.tgt_table_name }}</div>
            </div>
            <div class="detail-item">
              <label>Column</label>
              <div class="detail-value">{{ selectedMapping.tgt_column_name }}</div>
            </div>
            <div class="detail-item">
              <label>Physical Name</label>
              <div class="detail-value code">{{ selectedMapping.tgt_column_physical_name }}</div>
            </div>
            <div class="detail-item" v-if="selectedMapping.tgt_comments">
              <label>Description</label>
              <div class="detail-value">{{ selectedMapping.tgt_comments }}</div>
            </div>
          </div>
        </div>

        <!-- Source Info Section -->
        <div class="detail-section">
          <h3><i class="pi pi-list"></i> Source Information</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Source Table(s)</label>
              <div class="detail-value">{{ selectedMapping.source_tables || 'N/A' }}</div>
            </div>
            <div class="detail-item">
              <label>Source Tables (Physical)</label>
              <div class="detail-value code">{{ (selectedMapping as any).source_tables_physical || 'N/A' }}</div>
            </div>
            <div class="detail-item">
              <label>Source Column(s)</label>
              <div class="detail-value">{{ selectedMapping.source_columns || 'N/A' }}</div>
            </div>
            <div class="detail-item">
              <label>Source Columns (Physical)</label>
              <div class="detail-value code">{{ (selectedMapping as any).source_columns_physical || 'N/A' }}</div>
            </div>
            <div class="detail-item">
              <label>Relationship Type</label>
              <Tag 
                :value="selectedMapping.source_relationship_type" 
                :severity="getRelationshipSeverity(selectedMapping.source_relationship_type)"
              />
            </div>
            <div class="detail-item" v-if="selectedMapping.transformations_applied">
              <label>Transformations</label>
              <div class="detail-value">{{ selectedMapping.transformations_applied }}</div>
            </div>
            <div class="detail-item" v-if="(selectedMapping as any).source_domain">
              <label>Domain</label>
              <Tag :value="(selectedMapping as any).source_domain" severity="secondary" />
            </div>
            <div class="detail-item" v-if="selectedMapping.source_datatypes">
              <label>Source Data Types</label>
              <div class="detail-value code">{{ selectedMapping.source_datatypes }}</div>
            </div>
          </div>
        </div>

        <!-- SQL Expression Section -->
        <div class="detail-section">
          <h3>
            <i class="pi pi-code"></i> 
            SQL Expression
            <Tag 
              v-if="selectedMapping.ai_generated" 
              value="AI Generated" 
              severity="info" 
              class="ai-badge"
            />
          </h3>
          <pre class="sql-expression">{{ selectedMapping.source_expression }}</pre>
        </div>

        <!-- AI Info Section (if applicable) -->
        <div v-if="selectedMapping.ai_reasoning" class="detail-section">
          <h3><i class="pi pi-sparkles"></i> AI Reasoning</h3>
          <p class="ai-reasoning-text">{{ selectedMapping.ai_reasoning }}</p>
          <div v-if="selectedMapping.confidence_score" class="confidence-display">
            <label>Confidence Score:</label>
            <ProgressBar 
              :value="selectedMapping.confidence_score * 100" 
              :showValue="true"
              :style="{ width: '200px' }"
            />
          </div>
        </div>

        <!-- Metadata Section -->
        <div class="detail-section">
          <h3><i class="pi pi-info-circle"></i> Metadata</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Created</label>
              <div class="detail-value">{{ formatDate(selectedMapping.mapped_ts) }}</div>
            </div>
            <div class="detail-item">
              <label>Created By</label>
              <div class="detail-value">{{ selectedMapping.mapped_by || 'Unknown' }}</div>
            </div>
            <div class="detail-item">
              <label>Mapping Source</label>
              <Tag 
                :value="selectedMapping.mapping_source" 
                :severity="getMappingSourceSeverity(selectedMapping.mapping_source)"
              />
            </div>
            <div class="detail-item">
              <label>Status</label>
              <Tag 
                :value="selectedMapping.mapping_status" 
                :severity="getStatusSeverity(selectedMapping.mapping_status)"
              />
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <Button label="Close" icon="pi pi-times" @click="showDetailsDialog = false" severity="secondary" />
        <Button label="Edit" icon="pi pi-pencil" @click="handleEdit(selectedMapping); showDetailsDialog = false" />
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
          <div class="readonly-field">
            <div class="field-item">
              <label>Table:</label>
              <span>{{ editFormData.tgt_table_name }}</span>
            </div>
            <div class="field-item">
              <label>Column:</label>
              <span>{{ editFormData.tgt_column_name }}</span>
            </div>
          </div>
        </div>

        <!-- Source Expression Editor -->
        <div class="form-section">
          <div class="section-header">
            <i class="pi pi-code"></i>
            <h3>SQL Expression</h3>
            <Button 
              icon="pi pi-sparkles"
              label="AI Helper"
              size="small"
              severity="info"
              outlined
              @click="showAIHelper = true"
            />
          </div>
          
          <Textarea
            v-model="editFormData.source_expression"
            :rows="5"
            class="sql-editor w-full"
            placeholder="Enter SQL expression (e.g., TRIM(UPPER(column_name)))"
          />
          <small class="field-hint">
            Enter the complete SQL expression for this mapping. Use AI Helper for assistance.
          </small>
        </div>

        <!-- Source Metadata -->
        <div class="form-section">
          <div class="section-header">
            <i class="pi pi-database"></i>
            <h3>Source Metadata</h3>
          </div>
          
          <div class="metadata-grid">
            <div class="field">
              <label>Source Tables (Logical)</label>
              <InputText
                v-model="editFormData.source_tables"
                placeholder="Pipe-separated table names (e.g., Table One | Table Two)"
                class="w-full"
              />
            </div>
            <div class="field">
              <label>Source Tables (Physical)</label>
              <InputText
                v-model="editFormData.source_tables_physical"
                placeholder="Pipe-separated physical table names (e.g., table_one | table_two)"
                class="w-full"
              />
            </div>
            <div class="field">
              <label>Source Columns (Logical)</label>
              <InputText
                v-model="editFormData.source_columns"
                placeholder="Pipe-separated column names (e.g., Column One | Column Two)"
                class="w-full"
              />
            </div>
            <div class="field">
              <label>Source Columns (Physical)</label>
              <InputText
                v-model="editFormData.source_columns_physical"
                placeholder="Pipe-separated physical column names (e.g., col_one | col_two)"
                class="w-full"
              />
            </div>
            <div class="field">
              <label>Source Domain</label>
              <InputText
                v-model="editFormData.source_domain"
                placeholder="Domain category (e.g., member, claims, provider)"
                class="w-full"
              />
            </div>
            <div class="field">
              <label>Relationship Type</label>
              <Dropdown
                v-model="editFormData.source_relationship_type"
                :options="['SINGLE', 'JOIN', 'UNION']"
                placeholder="Select type"
                class="w-full"
              />
            </div>
            <div class="field">
              <label>Transformations Applied</label>
              <InputText
                v-model="editFormData.transformations_applied"
                placeholder="e.g., TRIM, UPPER"
                class="w-full"
              />
            </div>
          </div>
        </div>

        <!-- Status -->
        <div class="form-section">
          <div class="section-header">
            <i class="pi pi-flag"></i>
            <h3>Status</h3>
          </div>
          
          <div class="field">
            <Dropdown
              v-model="editFormData.mapping_status"
              :options="['ACTIVE', 'INACTIVE', 'PENDING_REVIEW']"
              placeholder="Select status"
              class="w-full"
            />
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

    <!-- AI Helper Dialog -->
    <Dialog 
      v-model:visible="showAIHelper" 
      modal 
      header="AI SQL Helper" 
      :style="{ width: '600px' }"
    >
      <div class="ai-helper-content">
        <p>Describe what you want the SQL to do:</p>
        <Textarea
          v-model="aiHelperRequest"
          :rows="4"
          class="w-full"
          placeholder="e.g., 'Combine first_name and last_name with a space, convert to uppercase, and trim whitespace'"
        />
        
        <div v-if="aiGeneratedSQL" class="ai-result">
          <h4>Generated SQL:</h4>
          <pre class="sql-preview">{{ aiGeneratedSQL }}</pre>
          <p v-if="aiExplanation" class="ai-explanation">{{ aiExplanation }}</p>
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
        />
        <Button 
          v-if="aiGeneratedSQL"
          label="Use This SQL" 
          icon="pi pi-check" 
          @click="useGeneratedSQL"
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
import { useMappingsStoreV3, type MappedFieldV3 } from '@/stores/mappingsStoreV3'
import { useUserStore } from '@/stores/user'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import ProgressBar from 'primevue/progressbar'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Dialog from 'primevue/dialog'

const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const mappingsStore = useMappingsStoreV3()
const userStore = useUserStore()

// State
const searchQuery = ref('')
const statusFilter = ref<string | null>(null)
const showDetailsDialog = ref(false)
const selectedMapping = ref<MappedFieldV3 | null>(null)
const showEditDialog = ref(false)
const editFormData = ref<any>(null)
const savingEdit = ref(false)

// AI Helper state
const showAIHelper = ref(false)
const aiHelperRequest = ref('')
const aiGeneratedSQL = ref('')
const aiExplanation = ref('')
const generatingSQL = ref(false)

// Status options
const statusOptions = [
  { label: 'All Statuses', value: null },
  { label: 'Active', value: 'ACTIVE' },
  { label: 'Inactive', value: 'INACTIVE' },
  { label: 'Pending Review', value: 'PENDING_REVIEW' }
]

// Computed
const mappings = computed(() => mappingsStore.mappings)
const loading = computed(() => mappingsStore.loading)
const error = computed(() => mappingsStore.error)

const filteredMappings = computed(() => {
  let result = mappings.value
  
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(m => 
      m.tgt_table_name.toLowerCase().includes(query) ||
      m.tgt_column_name.toLowerCase().includes(query) ||
      (m.source_tables && m.source_tables.toLowerCase().includes(query)) ||
      (m.source_columns && m.source_columns.toLowerCase().includes(query)) ||
      (m.source_expression && m.source_expression.toLowerCase().includes(query))
    )
  }
  
  return result
})

onMounted(async () => {
  await fetchMappings()
})

async function fetchMappings() {
  await mappingsStore.fetchMappings(statusFilter.value || undefined)
}

function handleStatusChange() {
  fetchMappings()
}

function handleRefresh() {
  fetchMappings()
}

function exportMappings() {
  if (filteredMappings.value.length === 0) {
    toast.add({
      severity: 'warn',
      summary: 'No Data',
      detail: 'No mappings to export',
      life: 3000
    })
    return
  }
  
  // Define CSV headers - includes all columns including physical names
  const headers = [
    'Target Table',
    'Target Table Physical',
    'Target Column',
    'Target Column Physical',
    'Source Tables',
    'Source Tables Physical',
    'Source Columns',
    'Source Columns Physical',
    'Source Descriptions',
    'Source Datatypes',
    'Source Domain',
    'Source Expression',
    'Relationship Type',
    'Transformations',
    'Confidence Score',
    'Mapping Source',
    'AI Reasoning',
    'Status',
    'Mapped By',
    'Mapped Date'
  ]
  
  // Build CSV rows - escape any field that might contain commas or quotes
  const escapeCSV = (val: string | undefined | null) => {
    if (!val) return ''
    const str = String(val)
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`
    }
    return str
  }
  
  const rows = filteredMappings.value.map(m => [
    escapeCSV(m.tgt_table_name),
    escapeCSV(m.tgt_table_physical_name),
    escapeCSV(m.tgt_column_name),
    escapeCSV(m.tgt_column_physical_name),
    escapeCSV(m.source_tables),
    escapeCSV((m as any).source_tables_physical),
    escapeCSV(m.source_columns),
    escapeCSV((m as any).source_columns_physical),
    escapeCSV(m.source_descriptions),
    escapeCSV(m.source_datatypes),
    escapeCSV((m as any).source_domain),
    escapeCSV(m.source_expression),
    escapeCSV(m.source_relationship_type || 'SINGLE'),
    escapeCSV(m.transformations_applied),
    m.confidence_score ? String(m.confidence_score) : '',
    escapeCSV(m.mapping_source),
    escapeCSV(m.ai_reasoning),
    escapeCSV(m.mapping_status),
    escapeCSV(m.mapped_by),
    m.mapped_ts ? new Date(m.mapped_ts).toISOString() : ''
  ])
  
  // Create CSV content
  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n')
  
  // Create and download file
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `mappings_export_${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  toast.add({
    severity: 'success',
    summary: 'Export Complete',
    detail: `Exported ${filteredMappings.value.length} mappings to CSV`,
    life: 3000
  })
}

// Helper functions
function parseSourceInfo(tables: string | undefined, columns: string | undefined): string[] {
  if (!tables || !columns) return columns ? columns.split(',').map(c => c.trim()) : []
  
  const tableList = tables.split(',').map(t => t.trim())
  const columnList = columns.split(',').map(c => c.trim())
  
  return columnList.map((col, idx) => {
    const table = tableList[Math.min(idx, tableList.length - 1)]
    return `${table}.${col}`
  })
}

function getSourceCount(columns: string | undefined): number {
  if (!columns) return 0
  return columns.split(',').length
}

function parseTransformations(transforms: string | undefined): string[] {
  if (!transforms) return []
  return transforms.split(',').map(t => t.trim()).slice(0, 3) // Show max 3
}

function getRelationshipSeverity(type: string): string {
  switch (type) {
    case 'SINGLE': return 'secondary'
    case 'JOIN': return 'info'
    case 'UNION': return 'warning'
    default: return 'secondary'
  }
}

function getRelationshipIcon(type: string): string {
  switch (type) {
    case 'SINGLE': return 'pi pi-minus'
    case 'JOIN': return 'pi pi-link'
    case 'UNION': return 'pi pi-sort-alt'
    default: return ''
  }
}

function getMappingSourceSeverity(source: string): string {
  switch (source) {
    case 'AI': return 'info'
    case 'MANUAL': return 'secondary'
    case 'BULK_UPLOAD': return 'warning'
    default: return 'secondary'
  }
}

function getMappingSourceIcon(source: string): string {
  switch (source) {
    case 'AI': return 'pi pi-sparkles'
    case 'MANUAL': return 'pi pi-user'
    case 'BULK_UPLOAD': return 'pi pi-upload'
    default: return ''
  }
}

function getStatusSeverity(status: string): string {
  switch (status) {
    case 'ACTIVE': return 'success'
    case 'INACTIVE': return 'secondary'
    case 'PENDING_REVIEW': return 'warning'
    default: return 'info'
  }
}

function getStatusIcon(status: string): string {
  switch (status) {
    case 'ACTIVE': return 'pi pi-check-circle'
    case 'INACTIVE': return 'pi pi-times-circle'
    case 'PENDING_REVIEW': return 'pi pi-clock'
    default: return 'pi pi-info-circle'
  }
}

function getRowClass(data: MappedFieldV3) {
  return data.mapping_status === 'INACTIVE' ? 'inactive-row' : ''
}

function formatDate(dateString: string | undefined): string {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function handleView(mapping: MappedFieldV3) {
  selectedMapping.value = mapping
  showDetailsDialog.value = true
}

function handleEdit(mapping: MappedFieldV3 | null) {
  if (!mapping) return
  
  showDetailsDialog.value = false
  
  editFormData.value = {
    mapped_field_id: mapping.mapped_field_id,
    tgt_table_name: mapping.tgt_table_name,
    tgt_column_name: mapping.tgt_column_name,
    source_expression: mapping.source_expression,
    source_tables: mapping.source_tables || '',
    source_columns: mapping.source_columns || '',
    source_relationship_type: mapping.source_relationship_type || 'SINGLE',
    transformations_applied: mapping.transformations_applied || '',
    mapping_status: mapping.mapping_status || 'ACTIVE'
  }
  
  showEditDialog.value = true
}

function resetEditForm() {
  editFormData.value = null
  aiHelperRequest.value = ''
  aiGeneratedSQL.value = ''
  aiExplanation.value = ''
}

async function saveEditedMapping() {
  if (!editFormData.value) return
  
  savingEdit.value = true
  
  try {
    await mappingsStore.updateMapping(editFormData.value.mapped_field_id, {
      source_expression: editFormData.value.source_expression,
      source_tables: editFormData.value.source_tables || undefined,
      source_columns: editFormData.value.source_columns || undefined,
      source_relationship_type: editFormData.value.source_relationship_type,
      transformations_applied: editFormData.value.transformations_applied || undefined,
      mapping_status: editFormData.value.mapping_status,
      updated_by: userStore.userEmail || 'unknown'
    })
    
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Mapping updated successfully',
      life: 3000
    })
    
    showEditDialog.value = false
    await fetchMappings()
    
  } catch (error: any) {
    console.error('Error updating mapping:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'Failed to update mapping',
      life: 5000
    })
  } finally {
    savingEdit.value = false
  }
}

async function generateSQL() {
  if (!aiHelperRequest.value.trim()) {
    toast.add({
      severity: 'warn',
      summary: 'Input Required',
      detail: 'Please describe what you want the SQL to do',
      life: 3000
    })
    return
  }
  
  generatingSQL.value = true
  
  try {
    // Parse source columns from edit form (handle pipe or comma delimiter)
    const colDelimiter = editFormData.value.source_columns?.includes(' | ') ? ' | ' : ','
    const tableDelimiter = editFormData.value.source_tables?.includes(' | ') ? ' | ' : ','
    
    const sourceColumns = editFormData.value.source_columns
      ? editFormData.value.source_columns.split(colDelimiter).map((col: string) => ({
          table: editFormData.value.source_tables?.split(tableDelimiter)[0]?.trim() || 'source',
          column: col.trim(),
          datatype: 'STRING'
        }))
      : []
    
    const result = await mappingsStore.generateSQLWithAI(
      aiHelperRequest.value,
      sourceColumns,
      {
        table: editFormData.value.tgt_table_name,
        column: editFormData.value.tgt_column_name,
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
  if (aiGeneratedSQL.value && editFormData.value) {
    editFormData.value.source_expression = aiGeneratedSQL.value
    editFormData.value.ai_generated = true
    showAIHelper.value = false
    
    toast.add({
      severity: 'success',
      summary: 'SQL Applied',
      detail: 'AI-generated SQL has been applied',
      life: 3000
    })
  }
}

function handleDelete(mapping: MappedFieldV3 | null) {
  if (!mapping) return
  
  confirm.require({
    message: `Are you sure you want to delete the mapping for "${mapping.tgt_table_name}.${mapping.tgt_column_name}"? This action cannot be undone.`,
    header: 'Confirm Deletion',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await mappingsStore.deleteMapping(mapping.mapped_field_id!, true)
        toast.add({
          severity: 'success',
          summary: 'Deleted',
          detail: 'Mapping deleted successfully',
          life: 3000
        })
        await fetchMappings()
      } catch (error: any) {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: error.message || 'Failed to delete mapping',
          life: 3000
        })
      }
    }
  })
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
  display: flex;
  gap: 1rem;
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

.status-filter {
  width: 180px;
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
  flex-wrap: wrap;
  gap: 0.25rem;
}

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

:deep(.inactive-row) {
  opacity: 0.6;
}

/* Details Dialog */
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

.ai-badge {
  margin-left: auto;
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
  white-space: pre-wrap;
  word-break: break-word;
}

.ai-reasoning-text {
  font-style: italic;
  color: var(--text-color-secondary);
  margin: 0;
}

.confidence-display {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
}

.confidence-display label {
  font-weight: 600;
  color: var(--text-color-secondary);
}

/* Edit Dialog */
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
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--surface-border);
}

.section-header h3 {
  flex: 1;
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

.sql-editor {
  font-family: 'Courier New', monospace;
  font-size: 0.95rem;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  color: var(--text-color);
  font-size: 0.95rem;
}

.field-hint {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

.w-full {
  width: 100%;
}

/* AI Helper Dialog */
.ai-helper-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.ai-result {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.ai-result h4 {
  margin: 0 0 0.5rem 0;
  color: var(--text-color);
}

.sql-preview {
  background: var(--surface-100);
  padding: 1rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  margin: 0;
  white-space: pre-wrap;
}

.ai-explanation {
  margin: 0.5rem 0 0 0;
  font-style: italic;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
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
  
  .status-filter {
    width: 100%;
  }
  
  .detail-grid {
    grid-template-columns: 1fr;
  }
  
  .metadata-grid {
    grid-template-columns: 1fr;
  }
  
  .readonly-field {
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>

