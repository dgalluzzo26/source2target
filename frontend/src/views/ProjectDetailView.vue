<template>
  <div class="project-detail-view">
    <!-- Header -->
    <div class="view-header">
      <div class="header-left">
        <Button 
          icon="pi pi-arrow-left" 
          text 
          rounded 
          @click="router.push({ name: 'projects' })"
          v-tooltip.right="'Back to Projects'"
        />
        <div class="header-info">
          <h1>{{ project?.project_name || 'Loading...' }}</h1>
          <p class="subtitle" v-if="project?.project_description">
            {{ project.project_description }}
          </p>
        </div>
        <Tag 
          v-if="project" 
          :value="project.project_status" 
          :severity="getStatusSeverity(project.project_status)"
        />
      </div>
      <div class="header-right">
        <Button 
          label="Upload Sources" 
          icon="pi pi-upload" 
          severity="secondary"
          outlined
          @click="showUploadDialog = true"
        />
        <Button 
          label="Initialize Tables" 
          icon="pi pi-database" 
          severity="info"
          @click="handleInitializeTables"
          :disabled="!project"
        />
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="stats-row" v-if="project">
      <!-- Source Stats -->
      <div class="stat-card source">
        <div class="stat-icon source-tables">
          <i class="pi pi-upload"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ project.source_tables_count || 0 }}</span>
          <span class="stat-label">Source Tables</span>
        </div>
      </div>
      <div class="stat-card source">
        <div class="stat-icon source-columns">
          <i class="pi pi-bars"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ project.source_columns_count || 0 }}</span>
          <span class="stat-label">Source Columns</span>
        </div>
      </div>
      <!-- Target Stats -->
      <div class="stat-card">
        <div class="stat-icon tables">
          <i class="pi pi-table"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ project.total_target_tables }}</span>
          <span class="stat-label">Target Tables</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon complete">
          <i class="pi pi-check-circle"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ project.tables_complete }}</span>
          <span class="stat-label">Tables Complete</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon progress">
          <i class="pi pi-spinner"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ project.tables_in_progress }}</span>
          <span class="stat-label">In Progress</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon columns">
          <i class="pi pi-list"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ project.columns_mapped }} / {{ project.total_target_columns }}</span>
          <span class="stat-label">Columns Mapped</span>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && targetTables.length === 0" class="loading-container">
      <ProgressSpinner />
      <p>Loading target tables...</p>
    </div>

    <!-- Error State -->
    <Message v-if="error" severity="error" :closable="true">
      {{ error }}
    </Message>

    <!-- Target Tables List -->
    <div class="tables-section" v-if="!loading || targetTables.length > 0">
      <div class="section-header">
        <h2>Target Tables</h2>
        <div class="section-actions">
          <IconField iconPosition="left">
            <InputIcon class="pi pi-search" />
            <InputText 
              v-model="tableSearch" 
              placeholder="Search tables..." 
              class="table-search"
            />
          </IconField>
        </div>
      </div>

      <DataTable 
        :value="filteredTables" 
        :paginator="true"
        :rows="15"
        :rowsPerPageOptions="[10, 15, 25, 50]"
        stripedRows
        class="tables-table"
        :rowClass="getRowClass"
      >
        <Column header="Table" :sortable="true" style="min-width: 14rem">
          <template #body="{ data }">
            <div class="table-name-cell">
              <i class="pi pi-table table-icon"></i>
              <div class="table-info">
                <strong>{{ data.tgt_table_name }}</strong>
                <span class="physical-name">{{ data.tgt_table_physical_name }}</span>
              </div>
            </div>
          </template>
        </Column>

        <Column header="Status" :sortable="true" style="min-width: 10rem">
          <template #body="{ data }">
            <Tag 
              :value="formatStatus(data.mapping_status)" 
              :severity="getTableStatusSeverity(data.mapping_status)"
              :icon="getTableStatusIcon(data.mapping_status)"
            />
          </template>
        </Column>

        <Column header="Progress" style="min-width: 12rem">
          <template #body="{ data }">
            <div class="progress-cell">
              <ProgressBar 
                :value="getTableProgress(data)" 
                :showValue="false"
                class="table-progress-bar"
              />
              <span class="progress-text">
                {{ data.columns_mapped }} / {{ data.total_columns }}
                ({{ getTableProgress(data) }}%)
              </span>
            </div>
          </template>
        </Column>

        <Column header="Pending" :sortable="true" style="min-width: 6rem">
          <template #body="{ data }">
            <Badge 
              :value="data.columns_pending_review" 
              :severity="data.columns_pending_review > 0 ? 'warning' : 'secondary'"
            />
          </template>
        </Column>

        <Column header="Confidence" style="min-width: 8rem">
          <template #body="{ data }">
            <div v-if="data.avg_confidence" class="confidence-cell">
              <ProgressBar 
                :value="data.avg_confidence * 100" 
                :showValue="false"
                :class="getConfidenceClass(data.avg_confidence)"
                style="width: 60px; height: 6px;"
              />
              <span>{{ (data.avg_confidence * 100).toFixed(0) }}%</span>
            </div>
            <span v-else class="no-data">-</span>
          </template>
        </Column>

        <Column :exportable="false" style="min-width: 14rem">
          <template #body="{ data }">
            <div class="action-buttons">
              <Button 
                v-if="data.mapping_status === 'NOT_STARTED'"
                icon="pi pi-play" 
                label="Discover"
                size="small"
                @click="handleStartDiscovery(data)"
                v-tooltip.top="'Start AI Discovery'"
              />
              <Button 
                v-else-if="data.mapping_status === 'DISCOVERING'"
                icon="pi pi-spinner pi-spin" 
                label="Discovering..."
                size="small"
                severity="secondary"
                disabled
              />
              <Button 
                v-else
                icon="pi pi-eye" 
                label="Review"
                size="small"
                severity="info"
                @click="handleReviewTable(data)"
              />
              <Button 
                icon="pi pi-ellipsis-v" 
                text 
                rounded 
                size="small"
                @click="toggleTableMenu($event, data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>

      <!-- Empty State -->
      <div v-if="targetTables.length === 0 && !loading" class="empty-state">
        <i class="pi pi-table" style="font-size: 4rem; color: var(--text-color-secondary);"></i>
        <h3>No Target Tables Yet</h3>
        <p>Upload source fields and initialize target tables to get started.</p>
        <div class="empty-actions">
          <Button label="Upload Sources" icon="pi pi-upload" @click="showUploadDialog = true" />
          <Button label="Initialize Tables" icon="pi pi-database" severity="info" @click="handleInitializeTables" />
        </div>
      </div>
    </div>

    <!-- Table Context Menu -->
    <Menu ref="tableMenu" :model="tableMenuItems" :popup="true" />

    <!-- Upload Dialog -->
    <Dialog 
      v-model:visible="showUploadDialog" 
      modal 
      header="Upload Source Fields" 
      :style="{ width: '600px' }"
    >
      <div class="upload-content">
        <Message severity="info" :closable="false">
          <strong>Important:</strong> The <code>src_comments</code> field is essential for AI matching. 
          Without descriptions, the AI cannot find the best source columns for your target fields.
        </Message>
        
        <p class="mt-3">Download the template, fill in your source fields, and upload the CSV file.</p>
        
        <div class="template-section">
          <Button 
            label="Download Template" 
            icon="pi pi-download" 
            outlined
            severity="secondary"
            @click="handleDownloadTemplate"
            v-tooltip.top="'Download CSV template with required format'"
          />
        </div>
        
        <h4>Required CSV Columns:</h4>
        <ul class="field-list">
          <li><code>src_table_name</code> - Logical source table name</li>
          <li><code>src_table_physical_name</code> - Physical table name in database</li>
          <li><code>src_column_name</code> - Logical source column name</li>
          <li><code>src_column_physical_name</code> - Physical column name in database</li>
          <li><code>src_physical_datatype</code> - Data type (STRING, INT, DATE, etc.)</li>
          <li><code>src_nullable</code> - Whether column is nullable (YES/NO)</li>
          <li><code>src_comments</code> - <strong>Column description (critical for AI matching)</strong></li>
          <li><code>domain</code> - Domain category (optional, e.g., member, provider)</li>
        </ul>
        
        <FileUpload
          mode="basic"
          accept=".csv"
          :maxFileSize="10000000"
          @select="handleFileSelect"
          chooseLabel="Select CSV File"
          class="w-full mt-3"
        />
        
        <div v-if="selectedFile" class="selected-file">
          <i class="pi pi-file"></i>
          <span>{{ selectedFile.name }}</span>
        </div>
      </div>

      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="showUploadDialog = false" 
          severity="secondary"
        />
        <Button 
          label="Upload" 
          icon="pi pi-upload" 
          @click="handleUpload"
          :loading="uploading"
          :disabled="!selectedFile"
        />
      </template>
    </Dialog>

    <!-- Review Suggestions Dialog -->
    <Dialog 
      v-model:visible="showReviewDialog" 
      modal 
      :header="`Review: ${reviewingTable?.tgt_table_name || ''}`" 
      :style="{ width: '95vw', maxWidth: '1400px' }"
      maximizable
    >
      <SuggestionReviewPanel
        v-if="reviewingTable"
        :project-id="projectId"
        :table-id="reviewingTable.target_table_status_id"
        :table-name="reviewingTable.tgt_table_name"
        @suggestion-updated="handleSuggestionUpdated"
      />
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useProjectsStore, type TargetTableStatus } from '@/stores/projectsStore'
import { useUserStore } from '@/stores/user'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import ProgressBar from 'primevue/progressbar'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Menu from 'primevue/menu'
import FileUpload from 'primevue/fileupload'
import SuggestionReviewPanel from '@/components/SuggestionReviewPanel.vue'

