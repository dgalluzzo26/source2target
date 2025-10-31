<script setup lang="ts">
import { ref } from 'vue'
import AppToolbar from './components/AppToolbar.vue'
import AppSidebar from './components/AppSidebar.vue'

const sidebarCollapsed = ref(false)

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}
</script>

<template>
  <div class="app-container">
    <AppToolbar 
      :sidebar-collapsed="sidebarCollapsed"
      @toggle-sidebar="toggleSidebar"
    />
    
    <AppSidebar :collapsed="sidebarCollapsed" />
    
    <main class="main-content" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  background-color: var(--surface-50);
  overflow-x: hidden;
  width: 100%;
}

.main-content {
  position: fixed;
  top: var(--toolbar-height);
  left: var(--sidebar-width);
  right: 0;
  bottom: 0;
  transition: left 0.3s ease;
  padding: 1.5rem;
  overflow-y: auto;
  overflow-x: hidden;
}

.main-content.sidebar-collapsed {
  left: var(--sidebar-collapsed-width);
}
</style>
