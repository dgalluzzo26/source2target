<template>
  <div class="unmapped-fields-view">
    <div class="view-header">
      <h1>Source Field Mapping (V2)</h1>
      <p class="subtitle">Select source fields to map to target fields. You can select multiple fields for combined mappings.</p>
    </div>

    <!-- Action Bar -->
    <div class="action-bar">
      <div class="action-bar-left">
        <Button 
          label="Download Template" 
          icon="pi pi-download" 
          severity="secondary"
          @click="handleDownloadTemplate"
          v-tooltip.top="'Download CSV template for bulk upload'"
        />
        <Button 
          label="Upload Fields" 
          icon="pi pi-upload" 
          @click="showUploadDialog = true"
          v-tooltip.top="'Bulk upload source fields from CSV'"
        />
      </div>
      <div class="action-bar-right" v-if="unmappedStore.hasSelection">
        <i class="pi pi-check-circle"></i>
        <span><strong>{{ unmappedStore.selectedCount }}</strong> field{{ unmappedStore.selectedCount !== 1 ? 's' : '' }} selected</span>
        <Button 
          label="Clear Selection" 
          icon="pi pi-times" 
          severity="secondary" 
          text 
          @click="unmappedStore.clearSelection()"
        />
        <Button 
          label="Get AI Suggestions" 
          icon="pi pi-sparkles" 
          severity="primary" 
          @click="handleGetSuggestions"
          :loading="aiStore.loading"
        />
      </div>
    </div>

    <!-- Info Message -->
    <Message v-if="!unmappedStore.hasSelection" severity="info" :closable="false">
      <strong>How it works:</strong> Select one or more source fields below, then click "Get AI Suggestions" to find matching target fields.
      For multi-field mappings (e.g., FIRST_NAME + LAST_NAME), select all relevant fields together.
    </Message>

    <!-- Loading State -->
    <div v-if="unmappedStore.loading" class="loading-container">
      <ProgressSpinner />
      <p>Loading unmapped fields...</p>
    </div>

    <!-- Error State -->
    <Message v-if="unmappedStore.error" severity="error" :closable="true">
      {{ unmappedStore.error }}
    </Message>

    <!-- Unmapped Fields Table -->
    <div v-if="!unmappedStore.loading && unmappedStore.unmappedFields.length > 0" class="fields-table-container">
      <DataTable 
        v-model:selection="unmappedStore.selectedFields"
        :value="unmappedStore.unmappedFields" 
        dataKey="id"
        :paginator="true"
        :rows="20"
        :rowsPerPageOptions="[10, 20, 50, 100]"
        paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
        currentPageReportTemplate="Showing {first} to {last} of {totalRecords} fields"
        filterDisplay="row"
        :globalFilterFields="['src_table_name', 'src_column_name', 'src_comments', 'src_physical_datatype']"
        class="unmapped-fields-table"
        stripedRows
        removableSort
      >
        <!-- Selection Column -->
        <Column selectionMode="multiple" headerStyle="width: 3rem" :exportable="false"></Column>
        
        <!-- Table Name -->
        <Column field="src_table_name" header="Source Table" :sortable="true" style="min-width: 12rem">
          <template #body="{ data }">
            <div class="table-name">
              <i class="pi pi-table"></i>
              <span>{{ data.src_table_name }}</span>
            </div>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText 
              v-model="filterModel.value" 
              type="text" 
              @input="filterCallback()" 
              class="p-column-filter" 
              placeholder="Filter by table"
            />
          </template>
        </Column>
        
        <!-- Column Name -->
        <Column field="src_column_name" header="Source Column" :sortable="true" style="min-width: 12rem">
          <template #body="{ data }">
            <div class="column-name">
              <Tag :value="data.src_physical_datatype" severity="info" />
              <strong>{{ data.src_column_name }}</strong>
            </div>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText 
              v-model="filterModel.value" 
              type="text" 
              @input="filterCallback()" 
              class="p-column-filter" 
              placeholder="Filter by column"
            />
          </template>
        </Column>
        
        <!-- Data Type -->
        <Column field="src_physical_datatype" header="Type" :sortable="true" style="min-width: 8rem">
          <template #body="{ data }">
            <Tag :value="data.src_physical_datatype" severity="info" />
          </template>
        </Column>
        
        <!-- Nullable -->
        <Column field="src_nullable" header="Nullable" :sortable="true" style="min-width: 6rem">
          <template #body="{ data }">
            <Tag :value="data.src_nullable" :severity="data.src_nullable === 'YES' ? 'warning' : 'success'" />
          </template>
        </Column>
        
        <!-- Comments -->
        <Column field="src_comments" header="Description" style="min-width: 20rem">
          <template #body="{ data }">
            <span class="comments">{{ data.src_comments || 'No description' }}</span>
          </template>
          <template #filter="{ filterModel, filterCallback }">
            <InputText 
              v-model="filterModel.value" 
              type="text" 
              @input="filterCallback()" 
              class="p-column-filter" 
              placeholder="Filter by description"
            />
          </template>
        </Column>
        
        <!-- Actions -->
        <Column :exportable="false" style="min-width: 8rem">
          <template #body="{ data }">
            <Button 
              icon="pi pi-trash" 
              severity="danger" 
              text 
              rounded 
              @click="handleDelete(data)"
              v-tooltip.top="'Remove from unmapped'"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Empty State -->
    <div v-if="!unmappedStore.loading && unmappedStore.unmappedFields.length === 0" class="empty-state">
      <i class="pi pi-inbox" style="font-size: 4rem; color: var(--text-color-secondary);"></i>
      <h3>No Unmapped Fields</h3>
      <p>All source fields have been mapped. Upload new source fields to continue mapping.</p>
      <Button label="Upload Source Fields" icon="pi pi-upload" @click="handleUpload" />
    </div>

    <!-- AI Suggestions Modal -->
    <AISuggestionsDialog 
      v-model:visible="showAISuggestions"
      @suggestion-selected="handleSuggestionSelected"
    />

    <!-- Upload Dialog -->
    <Dialog 
      v-model:visible="showUploadDialog" 
      modal 
      header="Upload Source Fields"
      :style="{ width: '800px' }"
    >
      <div class="upload-content">
        <Message severity="info" :closable="false">
          Download the template, fill in your source fields, and upload the CSV file.
        </Message>

        <FileUpload
          mode="basic"
          accept=".csv"
          :maxFileSize="10000000"
          chooseLabel="Choose CSV File"
          @select="handleFileSelect"
          :customUpload="true"
          @uploader="handleUpload"
        />

        <div v-if="uploadPreview.length > 0" class="preview-section">
          <h4>Preview (first 5 rows)</h4>
          <DataTable :value="uploadPreview" class="preview-table">
            <Column field="src_table_name" header="Table" />
            <Column field="src_column_name" header="Column" />
            <Column field="src_physical_datatype" header="Type" />
            <Column field="src_nullable" header="Nullable" />
            <Column field="src_comments" header="Comments" />
          </DataTable>
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" icon="pi pi-times" @click="closeUploadDialog" severity="secondary" />
        <Button 
          label="Import Fields" 
          icon="pi pi-check" 
          @click="handleBulkUpload"
          :loading="uploading"
          :disabled="!selectedFile"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUnmappedFieldsStore } from '@/stores/unmappedFieldsStore'
