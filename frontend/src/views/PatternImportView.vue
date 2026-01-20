<template>
  <div class="pattern-import-view">
    <div class="view-header">
      <div class="header-info">
        <h1><i class="pi pi-upload"></i> Import Historical Patterns</h1>
        <p class="subtitle">
          Upload a CSV with historical mappings to create approved patterns for AI learning
        </p>
      </div>
      <Tag value="Admin Only" severity="warning" />
    </div>

    <!-- Steps indicator -->
    <Steps :model="steps" :activeIndex="activeStep" class="mb-4" />

    <!-- Step 1: Upload -->
    <div v-if="activeStep === 0" class="step-content">
      <Card>
        <template #title>Upload CSV File</template>
        <template #subtitle>
          Upload a CSV file containing historical mapping patterns
        </template>
        <template #content>
          <div class="upload-section">
            <FileUpload 
              mode="basic" 
              accept=".csv"
              :auto="false"
              chooseLabel="Select CSV File"
              @select="onFileSelect"
              class="mb-3"
            />
            
            <div v-if="selectedFile" class="selected-file">
              <i class="pi pi-file"></i>
              <span>{{ selectedFile.name }}</span>
              <Button icon="pi pi-times" text rounded size="small" @click="selectedFile = null" />
            </div>

            <Message v-if="uploadError" severity="error" class="mt-3">
              {{ uploadError }}
            </Message>

            <div v-if="parsedData" class="parsed-preview mt-4">
              <h4>Preview ({{ parsedData.total_rows }} rows)</h4>
              <div class="csv-headers">
                <Tag v-for="header in parsedData.headers" :key="header" :value="header" severity="info" class="mr-1 mb-1" />
              </div>
              
              <DataTable :value="parsedData.preview_rows" class="mt-3" :paginator="false" scrollable scrollHeight="300px">
                <Column v-for="header in parsedData.headers" :key="header" :field="header" :header="header" style="min-width: 150px">
                  <template #body="{ data }">
                    <span class="cell-preview">{{ truncate(data[header], 50) }}</span>
                  </template>
                </Column>
              </DataTable>
            </div>
          </div>
        </template>
        <template #footer>
          <div class="step-actions">
            <Button label="Next: Map Columns" icon="pi pi-arrow-right" iconPos="right" @click="goToStep(1)" :disabled="!parsedData" />
          </div>
        </template>
      </Card>
    </div>

    <!-- Step 2: Map Columns -->
    <div v-if="activeStep === 1" class="step-content">
      <Card>
        <template #title>Map CSV Columns</template>
        <template #subtitle>
          Map your CSV columns to the mapped_fields table structure
        </template>
        <template #content>
          <div class="column-mapping-grid">
            <div class="mapping-row header">
              <div class="target-col">Target Field (mapped_fields)</div>
              <div class="csv-col">CSV Column</div>
            </div>
            
            <div v-for="col in mappableColumns" :key="col.name" class="mapping-row">
              <div class="target-col">
                <span class="col-name">{{ col.name }}</span>
                <Tag v-if="col.required" value="Required" severity="danger" size="small" />
              </div>
              <div class="csv-col">
                <Dropdown
                  v-model="columnMapping[col.name]"
                  :options="csvColumnOptions"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Select CSV column"
                  showClear
                  class="w-full"
                />
              </div>
            </div>
          </div>

          <Message v-if="mappingError" severity="error" class="mt-3">
            {{ mappingError }}
          </Message>
        </template>
        <template #footer>
          <div class="step-actions">
            <Button label="Back" icon="pi pi-arrow-left" severity="secondary" @click="goToStep(0)" />
            <Button label="Next: Process Patterns" icon="pi pi-arrow-right" iconPos="right" @click="createAndProcess" :loading="processing" :disabled="!isMappingValid" />
          </div>
        </template>
      </Card>
    </div>

    <!-- Step 3: Processing -->
    <div v-if="activeStep === 2" class="step-content">
      <Card>
        <template #title>Processing Patterns</template>
        <template #subtitle>
          Generating join_metadata for each pattern using AI...
        </template>
        <template #content>
          <div class="processing-section">
            <ProgressBar :value="processingProgress" class="mb-3" />
            <p class="text-center">
              Processing {{ processingProgress }}% complete
            </p>
            
            <div v-if="processingProgress < 100" class="processing-spinner">
              <ProgressSpinner style="width: 50px; height: 50px" />
              <span>This may take a few minutes for large files...</span>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Step 4: Review -->
    <div v-if="activeStep === 3" class="step-content">
      <Card>
        <template #title>Review Patterns</template>
        <template #subtitle>
          <div class="processing-status">
            <span v-if="!processingComplete">
              <i class="pi pi-spin pi-spinner"></i>
              Processing {{ processedCount }}/{{ totalToProcess }}...
            </span>
            <span v-else>
              <i class="pi pi-check-circle text-green-500"></i>
              Complete! {{ successfulPatterns.length }} processed, 
              {{ savablePatterns.length }} ready to save,
              {{ missingSemanticFieldPatterns.length }} missing semantic field,
              {{ failedPatterns.length }} failed
            </span>
          </div>
          <ProgressBar :value="processingProgress" class="mt-2" style="height: 8px" />
        </template>
        <template #content>
          <DataTable 
            :value="processedPatterns" 
            :paginator="true" 
            :rows="10"
            v-model:selection="selectedPatterns"
            dataKey="row_index"
            class="patterns-table"
          >
            <Column selectionMode="multiple" headerStyle="width: 3rem" />
            
            <Column field="status" header="Status" sortable style="width: 100px">
              <template #body="{ data }">
                <Tag v-if="data.status === 'READY' && !data.semantic_field_warning" value="Ready" severity="success" />
                <Tag v-else-if="data.status === 'READY' && data.semantic_field_warning" value="Warning" severity="warning" />
                <Tag v-else-if="data.status === 'ERROR'" value="Error" severity="danger" />
                <Tag v-else value="Processing" severity="info" />
              </template>
            </Column>
            
            <Column field="semantic_field_id" header="Semantic Field" sortable style="width: 130px">
              <template #body="{ data }">
                <Tag v-if="data.semantic_field_id" :value="'ID: ' + data.semantic_field_id" severity="success" />
                <Tag v-else value="Not Found" severity="danger" v-tooltip.top="data.semantic_field_warning || 'No matching target field in semantic_fields table'" />
              </template>
            </Column>
            
            <Column field="tgt_table_physical_name" header="Target Table" sortable style="min-width: 150px" />
            
            <Column field="tgt_column_physical_name" header="Target Column" sortable style="min-width: 150px">
              <template #body="{ data }">
                <code>{{ data.tgt_column_physical_name }}</code>
              </template>
            </Column>
            
            <Column field="source_relationship_type" header="Type" sortable style="width: 100px">
              <template #body="{ data }">
                <Tag :value="data.source_relationship_type || 'SINGLE'" />
              </template>
            </Column>
            
            <Column field="join_metadata" header="Metadata" style="width: 120px">
              <template #body="{ data }">
                <Tag v-if="data.join_metadata" value="Generated" severity="success" />
                <Tag v-else-if="data.status === 'ERROR'" value="Failed" severity="danger" />
                <Tag v-else value="None" severity="warning" />
              </template>
            </Column>
            
            <Column field="source_expression" header="SQL Preview" style="min-width: 300px">
              <template #body="{ data }">
                <code class="sql-preview">{{ truncate(data.source_expression, 100) }}</code>
                <div v-if="data.error" class="error-text">{{ data.error }}</div>
              </template>
            </Column>
            
            <Column header="Actions" style="width: 80px">
              <template #body="{ data }">
                <Button icon="pi pi-eye" text rounded size="small" @click="showPatternDetail(data)" v-tooltip.top="'View Details'" />
              </template>
            </Column>
          </DataTable>

          <div v-if="processingErrors.length" class="errors-section mt-4">
            <h4 class="text-red-500"><i class="pi pi-exclamation-triangle"></i> Errors ({{ processingErrors.length }})</h4>
            <ul>
              <li v-for="(error, i) in processingErrors" :key="i">
                Row {{ error.row_index + 1 }} ({{ error.column || 'unknown' }}): {{ error.error }}
              </li>
            </ul>
          </div>
        </template>
        <template #footer>
          <div class="step-actions">
            <Button label="Back" icon="pi pi-arrow-left" severity="secondary" @click="goToStep(1)" :disabled="!processingComplete || saving" />
            <span class="selection-info">
              {{ selectedPatterns.length }} selected ({{ savablePatterns.length }} savable, {{ missingSemanticFieldPatterns.length }} missing semantic field)
            </span>
            <div class="project-type-selector">
              <label>Project Type: </label>
              <Dropdown 
                v-model="selectedProjectType" 
                :options="projectTypes" 
                placeholder="Select project type *"
                style="min-width: 150px;"
              />
            </div>
            <Button 
              label="Save Selected Patterns" 
              icon="pi pi-check" 
              @click="savePatterns" 
              :loading="saving" 
              :disabled="!processingComplete || !selectedPatterns.length || saving || !selectedProjectType"
            />
          </div>
          
          <!-- Save Progress -->
          <div v-if="saving" class="save-progress mt-4">
            <div class="progress-header">
              <span>Saving patterns to database...</span>
              <span class="progress-text">{{ saveProgress.current }} / {{ saveProgress.total }}</span>
            </div>
            <ProgressBar :value="saveProgress.percent" :showValue="false" class="mt-2" />
            <div v-if="saveProgress.currentPattern" class="current-pattern mt-2">
              <i class="pi pi-spin pi-spinner mr-2"></i>
              Saving: <strong>{{ saveProgress.currentPattern }}</strong>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Step 5: Complete -->
    <div v-if="activeStep === 4" class="step-content">
      <Card>
        <template #title>
          <i class="pi pi-check-circle text-green-500"></i> Import Complete
        </template>
        <template #content>
          <div class="complete-section">
            <Message severity="success">
              Successfully imported {{ savedCount }} patterns as approved patterns.
              Vector search index has been synced.
            </Message>
            
            <p class="mt-4">
              These patterns are now available for AI to learn from when generating mapping suggestions.
            </p>
          </div>
        </template>
        <template #footer>
          <div class="step-actions">
            <Button label="Import More Patterns" icon="pi pi-plus" @click="resetWizard" />
            <Button label="Go to Projects" icon="pi pi-arrow-right" severity="secondary" @click="$router.push('/projects')" />
          </div>
        </template>
      </Card>
    </div>

    <!-- Pattern Detail Dialog -->
    <Dialog v-model:visible="showDetailDialog" modal header="Pattern Details" :style="{ width: '800px' }">
      <div v-if="detailPattern" class="pattern-detail">
        <div class="detail-row">
          <label>Target:</label>
          <span>{{ detailPattern.tgt_table_physical_name }}.{{ detailPattern.tgt_column_physical_name }}</span>
        </div>
        
        <div class="detail-row">
          <label>Source Tables:</label>
          <span>{{ detailPattern.source_tables_physical || '-' }}</span>
        </div>
        
        <div class="detail-row">
          <label>Source Columns:</label>
          <span>{{ detailPattern.source_columns_physical || '-' }}</span>
        </div>
        
        <div class="detail-row">
          <label>Type:</label>
          <Tag :value="detailPattern.source_relationship_type || 'SINGLE'" />
        </div>
        
        <div class="detail-row">
          <label>Transformations:</label>
          <span>{{ detailPattern.transformations_applied || '-' }}</span>
        </div>
        
        <h4 class="mt-4">SQL Expression</h4>
        <pre class="sql-block">{{ detailPattern.source_expression }}</pre>
        
        <h4 class="mt-4">Join Metadata (AI Generated)</h4>
        <pre class="json-block">{{ formatJson(detailPattern.join_metadata) }}</pre>
      </div>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useUserStore } from '@/stores/user'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Steps from 'primevue/steps'
