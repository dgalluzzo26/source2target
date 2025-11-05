<template>
  <div class="help-button-wrapper">
    <Button
      :icon="icon"
      :label="label"
      :severity="severity"
      :outlined="outlined"
      :text="text"
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
      :style="{ width: '90vw', maxWidth: '1200px' }"
    >
      <template #header>
        <div class="help-dialog-header">
          <i :class="getHeaderIcon()" class="help-header-icon"></i>
          <h2>{{ getHeaderTitle() }}</h2>
        </div>
      </template>
      
      <div class="help-content-wrapper">
        <iframe 
          v-if="helpUrl"
          :src="helpUrl"
          class="help-iframe"
          frameborder="0"
          @load="onIframeLoad"
        ></iframe>
        <div v-else class="help-loading">
          <i class="pi pi-spin pi-spinner" style="font-size: 2rem;"></i>
          <p>Loading help content...</p>
        </div>
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
  customClass?: string
  tooltip?: string
}

const props = withDefaults(defineProps<Props>(), {
  icon: 'pi pi-question-circle',
  label: '',
  severity: 'info',
  outlined: false,
  text: false,
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

:deep(.help-dialog) {
  height: 85vh;
}

:deep(.help-dialog .p-dialog-content) {
  padding: 0;
  height: calc(85vh - 80px);
  overflow: hidden;
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

.help-content-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
}

.help-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: white;
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
</style>
