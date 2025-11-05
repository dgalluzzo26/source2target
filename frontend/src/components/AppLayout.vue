<template>
  <div class="layout-wrapper">
    <!-- Top Header -->
    <div class="layout-topbar">
      <div class="layout-topbar-logo">
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
    <div class="layout-sidebar">
      <div class="layout-menu">
        <ul class="layout-menu-root">
          <li>
            <router-link to="/" class="layout-menuitem-link">
              <i class="layout-menuitem-icon pi pi-home"></i>
              <span class="layout-menuitem-text">Introduction</span>
            </router-link>
          </li>
          <li>
            <router-link to="/mapping" class="layout-menuitem-link">
              <i class="layout-menuitem-icon pi pi-sitemap"></i>
              <span class="layout-menuitem-text">Field Mapping</span>
            </router-link>
          </li>
          <li v-if="userStore.isAdmin">
            <router-link to="/config" class="layout-menuitem-link">
              <i class="layout-menuitem-icon pi pi-cog"></i>
              <span class="layout-menuitem-text">Configuration</span>
            </router-link>
          </li>
        </ul>
      </div>
    </div>

    <!-- Main Content -->
    <div class="layout-main-container" style="width: calc(100% - 16rem) !important; max-width: none !important; margin-right: 0 !important;">
      <div class="layout-main" style="width: 100% !important; max-width: none !important; margin: 0 !important; padding: 0.5rem !important;">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

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

.layout-topbar-logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
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
  width: 16rem;
  height: calc(100vh - 4rem);
  z-index: 996;
  background: var(--gainwell-light);
  border-right: 1px solid var(--gainwell-border);
  overflow-y: auto;
}

.layout-menu {
  padding: 1rem;
}

.layout-menu-root {
  list-style: none;
  margin: 0;
  padding: 0;
}

.layout-menu-root > li {
  margin-bottom: 0.5rem;
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
}

.layout-menuitem-link:hover {
  background: white;
  border-color: var(--gainwell-secondary);
  transform: translateY(-1px);
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

/* Main Content Area */
.layout-main-container {
  margin-left: 16rem;
  margin-top: 4rem;
  min-height: calc(100vh - 4rem);
  width: calc(100% - 16rem);
  max-width: none;
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