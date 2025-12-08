<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

interface MenuItem {
  label: string
  icon: string
  to?: string
  badge?: number
  items?: MenuItem[]
}

const props = defineProps<{
  collapsed: boolean
}>()

const router = useRouter()
const route = useRoute()

const menuItems = ref<MenuItem[]>([
  {
    label: 'Dashboard',
    icon: 'pi pi-home',
    to: '/'
  },
  {
    label: 'Data Sources',
    icon: 'pi pi-database',
    to: '/sources'
  },
  {
    label: 'Target Systems',
    icon: 'pi pi-cloud-upload',
    to: '/targets'
  },
  {
    label: 'Jobs',
    icon: 'pi pi-clock',
    to: '/jobs',
    badge: 3
  },
  {
    label: 'Monitoring',
    icon: 'pi pi-chart-line',
    to: '/monitoring'
  },
  {
    label: 'Settings',
    icon: 'pi pi-cog',
    to: '/settings'
  }
])

const isActive = (path: string) => {
  return route.path === path
}

const navigate = (path?: string) => {
  if (path) {
    router.push(path)
  }
}

const sidebarClass = computed(() => ({
  'sidebar': true,
  'sidebar-collapsed': props.collapsed
}))
</script>

<template>
  <div :class="sidebarClass">
    <nav class="sidebar-nav">
      <div class="nav-items">
        <div 
          v-for="item in menuItems" 
          :key="item.label"
          :class="['nav-item', { active: isActive(item.to || '') }]"
          @click="navigate(item.to)"
        >
          <i :class="['nav-icon', item.icon]"></i>
          <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
          <span v-if="item.badge && !collapsed" class="nav-badge">{{ item.badge }}</span>
        </div>
      </div>
    </nav>
    
    <div v-if="!collapsed" class="sidebar-footer">
      <div class="version-info">
        <i class="pi pi-info-circle"></i>
        <span>Version 1.0.0</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sidebar {
  position: fixed;
  top: var(--toolbar-height);
  left: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: white;
  border-right: 1px solid var(--border-color);
  transition: width 0.3s ease;
  overflow: hidden;
  z-index: 999;
  display: flex;
  flex-direction: column;
}

.sidebar-collapsed {
  width: var(--sidebar-collapsed-width);
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 1rem 0;
}

.nav-items {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0 0.5rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-color-secondary);
  font-weight: 500;
  position: relative;
  white-space: nowrap;
}

.sidebar-collapsed .nav-item {
  justify-content: center;
  padding: 0.875rem;
}

.nav-item:hover {
  background-color: var(--surface-100);
  color: var(--text-color);
}

.nav-item.active {
  background-color: rgba(0, 255, 163, 0.1);
  color: var(--gainwell-dark);
  font-weight: 600;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background-color: var(--gainwell-accent);
  border-radius: 0 2px 2px 0;
}

.nav-icon {
  font-size: 1.25rem;
  min-width: 1.25rem;
}

.nav-item.active .nav-icon {
  color: var(--gainwell-accent);
}

.nav-label {
  flex: 1;
  font-size: 0.9375rem;
}

.nav-badge {
  background-color: var(--gainwell-accent);
  color: var(--gainwell-dark);
  padding: 0.125rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 700;
  min-width: 20px;
  text-align: center;
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid var(--border-color);
}

.version-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-color-secondary);
  font-size: 0.75rem;
  padding: 0.5rem;
}

/* Scrollbar Styling */
.sidebar-nav::-webkit-scrollbar {
  width: 4px;
}

.sidebar-nav::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-nav::-webkit-scrollbar-thumb {
  background: var(--surface-300);
  border-radius: 4px;
}

.sidebar-nav::-webkit-scrollbar-thumb:hover {
  background: var(--surface-400);
}
</style>

