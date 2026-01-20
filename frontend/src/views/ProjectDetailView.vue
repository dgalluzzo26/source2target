<template>
  <div class="project-detail-view">
    <!-- Header -->
    <div class="view-header">
      <div class="header-left">
        <Button 
          icon="pi pi-arrow-left" 
          text 
          rounded 
          @click="router.push({ name: 'projects' })"
          v-tooltip.right="'Back to Projects'"
        />
        <div class="header-info">
          <h1>{{ project?.project_name || 'Loading...' }}</h1>
          <p class="subtitle" v-if="project?.project_description">
            {{ project.project_description }}
          </p>
        </div>
        <Tag 
          v-if="project" 
          :value="project.project_status" 
          :severity="getStatusSeverity(project.project_status)"
        />
      </div>
      <div class="header-right">
        <Button 
          label="Manage Sources" 
          icon="pi pi-list" 
          severity="secondary"
          text
          @click="showManageSourcesDialog = true"
          :disabled="!project?.source_columns_count"
          v-tooltip.bottom="'View, edit, or delete source fields'"
        />
        <Button 
          label="Upload Sources" 
          icon="pi pi-upload" 
          severity="secondary"
          outlined
          @click="showUploadDialog = true"
        />
        <Button 
          label="Export" 
          icon="pi pi-download" 
          severity="success"
          outlined
          @click="showExportDialog = true"
          :disabled="!project?.columns_mapped"
          v-tooltip.bottom="'Export mappings as CSV or SQL'"
        />
        <Button 
          label="Initialize Tables" 
          icon="pi pi-database" 
          severity="info"
          @click="handleInitializeTables"
          :disabled="!project"
        />
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="stats-row" v-if="project">
      <!-- Source Stats -->
      <div class="stat-card source">
        <div class="stat-icon source-tables">
          <i class="pi pi-upload"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ project.source_tables_count || 0 }}</span>
          <span class="stat-label">Source Tables</span>
        </div>
      </div>
      <div class="stat-card source">
        <div class="stat-icon source-columns">
          <i class="pi pi-bars"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ project.source_columns_count || 0 }}</span>
          <span class="stat-label">Source Columns</span>
        </div>
      </div>
      <!-- Target Stats -->
      <div class="stat-card">
        <div class="stat-icon tables">
          <i class="pi pi-table"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ project.total_target_tables }}</span>
          <span class="stat-label">Target Tables</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon complete">
          <i class="pi pi-check-circle"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ project.tables_complete }}</span>
          <span class="stat-label">Tables Complete</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon progress">
          <i class="pi pi-spinner"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ project.tables_in_progress }}</span>
          <span class="stat-label">In Progress</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon columns">
          <i class="pi pi-list"></i>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ project.columns_mapped }} / {{ project.total_target_columns }}</span>
          <span class="stat-label">Columns Mapped</span>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && targetTables.length === 0" class="loading-container">
      <ProgressSpinner />
      <p>Loading target tables...</p>
    </div>

    <!-- Error State -->
    <Message v-if="error" severity="error" :closable="true">
      {{ error }}
    </Message>

    <!-- Target Tables List -->
    <div class="tables-section" v-if="!loading || targetTables.length > 0">
      <div class="section-header">
        <h2>Target Tables</h2>
        <div class="section-actions">
          <IconField iconPosition="left">
            <InputIcon class="pi pi-search" />
            <InputText 
              v-model="tableSearch" 
              placeholder="Search tables..." 
              class="table-search"
            />
          </IconField>
        </div>
      </div>

      <DataTable 
        :value="filteredTables" 
        :paginator="true"
        :rows="15"
        :rowsPerPageOptions="[10, 15, 25, 50]"
        stripedRows
        class="tables-table"
        :rowClass="getRowClass"
      >
        <Column header="Table" :sortable="true" style="min-width: 14rem">
          <template #body="{ data }">
            <div class="table-name-cell">
              <i class="pi pi-table table-icon"></i>
              <div class="table-info">
                <strong>{{ data.tgt_table_name }}</strong>
                <span class="physical-name">{{ data.tgt_table_physical_name }}</span>
              </div>
            </div>
          </template>
        </Column>

        <Column header="Status" :sortable="true" style="min-width: 10rem">
          <template #body="{ data }">
            <Tag 
              :value="formatStatusWithProgress(data)" 
              :severity="getTableStatusSeverity(data.mapping_status)"
              :icon="getTableStatusIcon(data.mapping_status)"
            />
          </template>
        </Column>

        <Column header="Progress" style="min-width: 12rem">
          <template #body="{ data }">
            <div class="progress-cell">
              <ProgressBar 
                :value="getTableProgress(data)" 
                :showValue="false"
                class="table-progress-bar"
              />
              <span class="progress-text">
                {{ getColumnsProcessed(data) }} / {{ data.total_columns }}
                ({{ getTableProgress(data) }}%)
                <span v-if="data.mapping_status === 'DISCOVERING'" class="discovering-label">discovering...</span>
              </span>
            </div>
          </template>
        </Column>

        <Column header="Pending" :sortable="true" style="min-width: 6rem">
          <template #body="{ data }">
            <Badge 
              :value="data.columns_pending_review" 
              :severity="data.columns_pending_review > 0 ? 'warning' : 'secondary'"
            />
          </template>
        </Column>

        <Column header="Confidence" style="min-width: 8rem">
          <template #body="{ data }">
            <div v-if="data.avg_confidence" class="confidence-cell">
              <ProgressBar 
                :value="data.avg_confidence * 100" 
                :showValue="false"
                :class="getConfidenceClass(data.avg_confidence)"
                style="width: 60px; height: 6px;"
              />
              <span>{{ (data.avg_confidence * 100).toFixed(0) }}%</span>
            </div>
            <span v-else class="no-data">-</span>
          </template>
        </Column>

        <Column :exportable="false" style="min-width: 14rem">
          <template #body="{ data }">
            <div class="action-buttons">
              <Button 
                v-if="data.mapping_status === 'NOT_STARTED' && startingDiscoveryTableId !== data.target_table_status_id"
                icon="pi pi-play" 
                label="Discover"
                size="small"
                @click="handleStartDiscovery(data)"
                v-tooltip.top="'Start AI Discovery'"
              />
              <Button 
                v-else-if="data.mapping_status === 'DISCOVERING' || startingDiscoveryTableId === data.target_table_status_id"
                icon="pi pi-spinner pi-spin" 
                label="Discovering..."
                size="small"
                severity="secondary"
                disabled
              />
              <Button 
                v-else
                icon="pi pi-eye" 
                label="Review"
                size="small"
                severity="info"
                @click="handleReviewTable(data)"
              />
              <Button 
                icon="pi pi-ellipsis-v" 
                text 
                rounded 
                size="small"
                @click="toggleTableMenu($event, data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>

      <!-- Empty State -->
      <div v-if="targetTables.length === 0 && !loading" class="empty-state">
        <i class="pi pi-table" style="font-size: 4rem; color: var(--text-color-secondary);"></i>
        <h3>No Target Tables Yet</h3>
        <p>Upload source fields and initialize target tables to get started.</p>
        <div class="empty-actions">
          <Button label="Upload Sources" icon="pi pi-upload" @click="showUploadDialog = true" />
          <Button label="Initialize Tables" icon="pi pi-database" severity="info" @click="handleInitializeTables" />
        </div>
      </div>
    </div>

    <!-- Table Context Menu -->
    <Menu ref="tableMenu" :model="tableMenuItems" :popup="true" />

    <!-- Upload Dialog -->
    <Dialog 
      v-model:visible="showUploadDialog" 
      modal 
      header="Upload Source Fields" 
      :style="{ width: '600px' }"
      :closable="!uploading"
    >
      <!-- Show upload form when not uploading -->
      <div v-if="!uploading" class="upload-content">
        <Message severity="info" :closable="false">
          <strong>Important:</strong> The <code>src_comments</code> field is essential for AI matching. 
          Without descriptions, the AI cannot find the best source columns for your target fields.
        </Message>
        
        <p class="mt-3">Download the template, fill in your source fields, and upload the CSV file.</p>
        
        <div class="template-section">
          <Button 
            label="Download Template" 
            icon="pi pi-download" 
            outlined
            severity="secondary"
            @click="handleDownloadTemplate"
            v-tooltip.top="'Download CSV template with required format'"
          />
        </div>
        
        <h4>Required CSV Columns:</h4>
        <ul class="field-list">
          <li><code>src_table_name</code> - Logical source table name</li>
          <li><code>src_table_physical_name</code> - Physical table name in database</li>
          <li><code>src_column_name</code> - Logical source column name</li>
          <li><code>src_column_physical_name</code> - Physical column name in database</li>
          <li><code>src_physical_datatype</code> - Data type (STRING, INT, DATE, etc.)</li>
          <li><code>src_nullable</code> - Whether column is nullable (YES/NO)</li>
          <li><code>src_comments</code> - <strong>Column description (critical for AI matching)</strong></li>
          <li><code>domain</code> - Domain category (optional, e.g., member, provider)</li>
        </ul>
        
        <FileUpload
          mode="basic"
          accept=".csv"
          :maxFileSize="10000000"
          @select="handleFileSelect"
          chooseLabel="Select CSV File"
          class="w-full mt-3"
        />
        
        <div v-if="selectedFile" class="selected-file">
          <i class="pi pi-file"></i>
          <span>{{ selectedFile.name }}</span>
        </div>
      </div>

      <!-- Show progress when uploading -->
      <div v-else class="upload-progress">
        <div class="progress-icon">
          <i class="pi pi-spin pi-spinner" style="font-size: 3rem; color: var(--primary-color);"></i>
        </div>
        <h3>Uploading Source Fields...</h3>
        <p class="progress-message">
          Processing <strong>{{ selectedFile?.name }}</strong>
        </p>
        <ProgressBar mode="indeterminate" style="height: 6px; margin-top: 1rem;" />
        <p class="progress-hint">
          This may take a minute for larger files. Each field is being indexed for AI matching.
        </p>
      </div>

      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="showUploadDialog = false" 
          severity="secondary"
          :disabled="uploading"
        />
        <Button 
          label="Upload" 
          icon="pi pi-upload" 
          @click="handleUpload"
          :loading="uploading"
          :disabled="!selectedFile || uploading"
        />
      </template>
    </Dialog>

    <!-- Review Suggestions Dialog -->
    <Dialog 
      v-model:visible="showReviewDialog" 
      modal 
      :header="`Review: ${reviewingTable?.tgt_table_name || ''}`" 
      :style="{ width: '95vw', maxWidth: '1400px' }"
      maximizable
    >
      <SuggestionReviewPanel
        v-if="reviewingTable"
        :project-id="projectId"
        :table-id="reviewingTable.target_table_status_id"
        :table-name="reviewingTable.tgt_table_name"
        @suggestion-updated="handleSuggestionUpdated"
        @manual-mapping="handleManualMapping"
      />
    </Dialog>

    <!-- Manage Source Fields Dialog -->
    <Dialog 
      v-model:visible="showManageSourcesDialog" 
      modal 
      header="Manage Source Fields" 
      :style="{ width: '90vw', maxWidth: '1200px' }"
      maximizable
    >
      <div class="manage-sources-content">
        <!-- Toolbar -->
        <div class="sources-toolbar">
          <IconField iconPosition="left">
            <InputIcon class="pi pi-search" />
            <InputText v-model="sourceFieldSearch" placeholder="Search fields..." />
          </IconField>
          
          <div class="toolbar-actions">
            <Dropdown
              v-model="sourceTableFilter"
              :options="sourceTableOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Filter by table"
              showClear
              style="width: 200px"
            />
            <Button 
              label="AI Enhance Descriptions" 
              icon="pi pi-sparkles" 
              severity="info"
              outlined
              @click="startAIEnhance"
              :disabled="!selectedSourceFields.length && !filteredSourceFields.length"
              :loading="enhancingDescriptions"
              v-tooltip.top="selectedSourceFields.length ? `Enhance ${selectedSourceFields.length} selected` : 'Enhance all visible'"
            />
            <Button 
              label="Delete All" 
              icon="pi pi-trash" 
              severity="danger"
              outlined
              @click="confirmDeleteAllSources"
              :disabled="!filteredSourceFields.length"
            />
          </div>
        </div>

        <!-- Loading -->
        <div v-if="loadingSourceFields" class="loading-sources">
          <ProgressSpinner style="width: 50px; height: 50px" />
          <span>Loading source fields...</span>
        </div>

        <!-- Source Fields Table -->
        <DataTable 
          v-else
          :value="filteredSourceFields" 
          :paginator="true" 
          :rows="15"
          :rowsPerPageOptions="[15, 30, 50, 100]"
          dataKey="unmapped_field_id"
          :globalFilterFields="['src_table_name', 'src_column_name', 'src_comments']"
          v-model:selection="selectedSourceFields"
          selectionMode="multiple"
          responsiveLayout="scroll"
          class="sources-table"
          stripedRows
          :sortOrder="-1"
          sortField="src_table_name"
        >
          <template #empty>
            <div class="empty-sources">
              <i class="pi pi-inbox"></i>
              <span>No source fields found</span>
            </div>
          </template>

          <Column selectionMode="multiple" headerStyle="width: 3rem" />
          
          <Column field="src_table_name" header="Table" sortable style="min-width: 150px">
            <template #body="{ data }">
              <span class="table-name">{{ data.src_table_name }}</span>
            </template>
          </Column>
          
          <Column field="src_column_name" header="Column" sortable style="min-width: 150px">
            <template #body="{ data }">
              <code class="column-name">{{ data.src_column_physical_name }}</code>
              <div class="column-logical" v-if="data.src_column_name !== data.src_column_physical_name">
                {{ data.src_column_name }}
              </div>
            </template>
          </Column>
          
          <Column field="src_physical_datatype" header="Type" sortable style="width: 100px">
            <template #body="{ data }">
              <Tag :value="data.src_physical_datatype || 'STRING'" severity="info" />
            </template>
          </Column>
          
          <Column field="src_comments" header="Description" style="min-width: 250px">
            <template #body="{ data }">
              <div class="description-cell">
                {{ data.src_comments || '-' }}
              </div>
            </template>
            <template #editor="{ data }">
              <InputText v-model="data.src_comments" class="w-full" />
            </template>
          </Column>
          
          <Column field="mapping_status" header="Status" sortable style="width: 120px">
            <template #body="{ data }">
              <Tag 
                :value="data.mapping_status" 
                :severity="data.mapping_status === 'MAPPED' ? 'success' : data.mapping_status === 'PENDING' ? 'warning' : 'secondary'"
              />
            </template>
          </Column>
          
          <Column header="Actions" style="width: 100px">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button 
                  icon="pi pi-pencil" 
                  text 
                  rounded 
                  size="small"
                  @click="editSourceField(data)"
                  v-tooltip.top="'Edit'"
                />
                <Button 
                  icon="pi pi-trash" 
                  text 
                  rounded 
                  severity="danger" 
                  size="small"
                  @click="confirmDeleteSourceField(data)"
                  v-tooltip.top="'Delete'"
                />
              </div>
            </template>
          </Column>
        </DataTable>

        <!-- Bulk Actions -->
        <div v-if="selectedSourceFields.length" class="bulk-actions">
          <span>{{ selectedSourceFields.length }} field(s) selected</span>
          <Button 
            label="Delete Selected" 
            icon="pi pi-trash" 
            severity="danger"
            size="small"
            @click="confirmDeleteSelectedSources"
          />
        </div>
      </div>

      <template #footer>
        <Button label="Close" icon="pi pi-times" @click="showManageSourcesDialog = false" />
      </template>
    </Dialog>

    <!-- Edit Source Field Dialog -->
    <Dialog 
      v-model:visible="showEditSourceDialog" 
      modal 
      header="Edit Source Field" 
      :style="{ width: '500px' }"
    >
      <div v-if="editingSourceField" class="edit-source-form">
        <div class="form-field">
          <label>Table Name</label>
          <InputText v-model="editingSourceField.src_table_name" class="w-full" />
        </div>
        <div class="form-field">
          <label>Column Name</label>
          <InputText v-model="editingSourceField.src_column_name" class="w-full" />
        </div>
        <div class="form-field">
          <label>Physical Column Name</label>
          <InputText v-model="editingSourceField.src_column_physical_name" class="w-full" />
        </div>
        <div class="form-field">
          <label>Data Type</label>
          <InputText v-model="editingSourceField.src_physical_datatype" class="w-full" />
        </div>
        <div class="form-field">
          <label>Description</label>
          <Textarea v-model="editingSourceField.src_comments" rows="3" class="w-full" />
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" icon="pi pi-times" @click="showEditSourceDialog = false" severity="secondary" />
        <Button label="Save" icon="pi pi-check" @click="saveSourceField" :loading="savingSourceField" />
      </template>
    </Dialog>

    <!-- AI Enhance Descriptions Dialog -->
    <Dialog 
      v-model:visible="showEnhanceDialog" 
      modal 
      header="AI Enhanced Descriptions" 
      :style="{ width: '90vw', maxWidth: '1200px' }"
      maximizable
      :closable="!enhancingDescriptions"
    >
      <div class="enhance-dialog-content">
        <!-- Progress -->
        <div v-if="enhancingDescriptions" class="enhance-progress">
          <ProgressBar :value="enhanceProgress" :showValue="true" />
          <span class="progress-label">Enhancing descriptions... {{ enhancedCount }}/{{ totalToEnhance }}</span>
        </div>

        <!-- Review Table -->
        <DataTable 
          v-else-if="enhancedFields.length > 0"
          :value="enhancedFields" 
          :paginator="true" 
          :rows="10"
          dataKey="unmapped_field_id"
          responsiveLayout="scroll"
          class="enhance-table"
          stripedRows
        >
          <Column field="src_table_name" header="Table" style="width: 120px">
            <template #body="{ data }">
              <span class="table-name">{{ data.src_table_name }}</span>
            </template>
          </Column>
          
          <Column field="src_column_physical_name" header="Column" style="width: 150px">
            <template #body="{ data }">
              <code class="column-name">{{ data.src_column_physical_name }}</code>
            </template>
          </Column>
          
          <Column header="Original Description" style="width: 250px">
            <template #body="{ data }">
              <div class="original-desc">{{ data.original_comments || '-' }}</div>
            </template>
          </Column>
          
          <Column header="Enhanced Description" style="min-width: 300px">
            <template #body="{ data }">
              <Textarea 
                v-model="data.enhanced_comments" 
                rows="2" 
                class="w-full enhanced-textarea"
                :class="{ 'changed': data.enhanced_comments !== data.original_comments }"
              />
            </template>
          </Column>

          <Column header="Status" style="width: 80px">
            <template #body="{ data }">
              <Tag 
                v-if="data.enhanced_comments !== data.original_comments" 
                value="Changed" 
                severity="success" 
              />
              <Tag v-else value="Same" severity="secondary" />
            </template>
          </Column>
        </DataTable>

        <!-- Summary -->
        <div v-if="!enhancingDescriptions && enhancedFields.length > 0" class="enhance-summary">
          <i class="pi pi-info-circle"></i>
          <span>{{ changedDescriptionsCount }} of {{ enhancedFields.length }} descriptions were enhanced. Review and edit as needed before saving.</span>
        </div>
      </div>

      <template #footer>
        <div class="enhance-footer">
          <Button 
            label="Cancel" 
            icon="pi pi-times" 
            @click="cancelEnhance" 
            severity="secondary" 
            :disabled="enhancingDescriptions"
          />
          <Button 
            label="Save All Changes" 
            icon="pi pi-check" 
            @click="saveEnhancedDescriptions" 
            severity="success"
            :loading="savingEnhanced"
            :disabled="enhancingDescriptions || changedDescriptionsCount === 0"
          />
        </div>
      </template>
    </Dialog>

    <!-- Export Dialog -->
    <Dialog 
      v-model:visible="showExportDialog" 
      modal 
      header="Export Mappings" 
      :style="{ width: '600px' }"
    >
      <div class="export-content">
        <Message v-if="!exportableTables.length" severity="info">
          No mapped tables available for export. Complete some mappings first.
        </Message>
        
        <div v-else>
          <div class="form-field">
            <label>Select Table</label>
            <Dropdown
              v-model="exportSelectedTable"
              :options="exportTableOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Select a table to export"
              class="w-full"
            />
          </div>
          
          <div class="form-field mt-3">
            <label>Export Format</label>
            <div class="export-format-options">
              <div 
                class="format-option" 
                :class="{ selected: exportFormat === 'csv' }"
                @click="exportFormat = 'csv'"
              >
                <i class="pi pi-file"></i>
                <div>
                  <strong>CSV</strong>
                  <small>Download mapping details as spreadsheet</small>
                </div>
              </div>
              <div 
                class="format-option" 
                :class="{ selected: exportFormat === 'sql' }"
                @click="exportFormat = 'sql'"
              >
                <i class="pi pi-code"></i>
                <div>
                  <strong>SQL</strong>
                  <small>Generate Databricks INSERT statement</small>
                </div>
              </div>
            </div>
          </div>
          
          <div v-if="exportFormat === 'sql'" class="form-field mt-3">
            <label>Target Catalog</label>
            <InputText v-model="exportTargetCatalog" class="w-full" placeholder="${TARGET_CATALOG}" />
          </div>
          
          <div v-if="exportFormat === 'sql'" class="form-field mt-2">
            <label>Target Schema</label>
            <InputText v-model="exportTargetSchema" class="w-full" placeholder="${TARGET_SCHEMA}" />
          </div>
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" icon="pi pi-times" @click="showExportDialog = false" severity="secondary" />
        <Button 
          label="Export" 
          icon="pi pi-download" 
          @click="handleExport"
          :disabled="!exportSelectedTable"
          :loading="exporting"
        />
      </template>
    </Dialog>

    <!-- ConfirmDialog is global in App.vue -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useProjectsStore, type TargetTableStatus } from '@/stores/projectsStore'
