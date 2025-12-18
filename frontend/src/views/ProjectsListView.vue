<template>
  <div class="projects-list-view">
    <div class="view-header">
      <h1>Mapping Projects</h1>
      <p class="subtitle">Manage target-first mapping projects</p>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <IconField iconPosition="left">
          <InputIcon class="pi pi-search" />
          <InputText 
            v-model="searchQuery" 
            placeholder="Search projects..." 
            class="search-input"
          />
        </IconField>
      </div>
      <div class="toolbar-right">
        <Button 
          label="Refresh" 
          icon="pi pi-refresh" 
          severity="secondary"
          @click="handleRefresh"
          :loading="loading"
        />
        <Button 
          label="New Project" 
          icon="pi pi-plus" 
          @click="showCreateDialog = true"
        />
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && projects.length === 0" class="loading-container">
      <ProgressSpinner />
      <p>Loading projects...</p>
    </div>

    <!-- Error State -->
    <Message v-if="error" severity="error" :closable="true">
      {{ error }}
    </Message>

    <!-- Projects Grid -->
    <div v-if="!loading || projects.length > 0" class="projects-grid">
      <div 
        v-for="project in filteredProjects" 
        :key="project.project_id"
        class="project-card"
        @click="navigateToProject(project.project_id)"
      >
        <div class="project-header">
          <div class="project-title">
            <h3>{{ project.project_name }}</h3>
            <Tag 
              :value="project.project_status" 
              :severity="getStatusSeverity(project.project_status)"
            />
          </div>
          <div class="project-actions" @click.stop>
            <Button 
              icon="pi pi-ellipsis-v" 
              text 
              rounded
              @click="toggleMenu($event, project)"
            />
          </div>
        </div>

        <p class="project-description" v-if="project.project_description">
          {{ project.project_description }}
        </p>

        <div class="project-stats">
          <div class="stat-row">
            <div class="stat">
              <span class="stat-value">{{ project.total_target_tables }}</span>
              <span class="stat-label">Tables</span>
            </div>
            <div class="stat">
              <span class="stat-value">{{ project.tables_complete }}</span>
              <span class="stat-label">Complete</span>
            </div>
            <div class="stat">
              <span class="stat-value">{{ project.tables_in_progress }}</span>
              <span class="stat-label">In Progress</span>
            </div>
          </div>
        </div>

        <div class="project-progress">
          <div class="progress-header">
            <span>Column Mapping Progress</span>
            <span class="progress-value">
              {{ project.columns_mapped }} / {{ project.total_target_columns }}
              ({{ getProgressPercent(project) }}%)
            </span>
          </div>
          <ProgressBar 
            :value="getProgressPercent(project)" 
            :showValue="false"
            class="progress-bar"
          />
        </div>

        <div class="project-footer">
          <span v-if="project.target_domains" class="domain-tag">
            <i class="pi pi-tag"></i>
            {{ project.target_domains }}
          </span>
          <span v-if="project.source_system" class="source-tag">
            <i class="pi pi-database"></i>
            {{ project.source_system }}
          </span>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="filteredProjects.length === 0 && !loading" class="empty-card">
        <i class="pi pi-folder-open" style="font-size: 3rem; color: var(--text-color-secondary);"></i>
        <h3>No Projects Yet</h3>
        <p>Create a new project to get started with target-first mapping.</p>
        <Button label="Create First Project" icon="pi pi-plus" @click="showCreateDialog = true" />
      </div>
    </div>

    <!-- Context Menu -->
    <Menu ref="menu" :model="menuItems" :popup="true" />

    <!-- Create Project Dialog -->
    <Dialog 
      v-model:visible="showCreateDialog" 
      modal 
      header="Create New Project" 
      :style="{ width: '500px' }"
    >
      <div class="create-form">
        <div class="field">
          <label for="projectName">Project Name *</label>
          <InputText 
            id="projectName"
            v-model="newProject.project_name" 
            class="w-full"
            placeholder="e.g., Q1 2024 Member Migration"
          />
        </div>

        <div class="field">
          <label for="projectDescription">Description</label>
          <Textarea 
            id="projectDescription"
            v-model="newProject.project_description" 
            :rows="3"
            class="w-full"
            placeholder="Describe the purpose of this project..."
          />
        </div>

        <div class="field">
          <label for="sourceSystem">Source System</label>
          <InputText 
            id="sourceSystem"
            v-model="newProject.source_system" 
            class="w-full"
            placeholder="e.g., Legacy DW, DMES, Claims System"
          />
        </div>

        <div class="field">
          <label for="targetDomains">Target Domains</label>
          <InputText 
            id="targetDomains"
            v-model="newProject.target_domains" 
            class="w-full"
            placeholder="e.g., Member or Member|Claims"
          />
          <small class="field-hint">
            Pipe-separated list of domains to include. Leave blank for all.
          </small>
        </div>
      </div>

      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="showCreateDialog = false" 
          severity="secondary"
        />
        <Button 
          label="Create Project" 
          icon="pi pi-check" 
          @click="handleCreateProject"
          :loading="creating"
          :disabled="!newProject.project_name"
        />
      </template>
    </Dialog>

    <!-- Delete Confirmation -->
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useProjectsStore, type MappingProject } from '@/stores/projectsStore'
import { useUserStore } from '@/stores/user'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import ProgressBar from 'primevue/progressbar'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Dialog from 'primevue/dialog'
import ConfirmDialog from 'primevue/confirmdialog'
import Menu from 'primevue/menu'

