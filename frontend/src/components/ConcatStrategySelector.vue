<template>
  <div class="concat-strategy-selector">
    <div class="strategy-options">
      <div 
        v-for="option in strategyOptions" 
        :key="option.value"
        class="strategy-option"
        :class="{ 'selected': localStrategy === option.value }"
        @click="selectStrategy(option.value)"
      >
        <div class="option-header">
          <RadioButton 
            v-model="localStrategy" 
            :inputId="option.value" 
            :value="option.value"
            name="concat-strategy"
          />
          <label :for="option.value" class="option-label">
            <i :class="option.icon"></i>
            <strong>{{ option.label }}</strong>
          </label>
        </div>
        <div class="option-description">
          {{ option.description }}
        </div>
        <div class="option-example">
          <span class="example-label">Example:</span>
          <code>{{ option.example }}</code>
        </div>
      </div>
    </div>

    <!-- Custom Value Input -->
    <div v-if="localStrategy === 'CUSTOM'" class="custom-input-section">
      <label for="custom-concat">Custom Separator:</label>
      <div class="custom-input-wrapper">
        <InputText
          id="custom-concat"
          v-model="localCustomValue"
          placeholder="Enter custom separator (e.g., ' - ', ' | ', etc.)"
          class="custom-input"
          @input="handleCustomValueChange"
        />
        <small class="hint">Enter the text to use between fields (spaces, symbols, etc.)</small>
      </div>
    </div>

    <!-- Preview -->
    <div class="preview-section">
      <h4>
        <i class="pi pi-eye"></i>
        Concatenation Preview
      </h4>
      <div class="preview-box">
        <code>{{ previewText }}</code>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import RadioButton from 'primevue/radiobutton'
import InputText from 'primevue/inputtext'

interface Props {
  strategy: 'SPACE' | 'COMMA' | 'PIPE' | 'CUSTOM' | 'NONE'
  customValue?: string
}

interface Emits {
  (e: 'update:strategy', value: 'SPACE' | 'COMMA' | 'PIPE' | 'CUSTOM' | 'NONE'): void
  (e: 'update:customValue', value: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const localStrategy = ref(props.strategy)
const localCustomValue = ref(props.customValue || '')

const strategyOptions = [
  {
    value: 'SPACE',
    label: 'Space Separator',
    icon: 'pi pi-arrows-h',
    description: 'Fields separated by a single space',
    example: 'John Doe'
  },
  {
    value: 'COMMA',
    label: 'Comma Separator',
    icon: 'pi pi-ellipsis-h',
    description: 'Fields separated by comma and space',
    example: 'John, Doe'
  },
  {
    value: 'PIPE',
    label: 'Pipe Separator',
    icon: 'pi pi-minus',
    description: 'Fields separated by pipe symbol',
    example: 'John | Doe'
  },
  {
    value: 'CUSTOM',
    label: 'Custom Separator',
    icon: 'pi pi-pencil',
    description: 'Specify your own separator',
    example: 'John [your text] Doe'
  },
  {
    value: 'NONE',
    label: 'No Separator',
    icon: 'pi pi-link',
    description: 'Fields concatenated directly without separator',
    example: 'JohnDoe'
  }
]

const previewText = computed(() => {
  const field1 = 'FIRST_NAME'
  const field2 = 'LAST_NAME'
  
  switch (localStrategy.value) {
    case 'SPACE':
      return `CONCAT(${field1}, ' ', ${field2})`
    case 'COMMA':
      return `CONCAT(${field1}, ', ', ${field2})`
    case 'PIPE':
      return `CONCAT(${field1}, ' | ', ${field2})`
    case 'CUSTOM':
      const customSep = localCustomValue.value || '[separator]'
      return `CONCAT(${field1}, '${customSep}', ${field2})`
    case 'NONE':
      return `CONCAT(${field1}, ${field2})`
    default:
      return ''
  }
})

watch(() => props.strategy, (newVal) => {
  localStrategy.value = newVal
})

watch(() => props.customValue, (newVal) => {
  localCustomValue.value = newVal || ''
})

watch(localStrategy, (newVal) => {
  emit('update:strategy', newVal)
})

function selectStrategy(value: typeof localStrategy.value) {
  localStrategy.value = value
}

function handleCustomValueChange() {
  emit('update:customValue', localCustomValue.value)
}
</script>

<style scoped>
.concat-strategy-selector {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.strategy-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.strategy-option {
  padding: 1rem;
  border: 2px solid var(--surface-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.strategy-option:hover {
  border-color: var(--gainwell-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.strategy-option.selected {
  border-color: var(--gainwell-primary);
  background: var(--gainwell-light);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.option-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.option-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  flex: 1;
}

.option-label i {
  color: var(--gainwell-primary);
}

.option-label strong {
  color: var(--text-color);
}

.option-description {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
  padding-left: 2rem;
}

.option-example {
  padding-left: 2rem;
  margin-top: 0.5rem;
}

.example-label {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  margin-right: 0.5rem;
}

.option-example code {
  font-family: 'Courier New', monospace;
  background: var(--surface-100);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.9rem;
  color: var(--gainwell-dark);
}

.custom-input-section {
  padding: 1rem;
  background: var(--surface-50);
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.custom-input-section label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.custom-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.custom-input {
  width: 100%;
}

.hint {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
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

.preview-box {
  padding: 1rem;
  background: white;
  border: 1px solid var(--surface-border);
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  overflow-x: auto;
}

.preview-box code {
  color: var(--gainwell-dark);
  font-size: 0.95rem;
}

/* Responsive */
@media (max-width: 768px) {
  .strategy-options {
    grid-template-columns: 1fr;
  }
}
</style>