import { useUserStore } from '@/stores/user'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import ProgressBar from 'primevue/progressbar'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Menu from 'primevue/menu'
import FileUpload from 'primevue/fileupload'
import Dropdown from 'primevue/dropdown'
import Textarea from 'primevue/textarea'
// ConfirmDialog is global in App.vue
import { useConfirm } from 'primevue/useconfirm'
import SuggestionReviewPanel from '@/components/SuggestionReviewPanel.vue'
import { getAuthHeaders } from '@/services/api'

const router = useRouter()
const route = useRoute()
const toast = useToast()
const projectsStore = useProjectsStore()
const userStore = useUserStore()

// Props
const projectId = computed(() => Number(route.params.id))

// State
const tableSearch = ref('')
const showUploadDialog = ref(false)
const showReviewDialog = ref(false)
const showManageSourcesDialog = ref(false)
const showEditSourceDialog = ref(false)
const showExportDialog = ref(false)
const uploading = ref(false)
const exporting = ref(false)

// Export state
const exportableTables = ref<any[]>([])
const exportSelectedTable = ref<string | null>(null)
const exportFormat = ref<'csv' | 'sql'>('csv')
const exportTargetCatalog = ref('${TARGET_CATALOG}')
const exportTargetSchema = ref('${TARGET_SCHEMA}')
const selectedFile = ref<File | null>(null)
const tableMenu = ref()
const selectedTable = ref<TargetTableStatus | null>(null)
const reviewingTable = ref<TargetTableStatus | null>(null)

