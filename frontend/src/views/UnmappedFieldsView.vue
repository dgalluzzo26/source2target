<template>
  <div class="unmapped-fields-view">
    <div class="view-header">
      <h1>Source Field Mapping (V2)</h1>
      <p class="subtitle">Select source fields to map to target fields. You can select multiple fields for combined mappings.</p>
    </div>

    <!-- Selection Summary -->
    <div v-if="unmappedStore.hasSelection" class="selection-summary">
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

function handleUpload() {
  // TODO: Navigate to upload view
  toast.add({
    severity: 'info',
    summary: 'Coming Soon',
    detail: 'Upload functionality will be available soon',
    life: 3000
  })
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

