<template>
  <div class="admin-view">
    <div class="page-header">
      <h1>
        <i class="pi pi-shield"></i>
        Transformation Library
      </h1>
      <p>Manage reusable SQL transformation templates</p>
    </div>

    <TransformationManager />
  </div>
</template>

<script setup lang="ts">
import TransformationManager from '@/components/TransformationManager.vue';
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
</style>
