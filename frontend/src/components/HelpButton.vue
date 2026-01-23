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
        style="width: 100%; height: 80vh; min-height: 80vh; border: none; display: block;"
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
/**
 * HelpButton Component
 * 
 * A reusable help button component that displays context-sensitive help documentation
 * in a modal dialog. The help content is loaded from static HTML files via iframe.
 * 
 * Features:
 * - Configurable button appearance (icon, label, severity, style)
 * - Maps help types to appropriate HTML documentation files
 * - Large, readable dialog (90vh) with embedded iframe
 * - Highly visible close button for better UX
 * - Support for deep linking to specific sections via anchor tags
 * - Responsive tooltip on hover
 * 
 * Usage:
 * ```vue
 * <HelpButton 
 *   helpType="quick-start"
 *   label="Quick Start"
 *   severity="info"
 * />
 * ```
 * 
 * Help Types:
 * - quick-start: Getting started guide
 * - user-guide: Comprehensive user documentation
 * - ai-mapping: AI suggestion feature help
 * - manual-search: Manual search feature help
 * - templates: CSV template upload help
 * - admin-config: Admin configuration guide
 * - system-status: System health check help
 * 
 * @component
 */
import { ref, computed } from 'vue'
import Dialog from 'primevue/dialog'

/**
 * Component props interface.
 * 
 * Defines all configurable properties for the HelpButton component,
 * allowing flexible customization of appearance and behavior.
 */
interface Props {
  /** Type of help content to display (maps to HTML file) */
  helpType: 'quick-start' | 'user-guide' | 'ai-mapping' | 'manual-search' | 'templates' | 'admin-config' | 'admin-guide' | 'developer-guide' | 'system-status'
  /** Optional section anchor for deep linking (e.g., "#mapping-fields") */
  section?: string
  /** Button icon (PrimeIcon class name) */
  icon?: string
  /** Button text label */
  label?: string
  /** Button color severity (primary, secondary, success, info, warning, danger) */
  severity?: string
  /** Whether to use outlined button style */
  outlined?: boolean
  /** Whether to use text-only button style */
  text?: boolean
  /** Whether to use rounded button style */
  rounded?: boolean
  /** Additional CSS class for custom styling */
  customClass?: string
  /** Tooltip text shown on hover */
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

// ============================================================================
// Component State
// ============================================================================

/** Controls dialog visibility */
const showDialog = ref(false)

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Computed URL for help content based on helpType prop.
 * 
 * Maps help type to the corresponding HTML file in the /help directory.
 * Supports optional section anchors for deep linking to specific parts.
 * 
 * @returns Full URL path to the help HTML file
 */
const helpUrl = computed(() => {
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
    case 'admin-guide':
      return `${baseUrl}/admin-guide.html${props.section ? '#' + props.section : ''}`
    case 'developer-guide':
      return `${baseUrl}/developer-guide.html${props.section ? '#' + props.section : ''}`
    case 'system-status':
      return `${baseUrl}/system-status-help.html`
    default:
      return `${baseUrl}/user-guide.html`
  }
})

// ============================================================================
// Helper Methods
// ============================================================================

/**
 * Get icon for dialog header based on help type.
 * 
 * Returns an appropriate PrimeIcon class name that visually represents
 * the type of help content being displayed.
 * 
 * @returns PrimeIcon class name (e.g., 'pi pi-book')
 */
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
    case 'admin-guide':
      return 'pi pi-shield'
    case 'developer-guide':
      return 'pi pi-code'
    case 'system-status':
      return 'pi pi-heart'
    default:
      return 'pi pi-question-circle'
  }
}

/**
 * Get title for dialog header based on help type.
 * 
 * Returns a user-friendly title that clearly indicates what help
 * content is being displayed in the dialog.
 * 
 * @returns Human-readable dialog title
 */
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
    case 'admin-guide':
      return 'Administrator Guide'
    case 'developer-guide':
      return 'Developer Guide'
    case 'system-status':
      return 'System Status Help'
    default:
      return 'Help'
  }
}

/**
 * Iframe load event handler.
 * 
 * Called when the help HTML content finishes loading in the iframe.
 * Currently just logs for debugging; could be extended for loading indicators.
 */
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
  fill: #fff !important;
  stroke: #fff !important;
}

/* Force all SVG paths to be white */
:deep(.help-dialog .p-dialog-header-icon svg path),
:deep(.help-dialog .p-dialog-header-icon .p-icon path) {
  fill: #fff !important;
  stroke: #fff !important;
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
