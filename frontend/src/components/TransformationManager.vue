<template>
  <div class="transformation-manager">
    <div class="header-section">
      <div class="header-left">
        <h2>
          <i class="pi pi-code"></i>
          Transformation Library
        </h2>
        <p>Manage reusable SQL transformation templates</p>
      </div>
      <div class="header-right">
        <Button 
          label="Add Transformation" 
          icon="pi pi-plus" 
          @click="openCreateDialog"
          severity="success"
        />
      </div>
    </div>

    <Card>
      <template #content>
        <DataTable 
          :value="transformations" 
          :loading="loading"
          stripedRows
          paginator 
          :rows="10"
          :rowsPerPageOptions="[10, 25, 50]"
          filterDisplay="row"
          v-model:filters="filters"
          :globalFilterFields="['transformation_name', 'transformation_code', 'category', 'transformation_description']"
          sortField="category"
          :sortOrder="1"
        >
          <template #empty>
            <div class="empty-state">
              <i class="pi pi-code" style="font-size: 3rem; color: var(--gainwell-secondary); margin-bottom: 1rem;"></i>
              <p>No transformations found</p>
            </div>
          </template>

          <Column field="transformation_name" header="Name" sortable>
            <template #filter="{ filterModel, filterCallback }">
              <InputText 
                v-model="filterModel.value" 
                @input="filterCallback()" 
                placeholder="Search name"
                class="p-column-filter"
              />
            </template>
            <template #body="{ data }">
              <div class="transformation-name">
                {{ data.transformation_name }}
                <Tag v-if="data.is_system" value="SYSTEM" severity="info" class="system-tag" />
              </div>
            </template>
          </Column>

          <Column field="transformation_code" header="Code" sortable>
            <template #filter="{ filterModel, filterCallback }">
              <InputText 
                v-model="filterModel.value" 
                @input="filterCallback()" 
                placeholder="Search code"
                class="p-column-filter"
              />
            </template>
            <template #body="{ data }">
              <code class="code-badge">{{ data.transformation_code }}</code>
            </template>
          </Column>

          <Column field="transformation_expression" header="Expression" sortable>
            <template #body="{ data }">
              <code class="sql-expression">{{ data.transformation_expression }}</code>
            </template>
          </Column>

          <Column field="category" header="Category" sortable>
            <template #filter="{ filterModel, filterCallback }">
              <InputText 
                v-model="filterModel.value" 
                @input="filterCallback()" 
                placeholder="Search category"
                class="p-column-filter"
              />
            </template>
            <template #body="{ data }">
              <Tag 
                :value="data.category || 'GENERAL'" 
                :severity="getCategorySeverity(data.category)"
              />
            </template>
          </Column>

          <Column field="transformation_description" header="Description">
            <template #body="{ data }">
              <span class="description">{{ data.transformation_description || '—' }}</span>
            </template>
          </Column>

          <Column header="Actions" style="width: 150px">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button 
                  icon="pi pi-pencil" 
                  severity="info"
                  size="small"
                  text
                  @click="openEditDialog(data)"
                  :disabled="data.is_system"
                  v-tooltip.top="data.is_system ? 'System transformations cannot be edited' : 'Edit transformation'"
                />
                <Button 
                  icon="pi pi-trash" 
                  severity="danger"
                  size="small"
                  text
                  @click="confirmDelete(data)"
                  :disabled="data.is_system"
                  v-tooltip.top="data.is_system ? 'System transformations cannot be deleted' : 'Delete transformation'"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Create/Edit Dialog -->
    <Dialog 
      v-model:visible="dialogVisible" 
      :header="dialogMode === 'create' ? 'Create Transformation' : 'Edit Transformation'"
      modal
      :style="{ width: '600px' }"
      @hide="resetForm"
    >
      <div class="dialog-content">
        <div class="field">
          <label for="name" class="required">Name</label>
          <InputText 
            id="name"
            v-model="formData.transformation_name" 
            placeholder="e.g., Trim Whitespace"
            class="full-width"
            :class="{ 'p-invalid': formErrors.transformation_name }"
          />
          <small v-if="formErrors.transformation_name" class="p-error">{{ formErrors.transformation_name }}</small>
        </div>

        <div class="field">
          <label for="code" class="required">Code</label>
          <InputText 
            id="code"
            v-model="formData.transformation_code" 
            placeholder="e.g., TRIM"
            class="full-width"
            :class="{ 'p-invalid': formErrors.transformation_code }"
          />
          <small v-if="formErrors.transformation_code" class="p-error">{{ formErrors.transformation_code }}</small>
          <small class="field-hint">Unique identifier for this transformation</small>
        </div>

        <div class="field">
          <label for="expression" class="required">SQL Expression</label>
          <Textarea 
            id="expression"
            v-model="formData.transformation_expression" 
            placeholder="e.g., TRIM({field})"
            rows="3"
            class="full-width"
            :class="{ 'p-invalid': formErrors.transformation_expression }"
          />
          <small v-if="formErrors.transformation_expression" class="p-error">{{ formErrors.transformation_expression }}</small>
          <small class="field-hint">Use {field} as a placeholder for the source field name</small>
        </div>

        <div class="field">
          <label for="description">Description</label>
          <Textarea 
            id="description"
            v-model="formData.transformation_description" 
            placeholder="e.g., Remove leading and trailing whitespace"
            rows="2"
            class="full-width"
          />
        </div>

        <div class="field">
          <label for="category">Category</label>
          <Dropdown 
            id="category"
            v-model="formData.category" 
            :options="categoryOptions"
            placeholder="Select a category"
            class="full-width"
            showClear
          />
          <small class="field-hint">Group similar transformations together</small>
        </div>

        <div class="field" v-if="dialogMode === 'create'">
          <div class="checkbox-field">
            <Checkbox 
              id="isSystem"
              v-model="formData.is_system" 
              :binary="true"
            />
            <label for="isSystem">Mark as system transformation</label>
          </div>
          <small class="field-hint">System transformations cannot be edited or deleted</small>
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" @click="dialogVisible = false" />
        <Button 
          :label="dialogMode === 'create' ? 'Create' : 'Update'" 
          :loading="saving"
          @click="saveTransformation"
        />
      </template>
    </Dialog>

    <!-- Delete Confirmation Dialog -->
    <Dialog 
      v-model:visible="deleteDialogVisible" 
      header="Delete Transformation"
      modal
      :style="{ width: '450px' }"
    >
      <div class="delete-confirmation">
        <i class="pi pi-exclamation-triangle" style="font-size: 3rem; color: var(--red-500); margin-bottom: 1rem;"></i>
        <p>Are you sure you want to delete this transformation?</p>
        <div class="delete-details">
          <strong>{{ transformationToDelete?.transformation_name }}</strong>
          <code>{{ transformationToDelete?.transformation_code }}</code>
        </div>
        <p class="warning-text">This action cannot be undone.</p>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" @click="deleteDialogVisible = false" />
        <Button 
          label="Delete" 
          severity="danger"
          :loading="deleting"
          @click="deleteTransformation"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import Button from 'primevue/button';
