<template>
  <div class="admin-view">
    <div class="page-header">
      <h1>
        <i class="pi pi-shield"></i>
        Administration
      </h1>
      <p>System administration and configuration</p>
    </div>

    <TabView>
      <TabPanel header="Transformation Library">
        <template #header>
          <i class="pi pi-code tab-icon"></i>
          <span>Transformation Library</span>
        </template>
        <TransformationManager />
      </TabPanel>

      <TabPanel header="System Settings">
        <template #header>
          <i class="pi pi-cog tab-icon"></i>
          <span>System Settings</span>
        </template>
        <Card>
          <template #content>
            <div class="coming-soon">
              <i class="pi pi-cog" style="font-size: 3rem; color: var(--gainwell-secondary); margin-bottom: 1rem;"></i>
              <h3>Coming Soon</h3>
              <p>System settings and configuration options will be available here.</p>
            </div>
          </template>
        </Card>
      </TabPanel>

      <TabPanel header="User Management">
        <template #header>
          <i class="pi pi-users tab-icon"></i>
          <span>User Management</span>
        </template>
        <Card>
          <template #content>
            <div class="coming-soon">
              <i class="pi pi-users" style="font-size: 3rem; color: var(--gainwell-secondary); margin-bottom: 1rem;"></i>
              <h3>Coming Soon</h3>
              <p>User management and permissions will be available here.</p>
            </div>
          </template>
        </Card>
      </TabPanel>

      <TabPanel header="Audit Logs">
        <template #header>
          <i class="pi pi-history tab-icon"></i>
          <span>Audit Logs</span>
        </template>
        <Card>
          <template #content>
            <div class="coming-soon">
              <i class="pi pi-history" style="font-size: 3rem; color: var(--gainwell-secondary); margin-bottom: 1rem;"></i>
              <h3>Coming Soon</h3>
              <p>System audit logs and activity trails will be available here.</p>
            </div>
          </template>
        </Card>
      </TabPanel>
    </TabView>
  </div>
</template>

<script setup lang="ts">
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';
import Card from 'primevue/card';
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

.tab-icon {
  margin-right: 0.5rem;
}

.coming-soon {
  text-align: center;
  padding: 3rem 2rem;
}

.coming-soon h3 {
  margin: 0 0 1rem 0;
  color: var(--gainwell-text-primary);
}

.coming-soon p {
  margin: 0;
  color: var(--gainwell-text-secondary);
  font-size: 1rem;
}

:deep(.p-tabview .p-tabview-nav) {
  background: transparent;
}

:deep(.p-tabview .p-tabview-panels) {
  background: transparent;
  padding: 1.5rem 0 0 0;
}
</style>