// Source field management
const sourceFields = ref<any[]>([])
const loadingSourceFields = ref(false)
const sourceFieldSearch = ref('')
const sourceTableFilter = ref<string | null>(null)
const selectedSourceFields = ref<any[]>([])
const editingSourceField = ref<any>(null)
const savingSourceField = ref(false)
const startingDiscoveryTableId = ref<number | null>(null)  // Track which table is starting discovery
const confirm = useConfirm()

// AI Enhance Descriptions state
const showEnhanceDialog = ref(false)
const enhancingDescriptions = ref(false)
const enhancedFields = ref<any[]>([])
const enhancedCount = ref(0)
const totalToEnhance = ref(0)
const savingEnhanced = ref(false)

// Computed
const project = computed(() => projectsStore.currentProject)
const targetTables = computed(() => projectsStore.targetTables)
const loading = computed(() => projectsStore.loading)
const error = computed(() => projectsStore.error)

const filteredTables = computed(() => {
  if (!tableSearch.value) return targetTables.value
  
  const query = tableSearch.value.toLowerCase()
  return targetTables.value.filter(t => 
    t.tgt_table_name.toLowerCase().includes(query) ||
    t.tgt_table_physical_name.toLowerCase().includes(query)
  )
})

const tableMenuItems = computed(() => [
  {
    label: 'Start Discovery',
    icon: 'pi pi-play',
    command: () => {
      if (selectedTable.value) handleStartDiscovery(selectedTable.value)
    },
    disabled: selectedTable.value?.mapping_status !== 'NOT_STARTED'
  },
  {
    label: 'Review Suggestions',
    icon: 'pi pi-eye',
    command: () => {
      if (selectedTable.value) handleReviewTable(selectedTable.value)
    }
  },
  {
    separator: true
  },
  {
    label: 'Rerun All Fields',
    icon: 'pi pi-refresh',
    command: () => {
      console.log('[Menu] Rerun All Fields clicked, selectedTable:', selectedTable.value)
      if (selectedTable.value) {
        handleRerunDiscovery(selectedTable.value)
      } else {
        console.error('[Menu] selectedTable is null!')
      }
    }
  },
  {
    label: 'Skip Table',
    icon: 'pi pi-forward',
    command: () => {
      toast.add({ severity: 'info', summary: 'Coming Soon', detail: 'Skip table feature', life: 2000 })
    }
  }
])