import Tag from 'primevue/tag'
import FileUpload from 'primevue/fileupload'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dropdown from 'primevue/dropdown'
import ProgressBar from 'primevue/progressbar'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'

const router = useRouter()
const toast = useToast()
const userStore = useUserStore()

// Helper to get auth headers with user email
function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {}
  if (userStore.userEmail) {
    headers['X-User-Email'] = userStore.userEmail
  }
  return headers
}

// Steps
const steps = ref([
  { label: 'Upload' },
  { label: 'Map Columns' },
  { label: 'Process' },
  { label: 'Review' },
  { label: 'Complete' }
])
const activeStep = ref(0)

// State
const selectedFile = ref<File | null>(null)
const parsedData = ref<any>(null)
const uploadError = ref('')
const mappingError = ref('')
const columnMapping = ref<Record<string, string>>({})
const sessionId = ref('')
const processing = ref(false)
const processingProgress = ref(0)
const processingComplete = ref(false)
const processedCount = ref(0)
const totalToProcess = ref(0)
const processedPatterns = ref<any[]>([])
const processingErrors = ref<any[]>([])
const selectedPatterns = ref<any[]>([])
const saving = ref(false)
const savedCount = ref(0)
const projectTypes = ref<string[]>([])
const selectedProjectType = ref('')
const saveProgress = ref({
  percent: 0,
  current: 0,
  total: 0,
  currentPattern: ''
})
const savePollingInterval = ref<number | null>(null)
const showDetailDialog = ref(false)
const detailPattern = ref<any>(null)

