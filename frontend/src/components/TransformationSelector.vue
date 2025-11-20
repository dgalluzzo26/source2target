<template>
  <div class="transformation-selector">
    <Message severity="info" :closable="false" class="info-message">
      <i class="pi pi-info-circle"></i>
      Select optional transformations to apply to each field. Transformations are applied before concatenation.
    </Message>

    <div class="fields-list">
      <div v-for="field in localFields" :key="field.src_column_physical_name" class="field-item">
        <div class="field-header">
          <div class="field-info">
            <Tag :value="`${field.field_order}`" severity="info" />
            <strong>{{ field.src_table_name }}.{{ field.src_column_name }}</strong>
          </div>
        </div>

        <div class="transformation-controls">
          <div class="transformation-dropdown">
            <label :for="`transform-${field.src_column_physical_name}`">Transformation:</label>
            <Dropdown
              :id="`transform-${field.src_column_physical_name}`"
              v-model="field.selectedTransformation"
              :options="transformationOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="No transformation"
              showClear
              @change="handleTransformationChange(field)"
              class="w-full"
            >
              <template #option="{ option }">
                <div class="transformation-option">
                  <strong>{{ option.label }}</strong>
                  <span class="option-description">{{ option.description }}</span>
                  <code class="option-code">{{ option.code }}</code>
                </div>
              </template>
            </Dropdown>
          </div>

          <div v-if="field.transformation_expr" class="transformation-preview">
            <label>SQL Expression:</label>
            <div class="sql-preview">
              <code>{{ field.transformation_expr }}</code>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="combined-preview">
      <h4>
        <i class="pi pi-eye"></i>
        All Transformations
      </h4>
      <div class="combined-list">
        <div v-for="field in localFields" :key="field.src_column_physical_name" class="preview-item">
          <Tag :value="`${field.field_order}`" severity="info" />
          <span class="field-name">{{ field.src_column_name }}</span>
          <i class="pi pi-arrow-right"></i>
          <code v-if="field.transformation_expr">{{ field.transformation_expr }}</code>
          <span v-else class="no-transform">No transformation</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useMappingsStoreV2 } from '@/stores/mappingsStoreV2'
import Message from 'primevue/message'
import Dropdown from 'primevue/dropdown'
import Tag from 'primevue/tag'
import type { MappingDetailV2 } from '@/stores/mappingsStoreV2'

interface FieldWithTransformation extends MappingDetailV2 {
  selectedTransformation?: string | null
}

interface Props {
  fields: MappingDetailV2[]
}

interface Emits {
  (e: 'update:fields', fields: MappingDetailV2[]): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const mappingsStore = useMappingsStoreV2()
const localFields = ref<FieldWithTransformation[]>([])
const transformationOptions = ref<any[]>([])

onMounted(async () => {
  // Load transformations
  await mappingsStore.fetchTransformations()
  
  // Build options
  transformationOptions.value = [
    {
      label: 'None',
      value: null,
      description: 'No transformation',
      code: '{field}'
    },
    ...mappingsStore.transformations.map(t => ({
      label: t.transform_name,
      value: t.transform_code,
      description: t.description,
      code: t.transform_code,
      category: t.category
    }))
  ]

  // Initialize local fields
  localFields.value = props.fields.map(field => ({
    ...field,
    selectedTransformation: field.transformation_expr ? 
      findTransformationValue(field.transformation_expr) : null
  }))
})

watch(() => props.fields, (newFields) => {
  localFields.value = newFields.map(field => ({
    ...field,
    selectedTransformation: field.transformation_expr ? 
      findTransformationValue(field.transformation_expr) : null
  }))
}, { deep: true })

function findTransformationValue(expr: string): string | null {
  // Try to match the transformation code
  const option = transformationOptions.value.find(opt => 
    opt.value && expr.includes(opt.value.replace('{field}', ''))
  )
  return option?.value || null
}

function handleTransformationChange(field: FieldWithTransformation) {
  if (field.selectedTransformation) {
    // Apply transformation
    const transformCode = field.selectedTransformation
    field.transformation_expr = transformCode.replace('{field}', field.src_column_physical_name)
  } else {
    // Clear transformation
    field.transformation_expr = undefined
  }

  // Emit updated fields
  const updatedFields: MappingDetailV2[] = localFields.value.map(f => ({
    src_table_name: f.src_table_name,
    src_table_physical_name: f.src_table_physical_name,
    src_column_name: f.src_column_name,
    src_column_physical_name: f.src_column_physical_name,
    field_order: f.field_order,
    transformation_expr: f.transformation_expr
  }))
  emit('update:fields', updatedFields)
}
</script>

<style scoped>
.transformation-selector {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.info-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.fields-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field-item {
  padding: 1.5rem;
  background: var(--surface-50);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
}

.field-header {
  margin-bottom: 1rem;
}

.field-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.field-info strong {
  color: var(--text-color);
  font-size: 1rem;
}

.transformation-controls {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.transformation-dropdown {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.transformation-dropdown label {
  font-weight: 600;
  color: var(--text-color);
  font-size: 0.9rem;
}

.transformation-option {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.5rem 0;
}

.transformation-option strong {
  color: var(--text-color);
}

.option-description {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.option-code {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  color: var(--gainwell-primary);
  background: var(--surface-100);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  margin-top: 0.25rem;
  display: inline-block;
}

.transformation-preview {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: white;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
}

.transformation-preview label {
  font-weight: 600;
  color: var(--text-color);
  font-size: 0.9rem;
}

.sql-preview {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
}

.sql-preview code {
  color: var(--gainwell-dark);
}

.combined-preview {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.combined-preview h4 {
  margin: 0 0 1rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--gainwell-dark);
}

.combined-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.preview-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: white;
  border: 1px solid var(--surface-border);
  border-radius: 4px;
}

.field-name {
  font-weight: 600;
  color: var(--text-color);
}

.preview-item i {
  color: var(--text-color-secondary);
}

.preview-item code {
  font-family: 'Courier New', monospace;
  color: var(--gainwell-primary);
  background: var(--surface-100);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.no-transform {
  color: var(--text-color-secondary);
  font-style: italic;
}

/* Responsive */
@media (max-width: 768px) {
  .field-item {
    padding: 1rem;
  }

  .preview-item {
    flex-wrap: wrap;
  }
}
</style>