const router = useRouter()
const route = useRoute()
const toast = useToast()
const projectsStore = useProjectsStore()
const userStore = useUserStore()

// Props
const projectId = computed(() => Number(route.params.id))

// State
const tableSearch = ref('')
const showUploadDialog = ref(false)
const showReviewDialog = ref(false)
const uploading = ref(false)
const selectedFile = ref<File | null>(null)
const tableMenu = ref()
const selectedTable = ref<TargetTableStatus | null>(null)
const reviewingTable = ref<TargetTableStatus | null>(null)

// Computed
const project = computed(() => projectsStore.currentProject)
const targetTables = computed(() => projectsStore.targetTables)
const loading = computed(() => projectsStore.loading)
const error = computed(() => projectsStore.error)

const filteredTables = computed(() => {
  if (!tableSearch.value) return targetTables.value
  
  const query = tableSearch.value.toLowerCase()
  return targetTables.value.filter(t => 
    t.tgt_table_name.toLowerCase().includes(query) ||
    t.tgt_table_physical_name.toLowerCase().includes(query)
  )
})

const tableMenuItems = computed(() => [
  {
    label: 'Start Discovery',
    icon: 'pi pi-play',
    command: () => {
      if (selectedTable.value) handleStartDiscovery(selectedTable.value)
    },
    disabled: selectedTable.value?.mapping_status !== 'NOT_STARTED'
  },
  {
    label: 'Review Suggestions',
    icon: 'pi pi-eye',
    command: () => {
      if (selectedTable.value) handleReviewTable(selectedTable.value)
    }
  },
  {
    separator: true
  },
  {
    label: 'Skip Table',
    icon: 'pi pi-forward',
    command: () => {
      toast.add({ severity: 'info', summary: 'Coming Soon', detail: 'Skip table feature', life: 2000 })
    }
  }
])