// Mappable columns (source_relationship_type, transformations_applied, confidence_score are auto-populated)
const mappableColumns = computed(() => [
  { name: 'tgt_table_name', required: false },
  { name: 'tgt_table_physical_name', required: true },
  { name: 'tgt_column_name', required: false },
  { name: 'tgt_column_physical_name', required: true },
  { name: 'tgt_comments', required: false },
  { name: 'source_expression', required: true },
  { name: 'source_tables', required: false },
  { name: 'source_tables_physical', required: false },
  { name: 'source_columns', required: false },
  { name: 'source_columns_physical', required: false },
  { name: 'source_descriptions', required: false },
  { name: 'source_datatypes', required: false },
  { name: 'source_domain', required: false },
  { name: 'target_domain', required: false },
  { name: 'join_column_description', required: false }  // COLUMN:Description|... for join/filter columns
])

const csvColumnOptions = computed(() => {
  if (!parsedData.value?.headers) return []
  return [
    { label: '-- Not Mapped --', value: '' },
    ...parsedData.value.headers.map((h: string) => ({ label: h, value: h }))
  ]
})

const successfulPatterns = computed(() => {
  return processedPatterns.value.filter(p => p.status === 'READY')
})

const failedPatterns = computed(() => {
  return processedPatterns.value.filter(p => p.status === 'ERROR')
})