const router = useRouter()
const confirm = useConfirm()
const toast = useToast()
const projectsStore = useProjectsStore()
const userStore = useUserStore()

// State
const searchQuery = ref('')
const showCreateDialog = ref(false)
const creating = ref(false)
const menu = ref()
const selectedProject = ref<MappingProject | null>(null)

const newProject = ref({
  project_name: '',
  project_description: '',
  source_system: '',
  target_domains: ''
})

// Computed
const projects = computed(() => projectsStore.projects)
const loading = computed(() => projectsStore.loading)
const error = computed(() => projectsStore.error)

const filteredProjects = computed(() => {
  if (!searchQuery.value) return projects.value
  
  const query = searchQuery.value.toLowerCase()
  return projects.value.filter(p => 
    p.project_name.toLowerCase().includes(query) ||
    (p.project_description && p.project_description.toLowerCase().includes(query)) ||
    (p.source_system && p.source_system.toLowerCase().includes(query)) ||
    (p.target_domains && p.target_domains.toLowerCase().includes(query))
  )
})

const menuItems = computed(() => [
  {
    label: 'Open Project',
    icon: 'pi pi-folder-open',
    command: () => {
      if (selectedProject.value) {
        navigateToProject(selectedProject.value.project_id)
      }
    }
  },
  {
    label: 'Edit',
    icon: 'pi pi-pencil',
    command: () => {
      toast.add({ severity: 'info', summary: 'Coming Soon', detail: 'Edit functionality', life: 2000 })
    }
  },
  {
    separator: true
  },
  {
    label: 'Archive',
    icon: 'pi pi-inbox',
    command: () => handleArchive()
  },
  {
    label: 'Delete',
    icon: 'pi pi-trash',
    class: 'text-danger',
    command: () => handleDelete()
  }
])

// Lifecycle
onMounted(async () => {
  await projectsStore.fetchProjects()
})

// Methods
function handleRefresh() {
  projectsStore.fetchProjects()
}

function navigateToProject(projectId: number) {
  router.push({ name: 'project-detail', params: { id: projectId } })
}

function toggleMenu(event: Event, project: MappingProject) {
  selectedProject.value = project
  menu.value.toggle(event)
}

async function handleCreateProject() {
  if (!newProject.value.project_name) {
    toast.add({ 
      severity: 'warn', 
      summary: 'Validation Error', 
      detail: 'Project name is required',
      life: 3000 
    })
    return
  }

  creating.value = true
  try {
    const result = await projectsStore.createProject({
      project_name: newProject.value.project_name,
      project_description: newProject.value.project_description || undefined,
      source_system: newProject.value.source_system || undefined,
      target_domains: newProject.value.target_domains || undefined,
      created_by: userStore.userEmail || 'unknown'
    })

    toast.add({ 
      severity: 'success', 
      summary: 'Project Created', 
      detail: `${newProject.value.project_name} created successfully`,
      life: 3000 
    })

    showCreateDialog.value = false
    resetNewProject()

    // Navigate to the new project
    if (result?.project_id) {
      router.push({ name: 'project-detail', params: { id: result.project_id } })
    }
  } catch (e: any) {
    toast.add({ 
      severity: 'error', 
      summary: 'Error', 
      detail: e.message || 'Failed to create project',
      life: 5000 
    })
  } finally {
    creating.value = false
  }
}