// Source field management computed
const sourceTableOptions = computed(() => {
  const tables = new Set(sourceFields.value.map(f => f.src_table_physical_name || f.src_table_name))
  return [
    { label: 'All Tables', value: null },
    ...Array.from(tables).map(t => ({ label: t, value: t }))
  ]
})

const filteredSourceFields = computed(() => {
  let result = sourceFields.value
  
  // Filter by table
  if (sourceTableFilter.value) {
    result = result.filter(f => 
      (f.src_table_physical_name || f.src_table_name) === sourceTableFilter.value
    )
  }
  
  // Filter by search
  if (sourceFieldSearch.value) {
    const query = sourceFieldSearch.value.toLowerCase()
    result = result.filter(f =>
      (f.src_table_name || '').toLowerCase().includes(query) ||
      (f.src_column_name || '').toLowerCase().includes(query) ||
      (f.src_column_physical_name || '').toLowerCase().includes(query) ||
      (f.src_comments || '').toLowerCase().includes(query)
    )
  }
  
  return result
})

const exportTableOptions = computed(() => {
  return [
    { label: 'All Tables', value: 'ALL' },
    ...exportableTables.value.map(t => ({
      label: `${t.tgt_table_name} (${t.column_count} columns)`,
      value: t.tgt_table_physical_name
    }))
  ]
})

// Lifecycle
onMounted(async () => {
  await loadData()
})

watch(() => route.params.id, () => {
  loadData()
})

// Methods
async function loadData() {
  await projectsStore.fetchProject(projectId.value)
  await projectsStore.fetchTargetTables(projectId.value)
}

function handleFileSelect(event: any) {
  selectedFile.value = event.files[0]
}

