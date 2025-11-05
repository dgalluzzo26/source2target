<template>
  <div class="introduction-view" style="width: 100% !important; max-width: none !important;">
    <!-- Hero Section -->
    <div class="hero-section" style="width: 100% !important; max-width: none !important;">
      <div class="hero-content" style="width: 100% !important; max-width: none !important;">
        <h1 class="hero-title">
          <i class="pi pi-sitemap hero-icon"></i>
          Source-to-Target Mapping Platform
        </h1>
        <p class="hero-description">
          Streamline your data mapping process with AI-powered field suggestions, 
          comprehensive data discovery, and intelligent automation tools.
        </p>
      </div>
    </div>

    <!-- System Status Section -->
    <Card class="status-card">
      <template #title>
        <div class="card-title">
          <i class="pi pi-heart-fill"></i>
          System Status
        </div>
      </template>
      <template #content>
        <div class="status-grid">
          <div class="status-item">
            <div class="status-metric">
              <Tag 
                :value="systemStatus.database.status" 
                :severity="systemStatus.database.status === 'Connected' ? 'success' : (systemStatus.database.status === 'Warning' ? 'warning' : 'danger')"
                :icon="systemStatus.database.status === 'Connected' ? 'pi pi-check' : (systemStatus.database.status === 'Warning' ? 'pi pi-exclamation-triangle' : 'pi pi-times')"
              />
              <span class="status-label">Database Connection</span>
            </div>
            <small class="status-message">{{ systemStatus.database.message }}</small>
          </div>

          <div class="status-item">
            <div class="status-metric">
              <Tag 
                :value="systemStatus.vectorSearch.status" 
                :severity="systemStatus.vectorSearch.status === 'Available' ? 'success' : 'warning'"
                :icon="systemStatus.vectorSearch.status === 'Available' ? 'pi pi-check' : 'pi pi-exclamation-triangle'"
              />
              <span class="status-label">Vector Search</span>
            </div>
            <small class="status-message">{{ systemStatus.vectorSearch.message }}</small>
          </div>

          <div class="status-item">
            <div class="status-metric">
              <Tag 
                :value="systemStatus.aiModel.status" 
                :severity="systemStatus.aiModel.status === 'Ready' ? 'success' : 'warning'"
                :icon="systemStatus.aiModel.status === 'Ready' ? 'pi pi-check' : 'pi pi-exclamation-triangle'"
              />
              <span class="status-label">AI Model</span>
            </div>
            <small class="status-message">{{ systemStatus.aiModel.message }}</small>
          </div>

          <div class="status-item">
            <div class="status-metric">
              <Tag 
                :value="systemStatus.configuration.status" 
                :severity="systemStatus.configuration.status === 'Valid' ? 'success' : 'danger'"
                :icon="systemStatus.configuration.status === 'Valid' ? 'pi pi-check' : 'pi pi-times'"
              />
              <span class="status-label">Configuration</span>
            </div>
            <small class="status-message">{{ systemStatus.configuration.message }}</small>
          </div>
        </div>
      </template>
    </Card>

    <!-- Quick Actions -->
    <div class="actions-grid">
      <Card class="action-card" @click="navigateTo('/mapping')">
        <template #content>
          <div class="action-content">
            <i class="pi pi-sitemap action-icon"></i>
            <h3>Field Mapping</h3>
            <p>Map source fields to target schema with AI assistance</p>
            <Button label="Start Mapping" icon="pi pi-arrow-right" />
          </div>
        </template>
      </Card>

      <Card v-if="userStore.isAdmin" class="action-card" @click="navigateTo('/config')">
        <template #content>
          <div class="action-content">
            <i class="pi pi-cog action-icon"></i>
            <h3>Configuration</h3>
            <p>Manage database connections and AI model settings</p>
            <Button label="Configure" icon="pi pi-arrow-right" />
          </div>
        </template>
      </Card>

      <Card class="action-card" v-if="userStore.isAdmin" @click="navigateTo('/admin')">
        <template #content>
          <div class="action-content">
            <i class="pi pi-shield action-icon"></i>
            <h3>Administration</h3>
            <p>User management and system administration</p>
            <Button label="Manage" icon="pi pi-arrow-right" />
          </div>
        </template>
      </Card>
    </div>

    <!-- Getting Started -->
    <Card class="getting-started-card">
      <template #title>
        <div class="card-title">
          <i class="pi pi-info-circle"></i>
          Getting Started
        </div>
      </template>
      <template #content>
        <div class="getting-started-content">
          <div class="step">
            <div class="step-number">1</div>
            <div class="step-content">
              <h4>Configure Connections</h4>
              <p>Set up your database connections and AI model endpoints in the Configuration section.</p>
            </div>
          </div>
          
          <div class="step">
            <div class="step-number">2</div>
            <div class="step-content">
              <h4>Discover Data</h4>
              <p>Browse and analyze your source tables and columns in the Field Mapping section.</p>
            </div>
          </div>
          
          <div class="step">
            <div class="step-number">3</div>
            <div class="step-content">
              <h4>Map Fields</h4>
              <p>Use AI-powered suggestions or manual search to map fields to your target schema.</p>
            </div>
          </div>
          
          <div class="step">
            <div class="step-number">4</div>
            <div class="step-content">
              <h4>Export Results</h4>
              <p>Download your completed mappings as CSV templates for further processing.</p>
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const systemStatus = ref({
  database: { status: 'Loading...', message: 'Checking database connection...' },
  vectorSearch: { status: 'Loading...', message: 'Checking vector search...' },
  aiModel: { status: 'Loading...', message: 'Checking AI model...' },
  configuration: { status: 'Loading...', message: 'Checking configuration...' }
})