import Card from 'primevue/card';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import Textarea from 'primevue/textarea';
import Dropdown from 'primevue/dropdown';
import Checkbox from 'primevue/checkbox';
import Tag from 'primevue/tag';
import { FilterMatchMode } from '@primevue/core/api';
import api from '@/services/api';

interface Transformation {
  transformation_id: number;
  transformation_name: string;
  transformation_code: string;
  transformation_expression: string;
  transformation_description?: string;
  category?: string;
  is_system: boolean;
  created_ts?: string;
}

interface FormData {
  transformation_name: string;
  transformation_code: string;
  transformation_expression: string;
  transformation_description?: string;
  category?: string;
  is_system: boolean;
}

const toast = useToast();

// State
const loading = ref(false);
const saving = ref(false);
const deleting = ref(false);
const transformations = ref<Transformation[]>([]);
const dialogVisible = ref(false);
const deleteDialogVisible = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const selectedTransformation = ref<Transformation | null>(null);
const transformationToDelete = ref<Transformation | null>(null);

// Form data
const formData = ref<FormData>({
  transformation_name: '',
  transformation_code: '',
  transformation_expression: '',
  transformation_description: '',
  category: '',
  is_system: false
});

const formErrors = ref<Record<string, string>>({});

// Table filters
const filters = ref({
  transformation_name: { value: '', matchMode: FilterMatchMode.CONTAINS },
  transformation_code: { value: '', matchMode: FilterMatchMode.CONTAINS },
  category: { value: '', matchMode: FilterMatchMode.CONTAINS }
});

// Category options
const categoryOptions = [
  'STRING',
  'DATE',
  'NUMERIC',
  'CONVERSION',
  'NULL_HANDLING',
  'CUSTOM'
];

// Methods
const loadTransformations = async () => {
  loading.value = true;
  try {
    const response = await api.get('/api/v2/transformations/');
    transformations.value = response.data;
    console.log(`[Transformations] Loaded ${response.data.length} transformations`);
  } catch (error: any) {
    console.error('Error loading transformations:', error);
    
    let errorMessage = 'Failed to load transformations';
    
    if (error.response) {
      // Server responded with error
      errorMessage = error.response.data?.detail || `Server error: ${error.response.status}`;
    } else if (error.request) {
      // Request made but no response
      errorMessage = 'No response from server. Is the backend running?';
    } else {
      // Error setting up request
      errorMessage = error.message || 'Unknown error occurred';
    }
    
    toast.add({
      severity: 'error',
      summary: 'Error Loading Transformations',
      detail: errorMessage,
      life: 8000
    });
  } finally {
    loading.value = false;
  }
};

const openCreateDialog = () => {
  dialogMode.value = 'create';
  resetForm();
  dialogVisible.value = true;
};

const openEditDialog = (transformation: Transformation) => {
  dialogMode.value = 'edit';
  selectedTransformation.value = transformation;
  formData.value = {
    transformation_name: transformation.transformation_name,
    transformation_code: transformation.transformation_code,
    transformation_expression: transformation.transformation_expression,
    transformation_description: transformation.transformation_description || '',
    category: transformation.category || '',
    is_system: transformation.is_system
  };
  dialogVisible.value = true;
};

