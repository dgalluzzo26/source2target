<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import { checkHealth, getData } from '../services/api'

interface DataItem {
  id: number
  name: string
  value: number
}

const healthStatus = ref<string>('')
const data = ref<DataItem[]>([])
const loading = ref(false)
const error = ref<string>('')

const checkApiHealth = async () => {
  loading.value = true
  error.value = ''
  
  const response = await checkHealth()
  
  if (response.error) {
    error.value = `Backend Error: ${response.error}`
    healthStatus.value = 'offline'
  } else {
    healthStatus.value = response.data?.status || 'unknown'
  }
  
  loading.value = false
}

const fetchData = async () => {
  loading.value = true
  error.value = ''
  
  const response = await getData()
  
  if (response.error) {
    error.value = `Failed to fetch data: ${response.error}`
  } else {
    data.value = response.data?.data || []
  }
  
  loading.value = false
}

onMounted(() => {
  checkApiHealth()
})
</script>

<template>
  <div class="home-view">
    <div class="page-header">
      <div class="flex align-items-center gap-2">
        <i class="pi pi-home"></i>
        <h1>Source2Target Dashboard</h1>
      </div>
    </div>

    <div class="content-wrapper">
      <!-- API Health Status -->
      <Card class="status-card">
        <template #content>
          <h3>API Health Status</h3>
          <div class="flex align-items-center gap-3">
            <Button 
              label="Check Health" 
              icon="pi pi-refresh" 
              @click="checkApiHealth"
              :loading="loading"
              severity="secondary"
            />
            <span v-if="healthStatus" class="status-badge">
              <i 
                :class="['pi', healthStatus === 'healthy' ? 'pi-check-circle' : 'pi-times-circle']"
                :style="{ color: healthStatus === 'healthy' ? 'green' : 'red' }"
              ></i>
              Backend: {{ healthStatus }}
            </span>
          </div>
        </template>
      </Card>

      <!-- Error Message -->
      <Message v-if="error" severity="error" :closable="false">
        {{ error }}
      </Message>

      <!-- Data Section -->
      <Card class="data-card">
        <template #content>
          <h3>Sample Data from Backend</h3>
          <Button 
            label="Fetch Data" 
            icon="pi pi-download" 
            @click="fetchData"
            :loading="loading"
          />
          
          <ProgressSpinner v-if="loading" class="spinner" />
          
          <DataTable 
            v-else-if="data.length > 0" 
            :value="data" 
            class="data-table"
            stripedRows
            showGridlines
          >
            <Column field="id" header="ID" sortable></Column>
            <Column field="name" header="Name" sortable></Column>
            <Column field="value" header="Value" sortable>
              <template #body="slotProps">
                <span class="value-badge">{{ slotProps.data.value }}</span>
              </template>
            </Column>
          </DataTable>
        </template>
      </Card>

      <!-- Info Section -->
      <div class="tech-section">
        <h3>Technologies Used</h3>
        <div class="tech-grid">
          <Card class="tech-card">
            <template #content>
              <i class="pi pi-code tech-icon"></i>
              <h4>Vue 3</h4>
              <p>Progressive JavaScript Framework</p>
            </template>
          </Card>
          <Card class="tech-card">
            <template #content>
              <i class="pi pi-palette tech-icon"></i>
              <h4>PrimeVue</h4>
              <p>Rich UI Component Library</p>
            </template>
          </Card>
          <Card class="tech-card">
            <template #content>
              <i class="pi pi-server tech-icon"></i>
              <h4>FastAPI</h4>
              <p>Modern Python Web Framework</p>
            </template>
          </Card>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  width: 100%;
  min-height: 100%;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--gainwell-dark);
  margin: 0;
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
}

.status-card,
.data-card {
  width: 100%;
}

.tech-section {
  width: 100%;
}

h3 {
  margin-bottom: 1rem;
  color: var(--primary-color);
  font-size: 1.25rem;
  font-weight: 600;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  padding: 0.5rem 1rem;
  background-color: var(--surface-50);
  border-radius: 6px;
}

.data-table {
  margin-top: 1rem;
  width: 100%;
}

.value-badge {
  background-color: var(--primary-color);
  color: var(--gainwell-dark);
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-weight: 600;
}

.spinner {
  margin: 2rem auto;
  display: block;
}

.tech-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-top: 1rem;
  width: 100%;
}

.tech-card {
  text-align: center;
  transition: transform 0.2s;
}

.tech-card:hover {
  transform: translateY(-5px);
}

.tech-icon {
  font-size: 3rem;
  color: var(--primary-color);
  margin-bottom: 0.5rem;
}

.tech-card h4 {
  margin: 0.5rem 0;
  color: var(--gainwell-dark);
}

.tech-card p {
  font-size: 0.9rem;
  color: var(--text-color-secondary);
  margin: 0;
}
</style>