const missingSemanticFieldPatterns = computed(() => {
  return processedPatterns.value.filter(p => p.semantic_field_warning || !p.semantic_field_id)
})

const savablePatterns = computed(() => {
  return processedPatterns.value.filter(p => p.status === 'READY' && p.semantic_field_id)
})

const isMappingValid = computed(() => {
  const required = ['tgt_table_physical_name', 'tgt_column_physical_name', 'source_expression']
  return required.every(col => columnMapping.value[col])
})

// Methods
function goToStep(step: number) {
  activeStep.value = step
}

async function onFileSelect(event: any) {
  const file = event.files[0]
  if (!file) return
  
  selectedFile.value = file
  uploadError.value = ''
  
  try {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch('/api/v4/admin/patterns/upload', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData
    })
    
    if (response.ok) {
      parsedData.value = await response.json()
      
      // Auto-map columns with matching names
      for (const col of mappableColumns.value) {
        const match = parsedData.value.headers.find((h: string) => 
          h.toLowerCase() === col.name.toLowerCase() ||
          h.toLowerCase().replace(/_/g, '') === col.name.toLowerCase().replace(/_/g, '')
        )
        if (match) {
          columnMapping.value[col.name] = match
        }
      }
    } else {
      const error = await response.json()
      uploadError.value = error.detail || 'Upload failed'
    }
  } catch (e: any) {
    uploadError.value = e.message
  }
}