async function handleUpload() {
  if (!selectedFile.value) return
  
  uploading.value = true
  try {
    const result = await projectsStore.uploadSourceFields(projectId.value, selectedFile.value)
    
    toast.add({ 
      severity: 'success', 
      summary: 'Upload Complete', 
      detail: `Uploaded ${result.fields_uploaded} fields from ${result.tables_found?.length || 0} tables`,
      life: 5000 
    })
    
    showUploadDialog.value = false
    selectedFile.value = null
  } catch (e: any) {
    toast.add({ 
      severity: 'error', 
      summary: 'Upload Failed', 
      detail: e.message,
      life: 5000 
    })
  } finally {
    uploading.value = false
  }
}

function handleDownloadTemplate() {
  // Create CSV template for source fields - matches the original unmapped fields format
  const headers = [
    'src_table_name',
    'src_table_physical_name',
    'src_column_name',
    'src_column_physical_name',
    'src_physical_datatype',
    'src_nullable',
    'src_comments',
    'domain'
  ]
  
  const exampleRows = [
    [
      'T_MEMBER',
      't_member',
      'MEMBER_ID',
      'member_id',
      'STRING',
      'NO',
      'Unique member identifier assigned by the state',
      'member'
    ],
    [
      'T_MEMBER',
      't_member',
      'FIRST_NAME',
      'first_name',
      'STRING',
      'YES',
      'Member first name',
      'member'
    ],
    [
      'T_ADDRESS',
      't_address',
      'ADDR_LINE_1',
      'addr_line_1',
      'STRING',
      'YES',
      'Primary address street line 1',
      'member'
    ]
  ]
  
  const csvContent = [
    headers.join(','),
    ...exampleRows.map(row => row.map(cell => 
      // Escape cells containing commas or quotes
      cell.includes(',') || cell.includes('"') ? `"${cell.replace(/"/g, '""')}"` : cell
    ).join(','))
  ].join('\n')
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'source_fields_template.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  
  toast.add({
    severity: 'success',
    summary: 'Template Downloaded',
    detail: 'Fill in the template with your source fields and upload',
    life: 3000
  })
}

async function handleInitializeTables() {
  try {
    const result = await projectsStore.initializeTargetTables(
      projectId.value, 
      project.value?.target_domains || undefined
    )
    
    toast.add({ 
      severity: 'success', 
      summary: 'Tables Initialized', 
      detail: `Initialized ${result.tables_initialized} target tables`,
      life: 3000 
    })
    
    await loadData()
  } catch (e: any) {
    toast.add({ 
      severity: 'error', 
      summary: 'Initialization Failed', 
      detail: e.message,
      life: 5000 
    })
  }
}

async function handleStartDiscovery(table: TargetTableStatus) {
  // Immediately show loading state
  startingDiscoveryTableId.value = table.target_table_status_id
  
  try {
    await projectsStore.startDiscovery(
      projectId.value,
      table.target_table_status_id,
      userStore.userEmail || 'unknown'
    )
    
    toast.add({ 
      severity: 'info', 
      summary: 'Discovery Started', 
      detail: `AI is discovering mappings for ${table.tgt_table_name}`,
      life: 3000 
    })
    
    // Poll for completion
    pollForDiscovery(table.target_table_status_id)
  } catch (e: any) {
    // Clear loading state on error
    startingDiscoveryTableId.value = null
    
    toast.add({ 
      severity: 'error', 
      summary: 'Discovery Failed', 
      detail: e.message,
      life: 5000 
    })
  }
}

async function handleRerunDiscovery(table: TargetTableStatus) {
  console.log('[Rerun Discovery] Called with table:', table)
  console.log('[Rerun Discovery] Table status:', table?.mapping_status)
  
  if (!table) {
    console.error('[Rerun Discovery] No table provided!')
    toast.add({ 
      severity: 'error', 
      summary: 'Error', 
      detail: 'No table selected',
      life: 3000 
    })
    return
  }
  
  // Skip confirmation and just run - for debugging
  console.log('[Rerun Discovery] Starting discovery without confirmation (debugging)...')
  
  // TODO: Restore confirmation dialog after debugging
  // const confirmed = window.confirm(`...`)
  // if (!confirmed) return
  
  // Use the same discovery flow - backend already clears existing suggestions
  startingDiscoveryTableId.value = table.target_table_status_id
  
  try {
    console.log('[Rerun Discovery] Calling startDiscovery...')
    await projectsStore.startDiscovery(
      projectId.value,
      table.target_table_status_id,
      userStore.userEmail || 'unknown'
    )
    
    console.log('[Rerun Discovery] startDiscovery completed, starting poll...')
    
    toast.add({ 
      severity: 'info', 
      summary: 'Rerun Started', 
      detail: `AI is regenerating all mappings for ${table.tgt_table_name}`,
      life: 3000 
    })
    
    // Poll for completion
    pollForDiscovery(table.target_table_status_id)
  } catch (e: any) {
    console.error('[Rerun Discovery] Error:', e)
    startingDiscoveryTableId.value = null
    
    toast.add({ 
      severity: 'error', 
      summary: 'Rerun Failed', 
      detail: e.message,
      life: 5000 
    })
  }
}

async function pollForDiscovery(tableId: number) {
  // Clear the starting state - now we're in polling mode
  startingDiscoveryTableId.value = null
  
  // Poll every 3 seconds for up to 10 minutes
  const maxAttempts = 200
  let attempts = 0
  
  const poll = async () => {
    attempts++
    
    try {
      await projectsStore.fetchTargetTables(projectId.value)
      
      // Small delay to let Vue reactivity process the update
      await new Promise(resolve => setTimeout(resolve, 100))
      
      const table = targetTables.value.find(t => t.target_table_status_id === tableId)
      
      if (!table || table.mapping_status !== 'DISCOVERING') {
        // Discovery complete or table removed
        if (table?.mapping_status === 'SUGGESTIONS_READY') {
          toast.add({ 
            severity: 'success', 
            summary: 'Discovery Complete', 
            detail: `${table.tgt_table_name} has ${table.columns_pending_review} suggestions ready for review`,
            life: 5000 
          })
        } else if (table?.mapping_status === 'NOT_STARTED') {
          // Discovery may have errored out
          toast.add({ 
            severity: 'warn', 
            summary: 'Discovery Stopped', 
            detail: `Discovery for ${table.tgt_table_name} was stopped. Check logs for details.`,
            life: 5000 
          })
        }
        return // Stop polling
      }
      
      if (attempts >= maxAttempts) {
        toast.add({ 
          severity: 'warn', 
          summary: 'Discovery Timeout', 
          detail: 'Discovery is taking longer than expected. Please refresh the page.',
          life: 5000 
        })
        return // Stop polling
      }
      
      // Continue polling
      setTimeout(poll, 3000)
    } catch (e) {
      console.error('Poll error:', e)
      setTimeout(poll, 5000) // Retry with longer delay on error
    }
  }
  
  // Start polling
  setTimeout(poll, 3000)
}

function handleReviewTable(table: TargetTableStatus) {
  reviewingTable.value = table
  showReviewDialog.value = true
}

async function handleSuggestionUpdated() {
  // Refresh table data when suggestion is updated
  await projectsStore.fetchTargetTables(projectId.value)
  await projectsStore.fetchProject(projectId.value)
}

