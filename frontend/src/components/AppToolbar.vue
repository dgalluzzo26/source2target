<script setup lang="ts">
import { ref } from 'vue'
import Avatar from 'primevue/avatar'
import Button from 'primevue/button'

defineProps<{
  sidebarCollapsed: boolean
}>()

const emit = defineEmits<{
  toggleSidebar: []
}>()

const user = ref({
  name: 'John Doe',
  email: 'john.doe@gainwell.com'
})
</script>

<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <Button 
        icon="pi pi-bars" 
        text 
        rounded
        class="menu-toggle"
        @click="emit('toggleSidebar')"
      />
      <div class="logo-container">
        <svg class="logo" viewBox="0 0 200 50" xmlns="http://www.w3.org/2000/svg">
          <!-- Stylized 'g' with accent -->
          <text x="10" y="38" font-family="Arial, sans-serif" font-size="32" font-weight="700" fill="#424d5c">g</text>
          <rect x="18" y="12" width="8" height="20" fill="#00ffa3" transform="rotate(45 22 22)" />
          <text x="35" y="38" font-family="Arial, sans-serif" font-size="32" font-weight="700" fill="#424d5c">ainwell</text>
        </svg>
      </div>
    </div>
    
    <div class="toolbar-right">
      <div class="user-info">
        <div class="user-details">
          <span class="user-name">{{ user.name }}</span>
          <span class="user-email">{{ user.email }}</span>
        </div>
        <Avatar 
          :label="user.name.split(' ').map(n => n[0]).join('')" 
          class="user-avatar"
          shape="circle"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--toolbar-height);
  background: var(--gainwell-dark);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 1000;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.menu-toggle {
  color: white !important;
}

.menu-toggle:hover {
  background-color: rgba(255, 255, 255, 0.1) !important;
}

.logo-container {
  display: flex;
  align-items: center;
}

.logo {
  height: 32px;
  width: auto;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  transition: background-color 0.2s;
  cursor: pointer;
}

.user-info:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

.user-details {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.125rem;
}

.user-name {
  color: white;
  font-weight: 600;
  font-size: 0.875rem;
}

.user-email {
  color: var(--gainwell-gray-light);
  font-size: 0.75rem;
}

.user-avatar {
  background-color: var(--gainwell-accent);
  color: var(--gainwell-dark);
  font-weight: 700;
}

@media (max-width: 768px) {
  .user-details {
    display: none;
  }
}
</style>