const loadSystemStatus = async () => {
  try {
    const response = await fetch('/api/system/status')
    if (response.ok) {
      const data = await response.json()
      systemStatus.value = data
    } else {
      console.error('Failed to load system status')
        systemStatus.value = {
        database: { status: 'Error', message: 'Failed to check database' },
        vectorSearch: { status: 'Error', message: 'Failed to check vector search' },
        aiModel: { status: 'Error', message: 'Failed to check AI model' },
        configuration: { status: 'Error', message: 'Failed to check configuration' }
        }
    }
  } catch (error) {
    console.error('Error loading system status:', error)
    systemStatus.value = {
      database: { status: 'Error', message: 'Failed to check database' },
      vectorSearch: { status: 'Error', message: 'Failed to check vector search' },
      aiModel: { status: 'Error', message: 'Failed to check AI model' },
      configuration: { status: 'Error', message: 'Failed to check configuration' }
    }
  }
}

const navigateTo = (path: string) => {
  router.push(path)
}

// Load system status on mount
onMounted(() => {
  loadSystemStatus()
})
</script>

<style scoped>
.introduction-view {
  max-width: 100%;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.hero-section {
  text-align: center;
  padding: 3rem 0;
  background: linear-gradient(135deg, var(--p-primary-50) 0%, var(--p-primary-100) 100%);
  border-radius: var(--p-border-radius-lg);
  margin-bottom: 1rem;
}

.hero-content {
  max-width: 100%;
  margin: 0;
  padding: 0 2rem;
}

.hero-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--p-primary-color);
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

.hero-icon {
  font-size: 2.5rem;
}

.hero-description {
  font-size: 1.25rem;
  color: var(--p-text-muted-color);
  line-height: 1.6;
  margin: 0;
}

.status-card {
  width: 100%;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  font-weight: 600;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
}

.status-metric {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.status-label {
  font-weight: 600;
  color: var(--p-text-color);
}

.status-message {
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  word-wrap: break-word;
  overflow-wrap: break-word;
  line-height: 1.4;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.action-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.action-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  border-color: var(--p-primary-color);
}

.action-content {
  text-align: center;
  padding: 1rem;
}

.action-icon {
  font-size: 3rem;
  color: var(--p-primary-color);
  margin-bottom: 1rem;
}

.action-content h3 {
  margin: 0 0 0.5rem 0;
  color: var(--p-text-color);
}

.action-content p {
  margin: 0 0 1.5rem 0;
  color: var(--p-text-muted-color);
  line-height: 1.5;
}

.getting-started-card {
  width: 100%;
}

.getting-started-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.step {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.step-number {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
}

.step-content h4 {
  margin: 0 0 0.5rem 0;
  color: var(--p-text-color);
}

.step-content p {
  margin: 0;
  color: var(--p-text-muted-color);
  line-height: 1.5;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2rem;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .hero-icon {
    font-size: 2rem;
  }
  
  .hero-description {
    font-size: 1.125rem;
  }
  
  .status-grid {
    grid-template-columns: 1fr;
  }
  
  .actions-grid {
    grid-template-columns: 1fr;
  }
}
</style>