function handleManualMapping(suggestion: any) {
  // Show a dialog for manual mapping
  toast.add({
    severity: 'info',
    summary: 'Manual Mapping',
    detail: `Manual mapping for ${suggestion.tgt_column_name} - Feature coming soon. You can edit the SQL directly using the Edit button.`,
    life: 5000
  })
  
  // TODO: Implement full manual mapping dialog that:
  // 1. Shows list of available source fields
  // 2. Lets user pick source columns
  // 3. Generates SQL expression
  // 4. Saves as a new suggestion or directly as a mapping
}

function toggleTableMenu(event: Event, table: TargetTableStatus) {
  console.log('[toggleTableMenu] Called with table:', table?.tgt_table_name)
  selectedTable.value = table
  console.log('[toggleTableMenu] selectedTable set, toggling menu...')
  tableMenu.value.toggle(event)
  console.log('[toggleTableMenu] Menu toggled')
}

function getStatusSeverity(status: string): 'success' | 'info' | 'warning' | 'danger' | 'secondary' {
  switch (status) {
    case 'COMPLETE': return 'success'
    case 'ACTIVE': return 'info'
    case 'PAUSED': return 'warning'
    case 'DRAFT': return 'secondary'
    default: return 'secondary'
  }
}

function getTableStatusSeverity(status: string): 'success' | 'info' | 'warning' | 'danger' | 'secondary' {
  switch (status) {
    case 'COMPLETE': return 'success'
    case 'SUGGESTIONS_READY': return 'info'
    case 'IN_REVIEW': return 'info'
    case 'DISCOVERING': return 'warning'
    case 'NOT_STARTED': return 'secondary'
    case 'SKIPPED': return 'secondary'
    default: return 'secondary'
  }
}

function getTableStatusIcon(status: string): string {
  switch (status) {
    case 'COMPLETE': return 'pi pi-check-circle'
    case 'SUGGESTIONS_READY': return 'pi pi-inbox'
    case 'IN_REVIEW': return 'pi pi-eye'
    case 'DISCOVERING': return 'pi pi-spinner pi-spin'
    case 'NOT_STARTED': return 'pi pi-circle'
    case 'SKIPPED': return 'pi pi-forward'
    default: return ''
  }
}

function formatStatus(status: string): string {
  return status.replace(/_/g, ' ')
}

function formatStatusWithProgress(table: TargetTableStatus): string {
  if (table.mapping_status === 'DISCOVERING') {
    const progress = getDiscoveryProgress(table)
    return `DISCOVERING ${progress}`
  }
  return table.mapping_status.replace(/_/g, ' ')
}

function getTableProgress(table: TargetTableStatus): number {
  if (!table.total_columns) return 0
  return Math.round((table.columns_mapped / table.total_columns) * 100)
}

function getColumnsProcessed(table: TargetTableStatus): number {
  // Total columns that have been processed (mapped + pending review + no match)
  return (table.columns_mapped || 0) + 
         (table.columns_pending_review || 0) + 
         (table.columns_no_match || 0)
}

function getDiscoveryProgress(table: TargetTableStatus): string {
  if (table.mapping_status !== 'DISCOVERING') return ''
  const columnsProcessed = (table.columns_mapped || 0) + 
                           (table.columns_pending_review || 0) + 
                           (table.columns_no_match || 0)
  return `${columnsProcessed}/${table.total_columns || 0}`
}

function getConfidenceClass(confidence: number): string {
  if (confidence >= 0.8) return 'confidence-high'
  if (confidence >= 0.6) return 'confidence-medium'
  return 'confidence-low'
}

function getRowClass(data: TargetTableStatus): string {
  if (data.mapping_status === 'COMPLETE') return 'complete-row'
  if (data.mapping_status === 'SKIPPED') return 'skipped-row'
  return ''
}

// =========================================================================
// SOURCE FIELD MANAGEMENT
// =========================================================================

// Watch for dialog open to load source fields
watch(showManageSourcesDialog, async (visible) => {
  if (visible) {
    await loadSourceFields()
  }
})

// Watch for export dialog to load exportable tables
watch(showExportDialog, async (visible) => {
  if (visible) {
    await loadExportableTables()
  }
})

async function loadSourceFields() {
  loadingSourceFields.value = true
  try {
    const response = await fetch(`/api/v4/projects/${projectId.value}/source-fields`, {
      headers: getAuthHeaders()
    })
    if (response.ok) {
      sourceFields.value = await response.json()
    } else {
      throw new Error('Failed to load source fields')
    }
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 3000 })
  } finally {
    loadingSourceFields.value = false
  }
}

function editSourceField(field: any) {
  editingSourceField.value = { ...field }
  showEditSourceDialog.value = true
}

async function saveSourceField() {
  if (!editingSourceField.value) return
  
  savingSourceField.value = true
  try {
    const response = await fetch(
      `/api/v4/projects/${projectId.value}/source-fields/${editingSourceField.value.unmapped_field_id}`,
      {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          src_table_name: editingSourceField.value.src_table_name,
          src_column_name: editingSourceField.value.src_column_name,
          src_column_physical_name: editingSourceField.value.src_column_physical_name,
          src_physical_datatype: editingSourceField.value.src_physical_datatype,
          src_comments: editingSourceField.value.src_comments
        })
      }
    )
    
    if (response.ok) {
      toast.add({ severity: 'success', summary: 'Saved', detail: 'Source field updated', life: 2000 })
      showEditSourceDialog.value = false
      await loadSourceFields()
      // Refresh project to update counts
      await projectsStore.fetchProject(projectId.value)
    } else {
      throw new Error('Failed to save')
    }
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 3000 })
  } finally {
    savingSourceField.value = false
  }
}

// Computed for enhance dialog
const enhanceProgress = computed(() => {
  if (totalToEnhance.value === 0) return 0
  return Math.round((enhancedCount.value / totalToEnhance.value) * 100)
})

const changedDescriptionsCount = computed(() => {
  return enhancedFields.value.filter(f => f.enhanced_comments !== f.original_comments).length
})

// AI Enhance Description Functions
async function startAIEnhance() {
  // Use selected fields if any, otherwise all visible
  const fieldsToEnhance = selectedSourceFields.value.length > 0 
    ? selectedSourceFields.value 
    : filteredSourceFields.value
  
  if (fieldsToEnhance.length === 0) {
    toast.add({ severity: 'warn', summary: 'No fields', detail: 'No source fields to enhance', life: 3000 })
    return
  }
  
  // Initialize state
  enhancedFields.value = fieldsToEnhance.map(f => ({
    ...f,
    original_comments: f.src_comments || '',
    enhanced_comments: f.src_comments || ''
  }))
  totalToEnhance.value = fieldsToEnhance.length
  enhancedCount.value = 0
  enhancingDescriptions.value = true
  showEnhanceDialog.value = true
  
  // Process in batches of 10 for parallel processing
  const batchSize = 10
  for (let i = 0; i < enhancedFields.value.length; i += batchSize) {
    const batch = enhancedFields.value.slice(i, i + batchSize)
    
    // Process batch in parallel
    await Promise.all(batch.map(async (field) => {
      try {
        const response = await fetch('/api/v4/ai/enhance-description', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            table_name: field.src_table_name,
            column_name: field.src_column_physical_name,
            current_description: field.original_comments,
            data_type: field.src_physical_datatype
          })
        })
        
        if (response.ok) {
          const result = await response.json()
          field.enhanced_comments = result.enhanced_description || field.original_comments
        }
      } catch (e) {
        console.error('Enhancement failed for', field.src_column_physical_name, e)
      }
      enhancedCount.value++
    }))
  }
  
  enhancingDescriptions.value = false
  toast.add({ 
    severity: 'success', 
    summary: 'Enhancement Complete', 
    detail: `Enhanced ${changedDescriptionsCount.value} descriptions`, 
    life: 3000 
  })
}

