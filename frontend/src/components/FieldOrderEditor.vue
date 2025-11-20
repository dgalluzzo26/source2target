<template>
  <div class="field-order-editor">
    <Message severity="info" :closable="false" class="info-message">
      <i class="pi pi-info-circle"></i>
      <strong>Drag and drop</strong> to reorder fields. The first field will appear first in the concatenated result.
    </Message>

    <div class="field-list">
      <draggable
        v-model="localFields"
        item-key="src_column_physical_name"
        handle=".drag-handle"
        @end="handleDragEnd"
        :animation="200"
        ghost-class="ghost"
      >
        <template #item="{ element, index }">
          <div class="field-item">
            <div class="drag-handle">
              <i class="pi pi-bars"></i>
            </div>
            <div class="field-order">
              <Tag :value="`${index + 1}`" severity="info" />
            </div>
            <div class="field-content">
              <div class="field-name">
                <strong>{{ element.src_table_name }}.{{ element.src_column_name }}</strong>
                <span class="physical-name">{{ element.src_column_physical_name }}</span>
              </div>
            </div>
          </div>
        </template>
      </draggable>
    </div>

    <div class="preview-section">
      <h4>
        <i class="pi pi-eye"></i>
        Order Preview
      </h4>
      <div class="order-preview">
        <Tag
          v-for="(field, idx) in localFields"
          :key="field.src_column_physical_name"
          :value="`${idx + 1}. ${field.src_column_name}`"
          severity="info"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import draggable from 'vuedraggable'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import type { MappingDetailV2 } from '@/stores/mappingsStoreV2'

interface Props {
  fields: MappingDetailV2[]
}

interface Emits {
  (e: 'update:fields', fields: MappingDetailV2[]): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const localFields = ref<MappingDetailV2[]>([...props.fields])

// Watch for external changes
watch(() => props.fields, (newFields) => {
  localFields.value = [...newFields]
}, { deep: true })

// Watch for local changes
watch(localFields, (newFields) => {
  // Update field_order based on new position
  const updatedFields = newFields.map((field, index) => ({
    ...field,
    field_order: index + 1
  }))
  emit('update:fields', updatedFields)
}, { deep: true })

function handleDragEnd() {
  console.log('[Field Order Editor] Drag ended, new order:', localFields.value.map(f => f.src_column_name))
}
</script>

<style scoped>
.field-order-editor {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.info-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.field-list {
  background: var(--surface-50);
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 1rem;
}

.field-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: white;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  margin-bottom: 0.5rem;
  transition: all 0.2s ease;
  cursor: move;
}

.field-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-color: var(--gainwell-primary);
}

.field-item:last-child {
  margin-bottom: 0;
}

.drag-handle {
  color: var(--text-color-secondary);
  cursor: grab;
  padding: 0.5rem;
}

.drag-handle:active {
  cursor: grabbing;
}

/* Ghost element while dragging */
.ghost {
  opacity: 0.5;
  background: var(--gainwell-light);
}

.field-order {
  flex-shrink: 0;
}

.field-content {
  flex: 1;
  min-width: 0;
}

.field-name {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.field-name strong {
  color: var(--text-color);
}

.physical-name {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  font-family: 'Courier New', monospace;
}

.preview-section {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.preview-section h4 {
  margin: 0 0 0.75rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--gainwell-dark);
}

.order-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}


/* Responsive */
@media (max-width: 768px) {
  .field-item {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>