// Lifecycle
onMounted(async () => {
  await loadData()
})

watch(() => route.params.id, () => {
  loadData()
})

// Methods
async function loadData() {
  await projectsStore.fetchProject(projectId.value)
  await projectsStore.fetchTargetTables(projectId.value)
}

function handleFileSelect(event: any) {
  selectedFile.value = event.files[0]
}

async function handleUpload() {
  if (!selectedFile.value) return
  
  uploading.value = true
  try {
    const result = await projectsStore.uploadSourceFields(projectId.value, selectedFile.value)
    
    toast.add({ 
      severity: 'success', 
      summary: 'Upload Complete', 
      detail: `Uploaded ${result.fields_uploaded} fields from ${result.tables_found?.length || 0} tables`,
      life: 5000 
    })
    
    showUploadDialog.value = false
    selectedFile.value = null
  } catch (e: any) {
    toast.add({ 
      severity: 'error', 
      summary: 'Upload Failed', 
      detail: e.message,
      life: 5000 
    })
  } finally {
    uploading.value = false
  }
}

function handleDownloadTemplate() {
  // Create CSV template for source fields - matches the original unmapped fields format
  const headers = [
    'src_table_name',
    'src_table_physical_name',
    'src_column_name',
    'src_column_physical_name',
    'src_physical_datatype',
    'src_nullable',
    'src_comments',
    'domain'
  ]
  
  const exampleRows = [
    [
      'T_MEMBER',
      't_member',
      'MEMBER_ID',
      'member_id',
      'STRING',
      'NO',
      'Unique member identifier assigned by the state',
      'member'
    ],
    [
      'T_MEMBER',
      't_member',
      'FIRST_NAME',
      'first_name',
      'STRING',
      'YES',
      'Member first name',
      'member'
    ],
    [
      'T_ADDRESS',
      't_address',
      'ADDR_LINE_1',
      'addr_line_1',
      'STRING',
      'YES',
      'Primary address street line 1',
      'member'
    ]
  ]
  
  const csvContent = [
    headers.join(','),
    ...exampleRows.map(row => row.map(cell => 
      // Escape cells containing commas or quotes
      cell.includes(',') || cell.includes('"') ? `"${cell.replace(/"/g, '""')}"` : cell
    ).join(','))
  ].join('\n')
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'source_fields_template.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  toast.add({
    severity: 'success',
    summary: 'Template Downloaded',
    detail: 'Fill in the template with your source fields and upload',
    life: 3000
  })
}

