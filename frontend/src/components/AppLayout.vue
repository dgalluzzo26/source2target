<template>
  <div class="layout-wrapper">
    <!-- Top Header -->
    <div class="layout-topbar">
      <div class="layout-topbar-left">
        <div class="sidebar-toggle-header" @click="toggleSidebar">
          <i class="pi pi-bars"></i>
        </div>
        
        <img src="/gainwell-logo-suite-061720-logosuite-png-gainwell-logo-150-r.png" alt="Gainwell Technologies" class="logo" />
        
        <span class="logo-text">Source-to-Target Mapping Platform</span>
      </div>
      
      <div class="layout-topbar-menu">
        <div class="user-info">
          <i class="pi pi-user"></i>
          <span>{{ userStore.currentUser?.display_name || userStore.currentUser?.email || 'Loading...' }}</span>
          <Badge v-if="userStore.isAdmin" value="Admin" severity="success" class="user-badge" />
          <Badge v-else value="User" severity="secondary" class="user-badge" />
        </div>
      </div>
    </div>

    <!-- Sidebar Navigation -->
    <div class="layout-sidebar" :class="{ 'collapsed': sidebarCollapsed }">
      <div class="layout-menu">
        <ul class="layout-menu-root">
          <li>
            <router-link to="/" class="layout-menuitem-link" v-tooltip.right="sidebarCollapsed ? 'Home' : ''">
              <i class="layout-menuitem-icon pi pi-home"></i>
              <span class="layout-menuitem-text" v-if="!sidebarCollapsed">Home</span>
            </router-link>
          </li>
          
          <!-- V4 Target-First Workflow -->
          <li class="menu-section" v-if="!sidebarCollapsed">
            <span class="menu-section-label">Target-First Mapping</span>
          </li>
          <li>
            <router-link to="/projects" class="layout-menuitem-link" v-tooltip.right="sidebarCollapsed ? 'Projects' : ''">
              <i class="layout-menuitem-icon pi pi-folder"></i>
              <span class="layout-menuitem-text" v-if="!sidebarCollapsed">Projects</span>
            </router-link>
          </li>
          
          <!-- V3 Source-First Workflow (Legacy) - Hidden, accessible via direct URL if needed -->
          <!-- 
          <li class="menu-section" v-if="!sidebarCollapsed">
            <span class="menu-section-label">Source-First (Legacy)</span>
          </li>
          <li>
            <router-link to="/unmapped-fields" class="layout-menuitem-link" v-tooltip.right="sidebarCollapsed ? 'Create Mappings' : ''">
              <i class="layout-menuitem-icon pi pi-plus-circle"></i>
              <span class="layout-menuitem-text" v-if="!sidebarCollapsed">Create Mappings</span>
            </router-link>
          </li>
          <li>
            <router-link to="/mappings" class="layout-menuitem-link" v-tooltip.right="sidebarCollapsed ? 'View Mappings' : ''">
              <i class="layout-menuitem-icon pi pi-list"></i>
              <span class="layout-menuitem-text" v-if="!sidebarCollapsed">View Mappings</span>
            </router-link>
          </li>
          -->
          
          <!-- Admin Section -->
          <li class="menu-section" v-if="!sidebarCollapsed && userStore.isAdmin">
            <span class="menu-section-label">Administration</span>
          </li>
          <li v-if="userStore.isAdmin">
            <router-link to="/semantic-fields" class="layout-menuitem-link" v-tooltip.right="sidebarCollapsed ? 'Semantic Management' : ''">
              <i class="layout-menuitem-icon pi pi-database"></i>
              <span class="layout-menuitem-text" v-if="!sidebarCollapsed">Semantic Management</span>
            </router-link>
          </li>
          <li v-if="userStore.isAdmin">
            <router-link to="/admin/patterns" class="layout-menuitem-link" v-tooltip.right="sidebarCollapsed ? 'Import Patterns' : ''">
              <i class="layout-menuitem-icon pi pi-upload"></i>
              <span class="layout-menuitem-text" v-if="!sidebarCollapsed">Import Patterns</span>
            </router-link>
          </li>
          <li v-if="userStore.isAdmin">
            <router-link to="/config" class="layout-menuitem-link" v-tooltip.right="sidebarCollapsed ? 'Settings' : ''">
              <i class="layout-menuitem-icon pi pi-cog"></i>
              <span class="layout-menuitem-text" v-if="!sidebarCollapsed">Settings</span>
            </router-link>
          </li>
          
          <!-- Help Section -->
          <li class="menu-section" v-if="!sidebarCollapsed">
            <span class="menu-section-label">Help</span>
          </li>
          <li>
            <div class="layout-menuitem-link help-button-wrapper" v-tooltip.right="sidebarCollapsed ? 'User Guide' : ''">
              <HelpButton 
                help-type="user-guide" 
                label="User Guide" 
                severity="secondary"
                icon="pi pi-book"
                tooltip=""
                :outlined="true"
                custom-class="sidebar-help-button"
              />
            </div>
          </li>
          <li v-if="userStore.isAdmin">
            <div class="layout-menuitem-link help-button-wrapper" v-tooltip.right="sidebarCollapsed ? 'Admin Guide' : ''">
              <HelpButton 
                help-type="admin-guide" 
                label="Admin Guide" 
                severity="secondary"
                icon="pi pi-cog"
                tooltip=""
                :outlined="true"
                custom-class="sidebar-help-button"
              />
            </div>
          </li>
          <li v-if="userStore.isAdmin">
            <div class="layout-menuitem-link help-button-wrapper" v-tooltip.right="sidebarCollapsed ? 'Developer Guide' : ''">
              <HelpButton 
                help-type="developer-guide" 
                label="Developer Guide" 
                severity="secondary"
                icon="pi pi-code"
                tooltip=""
                :outlined="true"
                custom-class="sidebar-help-button"
              />
            </div>
          </li>
          <li>
            <a href="/help/ai-architecture.html" target="_blank" class="layout-menuitem-link" v-tooltip.right="sidebarCollapsed ? 'AI Architecture' : ''">
              <i class="layout-menuitem-icon pi pi-sitemap"></i>
              <span class="layout-menuitem-text" v-if="!sidebarCollapsed">AI Architecture</span>
            </a>
          </li>
        </ul>
      </div>
    </div>

    <!-- Main Content -->
    <div class="layout-main-container" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <div class="layout-main" style="width: 100% !important; max-width: none !important; margin: 0 !important; padding: 0.5rem !important;">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import Badge from 'primevue/badge'