const resetForm = () => {
  formData.value = {
    transformation_name: '',
    transformation_code: '',
    transformation_expression: '',
    transformation_description: '',
    category: '',
    is_system: false
  };
  formErrors.value = {};
  selectedTransformation.value = null;
};

const validateForm = (): boolean => {
  formErrors.value = {};
  
  if (!formData.value.transformation_name.trim()) {
    formErrors.value.transformation_name = 'Name is required';
  }
  
  if (!formData.value.transformation_code.trim()) {
    formErrors.value.transformation_code = 'Code is required';
  }
  
  if (!formData.value.transformation_expression.trim()) {
    formErrors.value.transformation_expression = 'SQL expression is required';
  } else if (!formData.value.transformation_expression.includes('{field}')) {
    formErrors.value.transformation_expression = 'Expression must include {field} placeholder';
  }
  
  return Object.keys(formErrors.value).length === 0;
};

const saveTransformation = async () => {
  if (!validateForm()) {
    return;
  }

  saving.value = true;
  try {
    if (dialogMode.value === 'create') {
      await api.post('/api/v2/transformations/', formData.value);
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Transformation created successfully',
        life: 3000
      });
    } else {
      await api.put(`/api/v2/transformations/${selectedTransformation.value!.transformation_id}`, formData.value);
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Transformation updated successfully',
        life: 3000
      });
    }
    
    dialogVisible.value = false;
    await loadTransformations();
  } catch (error: any) {
    console.error('Error saving transformation:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.response?.data?.detail || 'Failed to save transformation',
      life: 5000
    });
  } finally {
    saving.value = false;
  }
};

const confirmDelete = (transformation: Transformation) => {
  transformationToDelete.value = transformation;
  deleteDialogVisible.value = true;
};

const deleteTransformation = async () => {
  if (!transformationToDelete.value) return;

  deleting.value = true;
  try {
    await api.delete(`/api/v2/transformations/${transformationToDelete.value.transformation_id}`);
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Transformation deleted successfully',
      life: 3000
    });
    
    deleteDialogVisible.value = false;
    await loadTransformations();
  } catch (error: any) {
    console.error('Error deleting transformation:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.response?.data?.detail || 'Failed to delete transformation',
      life: 5000
    });
  } finally {
    deleting.value = false;
  }
};

const getCategorySeverity = (category?: string): string => {
  if (!category) return 'secondary';
  
  const severityMap: Record<string, string> = {
    STRING: 'success',
    DATE: 'info',
    NUMERIC: 'warn',
    CONVERSION: 'primary',
    NULL_HANDLING: 'secondary',
    CUSTOM: 'contrast'
  };
  
  return severityMap[category] || 'secondary';
};

// Lifecycle
onMounted(() => {
  loadTransformations();
});
</script>

<style scoped>
.transformation-manager {
  width: 100%;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.header-left h2 {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0 0 0.5rem 0;
  color: var(--gainwell-primary);
  font-size: 1.75rem;
}

.header-left p {
  margin: 0;
  color: var(--gainwell-text-secondary);
  font-size: 1rem;
}

.header-right {
  padding-top: 0.25rem;
}

.transformation-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.system-tag {
  font-size: 0.7rem;
}

.code-badge {
  background: var(--gainwell-surface-variant);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  color: var(--gainwell-primary);
}

.sql-expression {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  color: var(--gainwell-text-primary);
  display: block;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.description {
  color: var(--gainwell-text-secondary);
  font-size: 0.9rem;
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
  justify-content: flex-end;
}

.empty-state {
  text-align: center;
  padding: 3rem 2rem;
}

.empty-state p {
  margin: 0;
  color: var(--gainwell-text-secondary);
  font-size: 1.125rem;
}

/* Dialog Styles */
.dialog-content {
  padding: 0.5rem 0;
}

.field {
  margin-bottom: 1.5rem;
}

.field label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: var(--gainwell-text-primary);
}

.field label.required::after {
  content: ' *';
  color: var(--red-500);
}

.full-width {
  width: 100%;
}

.field-hint {
  display: block;
  margin-top: 0.25rem;
  color: var(--gainwell-text-secondary);
  font-size: 0.875rem;
}

.checkbox-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.checkbox-field label {
  margin: 0;
  font-weight: normal;
}

.delete-confirmation {
  text-align: center;
  padding: 1rem 0;
}

.delete-confirmation p {
  margin: 0.5rem 0;
  color: var(--gainwell-text-primary);
}

.delete-details {
  background: var(--gainwell-surface-variant);
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
}

.delete-details strong {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--gainwell-text-primary);
}

.delete-details code {
  background: var(--gainwell-surface-variant);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  color: var(--gainwell-primary);
}

.warning-text {
  color: var(--red-500);
  font-weight: 500;
  margin-top: 1rem !important;
}

:deep(.p-datatable .p-datatable-tbody > tr > td) {
  padding: 0.75rem;
}

:deep(.p-column-filter) {
  width: 100%;
}
</style>