function cancelEnhance() {
  showEnhanceDialog.value = false
  enhancedFields.value = []
  enhancedCount.value = 0
  totalToEnhance.value = 0
}

async function saveEnhancedDescriptions() {
  const changedFields = enhancedFields.value.filter(f => f.enhanced_comments !== f.original_comments)
  
  if (changedFields.length === 0) {
    toast.add({ severity: 'info', summary: 'No changes', detail: 'No descriptions were changed', life: 2000 })
    return
  }
  
  savingEnhanced.value = true
  let successCount = 0
  let errorCount = 0
  
  // Save in parallel batches
  const batchSize = 10
  for (let i = 0; i < changedFields.length; i += batchSize) {
    const batch = changedFields.slice(i, i + batchSize)
    
    await Promise.all(batch.map(async (field) => {
      try {
        const response = await fetch(
          `/api/v4/projects/${projectId.value}/source-fields/${field.unmapped_field_id}`,
          {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({
              src_table_name: field.src_table_name,
              src_column_name: field.src_column_name,
              src_column_physical_name: field.src_column_physical_name,
              src_physical_datatype: field.src_physical_datatype,
              src_comments: field.enhanced_comments
            })
          }
        )
        
        if (response.ok) {
          successCount++
        } else {
          errorCount++
        }
      } catch (e) {
        errorCount++
      }
    }))
  }
  
  savingEnhanced.value = false
  
  if (successCount > 0) {
    toast.add({ 
      severity: 'success', 
      summary: 'Saved', 
      detail: `Updated ${successCount} descriptions${errorCount > 0 ? `, ${errorCount} failed` : ''}`, 
      life: 3000 
    })
    showEnhanceDialog.value = false
    await loadSourceFields()
    await projectsStore.fetchProject(projectId.value)
  } else {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to save changes', life: 3000 })
  }
}

function confirmDeleteSourceField(field: any) {
  confirm.require({
    message: `Delete field "${field.src_column_name}" from table "${field.src_table_name}"?`,
    header: 'Confirm Delete',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => deleteSourceField(field.unmapped_field_id)
  })
}

async function deleteSourceField(fieldId: number) {
  try {
    const response = await fetch(
      `/api/v4/projects/${projectId.value}/source-fields/${fieldId}`,
      { method: 'DELETE', headers: getAuthHeaders() }
    )
    
    if (response.ok) {
      toast.add({ severity: 'success', summary: 'Deleted', detail: 'Source field removed', life: 2000 })
      await loadSourceFields()
      await projectsStore.fetchProject(projectId.value)
    } else {
      throw new Error('Failed to delete')
    }
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 3000 })
  }
}

function confirmDeleteSelectedSources() {
  confirm.require({
    message: `Delete ${selectedSourceFields.value.length} selected field(s)?`,
    header: 'Confirm Delete',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => deleteSelectedSources()
  })
}

async function deleteSelectedSources() {
  for (const field of selectedSourceFields.value) {
    await deleteSourceField(field.unmapped_field_id)
  }
  selectedSourceFields.value = []
}

function confirmDeleteAllSources() {
  const tableName = sourceTableFilter.value
  const message = tableName 
    ? `Delete all fields from table "${tableName}"?`
    : `Delete ALL ${sourceFields.value.length} source fields?`
  
  confirm.require({
    message,
    header: 'Confirm Delete All',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => deleteAllSources()
  })
}

async function deleteAllSources() {
  try {
    const url = sourceTableFilter.value
      ? `/api/v4/projects/${projectId.value}/source-fields?table_name=${encodeURIComponent(sourceTableFilter.value)}`
      : `/api/v4/projects/${projectId.value}/source-fields`
    
    const response = await fetch(url, { method: 'DELETE', headers: getAuthHeaders() })
    
    if (response.ok) {
      const result = await response.json()
      toast.add({ 
        severity: 'success', 
        summary: 'Deleted', 
        detail: `Removed ${result.deleted_count} fields`, 
        life: 3000 
      })
      await loadSourceFields()
      await projectsStore.fetchProject(projectId.value)
    } else {
      throw new Error('Failed to delete')
    }
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 3000 })
  }
}

// =========================================================================
// EXPORT FUNCTIONS
// =========================================================================

async function loadExportableTables() {
  try {
    const response = await fetch(`/api/v4/projects/${projectId.value}/export/tables`, {
      headers: getAuthHeaders()
    })
    if (response.ok) {
      const data = await response.json()
      exportableTables.value = data.tables || []
      // Default to first table if available
      if (exportableTables.value.length > 0) {
        exportSelectedTable.value = exportableTables.value[0].tgt_table_physical_name
      }
    } else {
      console.error('Error loading exportable tables:', response.status, await response.text())
    }
  } catch (e: any) {
    console.error('Error loading exportable tables:', e)
  }
}