import HelpButton from '@/components/HelpButton.vue'

const userStore = useUserStore()
const sidebarCollapsed = ref(false)

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// Automatically initialize user on app load (like original app)
onMounted(() => {
  userStore.initializeAuth()
})
</script>

<style scoped>
/* Gainwell Brand Colors - Based on Actual Logo and Original App */
:root {
  --gainwell-primary: #4a5568;      /* Dark slate gray (from original app) */
  --gainwell-secondary: #38a169;    /* Gainwell green (from logo) */
  --gainwell-light: #f8f9fa;        /* Light gray background */
  --gainwell-border: #dee2e6;       /* Light gray borders */
}

.layout-wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Top Header with Gainwell Styling */
.layout-topbar {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 4rem;
  z-index: 997;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  background: var(--gainwell-primary);
  border-bottom: 2px solid var(--gainwell-secondary);
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.15);
  color: white;
}

/* Left side of header - Logo + Hamburger + Title */
.layout-topbar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

/* Sidebar Toggle - Hamburger Menu Icon */
.sidebar-toggle-header {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.sidebar-toggle-header:hover {
  background: rgba(255, 255, 255, 0.25);
}

.sidebar-toggle-header i {
  font-size: 1.25rem;
  color: white;
}

.logo {
  height: 2.5rem;
  width: auto;
}

.logo-text {
  font-size: 1.5rem;
  font-weight: 600;
  color: white;
  margin: 0;
}

.layout-topbar-menu {
  display: flex;
  align-items: center;
  gap: 1rem;
}

/* User Info with Gainwell Styling */
.user-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: rgba(255, 255, 255, 0.15);
  padding: 0.5rem 1rem;
  border-radius: 20px;
  backdrop-filter: blur(10px);
  transition: all 0.2s ease;
  color: white;
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateY(-1px);
}

.user-info i {
  font-size: 1rem;
  color: var(--gainwell-secondary);
}

.user-badge {
  font-weight: 600;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
}

/* Sidebar with Gainwell Light Background */
.layout-sidebar {
  position: fixed;
  top: 4rem;
  left: 0;
  width: 20rem;
  height: calc(100vh - 4rem);
  z-index: 996;
  background: var(--gainwell-light);
  border-right: 1px solid var(--gainwell-border);
  overflow-y: auto;
  transition: width 0.3s ease;
}

.layout-sidebar.collapsed {
  width: 4rem;
}

.layout-menu {
  padding: 1rem;
}

.layout-sidebar.collapsed .layout-menu {
  padding: 1rem 0.5rem;
}

.layout-menu-root {
  list-style: none;
  margin: 0;
  padding: 0;
}

.layout-menu-root > li {
  margin-bottom: 0.5rem;
}

/* Menu Section Labels */
.menu-section {
  margin-top: 1.5rem;
  margin-bottom: 0.5rem;
  padding: 0 1rem;
}

.menu-section-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-color-secondary);
  opacity: 0.7;
}

