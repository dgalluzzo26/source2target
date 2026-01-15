<template>
  <div class="semantic-fields-view">
    <div class="view-header">
      <div>
        <h1>
          <i class="pi pi-database"></i>
          Semantic Target Fields
        </h1>
        <p class="subtitle">Manage target field definitions for AI-powered mapping suggestions</p>
      </div>
      <HelpButton 
        help-type="admin-config"
        label="Help"
        severity="help"
        icon="pi pi-question-circle"
        tooltip="Semantic fields documentation"
      />
    </div>

    <!-- Admin Check -->
    <Message v-if="!userStore.isAdmin" severity="warn" :closable="false">
      <strong>Admin Access Required:</strong> Only administrators can manage semantic target fields.
    </Message>

    <div v-else>
      <!-- Toolbar -->
      <div class="toolbar">
        <div class="toolbar-left">
          <IconField iconPosition="left">
            <InputIcon class="pi pi-search" />
            <InputText 
              v-model="searchQuery" 
              placeholder="Search by table, column, or description..."
              class="search-input"
            />
          </IconField>
        </div>
        <div class="toolbar-right">
          <Button 
            icon="pi pi-refresh" 
            @click="loadSemanticFields"
            :loading="loading"
            severity="secondary"
            v-tooltip.top="'Refresh'"
          />
          <Button 
            label="AI Enhance Descriptions" 
            icon="pi pi-sparkles" 
            @click="handleEnhanceDescriptions"
            :loading="enhancingDescriptions"
            severity="help"
            v-tooltip.top="'Use AI to enhance field descriptions'"
            :disabled="semanticFields.length === 0"
          />
          <Button 
            label="Download Template" 
            icon="pi pi-download" 
            @click="handleDownloadTemplate"
            severity="secondary"
            v-tooltip.top="'Download CSV template for bulk upload'"
          />
          <Button 
            label="Upload Fields" 
            icon="pi pi-upload" 
            @click="showUploadDialog = true"
            v-tooltip.top="'Bulk upload semantic fields from CSV'"
          />
        </div>
      </div>

      <!-- Info Message -->
      <Message severity="info" :closable="false" class="info-message">
        <strong>Bulk Upload:</strong> Download the CSV template, fill in your semantic fields, and upload for bulk import.
        Each field is automatically vectorized and indexed for semantic similarity search.
        Changes to fields will trigger a re-sync of the vector search index.
      </Message>

      <!-- Loading State -->
      <div v-if="loading" class="loading-container">
        <ProgressSpinner />
        <p>Loading semantic fields...</p>
      </div>

      <!-- Error State -->
      <Message v-if="error" severity="error" :closable="true" @close="error = null">
        {{ error }}
      </Message>

      <!-- Semantic Fields Table -->
      <div v-if="!loading && semanticFields.length > 0" class="table-container">
        <DataTable 
          :value="filteredFields" 
          :paginator="true"
          :rows="20"
          :rowsPerPageOptions="[10, 20, 50, 100]"
          paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
          currentPageReportTemplate="Showing {first} to {last} of {totalRecords} fields"
          class="semantic-table"
          stripedRows
          removableSort
        >
          <!-- Table Name -->
          <Column field="tgt_table_name" header="Target Table" :sortable="true" style="min-width: 12rem">
            <template #body="{ data }">
              <div class="table-cell">
                <i class="pi pi-table"></i>
                <span>{{ data.tgt_table_name }}</span>
              </div>
            </template>
          </Column>

          <!-- Column Name -->
          <Column field="tgt_column_name" header="Target Column" :sortable="true" style="min-width: 12rem">
            <template #body="{ data }">
              <strong>{{ data.tgt_column_name }}</strong>
            </template>
          </Column>

          <!-- Physical Name -->
          <Column field="tgt_column_physical_name" header="Physical Name" style="min-width: 12rem">
            <template #body="{ data }">
              <span class="physical-name">{{ data.tgt_column_physical_name }}</span>
            </template>
          </Column>

          <!-- Data Type -->
          <Column field="tgt_physical_datatype" header="Data Type" :sortable="true" style="min-width: 10rem">
            <template #body="{ data }">
              <Tag :value="data.tgt_physical_datatype" severity="info" />
            </template>
          </Column>

          <!-- Nullable -->
          <Column field="tgt_nullable" header="Nullable" :sortable="true" style="min-width: 8rem">
            <template #body="{ data }">
              <Tag 
                :value="data.tgt_nullable" 
                :severity="data.tgt_nullable === 'YES' ? 'warning' : 'success'"
              />
            </template>
          </Column>

          <!-- Description -->
          <Column field="tgt_comments" header="Description" style="min-width: 20rem">
            <template #body="{ data }">
              <span class="description-text">{{ data.tgt_comments || 'No description' }}</span>
            </template>
          </Column>

          <!-- Actions -->
          <Column :exportable="false" style="min-width: 8rem">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button 
                  icon="pi pi-pencil" 
                  severity="info" 
                  text 
                  rounded 
                  @click="handleEdit(data)"
                  v-tooltip.top="'Edit Field'"
                />
                <Button 
                  icon="pi pi-trash" 
                  severity="danger" 
                  text 
                  rounded 
                  @click="handleDelete(data)"
                  v-tooltip.top="'Delete Field'"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>

      <!-- Empty State -->
      <div v-if="!loading && semanticFields.length === 0" class="empty-state">
        <i class="pi pi-database" style="font-size: 4rem; color: var(--text-color-secondary);"></i>
        <h3>No Semantic Fields</h3>
        <p>Add target field definitions to enable AI-powered mapping suggestions.</p>
        <Button label="Add First Field" icon="pi pi-plus" @click="showAddDialog = true" />
      </div>
    </div>

    <!-- Add Dialog -->
    <Dialog 
      v-model:visible="showAddDialog" 
      modal 
      header="Add Semantic Field"
      :style="{ width: '600px' }"
    >
      <div class="form-content">
        <div class="field">
          <label for="add_tgt_table_name">Target Table Name *</label>
          <InputText 
            id="add_tgt_table_name"
            v-model="newField.tgt_table_name"
            placeholder="e.g., slv_member"
            class="w-full"
          />
        </div>

        <div class="field">
          <label for="add_tgt_table_physical_name">Target Table Physical Name</label>
          <InputText 
            id="add_tgt_table_physical_name"
            v-model="newField.tgt_table_physical_name"
            placeholder="e.g., slv_member (defaults to table name)"
            class="w-full"
          />
          <small>Optional: Leave blank to use table name</small>
        </div>

        <div class="field">
          <label for="add_tgt_column_name">Target Column Name *</label>
          <InputText 
            id="add_tgt_column_name"
            v-model="newField.tgt_column_name"
            placeholder="e.g., full_name"
            class="w-full"
          />
        </div>

        <div class="field">
          <label for="add_tgt_column_physical_name">Target Column Physical Name</label>
          <InputText 
            id="add_tgt_column_physical_name"
            v-model="newField.tgt_column_physical_name"
            placeholder="e.g., full_name (defaults to column name)"
            class="w-full"
          />
          <small>Optional: Leave blank to use column name</small>
        </div>

        <div class="field">
          <label for="add_tgt_physical_datatype">Data Type *</label>
          <Dropdown 
            id="add_tgt_physical_datatype"
            v-model="newField.tgt_physical_datatype"
            :options="dataTypes"
            placeholder="Select data type"
            class="w-full"
          />
        </div>

        <div class="field">
          <label for="add_tgt_nullable">Nullable *</label>
          <Dropdown 
            id="add_tgt_nullable"
            v-model="newField.tgt_nullable"
            :options="['YES', 'NO']"
            placeholder="Is nullable?"
            class="w-full"
          />
        </div>

        <div class="field">
          <label for="add_tgt_comments">Description</label>
          <Textarea 
            id="add_tgt_comments"
            v-model="newField.tgt_comments"
            rows="3"
            placeholder="Description for AI context..."
            class="w-full"
          />
          <small>Provide a detailed description to help the AI suggest better mappings</small>
        </div>
      </div>

      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="closeAddDialog" 
          severity="secondary"
        />
        <Button 
          label="Add Field" 
          icon="pi pi-check" 
          @click="handleAdd" 
          :loading="saving"
        />
      </template>
    </Dialog>

    <!-- Edit Dialog -->
    <Dialog 
      v-model:visible="showEditDialog" 
      modal 
      header="Edit Semantic Field"
      :style="{ width: '600px' }"
    >
      <div class="form-content" v-if="editingField">
        <div class="field">
          <label for="edit_tgt_table_name">Target Table Name *</label>
          <InputText 
            id="edit_tgt_table_name"
            v-model="editingField.tgt_table_name"
            class="w-full"
          />
        </div>

        <div class="field">
          <label for="edit_tgt_table_physical_name">Target Table Physical Name</label>
          <InputText 
            id="edit_tgt_table_physical_name"
            v-model="editingField.tgt_table_physical_name"
            class="w-full"
          />
        </div>

        <div class="field">
          <label for="edit_tgt_column_name">Target Column Name *</label>
          <InputText 
            id="edit_tgt_column_name"
            v-model="editingField.tgt_column_name"
            class="w-full"
          />
        </div>

        <div class="field">
          <label for="edit_tgt_column_physical_name">Target Column Physical Name</label>
          <InputText 
            id="edit_tgt_column_physical_name"
            v-model="editingField.tgt_column_physical_name"
            class="w-full"
          />
        </div>

        <div class="field">
          <label for="edit_tgt_physical_datatype">Data Type *</label>
          <Dropdown 
            id="edit_tgt_physical_datatype"
            v-model="editingField.tgt_physical_datatype"
            :options="dataTypes"
            class="w-full"
          />
        </div>

        <div class="field">
          <label for="edit_tgt_nullable">Nullable *</label>
          <Dropdown 
            id="edit_tgt_nullable"
            v-model="editingField.tgt_nullable"
            :options="['YES', 'NO']"
            class="w-full"
          />
        </div>

        <div class="field">
          <label for="edit_tgt_comments">Description</label>
          <Textarea 
            id="edit_tgt_comments"
            v-model="editingField.tgt_comments"
            rows="3"
            class="w-full"
          />
        </div>
      </div>

      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="closeEditDialog" 
          severity="secondary"
        />
        <Button 
          label="Save Changes" 
          icon="pi pi-check" 
          @click="handleUpdate" 
          :loading="saving"
        />
      </template>
    </Dialog>

    <!-- AI Enhance Descriptions Dialog -->
    <Dialog 
      v-model:visible="showEnhanceDescriptionsDialog" 
      modal 
      header="Review AI Enhanced Descriptions"
      :style="{ width: '900px', maxHeight: '80vh' }"
      :closable="!savingEnhancedFields"
    >
      <div class="enhance-dialog-content">
        <!-- Progress indicator while enhancing -->
        <div v-if="enhancingDescriptions" class="enhance-progress">
          <ProgressSpinner style="width: 50px; height: 50px;" />
          <p>Enhancing descriptions... {{ enhancedFieldsProgress }} / {{ enhancedFieldsTotal }}</p>
          <div class="enhance-progress-bar">
            <div 
              class="enhance-progress-fill" 
              :style="{ width: (enhancedFieldsProgress / enhancedFieldsTotal * 100) + '%' }"
            ></div>
          </div>
        </div>

        <!-- Results table -->
        <div v-else-if="enhancedFields.length > 0">
          <Message severity="info" :closable="false" class="mb-3">
            Review the enhanced descriptions below. You can edit any description before saving.
          </Message>
          
          <DataTable 
            :value="enhancedFields" 
            class="enhanced-fields-table"
            :scrollable="true"
            scrollHeight="400px"
          >
            <Column field="tgt_table_name" header="Table" style="width: 15%">
              <template #body="{ data }">
                <span class="table-name">{{ data.tgt_table_name }}</span>
              </template>
            </Column>
            <Column field="tgt_column_name" header="Column" style="width: 15%">
              <template #body="{ data }">
                <strong>{{ data.tgt_column_name }}</strong>
              </template>
            </Column>
            <Column field="original_description" header="Original" style="width: 25%">
              <template #body="{ data }">
                <span class="original-desc">{{ data.original_description || '(empty)' }}</span>
              </template>
            </Column>
            <Column field="enhanced_description" header="Enhanced Description" style="width: 35%">
              <template #body="{ data }">
                <div class="enhanced-description-cell">
                  <Textarea 
                    v-model="data.enhanced_description" 
                    rows="2" 
                    class="enhanced-description-textarea"
                    :disabled="savingEnhancedFields"
                  />
                </div>
              </template>
            </Column>
            <Column header="Status" style="width: 10%">
              <template #body="{ data }">
                <Tag 
                  :value="getEnhancedFieldStatus(data)"
                  :severity="getEnhancedFieldStatus(data) === 'Enhanced' ? 'success' : 'secondary'"
                />
              </template>
            </Column>
          </DataTable>
        </div>

        <!-- No results -->
        <div v-else class="no-enhanced-fields">
          <p>No fields were enhanced. This may be because all fields already have good descriptions or an error occurred.</p>
        </div>
      </div>

      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="showEnhanceDescriptionsDialog = false" 
          severity="secondary"
          :disabled="savingEnhancedFields"
        />
        <Button 
          label="Save Enhanced Descriptions" 
          icon="pi pi-check" 
          @click="saveEnhancedDescriptions"
          :loading="savingEnhancedFields"
          :disabled="enhancedFields.length === 0"
        />
      </template>
    </Dialog>

    <!-- Upload Dialog -->
    <Dialog 
      v-model:visible="showUploadDialog" 
      modal 
      header="Bulk Upload Semantic Fields"
      :style="{ width: '600px' }"
    >
      <div class="upload-content">
        <Message severity="info" :closable="false">
          <strong>CSV Format:</strong> Download the template first to see the required format.
        </Message>

        <div class="upload-instructions">
          <h4>Upload Instructions:</h4>
          <ol>
            <li>Download the CSV template using the "Download Template" button</li>
            <li>Fill in your semantic fields in the template</li>
            <li>Upload the completed CSV file below</li>
          </ol>
        </div>

        <div class="file-upload-area">
          <FileUpload
            mode="basic"
            name="semantic_fields"
            accept=".csv"
            :maxFileSize="5000000"
            :auto="false"
            chooseLabel="Choose CSV File"
            @select="handleFileSelect"
            :customUpload="true"
            @uploader="handleUpload"
          />
        </div>

        <div v-if="uploadPreview.length > 0" class="upload-preview">
          <h4>Preview (First 5 rows):</h4>
          <DataTable :value="uploadPreview" class="preview-table">
            <Column field="tgt_table_name" header="Table" style="width: 25%"></Column>
            <Column field="tgt_column_name" header="Column" style="width: 25%"></Column>
            <Column field="tgt_physical_datatype" header="Type" style="width: 15%"></Column>
            <Column field="tgt_comments" header="Description" style="width: 35%"></Column>
          </DataTable>
          <p class="preview-info">
            <strong>{{ uploadPreview.length }}</strong> fields ready to upload
          </p>
        </div>
      </div>

      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="closeUploadDialog" 
          severity="secondary"
        />
        <Button 
          label="Upload Fields" 
          icon="pi pi-upload" 
          @click="handleBulkUpload" 
          :loading="uploading"
          :disabled="uploadPreview.length === 0"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import FileUpload from 'primevue/fileupload'