async function createAndProcess() {
  if (!selectedFile.value || !isMappingValid.value) return
  
  processing.value = true
  mappingError.value = ''
  
  try {
    // Create session
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('column_mapping', JSON.stringify(columnMapping.value))
    
    const createResponse = await fetch('/api/v4/admin/patterns/session', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData
    })
    
    if (!createResponse.ok) {
      throw new Error('Failed to create session')
    }
    
    const sessionData = await createResponse.json()
    sessionId.value = sessionData.session_id
    
    // Move to processing step - show review immediately so user sees progress
    activeStep.value = 3
    processingProgress.value = 0
    processedPatterns.value = []
    processingErrors.value = []
    processingComplete.value = false
    
    // Start polling for progress
    const pollInterval = setInterval(async () => {
      try {
        const previewResponse = await fetch(`/api/v4/admin/patterns/session/${sessionId.value}/preview`, {
          headers: getAuthHeaders()
        })
        if (previewResponse.ok) {
          const preview = await previewResponse.json()
          processedPatterns.value = preview.patterns || []
          processingErrors.value = preview.errors || []
          
          // Calculate progress
          const total = preview.total_rows || 10
          const processed = processedPatterns.value.length
          processingProgress.value = Math.round((processed / total) * 100)
          processedCount.value = processed
          totalToProcess.value = total
          
          // Check if complete
          if (preview.session_status === 'READY_FOR_REVIEW') {
            clearInterval(pollInterval)
            processingComplete.value = true
            processingProgress.value = 100
            
            // Select only successful patterns by default
            selectedPatterns.value = processedPatterns.value.filter(p => p.status === 'READY')
          }
        }
      } catch (e) {
        console.error('Error polling progress:', e)
      }
    }, 2000) // Poll every 2 seconds
    
    // Start processing in background (returns immediately)
    const processResponse = await fetch(`/api/v4/admin/patterns/session/${sessionId.value}/process`, {
      method: 'POST',
      headers: getAuthHeaders()
    })
    
    if (!processResponse.ok) {
      clearInterval(pollInterval)
      const errorData = await processResponse.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Failed to start processing')
    }
    
    // Processing started in background - polling will track progress
    // The pollInterval will detect when session_status === 'READY_FOR_REVIEW'
    // and set processingComplete = true
    console.log('Processing started in background, polling for progress...')
    
  } catch (e: any) {
    mappingError.value = e.message
    activeStep.value = 1  // Go back to mapping
    processing.value = false
  }
  // Note: Don't set processing = false here since polling continues
}

async function savePatterns() {
  if (!selectedPatterns.value.length) return
  
  saving.value = true
  saveProgress.value = {
    percent: 0,
    current: 0,
    total: selectedPatterns.value.length,
    currentPattern: ''
  }
  
  // Start polling for save progress
  startSaveProgressPolling()
  
  try {
    const indices = selectedPatterns.value.map(p => p.row_index)
    
    console.log('Saving patterns - session:', sessionId.value, 'indices:', indices)
    
    const response = await fetch(`/api/v4/admin/patterns/session/${sessionId.value}/save`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({ 
        pattern_indices: indices,
        project_type: selectedProjectType.value
      })
    })
    
    console.log('Save response status:', response.status, 'project_type:', selectedProjectType.value)
    
    if (response.ok) {
      const result = await response.json()
      savedCount.value = result.saved_count || 0
      
      // Update progress to 100%
      saveProgress.value = {
        percent: 100,
        current: savedCount.value,
        total: selectedPatterns.value.length,
        currentPattern: ''
      }
      
      toast.add({
        severity: 'success',
        summary: 'Patterns Saved',
        detail: `${savedCount.value} patterns imported successfully`,
        life: 3000
      })
      
      activeStep.value = 4
    } else {
      throw new Error('Save failed')
    }
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 3000 })
  } finally {
    stopSaveProgressPolling()
    saving.value = false
  }
}

function startSaveProgressPolling() {
  // Poll every 500ms for save progress
  savePollingInterval.value = window.setInterval(async () => {
    try {
      const response = await fetch(
        `/api/v4/admin/patterns/session/${sessionId.value}/preview`,
        { headers: getAuthHeaders() }
      )
      if (response.ok) {
        const data = await response.json()
        if (data.save_status === 'SAVING') {
          saveProgress.value = {
            percent: data.save_progress || 0,
            current: data.save_current || 0,
            total: data.save_total || selectedPatterns.value.length,
            currentPattern: data.save_current_pattern || ''
          }
        }
      }
    } catch (e) {
      console.error('Save progress poll error:', e)
    }
  }, 500)
}