async function handleExport() {
  if (!exportSelectedTable.value) return
  
  exporting.value = true
  try {
    let url: string
    let filename: string
    
    if (exportFormat.value === 'csv') {
      url = `/api/v4/projects/${projectId.value}/export/csv`
      if (exportSelectedTable.value !== 'ALL') {
        url += `?table_name=${encodeURIComponent(exportSelectedTable.value)}`
      }
      filename = `mappings_${projectId.value}${exportSelectedTable.value !== 'ALL' ? '_' + exportSelectedTable.value : ''}.csv`
    } else {
      // SQL export requires specific table
      if (exportSelectedTable.value === 'ALL') {
        toast.add({ severity: 'warn', summary: 'Select Table', detail: 'Please select a specific table for SQL export', life: 3000 })
        exporting.value = false
        return
      }
      url = `/api/v4/projects/${projectId.value}/export/sql?table_name=${encodeURIComponent(exportSelectedTable.value)}`
      url += `&target_catalog=${encodeURIComponent(exportTargetCatalog.value)}`
      url += `&target_schema=${encodeURIComponent(exportTargetSchema.value)}`
      filename = `${exportSelectedTable.value}_insert.sql`
    }
    
    const response = await fetch(url, {
      headers: getAuthHeaders()
    })
    
    if (response.ok) {
      const content = await response.text()
      
      // Download file
      const blob = new Blob([content], { type: exportFormat.value === 'csv' ? 'text/csv' : 'text/plain' })
      const downloadUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(downloadUrl)
      
      toast.add({ 
        severity: 'success', 
        summary: 'Exported', 
        detail: `Downloaded ${filename}`, 
        life: 3000 
      })
      
      showExportDialog.value = false
    } else {
      throw new Error('Export failed')
    }
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 3000 })
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
.project-detail-view {
  padding: 1.5rem;
  max-width: 1600px;
  margin: 0 auto;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-info h1 {
  margin: 0;
  color: var(--gainwell-dark);
  font-size: 1.5rem;
}

.subtitle {
  margin: 0.25rem 0 0 0;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.header-right {
  display: flex;
  gap: 0.5rem;
}

/* Stats Row */
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
  border: 1px solid var(--surface-border);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
}

.stat-icon.source-tables {
  background: #fce4ec;
  color: #c2185b;
}

.stat-icon.source-columns {
  background: #f3e5f5;
  color: #8e24aa;
}

.stat-icon.tables {
  background: #e3f2fd;
  color: #1976d2;
}

.stat-icon.complete {
  background: #e8f5e9;
  color: #388e3c;
}

.stat-icon.progress {
  background: #fff3e0;
  color: #f57c00;
}

.stat-icon.columns {
  background: #e0f7fa;
  color: #00838f;
}

.stat-card.source {
  border-left: 3px solid #c2185b;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-color);
}

.stat-label {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  gap: 1rem;
}

/* Tables Section */
.tables-section {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h2 {
  margin: 0;
  color: var(--text-color);
  font-size: 1.25rem;
}

.table-search {
  width: 250px;
}

/* Table cells */
.table-name-cell {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.table-icon {
  color: var(--gainwell-secondary);
  font-size: 1.25rem;
}

.table-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.physical-name {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  font-family: monospace;
}

.progress-cell {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.table-progress-bar {
  height: 6px;
}

.progress-text {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.confidence-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.no-data {
  color: var(--text-color-secondary);
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  gap: 1rem;
  text-align: center;
}

.empty-state h3 {
  margin: 0;
  color: var(--text-color);
}

.empty-state p {
  margin: 0;
  color: var(--text-color-secondary);
}

.empty-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

/* Upload Dialog */
.upload-content {
  line-height: 1.6;
}

.upload-content h4 {
  margin: 1rem 0 0.5rem 0;
  color: var(--text-color);
  font-size: 0.95rem;
}

.upload-content .field-list {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.upload-content .field-list li {
  margin-bottom: 0.35rem;
}

.upload-content code {
  background: var(--surface-100);
  padding: 0.15rem 0.35rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-family: 'SF Mono', 'Consolas', monospace;
}

.template-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 1rem 0;
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 8px;
  border: 1px dashed var(--surface-300);
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.75rem;
  background: var(--surface-100);
  border-radius: 6px;
}

.upload-progress {
  text-align: center;
  padding: 2rem 1rem;
}

.upload-progress .progress-icon {
  margin-bottom: 1.5rem;
}

.upload-progress h3 {
  margin: 0 0 0.5rem 0;
  color: var(--primary-color);
  font-size: 1.25rem;
}

.upload-progress .progress-message {
  margin: 0;
  color: var(--text-color);
  font-size: 1rem;
}

.upload-progress .progress-hint {
  margin: 1.5rem 0 0 0;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  font-style: italic;
}

.w-full {
  width: 100%;
}

/* Row classes */
:deep(.complete-row) {
  background: #f1f8e9 !important;
}

:deep(.skipped-row) {
  opacity: 0.6;
}

/* Confidence colors */
:deep(.confidence-high) .p-progressbar-value {
  background: #4caf50 !important;
}

:deep(.confidence-medium) .p-progressbar-value {
  background: #ff9800 !important;
}

:deep(.confidence-low) .p-progressbar-value {
  background: #f44336 !important;
}

/* Source Field Management */
.manage-sources-content {
  min-height: 400px;
}

.sources-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.toolbar-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.loading-sources {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  gap: 1rem;
  color: var(--text-color-secondary);
}

.empty-sources {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.empty-sources i {
  font-size: 2rem;
}

.sources-table .table-name {
  font-weight: 600;
  color: var(--gainwell-dark);
}

.sources-table .column-name {
  font-size: 0.85rem;
  padding: 0.15rem 0.4rem;
  background: var(--surface-200);
  border-radius: 3px;
}

.sources-table .column-logical {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  margin-top: 0.25rem;
}

.sources-table .description-cell {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sources-table .action-buttons {
  display: flex;
  gap: 0.25rem;
}

.bulk-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: var(--surface-100);
  border-radius: 6px;
  margin-top: 1rem;
}

.bulk-actions span {
  font-weight: 600;
  color: var(--gainwell-primary);
}

.edit-source-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.edit-source-form .form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.edit-source-form label {
  font-weight: 600;
  color: var(--text-color);
}

/* Export Dialog */
.export-content .form-field {
  margin-bottom: 1rem;
}

.export-content .form-field label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.export-format-options {
  display: flex;
  gap: 1rem;
}

.format-option {
  flex: 1;
  padding: 1rem;
  border: 2px solid var(--surface-300);
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  transition: all 0.2s;
}

.format-option:hover {
  border-color: var(--gainwell-primary);
  background: var(--surface-50);
}

.format-option.selected {
  border-color: var(--gainwell-primary);
  background: var(--gainwell-primary-light, rgba(0, 120, 212, 0.1));
}

.format-option i {
  font-size: 1.5rem;
  color: var(--gainwell-primary);
}

.format-option strong {
  display: block;
  color: var(--text-color);
}

.format-option small {
  display: block;
  color: var(--text-color-secondary);
  font-size: 0.8rem;
}

/* AI Enhance Dialog */
.enhance-dialog-content {
  min-height: 300px;
}

.enhance-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
}

.enhance-progress .p-progressbar {
  width: 100%;
  max-width: 400px;
}

.progress-label {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.enhance-table .table-name {
  font-weight: 500;
  color: var(--primary-color);
}

.enhance-table .column-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  background: var(--surface-100);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
}

.original-desc {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  background: var(--surface-50);
  padding: 0.5rem;
  border-radius: 4px;
  max-height: 60px;
  overflow-y: auto;
}

.enhanced-textarea {
  font-size: 0.85rem;
  transition: border-color 0.2s;
}

.enhanced-textarea.changed {
  border-color: var(--green-500);
  background: #f1f8e9;
}

.enhance-summary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--blue-50);
  color: var(--blue-700);
  border-radius: 6px;
  margin-top: 1rem;
  font-size: 0.9rem;
}

.enhance-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

/* Responsive */
@media (max-width: 768px) {
  .project-detail-view {
    padding: 1rem;
  }
  
  .view-header {
    flex-direction: column;
  }
  
  .header-right {
    width: 100%;
  }
  
  .stats-row {
    grid-template-columns: 1fr 1fr;
  }
  
  .section-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .table-search {
    width: 100%;
  }
  
  .sources-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