import { useAISuggestionsStoreV2 } from '@/stores/aiSuggestionsStoreV2'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import FileUpload from 'primevue/fileupload'
import ProgressSpinner from 'primevue/progressspinner'
import AISuggestionsDialog from '@/components/AISuggestionsDialog.vue'
import type { UnmappedField } from '@/stores/unmappedFieldsStore'
import type { AISuggestionV2 } from '@/stores/aiSuggestionsStoreV2'

const router = useRouter()
const unmappedStore = useUnmappedFieldsStore()
const aiStore = useAISuggestionsStoreV2()
const confirm = useConfirm()
const toast = useToast()

const showAISuggestions = ref(false)
const showUploadDialog = ref(false)
const uploading = ref(false)
const uploadPreview = ref<any[]>([])
const selectedFile = ref<File | null>(null)

onMounted(async () => {
  await unmappedStore.fetchUnmappedFields()
})

async function handleGetSuggestions() {
  if (!unmappedStore.hasSelection) {
    toast.add({
      severity: 'warn',
      summary: 'No Selection',
      detail: 'Please select at least one source field',
      life: 3000
    })
    return
  }

  // Generate AI suggestions
  await aiStore.generateSuggestions(unmappedStore.selectedFields)
  
  if (aiStore.hasSuggestions) {
    showAISuggestions.value = true
  } else {
    toast.add({
      severity: 'warn',
      summary: 'No Suggestions',
      detail: 'Could not generate suggestions for the selected fields',
      life: 3000
    })
  }
}

function handleSuggestionSelected(suggestion: AISuggestionV2) {
  // The suggestion is already stored in aiStore.selectedSuggestion
  // The source fields are already in aiStore.sourceFieldsUsed
  // Just navigate to the mapping configuration view
  console.log('[Unmapped Fields] Navigating to mapping config with:', suggestion.tgt_column_name)
  router.push({ name: 'mapping-config' })
}

function handleDelete(field: UnmappedField) {
  confirm.require({
    message: `Are you sure you want to remove "${field.src_table_name}.${field.src_column_name}" from unmapped fields?`,
    header: 'Confirm Deletion',
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
      try {
        await unmappedStore.deleteUnmappedField(field.id)
        toast.add({
          severity: 'success',
          summary: 'Deleted',
          detail: 'Field removed from unmapped list',
          life: 3000
        })
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to delete field',
          life: 3000
        })
      }
    }
  })
}