import HelpButton from '@/components/HelpButton.vue'
import { SemanticAPI } from '@/services/api'

const userStore = useUserStore()
const confirm = useConfirm()
const toast = useToast()

// State
const semanticFields = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const showUploadDialog = ref(false)
const editingField = ref<any | null>(null)
const uploadPreview = ref<any[]>([])
const selectedFile = ref<File | null>(null)

// AI Enhance Descriptions state
const showEnhanceDescriptionsDialog = ref(false)
const enhancingDescriptions = ref(false)
const enhancedFields = ref<any[]>([])
const enhancedFieldsProgress = ref(0)
const enhancedFieldsTotal = ref(0)
const savingEnhancedFields = ref(false)

const newField = ref({
  tgt_table_name: '',
  tgt_table_physical_name: '',
  tgt_column_name: '',
  tgt_column_physical_name: '',
  tgt_physical_datatype: '',
  tgt_nullable: 'NO',
  tgt_comments: ''
})

const dataTypes = [
  'STRING',
  'INT',
  'BIGINT',
  'DOUBLE',
  'DECIMAL',
  'BOOLEAN',
  'DATE',
  'TIMESTAMP',
  'VARCHAR',
  'CHAR'
]

// Computed
const filteredFields = computed(() => {
  if (!searchQuery.value) return semanticFields.value
  
  const query = searchQuery.value.toLowerCase()
  return semanticFields.value.filter(f => 
    f.tgt_table_name?.toLowerCase().includes(query) ||
    f.tgt_column_name?.toLowerCase().includes(query) ||
    f.tgt_comments?.toLowerCase().includes(query)
  )
})