function stopSaveProgressPolling() {
  if (savePollingInterval.value) {
    clearInterval(savePollingInterval.value)
    savePollingInterval.value = null
  }
}

function showPatternDetail(pattern: any) {
  detailPattern.value = pattern
  showDetailDialog.value = true
}

function resetWizard() {
  activeStep.value = 0
  selectedFile.value = null
  parsedData.value = null
  columnMapping.value = {}
  sessionId.value = ''
  processedPatterns.value = []
  processingErrors.value = []
  selectedPatterns.value = []
  savedCount.value = 0
}

function truncate(str: string, len: number): string {
  if (!str) return ''
  return str.length > len ? str.substring(0, len) + '...' : str
}

function formatJson(str: string): string {
  if (!str) return 'Not generated'
  try {
    return JSON.stringify(JSON.parse(str), null, 2)
  } catch {
    return str
  }
}

// Fetch project types from config
async function fetchProjectTypes() {
  try {
    const response = await fetch('/api/config/project-types')
    if (response.ok) {
      const data = await response.json()
      projectTypes.value = data.available_types || []
      // Set default
      if (data.default_type && !selectedProjectType.value) {
        selectedProjectType.value = data.default_type
      }
    }
  } catch (error) {
    console.error('Failed to fetch project types:', error)
    // Fallback
    projectTypes.value = ['DMES', 'MMIS', 'CLAIMS', 'ELIGIBILITY', 'PROVIDER', 'PHARMACY']
    selectedProjectType.value = 'DMES'
  }
}

// Check admin on mount and fetch project types
onMounted(async () => {
  if (!userStore.isAdmin) {
    toast.add({
      severity: 'warn',
      summary: 'Admin Required',
      detail: 'Pattern import is an admin-only feature',
      life: 5000
    })
  }
  await fetchProjectTypes()
})
</script>

<style scoped>
.pattern-import-view {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.header-info h1 {
  margin: 0;
  color: var(--gainwell-dark);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.subtitle {
  margin: 0.5rem 0 0 0;
  color: var(--text-color-secondary);
}

.step-content {
  margin-top: 1rem;
}

.step-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.selection-info {
  color: var(--text-color-secondary);
}

/* Upload */
.selected-file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--surface-100);
  border-radius: 6px;
}

.csv-headers {
  display: flex;
  flex-wrap: wrap;
}

.cell-preview {
  font-size: 0.85rem;
}

/* Column Mapping */
.column-mapping-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.mapping-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  padding: 0.75rem;
  border-radius: 6px;
}

.mapping-row.header {
  background: var(--surface-100);
  font-weight: 600;
}

.mapping-row:not(.header):hover {
  background: var(--surface-50);
}

.target-col {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.col-name {
  font-family: monospace;
}

/* Processing */
.processing-section {
  padding: 2rem;
  text-align: center;
}

.processing-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
  color: var(--text-color-secondary);
}

/* Patterns Table */
.sql-preview {
  font-size: 0.8rem;
  background: var(--surface-100);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
}

.errors-section ul {
  color: var(--red-500);
  font-size: 0.9rem;
}

/* Complete */
.complete-section {
  padding: 2rem;
  text-align: center;
}

/* Detail Dialog */
.pattern-detail .detail-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.pattern-detail .detail-row label {
  font-weight: 600;
  min-width: 120px;
}

.processing-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.processing-status i {
  font-size: 1rem;
}

.error-text {
  color: var(--red-500);
  font-size: 0.8rem;
  margin-top: 0.25rem;
}

.sql-block, .json-block {
  background: var(--surface-100);
  padding: 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Save Progress */
.save-progress {
  background: var(--surface-50);
  border: 1px solid var(--surface-200);
  border-radius: 8px;
  padding: 1rem 1.5rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-text {
  font-weight: 600;
  color: var(--primary-color);
}

.current-pattern {
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}
</style>