/* Menu Items with Gainwell Styling */
.layout-menuitem-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  color: var(--gainwell-dark);
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.3s ease;
  background: white;
  border: 1px solid transparent;
  white-space: nowrap;
}

.layout-sidebar.collapsed .layout-menuitem-link {
  justify-content: center;
  padding: 0.75rem 0.5rem;
  gap: 0;
}

.layout-menuitem-link:hover {
  background: white;
  border-color: var(--gainwell-secondary);
  box-shadow: 0 4px 12px rgba(56, 161, 105, 0.15);
}

.layout-menuitem-link.router-link-active {
  background: linear-gradient(135deg, var(--gainwell-primary) 0%, var(--gainwell-secondary) 100%);
  color: white;
  border-left: 4px solid var(--gainwell-secondary);
  box-shadow: 0 4px 12px rgba(56, 161, 105, 0.25);
}

.layout-menuitem-icon {
  font-size: 1.125rem;
  color: inherit;
}

.layout-menuitem-text {
  font-weight: 500;
}

/* Help Button Wrapper in Sidebar */
.help-button-wrapper {
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  cursor: default;
  width: 100%;
}

.help-button-wrapper:hover {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.layout-sidebar.collapsed .help-button-wrapper {
  padding: 0.25rem !important;
}

/* Style help buttons to match menu items */
:deep(.sidebar-help-button) {
  width: 100% !important;
  justify-content: flex-start !important;
  background: white !important;
  color: var(--gainwell-dark) !important;
  border: 1px solid transparent !important;
  padding: 0.75rem 1rem !important;
  border-radius: 8px !important;
  box-shadow: none !important;
  text-align: left !important;
}

:deep(.sidebar-help-button:hover) {
  background: white !important;
  border-color: var(--gainwell-secondary) !important;
  box-shadow: 0 4px 12px rgba(56, 161, 105, 0.15) !important;
  color: var(--gainwell-dark) !important;
}

:deep(.sidebar-help-button .p-button-label) {
  font-weight: 500 !important;
  flex: 1 !important;
  text-align: left !important;
}

:deep(.sidebar-help-button .p-button-icon) {
  color: inherit !important;
  font-size: 1.125rem !important;
}

.layout-sidebar.collapsed :deep(.sidebar-help-button) {
  justify-content: center !important;
  padding: 0.75rem 0.5rem !important;
}

.layout-sidebar.collapsed :deep(.sidebar-help-button .p-button-label) {
  display: none !important;
}

/* Main Content Area */
.layout-main-container {
  margin-left: 20rem;
  margin-top: 4rem;
  min-height: calc(100vh - 4rem);
  width: calc(100% - 20rem);
  max-width: none;
  transition: margin-left 0.3s ease, width 0.3s ease;
}

.layout-main-container.sidebar-collapsed {
  margin-left: 4rem;
  width: calc(100% - 4rem);
}

.layout-main {
  padding: 0.5rem;
  background: #f8f9fa;
  min-height: calc(100vh - 4rem);
  width: 100%;
  max-width: none;
  margin: 0;
  box-sizing: border-box;
}

/* Badge Styling with Gainwell Colors */
:deep(.p-badge) {
  background: var(--gainwell-secondary);
  color: var(--gainwell-dark);
  font-weight: 600;
}

:deep(.p-badge.p-badge-info) {
  background: var(--gainwell-primary);
  color: white;
}

:deep(.p-badge.p-badge-success) {
  background: var(--gainwell-secondary);
  color: var(--gainwell-dark);
}

/* Responsive Design */
@media (max-width: 768px) {
  .layout-sidebar {
    transform: translateX(-100%);
    transition: transform 0.3s;
  }
  
  .layout-main-container {
    margin-left: 0;
    width: 100%;
  }
  
  .layout-topbar {
    padding: 0 1rem;
  }
  
  .logo-text {
    display: none;
  }
}

/* Global Gainwell Button Styling */
:deep(.p-button) {
  background: linear-gradient(135deg, var(--gainwell-primary), var(--gainwell-accent));
  border: none;
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(204, 27, 198, 0.15);
}

:deep(.p-button:hover) {
  background: linear-gradient(135deg, var(--gainwell-dark), var(--gainwell-primary));
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(27, 36, 166, 0.25);
}

:deep(.p-button.p-button-secondary) {
  background: var(--gainwell-light);
  color: var(--gainwell-dark);
}

:deep(.p-button.p-button-info) {
  background: linear-gradient(135deg, var(--gainwell-secondary), #00d49a);
  color: var(--gainwell-dark);
}

:deep(.p-button.p-button-help) {
  background: linear-gradient(135deg, var(--gainwell-dark), #2d3bc4);
  color: white;
}
</style>