onMounted(async () => {
  if (userStore.isAdmin) {
    await loadSemanticFields()
  }
})

async function loadSemanticFields() {
  loading.value = true
  error.value = null
  
  try {
    const result = await SemanticAPI.getAllRecords()
    if (result.data) {
      semanticFields.value = result.data
      console.log(`[Semantic Fields] Loaded ${result.data.length} fields`)
    } else if (result.error) {
      error.value = result.error
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load semantic fields'
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  // Validate
  if (!newField.value.tgt_table_name || !newField.value.tgt_column_name || !newField.value.tgt_physical_datatype) {
    toast.add({
      severity: 'warn',
      summary: 'Validation Error',
      detail: 'Please fill in all required fields',
      life: 3000
    })
    return
  }

  // Default physical names if empty
  if (!newField.value.tgt_table_physical_name) {
    newField.value.tgt_table_physical_name = newField.value.tgt_table_name
  }
  if (!newField.value.tgt_column_physical_name) {
    newField.value.tgt_column_physical_name = newField.value.tgt_column_name
  }

  saving.value = true
  
  try {
    const result = await SemanticAPI.createRecord(newField.value)
    if (result.data) {
      semanticFields.value.push(result.data)
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Semantic field added successfully. Vector index will be synced.',
        life: 5000
      })
      closeAddDialog()
    } else if (result.error) {
      error.value = result.error
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to add semantic field'
  } finally {
    saving.value = false
  }
}

async function handleUpdate() {
  if (!editingField.value || !editingField.value.id) {
    return
  }

  // Validate
  if (!editingField.value.tgt_table_name || !editingField.value.tgt_column_name || !editingField.value.tgt_physical_datatype) {
    toast.add({
      severity: 'warn',
      summary: 'Validation Error',
      detail: 'Please fill in all required fields',
      life: 3000
    })
    return
  }

  saving.value = true
  
  try {
    const updateData = {
      tgt_table_name: editingField.value.tgt_table_name,
      tgt_table_physical_name: editingField.value.tgt_table_physical_name,
      tgt_column_name: editingField.value.tgt_column_name,
      tgt_column_physical_name: editingField.value.tgt_column_physical_name,
      tgt_nullable: editingField.value.tgt_nullable,
      tgt_physical_datatype: editingField.value.tgt_physical_datatype,
      tgt_comments: editingField.value.tgt_comments
    }
    
    const result = await SemanticAPI.updateRecord(editingField.value.id, updateData)
    if (result.data) {
      const index = semanticFields.value.findIndex(f => f.id === editingField.value!.id)
      if (index > -1) {
        semanticFields.value[index] = result.data
      }
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Semantic field updated successfully. Vector index will be synced.',
        life: 5000
      })
      closeEditDialog()
    } else if (result.error) {
      error.value = result.error
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to update semantic field'
  } finally {
    saving.value = false
  }
}

