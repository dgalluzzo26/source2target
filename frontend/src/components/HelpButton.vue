<template>
  <div class="help-button-wrapper">
    <Button
      :icon="icon"
      :label="label"
      :severity="severity"
      :outlined="outlined"
      :text="text"
      :rounded="rounded"
      @click="showDialog = true"
      :class="['help-button', customClass]"
      v-tooltip.left="tooltip"
    />
    
    <Dialog
      v-model:visible="showDialog"
      :modal="true"
      :dismissableMask="true"
      :closable="true"
      :draggable="false"
      class="help-dialog"
      :style="{ width: '95vw', maxWidth: '1400px', height: '90vh' }"
    >
      <template #header>
        <div class="help-dialog-header">
          <i :class="getHeaderIcon()" class="help-header-icon"></i>
          <h2>{{ getHeaderTitle() }}</h2>
        </div>
      </template>
      
      <iframe 
        v-if="helpUrl"
        :src="helpUrl"
        class="help-iframe"
        frameborder="0"
        style="width: 100%; height: 100%; border: none; display: block;"
        @load="onIframeLoad"
      ></iframe>
      <div v-else class="help-loading">
        <i class="pi pi-spin pi-spinner" style="font-size: 2rem;"></i>
        <p>Loading help content...</p>
      </div>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Dialog from 'primevue/dialog'

interface Props {
  helpType: 'quick-start' | 'user-guide' | 'ai-mapping' | 'manual-search' | 'templates' | 'admin-config' | 'system-status'
  section?: string
  icon?: string
  label?: string
  severity?: string
  outlined?: boolean
  text?: boolean
  rounded?: boolean
  customClass?: string
  tooltip?: string
}

const props = withDefaults(defineProps<Props>(), {
  icon: 'pi pi-question-circle',
  label: '',
  severity: 'info',
  outlined: false,
  text: false,
  rounded: false,
  customClass: '',
  tooltip: 'View help documentation'
})

const showDialog = ref(false)

const helpUrl = computed(() => {
  // Map help types to their HTML files
  const baseUrl = '/help'
  switch (props.helpType) {
    case 'quick-start':
      return `${baseUrl}/quick-start.html`
    case 'user-guide':
      return `${baseUrl}/user-guide.html${props.section ? '#' + props.section : ''}`
    case 'ai-mapping':
      return `${baseUrl}/ai-mapping-help.html`
    case 'manual-search':
      return `${baseUrl}/manual-search-help.html`
    case 'templates':
      return `${baseUrl}/templates-help.html`
    case 'admin-config':
      return `${baseUrl}/admin-config-help.html`
    case 'system-status':
      return `${baseUrl}/system-status-help.html`
    default:
      return `${baseUrl}/user-guide.html`
  }
})

const getHeaderIcon = () => {
  switch (props.helpType) {
    case 'quick-start':
      return 'pi pi-bolt'
    case 'user-guide':
      return 'pi pi-book'
    case 'ai-mapping':
      return 'pi pi-sparkles'
    case 'manual-search':
      return 'pi pi-search'
    case 'templates':
      return 'pi pi-file'
    case 'admin-config':
      return 'pi pi-cog'
    case 'system-status':
      return 'pi pi-heart'
    default:
      return 'pi pi-question-circle'
  }
}

const getHeaderTitle = () => {
  switch (props.helpType) {
    case 'quick-start':
      return 'Quick Start Guide'
    case 'user-guide':
      return 'User Guide'
    case 'ai-mapping':
      return 'AI Mapping Help'
    case 'manual-search':
      return 'Manual Search Help'
    case 'templates':
      return 'Templates Help'
    case 'admin-config':
      return 'Administrator Configuration'
    case 'system-status':
      return 'System Status Help'
    default:
      return 'Help'
  }
}

const onIframeLoad = () => {
  console.log('Help content loaded')
}
</script>

<style scoped>
.help-button-wrapper {
  display: inline-block;
}

.help-button {
  white-space: nowrap;
}

/* Simple approach - just set explicit heights */
:deep(.help-dialog) {
  height: 90vh !important;
  max-height: 90vh !important;
}

:deep(.help-dialog .p-dialog) {
  height: 90vh !important;
  max-height: 90vh !important;
  display: flex !important;
  flex-direction: column !important;
}

:deep(.help-dialog .p-dialog-header) {
  flex: 0 0 auto !important;
  padding: 1.25rem !important;
  border-bottom: 1px solid #dee2e6 !important;
}

:deep(.help-dialog .p-dialog-content) {
  padding: 0 !important;
  flex: 1 !important;
  overflow: hidden !important;
  height: 100% !important;
}

/* SUPER VISIBLE RED CLOSE BUTTON */
:deep(.help-dialog .p-dialog-header .p-dialog-header-icon),
:deep(.help-dialog .p-dialog-header-icons .p-dialog-header-icon),
:deep(.help-dialog .p-dialog-header-icon) {
  color: #fff !important;
  background: #dc3545 !important;
  border-radius: 6px !important;
  width: 2.5rem !important;
  height: 2.5rem !important;
  min-width: 2.5rem !important;
  min-height: 2.5rem !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  border: 2px solid #dc3545 !important;
  opacity: 1 !important;
}

:deep(.help-dialog .p-dialog-header .p-dialog-header-icon:hover),
:deep(.help-dialog .p-dialog-header-icons .p-dialog-header-icon:hover),
:deep(.help-dialog .p-dialog-header-icon:hover) {
  color: #fff !important;
  background: #c82333 !important;
  border-color: #c82333 !important;
  transform: scale(1.1) !important;
  opacity: 1 !important;
}

:deep(.help-dialog .p-dialog-header-icon svg),
:deep(.help-dialog .p-dialog-header-icon .p-icon),
:deep(.help-dialog .p-dialog-header-icon i) {
  width: 1.25rem !important;
  height: 1.25rem !important;
  font-size: 1.25rem !important;
  font-weight: bold !important;
  color: #fff !important;
}

.help-dialog-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--gainwell-primary);
}

.help-header-icon {
  font-size: 1.5rem;
}

.help-dialog-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.help-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: white;
  display: block;
}

.help-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  color: var(--gainwell-primary);
}

.help-loading p {
  font-size: 1.1rem;
}

/* Fix tooltip readability - solid grey background */
:deep(.p-tooltip .p-tooltip-text) {
  background-color: #495057 !important;
  color: white !important;
  padding: 0.5rem 0.75rem !important;
  font-size: 0.9rem !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
  border-radius: 6px !important;
  font-weight: 500 !important;
}

:deep(.p-tooltip .p-tooltip-arrow) {
  border-right-color: #495057 !important;
}

:deep(.p-tooltip.p-tooltip-top .p-tooltip-arrow) {
  border-top-color: #495057 !important;
}

:deep(.p-tooltip.p-tooltip-bottom .p-tooltip-arrow) {
  border-bottom-color: #495057 !important;
}

:deep(.p-tooltip.p-tooltip-left .p-tooltip-arrow) {
  border-left-color: #495057 !important;
}
</style>
