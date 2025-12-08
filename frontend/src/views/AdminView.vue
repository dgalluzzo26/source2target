<template>
  <div class="admin-view">
    <div class="page-header">
      <h1>
        <i class="pi pi-shield"></i>
        System Administration
      </h1>
      <p>Manage system settings and configuration</p>
    </div>

    <div class="admin-cards">
      <Card class="admin-card" @click="goToConfig">
        <template #title>
          <i class="pi pi-cog"></i> Configuration
        </template>
        <template #content>
          <p>Manage database connections, vector search, and application settings.</p>
        </template>
      </Card>

      <Card class="admin-card" @click="goToSemanticFields">
        <template #title>
          <i class="pi pi-table"></i> Semantic Fields
        </template>
        <template #content>
          <p>Manage target field definitions and semantic descriptions.</p>
        </template>
      </Card>

      <Card class="admin-card info-card">
        <template #title>
          <i class="pi pi-info-circle"></i> Quick Transforms
        </template>
        <template #content>
          <p>SQL transformations are now built into the mapping workflow. Use the "Quick Transform" dropdown or AI Helper when creating mappings.</p>
          <p class="hint">No separate transformation library needed.</p>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import Card from 'primevue/card'

const router = useRouter()

function goToConfig() {
  router.push({ name: 'config' })
}

function goToSemanticFields() {
  router.push({ name: 'semantic-fields' })
}
</script>

<style scoped>
.admin-view {
  padding: 0;
  max-width: 100%;
  margin: 0;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h1 {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0 0 0.5rem 0;
  color: var(--gainwell-primary);
  font-size: 2rem;
}

.page-header p {
  margin: 0;
  color: var(--gainwell-text-secondary);
  font-size: 1.125rem;
}

.admin-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.admin-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.admin-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
}

.admin-card.info-card {
  cursor: default;
  background: var(--surface-50);
}

.admin-card.info-card:hover {
  transform: none;
  box-shadow: none;
}

.admin-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--gainwell-primary);
}

.admin-card p {
  margin: 0 0 0.5rem 0;
  color: var(--text-color-secondary);
}

.admin-card .hint {
  font-style: italic;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}
</style>