async function handleInitializeTables() {
  try {
    const result = await projectsStore.initializeTargetTables(
      projectId.value, 
      project.value?.target_domains || undefined
    )
    
    toast.add({ 
      severity: 'success', 
      summary: 'Tables Initialized', 
      detail: `Initialized ${result.tables_initialized} target tables`,
      life: 3000 
    })
    
    await loadData()
  } catch (e: any) {
    toast.add({ 
      severity: 'error', 
      summary: 'Initialization Failed', 
      detail: e.message,
      life: 5000 
    })
  }
}

async function handleStartDiscovery(table: TargetTableStatus) {
  try {
    await projectsStore.startDiscovery(
      projectId.value,
      table.target_table_status_id,
      userStore.userEmail || 'unknown'
    )
    
    toast.add({ 
      severity: 'info', 
      summary: 'Discovery Started', 
      detail: `AI is discovering mappings for ${table.tgt_table_name}`,
      life: 3000 
    })
    
    // Poll for completion
    pollForDiscovery(table.target_table_status_id)
  } catch (e: any) {
    toast.add({ 
      severity: 'error', 
      summary: 'Discovery Failed', 
      detail: e.message,
      life: 5000 
    })
  }
}

async function pollForDiscovery(tableId: number) {
  // Poll every 5 seconds for up to 5 minutes
  const maxAttempts = 60
  let attempts = 0
  
  const interval = setInterval(async () => {
    attempts++
    await projectsStore.fetchTargetTables(projectId.value)
    
    const table = targetTables.value.find(t => t.target_table_status_id === tableId)
    
    if (!table || table.mapping_status !== 'DISCOVERING' || attempts >= maxAttempts) {
      clearInterval(interval)
      
      if (table?.mapping_status === 'SUGGESTIONS_READY') {
        toast.add({ 
          severity: 'success', 
          summary: 'Discovery Complete', 
          detail: `${table.tgt_table_name} has ${table.columns_pending_review} suggestions ready for review`,
          life: 5000 
        })
      }
    }
  }, 5000)
}

function handleReviewTable(table: TargetTableStatus) {
  reviewingTable.value = table
  showReviewDialog.value = true
}

async function handleSuggestionUpdated() {
  // Refresh table data when suggestion is updated
  await projectsStore.fetchTargetTables(projectId.value)
  await projectsStore.fetchProject(projectId.value)
}

function toggleTableMenu(event: Event, table: TargetTableStatus) {
  selectedTable.value = table
  tableMenu.value.toggle(event)
}

function getStatusSeverity(status: string): 'success' | 'info' | 'warning' | 'danger' | 'secondary' {
  switch (status) {
    case 'COMPLETE': return 'success'
    case 'ACTIVE': return 'info'
    case 'PAUSED': return 'warning'
    case 'DRAFT': return 'secondary'
    default: return 'secondary'
  }
}

function getTableStatusSeverity(status: string): 'success' | 'info' | 'warning' | 'danger' | 'secondary' {
  switch (status) {
    case 'COMPLETE': return 'success'
    case 'SUGGESTIONS_READY': return 'info'
    case 'IN_REVIEW': return 'info'
    case 'DISCOVERING': return 'warning'
    case 'NOT_STARTED': return 'secondary'
    case 'SKIPPED': return 'secondary'
    default: return 'secondary'
  }
}

