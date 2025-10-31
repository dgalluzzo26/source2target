<template>
  <div class="admin-view">
    <div class="page-header">
      <h1>
        <i class="pi pi-shield"></i>
        Administration
      </h1>
      <p>User management and system administration</p>
    </div>

    <Card>
      <template #content>
        <div class="coming-soon">
          <i class="pi pi-shield" style="font-size: 4rem; color: var(--p-primary-color); margin-bottom: 1rem;"></i>
          <h2>Coming Soon</h2>
          <p>The administration interface will include:</p>
          <ul>
            <li>User management and permissions</li>
            <li>System logs and audit trails</li>
            <li>Performance monitoring</li>
            <li>Data backup and recovery</li>
            <li>System maintenance tools</li>
          </ul>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
// Admin logic will be implemented here
</script>

<style scoped>
.admin-view {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h1 {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0 0 0.5rem 0;
  color: var(--p-text-color);
  font-size: 2rem;
}

.page-header p {
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: 1.125rem;
}

.coming-soon {
  text-align: center;
  padding: 3rem 2rem;
}

.coming-soon h2 {
  margin: 0 0 1rem 0;
  color: var(--p-text-color);
}

.coming-soon p {
  margin: 0 0 1.5rem 0;
  color: var(--p-text-muted-color);
  font-size: 1.125rem;
}

.coming-soon ul {
  text-align: left;
  max-width: 400px;
  margin: 0 auto;
  color: var(--p-text-muted-color);
}

.coming-soon li {
  margin-bottom: 0.5rem;
}
</style>