function handleEdit(field: any) {
  editingField.value = { ...field }
  showEditDialog.value = true
}

function handleDelete(field: any) {
  confirm.require({
    message: `Are you sure you want to delete "${field.tgt_table_name}.${field.tgt_column_name}"? This will also remove it from the vector search index.`,
    header: 'Confirm Deletion',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        const result = await SemanticAPI.deleteRecord(field.id)
        if (result.data) {
          const index = semanticFields.value.findIndex(f => f.id === field.id)
          if (index > -1) {
            semanticFields.value.splice(index, 1)
          }
          toast.add({
            severity: 'success',
            summary: 'Deleted',
            detail: 'Semantic field deleted successfully',
            life: 3000
          })
        } else if (result.error) {
          error.value = result.error
        }
      } catch (e) {
        error.value = e instanceof Error ? e.message : 'Failed to delete semantic field'
      }
    }
  })
}

function closeAddDialog() {
  showAddDialog.value = false
  newField.value = {
    tgt_table_name: '',
    tgt_table_physical_name: '',
    tgt_column_name: '',
    tgt_column_physical_name: '',
    tgt_physical_datatype: '',
    tgt_nullable: 'NO',
    tgt_comments: ''
  }
}

function closeEditDialog() {
  showEditDialog.value = false
  editingField.value = null
}