function getTableStatusIcon(status: string): string {
  switch (status) {
    case 'COMPLETE': return 'pi pi-check-circle'
    case 'SUGGESTIONS_READY': return 'pi pi-inbox'
    case 'IN_REVIEW': return 'pi pi-eye'
    case 'DISCOVERING': return 'pi pi-spinner pi-spin'
    case 'NOT_STARTED': return 'pi pi-circle'
    case 'SKIPPED': return 'pi pi-forward'
    default: return ''
  }
}

function formatStatus(status: string): string {
  return status.replace(/_/g, ' ')
}

function getTableProgress(table: TargetTableStatus): number {
  if (!table.total_columns) return 0
  return Math.round((table.columns_mapped / table.total_columns) * 100)
}

function getConfidenceClass(confidence: number): string {
  if (confidence >= 0.8) return 'confidence-high'
  if (confidence >= 0.6) return 'confidence-medium'
  return 'confidence-low'
}

function getRowClass(data: TargetTableStatus): string {
  if (data.mapping_status === 'COMPLETE') return 'complete-row'
  if (data.mapping_status === 'SKIPPED') return 'skipped-row'
  return ''
}
</script>

<style scoped>
.project-detail-view {
  padding: 1.5rem;
  max-width: 1600px;
  margin: 0 auto;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-info h1 {
  margin: 0;
  color: var(--gainwell-dark);
  font-size: 1.5rem;
}

.subtitle {
  margin: 0.25rem 0 0 0;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.header-right {
  display: flex;
  gap: 0.5rem;
}

/* Stats Row */
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
  border: 1px solid var(--surface-border);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
}

.stat-icon.source-tables {
  background: #fce4ec;
  color: #c2185b;
}

.stat-icon.source-columns {
  background: #f3e5f5;
  color: #8e24aa;
}

.stat-icon.tables {
  background: #e3f2fd;
  color: #1976d2;
}

.stat-icon.complete {
  background: #e8f5e9;
  color: #388e3c;
}

.stat-icon.progress {
  background: #fff3e0;
  color: #f57c00;
}

.stat-icon.columns {
  background: #e0f7fa;
  color: #00838f;
}

.stat-card.source {
  border-left: 3px solid #c2185b;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-color);
}

.stat-label {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  gap: 1rem;
}

/* Tables Section */
.tables-section {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h2 {
  margin: 0;
  color: var(--text-color);
  font-size: 1.25rem;
}

.table-search {
  width: 250px;
}

/* Table cells */
.table-name-cell {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.table-icon {
  color: var(--gainwell-secondary);
  font-size: 1.25rem;
}

.table-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.physical-name {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  font-family: monospace;
}

.progress-cell {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.table-progress-bar {
  height: 6px;
}

.progress-text {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.confidence-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.no-data {
  color: var(--text-color-secondary);
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

/* Empty State */
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

.empty-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

/* Upload Dialog */
.upload-content {
  line-height: 1.6;
}

.upload-content h4 {
  margin: 1rem 0 0.5rem 0;
  color: var(--text-color);
  font-size: 0.95rem;
}

.upload-content .field-list {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.upload-content .field-list li {
  margin-bottom: 0.35rem;
}

.upload-content code {
  background: var(--surface-100);
  padding: 0.15rem 0.35rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-family: 'SF Mono', 'Consolas', monospace;
}

.template-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 1rem 0;
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 8px;
  border: 1px dashed var(--surface-300);
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.75rem;
  background: var(--surface-100);
  border-radius: 6px;
}

.w-full {
  width: 100%;
}

/* Row classes */
:deep(.complete-row) {
  background: #f1f8e9 !important;
}

:deep(.skipped-row) {
  opacity: 0.6;
}

/* Confidence colors */
:deep(.confidence-high) .p-progressbar-value {
  background: #4caf50 !important;
}

:deep(.confidence-medium) .p-progressbar-value {
  background: #ff9800 !important;
}

:deep(.confidence-low) .p-progressbar-value {
  background: #f44336 !important;
}

/* Responsive */
@media (max-width: 768px) {
  .project-detail-view {
    padding: 1rem;
  }
  
  .view-header {
    flex-direction: column;
  }
  
  .header-right {
    width: 100%;
  }
  
  .stats-row {
    grid-template-columns: 1fr 1fr;
  }
  
  .section-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .table-search {
    width: 100%;
  }
}
</style>