function handleDownloadTemplate() {
  // Create CSV template for unmapped fields
  const headers = [
    'src_table_name',
    'src_table_physical_name',
    'src_column_name',
    'src_column_physical_name',
    'src_physical_datatype',
    'src_nullable',
    'src_comments'
  ]
  
  const exampleRow = [
    'T_MEMBER',
    't_member',
    'MEMBER_ID',
    'member_id',
    'STRING',
    'NO',
    'Unique member identifier'
  ]
  
  const csvContent = [
    headers.join(','),
    exampleRow.join(','),
    ',,,,,,', // Empty row for user
  ].join('\n')
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'unmapped_fields_template.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  toast.add({
    severity: 'success',
    summary: 'Template Downloaded',
    detail: 'Fill in the template and upload to import source fields',
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
        detail: 'CSV must have headers and at least one row',
        life: 3000
      })
      return
    }
    
    const rows = lines.slice(1).filter(line => line.trim() && !line.split(',').every(cell => !cell.trim()))
    
    uploadPreview.value = rows.slice(0, 5).map(line => {
      const values = line.split(',')
      return {
        src_table_name: values[0]?.trim() || '',
        src_table_physical_name: values[1]?.trim() || values[0]?.trim() || '',
        src_column_name: values[2]?.trim() || '',
        src_column_physical_name: values[3]?.trim() || values[2]?.trim() || '',
        src_physical_datatype: values[4]?.trim() || '',
        src_nullable: values[5]?.trim() || 'YES',
        src_comments: values[6]?.trim() || ''
      }
    })
  }
  
  reader.readAsText(file)
}

async function handleBulkUpload() {
  if (!selectedFile.value) return
  
  uploading.value = true
  
  try {
    // Parse CSV
    const text = await selectedFile.value.text()
    const lines = text.split('\n').filter(line => line.trim())
    const rows = lines.slice(1).filter(line => line.trim() && !line.split(',').every(cell => !cell.trim()))
    
    // Build field objects
    const fields = rows.map(line => {
      const values = line.split(',')
      return {
        src_table_name: values[0]?.trim(),
        src_table_physical_name: values[1]?.trim() || values[0]?.trim(),
        src_column_name: values[2]?.trim(),
        src_column_physical_name: values[3]?.trim() || values[2]?.trim(),
        src_physical_datatype: values[4]?.trim(),
        src_nullable: values[5]?.trim() || 'YES',
        src_comments: values[6]?.trim() || ''
      }
    }).filter(field => 
      field.src_table_name && field.src_column_name && field.src_physical_datatype
    )
    
    if (fields.length === 0) {
      toast.add({
        severity: 'warn',
        summary: 'No Valid Fields',
        detail: 'No valid fields found in CSV. Check that required columns are filled.',
        life: 5000
      })
      return
    }
    
    // Call bulk upload API
    const response = await fetch('/api/v2/unmapped-fields/bulk', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(fields)
    })
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`)
    }
    
    const result = await response.json()
    
    toast.add({
      severity: result.success_count > 0 ? 'success' : 'error',
      summary: 'Import Complete',
      detail: `Imported ${result.success_count} fields. ${result.error_count > 0 ? `${result.error_count} failed.` : ''}`,
      life: 5000
    })
    
    closeUploadDialog()
    await unmappedStore.fetchUnmappedFields()
  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Import Failed',
      detail: e instanceof Error ? e.message : 'Failed to import fields',
      life: 3000
    })
  } finally {
    uploading.value = false
  }
}

function handleUpload(event: any) {
  handleBulkUpload()
}

function closeUploadDialog() {
  showUploadDialog.value = false
  uploadPreview.value = []
  selectedFile.value = null
}
</script>

<style scoped>
.unmapped-fields-view {
  padding: 2rem;
  max-width: 1400px;
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

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.action-bar-left,
.action-bar-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.action-bar-right {
  padding: 1rem 1.5rem;
  background: var(--gainwell-light);
  border-left: 4px solid var(--gainwell-primary);
  border-radius: 6px;
}

.action-bar-right i {
  color: var(--gainwell-primary);
  font-size: 1.5rem;
}

.action-bar-right span {
  margin-right: auto;
}

.selection-summary {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  background: var(--gainwell-light);
  border-left: 4px solid var(--gainwell-primary);
  border-radius: 6px;
  margin-bottom: 1.5rem;
}

.selection-summary i {
  color: var(--gainwell-primary);
  font-size: 1.5rem;
}

.selection-summary span {
  flex: 1;
}

.upload-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.preview-section {
  margin-top: 1rem;
}

.preview-section h4 {
  margin: 0 0 0.75rem 0;
  color: var(--gainwell-dark);
}

.preview-table {
  border: 1px solid var(--surface-border);
  border-radius: 6px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  gap: 1rem;
}

.fields-table-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.table-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.table-name i {
  color: var(--gainwell-primary);
}

.column-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.comments {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
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

/* Responsive */
@media (max-width: 768px) {
  .unmapped-fields-view {
    padding: 1rem;
  }
  
  .selection-summary {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