function handleDownloadTemplate() {
  // Create CSV template
  const headers = [
    'tgt_table_name',
    'tgt_table_physical_name',
    'tgt_column_name',
    'tgt_column_physical_name',
    'tgt_physical_datatype',
    'tgt_nullable',
    'tgt_comments'
  ]
  
  const exampleRow = [
    'slv_member',
    'slv_member',
    'full_name',
    'full_name',
    'STRING',
    'NO',
    'Member full name for display'
  ]
  
  const csvContent = [
    headers.join(','),
    exampleRow.join(','),
    // Add empty row for user to fill
    ',,,,,,',
  ].join('\n')
  
  // Create and download file
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'semantic_fields_template.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  toast.add({
    severity: 'success',
    summary: 'Template Downloaded',
    detail: 'Fill in the template and upload to bulk import fields',
    life: 3000
  })
}

function handleFileSelect(event: any) {
  const file = event.files[0]
  if (!file) return
  
  selectedFile.value = file
  
  // Parse CSV to show preview
  const reader = new FileReader()
  reader.onload = (e) => {
    const text = e.target?.result as string
    const lines = text.split('\n').filter(line => line.trim())
    
    if (lines.length < 2) {
      toast.add({
        severity: 'error',
        summary: 'Invalid File',
        detail: 'CSV file must have headers and at least one row',
        life: 3000
      })
      return
    }
    
    // Parse CSV (simple implementation)
    const headers = lines[0].split(',')
    const rows = lines.slice(1).filter(line => line.trim() && !line.split(',').every(cell => !cell.trim()))
    
    uploadPreview.value = rows.slice(0, 5).map(line => {
      const values = line.split(',')
      return {
        tgt_table_name: values[0]?.trim() || '',
        tgt_table_physical_name: values[1]?.trim() || values[0]?.trim() || '',
        tgt_column_name: values[2]?.trim() || '',
        tgt_column_physical_name: values[3]?.trim() || values[2]?.trim() || '',
        tgt_physical_datatype: values[4]?.trim() || '',
        tgt_nullable: values[5]?.trim() || 'NO',
        tgt_comments: values[6]?.trim() || ''
      }
    })
    
    toast.add({
      severity: 'info',
      summary: 'File Loaded',
      detail: `Preview showing ${uploadPreview.value.length} of ${rows.length} fields`,
      life: 3000
    })
  }
  
  reader.readAsText(file)
}