function resetNewProject() {
  newProject.value = {
    project_name: '',
    project_description: '',
    source_system: '',
    target_domains: ''
  }
}

function handleArchive() {
  if (!selectedProject.value) return

  confirm.require({
    message: `Archive project "${selectedProject.value.project_name}"?`,
    header: 'Archive Project',
    icon: 'pi pi-inbox',
    accept: async () => {
      try {
        await projectsStore.updateProject(selectedProject.value!.project_id, {
          project_status: 'ARCHIVED'
        })
        toast.add({ severity: 'success', summary: 'Archived', detail: 'Project archived', life: 3000 })
      } catch (e: any) {
        toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
      }
    }
  })
}

function handleDelete() {
  if (!selectedProject.value) return

  confirm.require({
    message: `Delete project "${selectedProject.value.project_name}"? This cannot be undone.`,
    header: 'Delete Project',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await projectsStore.deleteProject(selectedProject.value!.project_id)
        toast.add({ severity: 'success', summary: 'Deleted', detail: 'Project deleted', life: 3000 })
      } catch (e: any) {
        toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
      }
    }
  })
}

function getStatusSeverity(status: string): 'success' | 'info' | 'warning' | 'danger' | 'secondary' {
  switch (status) {
    case 'COMPLETE': return 'success'
    case 'ACTIVE': return 'info'
    case 'PAUSED': return 'warning'
    case 'DRAFT': return 'secondary'
    case 'ARCHIVED': return 'secondary'
    default: return 'secondary'
  }
}

function getProgressPercent(project: MappingProject): number {
  if (!project.total_target_columns) return 0
  return Math.round((project.columns_mapped / project.total_target_columns) * 100)
}
</script>

<style scoped>
.projects-list-view {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.view-header {
  margin-bottom: 2rem;
}

.view-header h1 {
  margin: 0 0 0.5rem 0;
  color: var(--gainwell-dark);
}

.subtitle {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 1rem;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.toolbar-left {
  flex: 1;
  min-width: 250px;
}

.toolbar-right {
  display: flex;
  gap: 0.5rem;
}

.search-input {
  width: 100%;
  max-width: 350px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  gap: 1rem;
}

/* Projects Grid */
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.project-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--surface-border);
  cursor: pointer;
  transition: all 0.2s ease;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  border-color: var(--gainwell-secondary);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.project-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.project-title h3 {
  margin: 0;
  color: var(--text-color);
  font-size: 1.1rem;
}

.project-description {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
  margin: 0 0 1rem 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.project-stats {
  margin-bottom: 1rem;
}

.stat-row {
  display: flex;
  gap: 1.5rem;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--gainwell-primary);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.project-progress {
  margin-bottom: 1rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.progress-value {
  color: var(--text-color-secondary);
}

.progress-bar {
  height: 6px;
}

.project-footer {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.domain-tag,
.source-tag {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  background: var(--surface-100);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.domain-tag i,
.source-tag i {
  font-size: 0.75rem;
}

/* Empty State */
.empty-card {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  gap: 1rem;
  text-align: center;
  background: white;
  border-radius: 12px;
  border: 2px dashed var(--surface-border);
}

.empty-card h3 {
  margin: 0;
  color: var(--text-color);
}

.empty-card p {
  margin: 0;
  color: var(--text-color-secondary);
}

/* Create Form */
.create-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
  color: var(--text-color);
}

.field-hint {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

.w-full {
  width: 100%;
}

/* Responsive */
@media (max-width: 768px) {
  .projects-list-view {
    padding: 1rem;
  }

  .projects-grid {
    grid-template-columns: 1fr;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left,
  .toolbar-right {
    width: 100%;
  }

  .search-input {
    max-width: none;
  }
}
</style>