async function handleBulkUpload() {
  if (!selectedFile.value) return
  
  uploading.value = true
  
  try {
    // Parse entire file
    const text = await selectedFile.value.text()
    const lines = text.split('\n').filter(line => line.trim())
    const rows = lines.slice(1).filter(line => line.trim() && !line.split(',').every(cell => !cell.trim()))
    
    const fieldsToUpload = rows.map(line => {
      const values = line.split(',')
      return {
        tgt_table_name: values[0]?.trim() || '',
        tgt_table_physical_name: values[1]?.trim() || values[0]?.trim() || '',
        tgt_column_name: values[2]?.trim() || '',
        tgt_column_physical_name: values[3]?.trim() || values[2]?.trim() || '',
        tgt_physical_datatype: values[4]?.trim() || 'STRING',
        tgt_nullable: values[5]?.trim() || 'NO',
        tgt_comments: values[6]?.trim() || ''
      }
    })
    
    // Upload each field
    let successCount = 0
    let errorCount = 0
    
    for (const field of fieldsToUpload) {
      try {
        const result = await SemanticAPI.createRecord(field)
        if (result.data) {
          successCount++
        } else {
          errorCount++
        }
      } catch (e) {
        errorCount++
        console.error('Error uploading field:', field, e)
      }
    }
    
    toast.add({
      severity: successCount > 0 ? 'success' : 'error',
      summary: 'Upload Complete',
      detail: `Successfully uploaded ${successCount} fields. ${errorCount} errors.`,
      life: 5000
    })
    
    // Reload fields
    await loadSemanticFields()
    closeUploadDialog()
    
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to upload fields'
    toast.add({
      severity: 'error',
      summary: 'Upload Failed',
      detail: error.value,
      life: 5000
    })
  } finally {
    uploading.value = false
  }
}

function handleUpload(event: any) {
  // This is called by PrimeVue FileUpload's @uploader event
  handleBulkUpload()
}

function closeUploadDialog() {
  showUploadDialog.value = false
  uploadPreview.value = []
  selectedFile.value = null
}

// AI Enhance Descriptions
async function handleEnhanceDescriptions() {
  if (semanticFields.value.length === 0) {
    toast.add({
      severity: 'warn',
      summary: 'No Fields',
      detail: 'No semantic fields to enhance',
      life: 3000
    })
    return
  }

  // Open dialog and start enhancement
  showEnhanceDescriptionsDialog.value = true
  enhancingDescriptions.value = true
  enhancedFields.value = []
  enhancedFieldsProgress.value = 0
  enhancedFieldsTotal.value = semanticFields.value.length

  const BATCH_SIZE = 5
  const results: any[] = []

  try {
    for (let i = 0; i < semanticFields.value.length; i += BATCH_SIZE) {
      const batch = semanticFields.value.slice(i, i + BATCH_SIZE)
      
      // Process batch in parallel
      const batchPromises = batch.map(async (field: any) => {
        try {
          const response = await fetch('/api/v4/ai/enhance-description', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              table_name: field.tgt_table_name,
              column_name: field.tgt_column_name,
              data_type: field.tgt_physical_datatype || 'STRING',
              current_description: field.tgt_comments || ''
            })
          })
          
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`)
          }
          
          const data = await response.json()
          
          return {
            id: field.id,
            tgt_table_name: field.tgt_table_name,
            tgt_column_name: field.tgt_column_name,
            original_description: field.tgt_comments || '',
            enhanced_description: data.enhanced_description || field.tgt_comments || ''
          }
        } catch (err) {
          console.error(`Error enhancing ${field.tgt_column_name}:`, err)
          return {
            id: field.id,
            tgt_table_name: field.tgt_table_name,
            tgt_column_name: field.tgt_column_name,
            original_description: field.tgt_comments || '',
            enhanced_description: field.tgt_comments || '' // Keep original on error
          }
        }
      })
      
      const batchResults = await Promise.all(batchPromises)
      results.push(...batchResults)
      enhancedFieldsProgress.value = Math.min(i + BATCH_SIZE, semanticFields.value.length)
    }
    
    enhancedFields.value = results
    
    toast.add({
      severity: 'success',
      summary: 'Enhancement Complete',
      detail: `Enhanced ${results.length} field descriptions. Review and save.`,
      life: 5000
    })
  } catch (err) {
    console.error('Error during enhancement:', err)
    toast.add({
      severity: 'error',
      summary: 'Enhancement Failed',
      detail: 'An error occurred while enhancing descriptions',
      life: 5000
    })
  } finally {
    enhancingDescriptions.value = false
  }
}

async function saveEnhancedDescriptions() {
  savingEnhancedFields.value = true
  let successCount = 0
  let errorCount = 0

  try {
    for (const field of enhancedFields.value) {
      // Only save if description changed
      if (field.enhanced_description !== field.original_description) {
        try {
          const result = await SemanticAPI.updateRecord(field.id, {
            tgt_comments: field.enhanced_description
          })
          if (result.data) {
            successCount++
            // Update local state
            const idx = semanticFields.value.findIndex((f: any) => f.id === field.id)
            if (idx > -1) {
              semanticFields.value[idx].tgt_comments = field.enhanced_description
            }
          } else {
            errorCount++
          }
        } catch (err) {
          errorCount++
          console.error(`Error saving ${field.tgt_column_name}:`, err)
        }
      }
    }

    toast.add({
      severity: successCount > 0 ? 'success' : 'info',
      summary: 'Save Complete',
      detail: `Updated ${successCount} descriptions. ${errorCount} errors.`,
      life: 5000
    })

    showEnhanceDescriptionsDialog.value = false
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Save Failed',
      detail: 'An error occurred while saving descriptions',
      life: 5000
    })
  } finally {
    savingEnhancedFields.value = false
  }
}

function getEnhancedFieldStatus(field: any): string {
  if (field.enhanced_description !== field.original_description) {
    return 'Enhanced'
  }
  return 'Unchanged'
}
</script>

<style scoped>
.semantic-fields-view {
  padding: 2rem;
  max-width: 1600px;
  margin: 0 auto;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.view-header h1 {
  margin: 0 0 0.5rem 0;
  color: var(--gainwell-dark);
  display: flex;
  align-items: center;
  gap: 0.5rem;
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

.info-message {
  margin-bottom: 1.5rem;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  gap: 1rem;
}

.table-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.table-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.table-cell i {
  color: var(--gainwell-primary);
}

.physical-name {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  font-family: 'Courier New', monospace;
}

.description-text {
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

.form-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 600;
  color: var(--text-color);
}

.field small {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

/* Responsive */
@media (max-width: 768px) {
  .semantic-fields-view {
    padding: 1rem;
  }
  
  .view-header {
    flex-direction: column;
    gap: 1rem;
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

/* Upload Dialog */
.upload-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.upload-instructions {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.upload-instructions h4 {
  margin: 0 0 0.5rem 0;
  color: var(--gainwell-dark);
}

.upload-instructions ol {
  margin: 0;
  padding-left: 1.5rem;
}

.upload-instructions li {
  margin-bottom: 0.5rem;
}

.file-upload-area {
  display: flex;
  justify-content: center;
  padding: 1rem;
  border: 2px dashed var(--surface-border);
  border-radius: 6px;
  background: var(--surface-50);
}

.upload-preview {
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 1rem;
  background: white;
}

.upload-preview h4 {
  margin: 0 0 1rem 0;
  color: var(--gainwell-dark);
}

.preview-table {
  margin-bottom: 1rem;
}

.preview-info {
  margin: 0;
  padding: 0.5rem;
  background: var(--green-50);
  border-radius: 4px;
  color: var(--green-900);
  font-weight: 500;
}

/* AI Enhance Descriptions Dialog */
.enhance-dialog-content {
  min-height: 200px;
}

.enhance-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  gap: 1rem;
}

.enhance-progress p {
  color: var(--text-color-secondary);
  margin: 0;
}

.enhance-progress-bar {
  width: 100%;
  max-width: 400px;
  height: 8px;
  background: var(--surface-200);
  border-radius: 4px;
  overflow: hidden;
}

.enhance-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--gainwell-primary), var(--gainwell-secondary));
  transition: width 0.3s ease;
}

.enhanced-fields-table {
  font-size: 0.9rem;
}

.table-name {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.original-desc {
  color: var(--text-color-secondary);
  font-style: italic;
}

.enhanced-description-cell {
  width: 100%;
}

.enhanced-description-textarea {
  width: 100%;
  font-size: 0.85rem;
  resize: vertical;
}

.no-enhanced-fields {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.mb-3 {
  margin-bottom: 1rem;
}
</style>

