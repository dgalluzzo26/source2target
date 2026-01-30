<template>
  <div class="suggestion-review-panel">
    <!-- Summary Bar -->
    <div class="summary-bar">
      <div class="summary-stats">
        <div class="summary-stat">
          <span class="stat-num">{{ suggestions.length }}</span>
          <span class="stat-label">Total</span>
        </div>
        <div class="summary-stat pending">
          <span class="stat-num">{{ pendingCount }}</span>
          <span class="stat-label">Pending</span>
        </div>
        <div class="summary-stat approved">
          <span class="stat-num">{{ approvedCount }}</span>
          <span class="stat-label">Approved</span>
        </div>
        <div class="summary-stat rejected">
          <span class="stat-num">{{ noMatchCount }}</span>
          <span class="stat-label">No Match</span>
        </div>
      </div>
      <div class="summary-actions">
        <Button 
          icon="pi pi-refresh"
          size="small"
          severity="secondary"
          @click="loadSuggestions"
          :loading="loading"
          v-tooltip.top="'Refresh'"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading && suggestions.length === 0" class="loading-container">
      <ProgressSpinner />
      <p>Loading suggestions...</p>
    </div>

    <!-- Suggestions List -->
    <div v-else class="suggestions-list">
      <div 
        v-for="suggestion in suggestions" 
        :key="suggestion.suggestion_id"
        class="suggestion-card"
        :class="{ 
          'approved': suggestion.suggestion_status === 'APPROVED' || suggestion.suggestion_status === 'EDITED' || suggestion.suggestion_status === 'AUTO_MAPPED',
          'system-column': suggestion.suggestion_status === 'SYSTEM_COLUMN',
          'rejected': suggestion.suggestion_status === 'REJECTED',
          'skipped': suggestion.suggestion_status === 'SKIPPED',
          'no-match': suggestion.suggestion_status === 'NO_MATCH' || suggestion.suggestion_status === 'NO_PATTERN'
        }"
      >
        <!-- Clean Header: Column name + Status + Score + View Alternatives -->
        <div class="suggestion-header-clean">
          <div class="column-info-clean">
            <i class="pi pi-arrow-circle-right"></i>
            <strong>{{ suggestion.tgt_column_physical_name }}</strong>
            <Tag v-if="suggestion.pattern_type" :value="suggestion.pattern_type" severity="secondary" size="small" />
          </div>
          <div class="header-actions">
            <Button
              v-if="getMatchedFields(suggestion).length > 0"
              label="View Alternatives"
              icon="pi pi-list"
              size="small"
              text
              severity="info"
              @click="showVSCandidates(suggestion)"
              v-tooltip.top="'See all source field candidates'"
            />
            <Tag 
              :value="formatStatus(suggestion.suggestion_status)" 
              :severity="getStatusSeverity(suggestion.suggestion_status)"
              size="small"
            />
            <div v-if="suggestion.confidence_score" class="confidence-badge" :class="getConfidenceClass(suggestion.confidence_score)">
              {{ (suggestion.confidence_score * 100).toFixed(0) }}%
            </div>
          </div>
        </div>

        <!-- Description (if different from column name) -->
        <div class="suggestion-description-clean" v-if="suggestion.tgt_comments && suggestion.tgt_comments !== suggestion.tgt_column_name">
          {{ suggestion.tgt_comments }}
        </div>

        <!-- AI Reasoning (compact) -->
        <div v-if="suggestion.ai_reasoning" class="ai-reasoning-compact">
          <i class="pi pi-lightbulb"></i>
          <span class="reasoning-text-compact">{{ suggestion.ai_reasoning }}</span>
        </div>

        <!-- Warnings (right after reasoning) -->
        <div v-if="getWarnings(suggestion).length > 0" class="warnings-compact">
          <div v-for="(warning, idx) in getWarnings(suggestion)" :key="idx" class="warning-item-compact">
            <i class="pi pi-exclamation-triangle"></i>
            <span>{{ warning }}</span>
          </div>
        </div>

        <!-- SQL Preview (compact) -->
        <div v-if="suggestion.suggested_sql" class="sql-preview-compact">
          <div class="sql-header-compact">
            <span class="sql-label">SQL:</span>
            <Button 
              icon="pi pi-copy"
              text
              size="small"
              @click="copySQL(suggestion.suggested_sql)"
              v-tooltip.top="'Copy SQL'"
            />
          </div>
          <pre class="sql-code-compact">{{ suggestion.suggested_sql }}</pre>
        </div>

        <!-- Status Messages -->
        <div v-if="suggestion.suggestion_status === 'NO_MATCH'" class="status-message warning">
          <i class="pi pi-exclamation-triangle"></i>
          <span>No matching source fields found. Manual mapping may be required.</span>
        </div>
        <div v-if="suggestion.suggestion_status === 'NO_PATTERN'" class="status-message info">
          <i class="pi pi-info-circle"></i>
          <span>No historical pattern found. This will be the first mapping.</span>
        </div>

        <!-- Actions -->
        <div class="suggestion-actions" v-if="suggestion.suggestion_status === 'PENDING'">
          <!-- Has issues: Must review/edit first, no direct approve -->
          <template v-if="hasWarningsOrIssues(suggestion)">
            <Button 
              label="Review & Edit"
              icon="pi pi-pencil"
              size="small"
              severity="warning"
              :disabled="isOperationInProgress(suggestion.suggestion_id)"
              @click="openEditDialog(suggestion)"
            />
          </template>
          <!-- Clean: Can approve directly or edit -->
          <template v-else>
          <Button 
            label="Approve"
            icon="pi pi-check"
            size="small"
            severity="success"
            :loading="approvingId === suggestion.suggestion_id"
            :disabled="isOperationInProgress(suggestion.suggestion_id)"
            @click="handleApprove(suggestion)"
          />
          <Button 
              label="Edit"
            icon="pi pi-pencil"
            size="small"
            severity="info"
            outlined
            :disabled="isOperationInProgress(suggestion.suggestion_id)"
            @click="openEditDialog(suggestion)"
          />
          </template>
          <Button 
            label="Reject"
            icon="pi pi-times"
            size="small"
            severity="danger"
            outlined
            :disabled="isOperationInProgress(suggestion.suggestion_id)"
            @click="openRejectDialog(suggestion)"
          />
          <Button 
            icon="pi pi-refresh"
            size="small"
            severity="secondary"
            text
            :loading="regeneratingId === suggestion.suggestion_id"
            :disabled="isOperationInProgress(suggestion.suggestion_id)"
            @click="handleRegenerate(suggestion)"
            v-tooltip.top="'Regenerate this suggestion'"
          />
          <Button 
            label="Skip"
            icon="pi pi-forward"
            size="small"
            severity="secondary"
            text
            :loading="skippingId === suggestion.suggestion_id"
            :disabled="isOperationInProgress(suggestion.suggestion_id)"
            @click="handleSkip(suggestion)"
          />
        </div>

        <!-- Manual Mapping Action for No Match -->
        <div class="suggestion-actions" v-if="suggestion.suggestion_status === 'NO_MATCH' || suggestion.suggestion_status === 'NO_PATTERN'">
          <Button 
            label="Regenerate"
            icon="pi pi-refresh"
            size="small"
            severity="info"
            :loading="regeneratingId === suggestion.suggestion_id"
            :disabled="isOperationInProgress(suggestion.suggestion_id)"
            @click="handleRegenerate(suggestion)"
            v-tooltip.top="'Re-run AI discovery for this column'"
          />
          <Button 
            label="Create Manual Mapping"
            icon="pi pi-plus"
            size="small"
            severity="secondary"
            outlined
            :disabled="isOperationInProgress(suggestion.suggestion_id)"
            @click="$emit('manual-mapping', suggestion)"
          />
          <Button 
            label="Skip"
            icon="pi pi-forward"
            size="small"
            severity="secondary"
            text
            :loading="skippingId === suggestion.suggestion_id"
            :disabled="isOperationInProgress(suggestion.suggestion_id)"
            @click="handleSkip(suggestion)"
          />
        </div>

        <!-- Reviewed Info -->
        <div v-if="suggestion.reviewed_by" class="reviewed-info">
          <i class="pi pi-user"></i>
          Reviewed by {{ suggestion.reviewed_by }} on {{ formatDate(suggestion.reviewed_ts) }}
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="suggestions.length === 0 && !loading" class="empty-state">
        <i class="pi pi-check-circle" style="font-size: 3rem; color: var(--green-500);"></i>
        <h3>All Caught Up!</h3>
        <p>No suggestions to review for this table.</p>
      </div>
    </div>

    <!-- Enhanced Edit Dialog -->
    <Dialog 
      v-model:visible="showEditDialog" 
      modal 
      header="Edit Mapping" 
      :style="{ width: '95vw', maxWidth: '1400px' }"
      maximizable
    >
      <div v-if="editingSuggestion" class="edit-dialog-content">
        <!-- Target Info Header -->
        <div class="edit-header">
          <div class="target-info">
            <Tag value="TARGET" severity="info" />
            <strong>{{ editingSuggestion.tgt_table_name }}.{{ editingSuggestion.tgt_column_name }}</strong>
            <span class="datatype">({{ editingSuggestion.tgt_physical_datatype || 'STRING' }})</span>
          </div>
          <div class="target-description" v-if="editingSuggestion.tgt_comments">
            {{ editingSuggestion.tgt_comments }}
          </div>
        </div>

        <!-- Three Column Layout -->
        <div class="edit-columns-v2">
          <!-- Left: Collapsible Source & Changes Panel -->
          <div class="left-panel" :class="{ 'collapsed': leftPanelCollapsed }">
            <div class="panel-toggle" @click="leftPanelCollapsed = !leftPanelCollapsed">
              <i :class="leftPanelCollapsed ? 'pi pi-chevron-right' : 'pi pi-chevron-left'"></i>
              <span v-if="!leftPanelCollapsed">Sources & Notes</span>
            </div>
            
            <div v-if="!leftPanelCollapsed" class="left-panel-content">
              <!-- AI Changes Section - Collapsible, Grouped by Table -->
              <div v-if="getChanges(editingSuggestion).length > 0 || getWarnings(editingSuggestion).length > 0" class="changes-section">
                <div class="section-header" @click="aiChangesCollapsed = !aiChangesCollapsed">
                  <i :class="aiChangesCollapsed ? 'pi pi-chevron-right' : 'pi pi-chevron-down'"></i>
                  <h4><i class="pi pi-lightbulb"></i> AI Changes</h4>
                  <Badge 
                    :value="getChanges(editingSuggestion).length + getWarnings(editingSuggestion).length" 
                    :severity="getWarnings(editingSuggestion).length > 0 ? 'warning' : 'info'"
                  />
                </div>
                <div v-if="!aiChangesCollapsed" class="change-list">
                  <!-- Table replacements first -->
                  <template v-for="(group, idx) in getChangesByTable(editingSuggestion)" :key="'tg'+idx">
                    <!-- Table header with mapping -->
                    <div class="table-change-header" :class="{ 'is-unmapped': group.isUnmapped }">
                      <i class="pi pi-database"></i>
                      <Badge :value="group.patternTable" severity="secondary" class="table-badge-original" />
                      <i class="pi pi-arrow-right"></i>
                      <Badge 
                        :value="group.sourceTable" 
                        :severity="group.isUnmapped ? 'danger' : 'success'" 
                        class="table-badge-new" 
                      />
                      <span class="alias-label">({{ group.alias }})</span>
                      <Tag v-if="group.isUnmapped" value="Unmapped" severity="warning" size="small" class="unmapped-tag" />
                    </div>
                    <!-- Column changes for this table -->
                    <div 
                      v-for="(change, cidx) in group.changes" 
                      :key="'c'+idx+'-'+cidx"
                      class="change-item grouped-change"
                      :class="{ 
                        'is-problem': isProblemChange(change),
                        'is-system': isSystemColumnChange(change)
                      }"
                      @click="highlightInSQL(change)"
                    >
                      <i :class="getChangeIcon(change)"></i>
                      <div class="change-detail">
                        <span class="change-original">{{ change.originalColumn }}</span>
                        <i class="pi pi-arrow-right"></i>
                        <span class="change-new">{{ change.newColumn }}</span>
                        <span v-if="isSystemColumnChange(change)" class="system-badge">System</span>
                      </div>
                    </div>
                  </template>
                  <!-- Warnings -->
                  <div 
                    v-for="(warning, idx) in getWarnings(editingSuggestion)" 
                    :key="'w'+idx"
                    class="change-item is-warning"
                    @click="highlightWarningField(warning)"
                  >
                    <i class="pi pi-exclamation-triangle"></i>
                    <span>{{ warning }}</span>
                  </div>
                </div>
              </div>

              <!-- Source Fields Section -->
              <div class="source-section">
                <h4><i class="pi pi-table"></i> Source Fields</h4>
                <InputText 
                  v-model="sourceFilter" 
                  placeholder="Filter..." 
                  size="small"
                  class="source-filter"
                />
                
                <div class="source-tables">
                  <div v-for="table in groupedSourceFields" :key="table.tableName" class="source-table-group">
                    <div class="table-header" @click="toggleTableExpand(table.tableName)">
                      <i :class="expandedTables.includes(table.tableName) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
                      <strong>{{ table.tableName }}</strong>
                      <Badge :value="table.columns.length" severity="secondary" />
                    </div>
                    <div v-if="expandedTables.includes(table.tableName)" class="table-columns">
                      <div 
                        v-for="col in filteredColumns(table.columns)" 
                        :key="col.unmapped_field_id"
                        class="column-item"
                        :class="{ 'matched': isMatchedColumn(col) }"
                        @click="insertColumnToSQL(col)"
                        v-tooltip.right="col.src_comments || 'Click to insert'"
                      >
                        <span class="col-name">{{ col.src_column_physical_name }}</span>
                        <span class="col-type">{{ col.src_physical_datatype || 'STRING' }}</span>
                        <i v-if="isMatchedColumn(col)" class="pi pi-check matched-icon"></i>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Right: SQL Editor (takes remaining space) -->
          <div class="sql-panel-v2">
            <!-- SQL Editor Header -->
            <div class="sql-header">
              <label><i class="pi pi-code"></i> SQL Expression</label>
              <div class="sql-actions">
                <Button 
                  label="AI Assist" 
                  icon="pi pi-bolt" 
                  size="small"
                  severity="help"
                  @click="showAIAssist = true"
                  v-tooltip.top="'Get AI help with this expression'"
                  class="ai-assist-btn"
                />
                <Button 
                  icon="pi pi-copy" 
                  size="small"
                  severity="secondary"
                  outlined
                  @click="copySQL(editedSQL)"
                  v-tooltip.top="'Copy SQL'"
                />
              </div>
            </div>

            <!-- ORIGINAL Pattern SQL with Change Highlights -->
            <div class="original-sql-section" :class="{ 'has-problems': problemFieldsInSQL.length > 0, 'collapsed': sqlPreviewCollapsed }">
              <div 
                class="original-sql-header clickable" 
                @click="sqlPreviewCollapsed = !sqlPreviewCollapsed"
              >
                <div class="header-left">
                  <i :class="sqlPreviewCollapsed ? 'pi pi-chevron-right' : 'pi pi-chevron-down'" class="toggle-icon"></i>
                  <span class="section-title">Original Pattern SQL</span>
                </div>
                <div class="change-legend">
                  <span class="legend-item success"><span class="dot"></span> Changed</span>
                  <span class="legend-item warning"><span class="dot"></span> No Match</span>
                  <span class="legend-item system"><span class="dot"></span> System Column</span>
                </div>
              </div>
              <pre v-if="!sqlPreviewCollapsed" class="sql-original-highlighted" v-html="highlightedOriginalSQL"></pre>
            </div>

            <!-- NEW SQL (Editable) -->
            <div class="new-sql-section">
              <div class="new-sql-header">
                <span class="section-title">New SQL (Editable)</span>
                <Button 
                  icon="pi pi-copy"
                  size="small"
                  severity="secondary"
                  text
                  @click="copySQL(editedSQL)"
                  v-tooltip.top="'Copy SQL'"
                />
              </div>
              <div class="sql-editor-container">
                <Textarea 
                  ref="sqlTextarea"
                  v-model="editedSQL" 
                  :rows="12"
                  class="sql-editor-v2 w-full"
                  placeholder="Enter the SQL expression..."
                  spellcheck="false"
                />
              </div>
            </div>

            <!-- Matched Source Summary (compact) -->
            <div class="matched-summary-compact" v-if="getMatchedFields(editingSuggestion).length > 0">
              <span class="matched-label"><i class="pi pi-check-circle"></i> Matched:</span>
              <div class="matched-tags">
                <Tag 
                  v-for="field in getMatchedFields(editingSuggestion).slice(0, 5)" 
                  :key="field.unmapped_field_id"
                  :value="`${field.src_column_physical_name}`"
                  severity="success"
                  size="small"
                />
                <Badge 
                  v-if="getMatchedFields(editingSuggestion).length > 5"
                  :value="`+${getMatchedFields(editingSuggestion).length - 5}`"
                  severity="secondary"
                />
              </div>
              <Button
                label="View Alternatives"
                icon="pi pi-list"
                size="small"
                text
                severity="info"
                @click="showVSCandidates(editingSuggestion)"
                v-tooltip.top="'See all source field candidates from vector search'"
                class="view-alternatives-btn"
              />
            </div>

            <!-- Edit Notes (compact) -->
            <div class="notes-row">
          <InputText 
            v-model="editNotes" 
            class="w-full"
                placeholder="Notes (optional): Explain your changes..."
          />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" icon="pi pi-times" @click="showEditDialog = false" severity="secondary" />
        <Button label="Save & Approve" icon="pi pi-check" @click="handleEditApprove" :loading="saving" severity="success" />
      </template>
    </Dialog>

    <!-- AI Assist Dialog -->
    <Dialog 
      v-model:visible="showAIAssist" 
      modal 
      header="AI SQL Assistant" 
      :style="{ width: '600px' }"
    >
      <div class="ai-assist-content">
        <p>Describe what you need help with:</p>
        <Textarea 
          v-model="aiPrompt" 
          :rows="3"
          class="w-full"
          placeholder="e.g., Join recipient_master to member table on SAK_RECIP..."
        />
      </div>
      <template #footer>
        <Button label="Cancel" @click="showAIAssist = false" severity="secondary" />
        <Button label="Generate SQL" icon="pi pi-bolt" @click="handleAIAssist" :loading="aiGenerating" />
      </template>
    </Dialog>

    <!-- Reject Dialog -->
    <Dialog 
      v-model:visible="showRejectDialog" 
      modal 
      header="Reject Suggestion" 
      :style="{ width: '500px' }"
    >
      <div class="reject-dialog-content">
        <p>Why is this suggestion being rejected? This feedback helps improve future AI suggestions.</p>
        <Textarea 
          v-model="rejectReason" 
          :rows="4"
          class="w-full"
          placeholder="e.g., Wrong source table, incorrect transformation, missing join condition..."
        />
      </div>

      <template #footer>
        <Button label="Cancel" icon="pi pi-times" @click="showRejectDialog = false" severity="secondary" />
        <Button label="Reject" icon="pi pi-times" @click="handleReject" severity="danger" :loading="saving" :disabled="!rejectReason" />
      </template>
    </Dialog>

    <!-- Pattern Alternatives Dialog -->
    <Dialog 
      v-model:visible="showAlternativesDialog" 
      modal 
      header="Pattern Alternatives" 
      :style="{ width: '700px' }"
    >
      <div v-if="loadingAlternatives" class="loading-alternatives">
        <ProgressSpinner />
        <p>Loading alternatives...</p>
      </div>
      
      <div v-else class="alternatives-content">
        <p class="alternatives-intro">
          Multiple teams have mapped <strong>{{ alternativesSuggestion?.tgt_column_physical_name }}</strong> differently.
          Choose the pattern that best fits your source data.
        </p>
        
        <div 
          v-for="variant in patternVariants" 
          :key="variant.signature"
          class="variant-card"
          :class="{ 'is-current': variant.is_current }"
        >
          <div class="variant-header">
            <Tag :value="variant.description.split(' + ')[0]" />
            <span class="variant-transforms">
              {{ variant.description.includes(' + ') ? variant.description.split(' + ').slice(1).join(' + ') : '' }}
            </span>
            <Badge :value="variant.usage_count" severity="info" v-tooltip.top="'Times used'" />
            <Tag v-if="variant.is_current" value="Current" severity="success" size="small" />
          </div>
          
          <div class="variant-meta">
            <span><i class="pi pi-calendar"></i> Last used: {{ formatDate(variant.latest_mapped_ts) }}</span>
            <span><i class="pi pi-user"></i> {{ variant.latest_pattern.created_by || 'Unknown' }}</span>
          </div>
          
          <div class="variant-sql-preview">
            <code>{{ truncateSql(variant.latest_pattern.source_expression, 120) }}</code>
          </div>
          
          <Button 
            :label="variant.is_current ? 'Currently Selected' : 'Use This Pattern'"
            :icon="variant.is_current ? 'pi pi-check' : 'pi pi-arrow-right'"
            size="small"
            :disabled="variant.is_current"
            :severity="variant.is_current ? 'success' : 'info'"
            @click="useAlternativePattern(variant)"
            :loading="regeneratingWithPattern === variant.latest_pattern.mapped_field_id"
          />
        </div>
      </div>
    </Dialog>

    <!-- Vector Search Candidates Dialog -->
    <Dialog 
      v-model:visible="showVSCandidatesDialog" 
      modal 
      header="Source Field Alternatives" 
      :style="{ width: '800px', maxHeight: '80vh' }"
    >
      <div v-if="loadingVSCandidates" class="loading-alternatives">
        <ProgressSpinner />
        <p>Loading alternatives...</p>
      </div>
      
      <div v-else-if="vsCandidatesData" class="vs-candidates-content">
        <p class="vs-candidates-intro">
          Vector search candidates for <strong>{{ vsCandidatesSuggestion?.tgt_column_physical_name }}</strong>.
          Shows what the AI selected from available options.
        </p>
        
        <!-- Table Mappings Section (grouped by alias) -->
        <div v-if="vsCandidatesData.changes_by_table && Object.keys(vsCandidatesData.changes_by_table).length > 0" class="table-mappings-section">
          <h4><i class="pi pi-table"></i> Table Mappings</h4>
          <div class="table-mappings-list">
            <div 
              v-for="(group, alias) in vsCandidatesData.changes_by_table" 
              :key="alias"
              class="table-mapping-item"
            >
              <Badge :value="group.pattern_table || '?'" severity="secondary" class="pattern-table-badge" />
              <i class="pi pi-arrow-right"></i>
              <Badge :value="group.source_table || '?'" severity="success" class="source-table-badge" />
              <span class="alias-indicator">({{ alias }})</span>
            </div>
          </div>
        </div>
        
        <div v-if="!vsCandidatesData.has_candidates" class="no-candidates-message">
          <i class="pi pi-info-circle"></i>
          <span>No vector search candidate data available for this suggestion. It may be an older suggestion or a special case.</span>
        </div>
        
        <!-- Column Candidates Section - Show usage count for multi-table columns -->
        <div v-else class="candidates-by-column">
          <h4><i class="pi pi-list"></i> Column Candidates</h4>
          <div 
            v-for="(candidates, columnName) in vsCandidatesData.candidates_by_column" 
            :key="columnName"
            class="column-candidates"
          >
            <div class="column-candidates-header">
              <Badge :value="columnName" severity="secondary" class="original-column-badge" />
              <!-- Show usage count if used in multiple tables -->
              <span v-if="getColumnUsageCount(columnName) > 1" class="usage-count">
                Used in {{ getColumnUsageCount(columnName) }} tables
              </span>
              <Badge :value="candidates.length" severity="info" class="count-badge" />
            </div>
            
            <!-- Show per-table usage if column is used in multiple tables -->
            <div v-if="getColumnUsageCount(columnName) > 1" class="column-usages">
              <div 
                v-for="(usage, uidx) in getColumnUsages(columnName)" 
                :key="uidx"
                class="column-usage-item"
              >
                <span class="usage-table">In {{ usage.alias }} ({{ getTableNameForAlias(usage.alias) }}):</span>
                <Badge :value="usage.original" severity="secondary" class="original-badge" />
                <i class="pi pi-arrow-right"></i>
                <Badge :value="usage.new_column" severity="success" class="selected-badge" />
              </div>
            </div>
            
            <div class="candidates-list">
              <div 
                v-for="(candidate, idx) in candidates" 
                :key="idx"
                class="candidate-item"
                :class="{ 'was-selected': candidate.was_selected }"
              >
                <div class="candidate-main">
                  <span class="candidate-column">
                    {{ candidate.src_table_physical_name }}.{{ candidate.src_column_physical_name }}
                  </span>
                  <Tag 
                    v-if="candidate.was_selected" 
                    value="Selected" 
                    severity="success" 
                    size="small" 
                  />
                  <span class="candidate-score">{{ (candidate.score * 100).toFixed(1) }}%</span>
                </div>
                <div class="candidate-meta" v-if="candidate.src_comments">
                  {{ candidate.src_comments }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <Button label="Close" @click="showVSCandidatesDialog = false" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useProjectsStore, type MappingSuggestion, type MatchedSourceField } from '@/stores/projectsStore'
import { useUserStore } from '@/stores/user'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import ProgressSpinner from 'primevue/progressspinner'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'
import InputText from 'primevue/inputtext'

// Gainwell system columns - expected in bronze tables, not user-mapped
// These should NOT appear as warnings and should be highlighted differently
const GAINWELL_SYSTEM_COLUMNS = new Set([
  'CRT_BY_USER_ID',
  'CRT_DTTM', 
  'UPD_BY_USER_ID',
  'UPD_DTTM',
  'CURR_REC_IND',
  'SRC_SYS_CD',
  'REC_HASH_KEY'
])

const props = defineProps<{
  projectId: number
  tableId: number
  tableName: string
}>()

const emit = defineEmits(['suggestion-updated', 'manual-mapping'])

const toast = useToast()
const projectsStore = useProjectsStore()
const userStore = useUserStore()

// State
const showEditDialog = ref(false)
const showRejectDialog = ref(false)
const showAIAssist = ref(false)
const showAlternativesDialog = ref(false)
const showVSCandidatesDialog = ref(false)
const editingSuggestion = ref<MappingSuggestion | null>(null)
const rejectingSuggestion = ref<MappingSuggestion | null>(null)
const alternativesSuggestion = ref<MappingSuggestion | null>(null)
const vsCandidatesSuggestion = ref<MappingSuggestion | null>(null)
const vsCandidatesData = ref<any>(null)
const editingAliasMap = ref<Record<string, string>>({})  // alias -> pattern table name for left panel
const patternVariants = ref<any[]>([])
const loadingAlternatives = ref(false)
const loadingVSCandidates = ref(false)
const regeneratingWithPattern = ref<number | null>(null)
const editedSQL = ref('')
const editNotes = ref('')
const rejectReason = ref('')
const saving = ref(false)
const aiGenerating = ref(false)
const aiPrompt = ref('')
const sourceFilter = ref('')
const expandedTables = ref<string[]>([])
const sourceFields = ref<any[]>([])
const regeneratingId = ref<number | null>(null)
const leftPanelCollapsed = ref(false)
const aiChangesCollapsed = ref(false)
const sqlPreviewCollapsed = ref(false)
const sqlTextarea = ref<any>(null)
const skippingId = ref<number | null>(null)
const approvingId = ref<number | null>(null)

// Computed
// Sort suggestions by column name for consistent display
const suggestions = computed(() => {
  return [...projectsStore.suggestions].sort((a, b) => {
    const nameA = (a.tgt_column_physical_name || a.tgt_column_name || '').toLowerCase()
    const nameB = (b.tgt_column_physical_name || b.tgt_column_name || '').toLowerCase()
    return nameA.localeCompare(nameB)
  })
})
const loading = computed(() => projectsStore.loading)

const pendingCount = computed(() => 
  suggestions.value.filter(s => s.suggestion_status === 'PENDING').length
)
const approvedCount = computed(() => 
  suggestions.value.filter(s => 
    s.suggestion_status === 'APPROVED' || 
    s.suggestion_status === 'EDITED' || 
    s.suggestion_status === 'AUTO_MAPPED' ||
    s.suggestion_status === 'SYSTEM_COLUMN'
  ).length
)
const noMatchCount = computed(() => 
  suggestions.value.filter(s => s.suggestion_status === 'NO_MATCH' || s.suggestion_status === 'NO_PATTERN').length
)

// Check if any operation is in progress for a specific suggestion
function isOperationInProgress(suggestionId: number): boolean {
  return skippingId.value === suggestionId || 
         approvingId.value === suggestionId || 
         regeneratingId.value === suggestionId ||
         saving.value
}

// Problem fields from AI warnings that need user attention
// NOTE: We only highlight fields from WARNINGS (missing/not found), 
// NOT from successful changes (those are already fixed)
const problemFieldsInSQL = computed(() => {
  if (!editingSuggestion.value) return []
  
  const warnings = getWarnings(editingSuggestion.value)
  const problems: string[] = []
  
  // Extract field names from warnings about missing/unknown fields
  for (const warning of warnings) {
    // Common warning patterns we need to match:
    // - "Column CURR_REC_IND was found in multiple tables..."
    // - "Column ADDR_USAGE was used for filtering..."
    // - "No matching source column found for CDE_COUNTY"
    // - "Column 'XYZ' not found"
    // - "Missing: ABC_FIELD"
    
    // Match "Column FIELD_NAME was..." or "Column FIELD_NAME is..."
    const columnMatch = warning.match(/Column\s+([A-Z][A-Z0-9_]+)\s+(?:was|is|has)/i)
    if (columnMatch) {
      problems.push(columnMatch[1])
    }
    
    // Match field names in quotes
    const quotedMatches = warning.match(/['"`]([A-Za-z_][A-Za-z0-9_]*)['"`]/g)
    if (quotedMatches) {
      problems.push(...quotedMatches.map((m: string) => m.replace(/['"`]/g, '')))
    }
    
    // Match "for FIELD_NAME" or "found for FIELD_NAME" 
    const forMatch = warning.match(/for\s+([A-Z][A-Z0-9_]+)/i)
    if (forMatch) {
      problems.push(forMatch[1])
    }
    
    // Match "Missing: FIELD_NAME" or "Missing FIELD_NAME"
    const missingMatch = warning.match(/missing[:\s]+([A-Z][A-Z0-9_]+)/i)
    if (missingMatch) {
      problems.push(missingMatch[1])
    }
    
    // Match any ALL_CAPS_FIELD_NAME that looks like a column (fallback)
    const allCapsMatches = warning.match(/\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b/g)
    if (allCapsMatches) {
      problems.push(...allCapsMatches)
    }
    
    // Fallback: If the warning is JUST a column name (no sentence structure),
    // treat the whole thing as a problem field
    // This catches warnings like "entityid", "curr_rec_ind", etc.
    const trimmed = warning.trim()
    if (/^[a-zA-Z][a-zA-Z0-9_]*$/.test(trimmed) && trimmed.length < 50) {
      problems.push(trimmed)
    }
  }
  
  // Filter out SQL keywords
  const sqlKeywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'AND', 'OR', 'ON', 'AS', 'IN', 'NOT', 'NULL',
                       'LEFT', 'RIGHT', 'INNER', 'OUTER', 'UNION', 'DISTINCT', 'GROUP', 'BY', 'ORDER',
                       'HAVING', 'LIMIT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'TRIM', 'INITCAP', 'CONCAT']
  
  // Extract silver table aliases from the SQL (tables with "silver" in the path)
  // Matches patterns like: FROM silver.xxx AS alias, JOIN silver.xxx alias, silver.xxx.yyy mf
  const sql = editedSQL.value || editingSuggestion.value?.suggested_sql || ''
  const silverAliases = new Set<string>()
  
  // Match: silver.anything AS/followed by alias (1-3 chars typically)
  const silverPatterns = [
    /silver[._][^\s]+\s+(?:AS\s+)?(\w{1,4})\b/gi,  // silver.table AS mf or silver.table mf
    /FROM\s+(\w+)\.[^.]+\.(\w+)\s+(?:AS\s+)?(\w{1,4})\b/gi  // FROM catalog.silver.table mf
  ]
  
  for (const pattern of silverPatterns) {
    let match
    while ((match = pattern.exec(sql)) !== null) {
      // Check if "silver" appears before the alias
      const fullMatch = match[0].toLowerCase()
      if (fullMatch.includes('silver')) {
        const alias = match[match.length - 1] || match[1]
        if (alias && alias.length <= 4) {
          silverAliases.add(alias.toLowerCase())
        }
      }
    }
  }
  
  // Also check for direct "silver" in table references
  const directSilverMatch = sql.match(/\bsilver\.\w+/gi)
  if (directSilverMatch) {
    // Mark 'mf' as silver alias if we see silver.mbr_fndtn or similar
    silverAliases.add('mf')
  }
  
  const filtered = problems.filter(p => {
    const upper = p.toUpperCase()
    const lower = p.toLowerCase()
    
    // Exclude SQL keywords
    if (sqlKeywords.includes(upper)) return false
    
    // Exclude Gainwell system columns (expected in bronze tables, not user-mapped)
    if (GAINWELL_SYSTEM_COLUMNS.has(upper)) return false
    
    // Exclude if this looks like an alias.column from a silver table
    // Check if any warning mentions this column with a silver table alias
    for (const alias of silverAliases) {
      // If the SQL contains alias.COLUMN_NAME, exclude this column
      const aliasPattern = new RegExp(`\\b${alias}\\.${p}\\b`, 'i')
      if (aliasPattern.test(sql)) {
        return false
      }
    }
    
    return true
  })
  
  return [...new Set(filtered)] // unique values
})

// Detect system columns present in the SQL for special highlighting
const systemColumnsInSQL = computed(() => {
  if (!editingSuggestion.value) return []
  
  const sql = editedSQL.value || editingSuggestion.value?.suggested_sql || ''
  const sqlUpper = sql.toUpperCase()
  const found: string[] = []
  
  for (const sysCol of GAINWELL_SYSTEM_COLUMNS) {
    const pattern = new RegExp(`\\b${sysCol}\\b`, 'i')
    if (pattern.test(sqlUpper)) {
      found.push(sysCol)
    }
  }
  
  return found
})

// Highlighted ORIGINAL SQL showing what was changed (blue) and what wasn't (yellow/red)
const highlightedOriginalSQL = computed(() => {
  if (!editingSuggestion.value?.pattern_sql) {
    return ''
  }
  
  const originalSQL = editingSuggestion.value.pattern_sql
  let html = escapeHtml(originalSQL)
  
  // Get changes with their alias context - we need to match alias.column patterns precisely
  const changes = getChanges(editingSuggestion.value)
  
  // Track which aliases are mapped to UNKNOWN (unmapped tables)
  const unmappedAliases = new Set<string>()
  for (const change of changes) {
    if (change.type === 'table_replace') {
      const alias = change.alias?.toLowerCase() || ''
      const targetTable = (change.new || '').toUpperCase()
      if (targetTable === 'UNKNOWN' && alias) {
        unmappedAliases.add(alias)
      }
    }
  }
  
  // Track alias-qualified patterns separately from bare column names
  // Key: "alias.COLUMN" or just "COLUMN", Value: { success: boolean }
  const changesByAliasColumn = new Map<string, boolean>()
  const changesByBareColumn = new Map<string, boolean>()
  
  for (const change of changes) {
    if (change.original) {
      const newValue = change.new || ''
      let isSuccess = change.is_invalid !== true && !newValue.includes('NO_MATCH')
      
      // Check if the change has an alias (from the change object)
      const alias = change.alias || ''
      const parts = change.original.split('.')
      const bareColumn = parts[parts.length - 1].toUpperCase()
      
      // If this column belongs to an unmapped table alias, mark it as NOT success (warning)
      if (alias && unmappedAliases.has(alias.toLowerCase())) {
        isSuccess = false
      }
      
      if (alias) {
        // We have explicit alias info - use it
        const key = `${alias.toLowerCase()}.${bareColumn}`
        changesByAliasColumn.set(key, isSuccess)
      } else if (parts.length > 1) {
        // The original itself has alias prefix like "b.SAK_RECIP"
        const aliasFromOriginal = parts[0].toLowerCase()
        const key = `${aliasFromOriginal}.${bareColumn}`
        // If this alias is unmapped, mark as warning
        if (unmappedAliases.has(aliasFromOriginal)) {
          isSuccess = false
        }
        changesByAliasColumn.set(key, isSuccess)
      }
      
      // Also track bare column - but only set to true if ANY instance succeeded
      // and false only if ALL instances failed
      const existing = changesByBareColumn.get(bareColumn)
      if (existing === undefined) {
        changesByBareColumn.set(bareColumn, isSuccess)
      } else if (isSuccess) {
        changesByBareColumn.set(bareColumn, true) // At least one succeeded
      }
    }
  }
  
  // Get warning fields from problemFieldsInSQL
  const warnings = problemFieldsInSQL.value
  const warningSet = new Set(warnings.map(w => w.toUpperCase()))
  
  // Step 0: Highlight Gainwell system columns FIRST in teal
  // These are expected in bronze tables and should stand out from regular column changes
  for (const sysCol of GAINWELL_SYSTEM_COLUMNS) {
    const regex = new RegExp(`\\b(${escapeRegExp(sysCol)})\\b`, 'gi')
    html = html.replace(regex, '<mark class="system-column">$1</mark>')
  }
  
  // Strategy: Replace alias.column patterns FIRST (most specific), then bare columns
  // This ensures b.SAK_RECIP and a.SAK_RECIP can have different highlighting
  
  // Step 1: Highlight alias.column patterns (e.g., b.SAK_RECIP, a.SAK_RECIP)
  // Skip if already marked as system-column
  const aliasPatterns = [...changesByAliasColumn.entries()].sort((a, b) => b[0].length - a[0].length)
  for (const [pattern, isSuccess] of aliasPatterns) {
    // Skip if the column part is a system column
    const colPart = pattern.includes('.') ? pattern.split('.')[1] : pattern
    if (GAINWELL_SYSTEM_COLUMNS.has(colPart.toUpperCase())) continue
    
    const cssClass = isSuccess ? 'original-changed' : 'original-no-match'
    // Match alias.column pattern (case insensitive for alias and column), skip if already marked
    const regex = new RegExp(`(?![^<]*<\\/mark>)\\b(${escapeRegExp(pattern)})\\b`, 'gi')
    html = html.replace(regex, `<mark class="${cssClass}">$1</mark>`)
  }
  
  // Step 2: Highlight remaining bare column references not yet marked
  // Only for columns that don't have alias-qualified patterns in the SQL
  const bareColumns = [...changesByBareColumn.entries()].sort((a, b) => b[0].length - a[0].length)
  for (const [column, isSuccess] of bareColumns) {
    // Skip if in warning set
    if (warningSet.has(column)) continue
    // Skip if it's a system column (already highlighted in teal)
    if (GAINWELL_SYSTEM_COLUMNS.has(column.toUpperCase())) continue
    // Only match if not already inside a <mark> tag (avoid double-marking)
    const cssClass = isSuccess ? 'original-changed' : 'original-no-match'
    // Match bare column only if not preceded by a dot and letter (already part of alias.column)
    const regex = new RegExp(`(?<![a-zA-Z]\\.)(\\b${escapeRegExp(column)}\\b)(?![^<]*<\\/mark>)`, 'gi')
    html = html.replace(regex, `<mark class="${cssClass}">$1</mark>`)
  }
  
  // Step 3: Highlight table names from table_replace changes
  for (const change of changes) {
    if (change.type === 'table_replace' && change.original) {
      // Extract just the table name from fully qualified path
      const parts = change.original.split('.')
      const tableName = parts[parts.length - 1].toUpperCase()
      const targetTable = (change.new || '').toUpperCase()
      // Use warning style for UNKNOWN tables, success for mapped tables
      const cssClass = targetTable === 'UNKNOWN' ? 'original-no-match' : 'original-changed'
      const regex = new RegExp(`\\b(${escapeRegExp(tableName)})\\b`, 'gi')
      html = html.replace(regex, `<mark class="${cssClass}">$1</mark>`)
    }
  }
  
  // Step 3b: Highlight columns from UNKNOWN tables that weren't in changes
  // For UNION patterns WITHOUT explicit aliases, we need to identify which SQL segments
  // belong to UNKNOWN tables and highlight their columns as warnings
  
  // First, handle aliased columns (alias.COLUMN patterns)
  if (unmappedAliases.size > 0) {
    for (const unmappedAlias of unmappedAliases) {
      // Match alias.COLUMN patterns for unmapped aliases (skip if already marked)
      const regex = new RegExp(`(?![^<]*<\\/mark>)\\b(${escapeRegExp(unmappedAlias)}\\.(\\w+))\\b`, 'gi')
      html = html.replace(regex, '<mark class="original-no-match">$1</mark>')
    }
  }
  
  // Second, handle UNION patterns without aliases
  // Find UNKNOWN table names and re-highlight columns in their SELECT clauses
  const unknownTableNames: string[] = []
  for (const change of changes) {
    if (change.type === 'table_replace') {
      const targetTable = (change.new || '').toUpperCase()
      if (targetTable === 'UNKNOWN') {
        const parts = (change.original || '').split('.')
        unknownTableNames.push(parts[parts.length - 1].toUpperCase())
      }
    }
  }
  
  if (unknownTableNames.length > 0) {
    // Parse the original SQL (not html) to find segments containing UNKNOWN tables
    const originalSQL = editingSuggestion.value?.pattern_sql || ''
    
    // Split by UNION to get individual SELECT statements
    const unionParts = originalSQL.split(/\bUNION\b/i)
    
    for (let i = 0; i < unionParts.length; i++) {
      const part = unionParts[i]
      
      // Check if this part contains an UNKNOWN table
      let containsUnknownTable = false
      for (const tableName of unknownTableNames) {
        if (part.toUpperCase().includes(tableName)) {
          containsUnknownTable = true
          break
        }
      }
      
      if (containsUnknownTable) {
        // Extract column names from this UNION branch
        // Look for pattern: SELECT ... column ... FROM
        // Also look for columns in WHERE clause
        const selectMatch = part.match(/SELECT\s+(.+?)\s+FROM/is)
        const whereMatch = part.match(/WHERE\s+(.+?)$/is)
        
        const columnsInBranch: string[] = []
        
        // Extract columns from SELECT clause
        if (selectMatch) {
          const selectPart = selectMatch[1]
          // Find column references like INITCAP(COLUMN) or just COLUMN
          const colMatches = selectPart.match(/\b([A-Z_][A-Z0-9_]*)\b(?=\s*[\),\s]|\s+AS\b)/gi)
          if (colMatches) {
            for (const col of colMatches) {
              if (!['INITCAP', 'TRIM', 'CONCAT', 'COALESCE', 'AS', 'NULL', 'SELECT'].includes(col.toUpperCase())) {
                columnsInBranch.push(col.toUpperCase())
              }
            }
          }
        }
        
        // Extract columns from WHERE clause
        if (whereMatch) {
          const wherePart = whereMatch[1]
          const colMatches = wherePart.match(/\b([A-Z_][A-Z0-9_]*)\b(?=\s*[=<>!\(\),]|\s+IN\b|\s+AND\b|\s+OR\b)/gi)
          if (colMatches) {
            for (const col of colMatches) {
              if (!['AND', 'OR', 'IN', 'TRIM', 'WHERE', 'LIKE', 'BETWEEN', 'IS', 'NOT', 'NULL', 'R', 'M'].includes(col.toUpperCase())) {
                columnsInBranch.push(col.toUpperCase())
              }
            }
          }
        }
        
        // Re-highlight these columns as warnings in the HTML, but only in the matching UNION segment
        // We need to find the corresponding segment in the HTML
        for (const col of columnsInBranch) {
          // Find and replace existing blue highlighting with orange for this column
          // But only after the UNKNOWN table name in the HTML
          // This is tricky - we'll use a position-aware approach
          
          // Find the position of the UNKNOWN table mark in HTML
          for (const tableName of unknownTableNames) {
            const tableMarkRegex = new RegExp(`<mark class="original-no-match">${escapeRegExp(tableName)}</mark>`, 'i')
            const tableMatch = html.match(tableMarkRegex)
            if (tableMatch && tableMatch.index !== undefined) {
              // Only replace column marks AFTER this table position
              const beforeTable = html.substring(0, tableMatch.index)
              let afterTable = html.substring(tableMatch.index)
              
              // Replace blue (original-changed) with orange (original-no-match) for this column after the table
              const blueColRegex = new RegExp(`<mark class="original-changed">(${escapeRegExp(col)})</mark>`, 'gi')
              afterTable = afterTable.replace(blueColRegex, '<mark class="original-no-match">$1</mark>')
              
              html = beforeTable + afterTable
            }
          }
        }
      }
    }
  }
  
  // Highlight SQL keywords
  const keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 
                    'ON', 'AND', 'OR', 'AS', 'UNION', 'ALL', 'CASE', 'WHEN', 'THEN', 
                    'ELSE', 'END', 'TRIM', 'CONCAT', 'COALESCE', 'NULL', 'IS', 'NOT',
                    'DISTINCT', 'INITCAP', 'IN', 'LIKE', 'BETWEEN', 'GROUP', 'BY', 
                    'ORDER', 'HAVING', 'LIMIT', 'OFFSET', 'WITH', 'CTE']
  
  for (const kw of keywords) {
    const regex = new RegExp(`\\b(${kw})\\b`, 'gi')
    html = html.replace(regex, '<span class="sql-keyword">$1</span>')
  }
  
  return html
})

// Highlighted SQL with syntax highlighting and problem fields marked (for NEW SQL preview)
const highlightedSQL = computed(() => {
  if (!editedSQL.value) {
    return ''
  }
  
  let html = escapeHtml(editedSQL.value)
  
  // First, highlight problem fields (from warnings) in yellow
  if (problemFieldsInSQL.value.length > 0) {
    const sortedProblems = [...problemFieldsInSQL.value].sort((a, b) => b.length - a.length)
    
    for (const field of sortedProblems) {
      const regex = new RegExp(`\\b(${escapeRegExp(field)})\\b`, 'gi')
      html = html.replace(regex, '<mark class="problem-field">$1</mark>')
    }
  }
  
  // Highlight SQL keywords for readability
  const keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 
                    'ON', 'AND', 'OR', 'AS', 'UNION', 'ALL', 'CASE', 'WHEN', 'THEN', 
                    'ELSE', 'END', 'TRIM', 'CONCAT', 'COALESCE', 'NULL', 'IS', 'NOT',
                    'DISTINCT', 'INITCAP', 'IN', 'LIKE', 'BETWEEN', 'GROUP', 'BY', 
                    'ORDER', 'HAVING', 'LIMIT', 'OFFSET']
  
  for (const kw of keywords) {
    const regex = new RegExp(`\\b(${kw})\\b`, 'gi')
    html = html.replace(regex, '<span class="sql-keyword">$1</span>')
  }
  
  // Highlight string literals
  html = html.replace(/('(?:[^'\\]|\\.)*')/g, '<span class="sql-string">$1</span>')
  
  // Highlight placeholders like ${USER_BRONZE_CATALOG}
  html = html.replace(/(\$\{[A-Z_]+\})/g, '<span class="sql-placeholder">$1</span>')
  
  // Highlight table aliases (single letters followed by .)
  html = html.replace(/\b([a-z])\.([A-Za-z_][A-Za-z0-9_]*)/g, '<span class="sql-alias">$1</span>.<span class="sql-column">$2</span>')
  
  return html
})

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// Group source fields by table
const groupedSourceFields = computed(() => {
  const groups: { tableName: string; columns: any[] }[] = []
  const tableMap = new Map<string, any[]>()
  
  for (const field of sourceFields.value) {
    const tableName = field.src_table_physical_name || 'Unknown'
    if (!tableMap.has(tableName)) {
      tableMap.set(tableName, [])
    }
    tableMap.get(tableName)!.push(field)
  }
  
  tableMap.forEach((columns, tableName) => {
    groups.push({ tableName, columns })
  })
  
  return groups.sort((a, b) => a.tableName.localeCompare(b.tableName))
})

// Lifecycle
onMounted(() => {
  loadSuggestions()
})

watch(() => props.tableId, () => {
  loadSuggestions()
})

// Methods
async function loadSuggestions() {
  await projectsStore.fetchSuggestions(props.projectId, props.tableId)
}

function getMatchedFields(suggestion: MappingSuggestion): MatchedSourceField[] {
  return projectsStore.parseMatchedSourceFields(suggestion.matched_source_fields)
}

function getWarnings(suggestion: MappingSuggestion): string[] {
  if (!suggestion.warnings) return []
  try {
    const warnings = JSON.parse(suggestion.warnings) as string[]
    if (!warnings || warnings.length === 0) return []
    
    // Get the changes to filter out false positives
    const changes = getChanges(suggestion)
    if (!changes || changes.length === 0) return warnings
    
    // Build set of successfully replaced columns WITH their table context
    // Key: "TABLE:COLUMN" for context-aware filtering
    const replacedColumnsWithTable = new Set<string>()
    // Also track just column names for partial matching
    const replacedColumnNames = new Set<string>()
    
    for (const change of changes) {
      if (change.type === 'column_replace' || change.new) {
        let original = change.original || ''
        const patternTable = (change.pattern_table || '').toUpperCase()
        // Extract just column name if TABLE.COLUMN format
        if (original.includes('.')) {
          original = original.split('.').pop() || original
        }
        if (original) {
          const colUpper = original.toUpperCase()
          replacedColumnNames.add(colUpper)
          if (patternTable) {
            replacedColumnsWithTable.add(`${patternTable}:${colUpper}`)
          }
        }
      }
    }
    
    if (replacedColumnNames.size === 0) return warnings
    
    // Filter out warnings that mention successfully replaced columns or system columns
    return warnings.filter(warning => {
      const warningUpper = warning.toUpperCase()
      
      // Check if warning mentions UNKNOWN or "no source table match" - these are valid warnings
      // Don't filter them even if the column was replaced in a different table
      if (warningUpper.includes('UNKNOWN') || 
          warningUpper.includes('NO SOURCE TABLE') ||
          warningUpper.includes('NO MATCH') ||
          warningUpper.includes('UNMAPPED')) {
        return true // Keep this warning - it's about an unmapped table
      }
      
      // For other warnings, check if the column+table combination was replaced
      // Try to extract table context from warning (e.g., "from T_RE_MULTI_ADDRESS")
      const tableMatch = warning.match(/from\s+([A-Z_][A-Z0-9_]*)/i)
      if (tableMatch) {
        const warningTable = tableMatch[1].toUpperCase()
        
        // Check each replaced column
        for (const col of replacedColumnNames) {
          const regex = new RegExp(`\\b${col}\\b`, 'i')
          if (regex.test(warningUpper)) {
            // Column mentioned in warning - but was it replaced in THIS table?
            if (replacedColumnsWithTable.has(`${warningTable}:${col}`)) {
              return false // Column was replaced in the same table - false positive
            }
            // Column exists but was replaced in a DIFFERENT table - keep the warning
          }
        }
        return true // Keep warning - either no column match or different table context
      }
      
      // No table context in warning - fall back to simple column check
      for (const col of replacedColumnNames) {
        const regex = new RegExp(`\\b${col}\\b`, 'i')
        if (regex.test(warningUpper)) {
          return false // This is potentially a false positive
        }
      }
      
      // Filter out warnings about Gainwell system columns (expected in bronze tables)
      for (const sysCol of GAINWELL_SYSTEM_COLUMNS) {
        const regex = new RegExp(`\\b${sysCol}\\b`, 'i')
        if (regex.test(warningUpper)) {
          return false // System column - not a real warning
        }
      }
      
      return true
    })
  } catch {
    return []
  }
}

async function handleApprove(suggestion: MappingSuggestion) {
  approvingId.value = suggestion.suggestion_id
  try {
    await projectsStore.approveSuggestion(suggestion.suggestion_id, userStore.userEmail || 'unknown')
    toast.add({ severity: 'success', summary: 'Approved', detail: 'Mapping created', life: 2000 })
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  } finally {
    approvingId.value = null
  }
}

async function openEditDialog(suggestion: MappingSuggestion) {
  editingSuggestion.value = suggestion
  editedSQL.value = suggestion.suggested_sql || ''
  editNotes.value = ''
  sourceFilter.value = ''
  expandedTables.value = []
  editingAliasMap.value = {}
  showEditDialog.value = true
  
  // Load source fields for the project
  loadSourceFields()
  
  // Also fetch VS candidates data to get alias-to-pattern-table mapping
  try {
    const response = await fetch(`/api/v4/suggestions/${suggestion.suggestion_id}/vs-candidates`)
    if (response.ok) {
      const data = await response.json()
      if (data.alias_to_pattern_table) {
        editingAliasMap.value = data.alias_to_pattern_table
      }
    }
  } catch (e) {
    // Non-critical - left panel will fall back to alias display
    console.log('Could not fetch alias mapping:', e)
  }
}

async function loadSourceFields() {
  try {
    const response = await fetch(`/api/v4/projects/${props.projectId}/source-fields`)
    if (response.ok) {
      sourceFields.value = await response.json()
      // Auto-expand first table
      if (groupedSourceFields.value.length > 0) {
        expandedTables.value = [groupedSourceFields.value[0].tableName]
      }
    }
  } catch (e) {
    console.error('Error loading source fields:', e)
  }
}

function toggleTableExpand(tableName: string) {
  if (expandedTables.value.includes(tableName)) {
    expandedTables.value = expandedTables.value.filter(t => t !== tableName)
  } else {
    expandedTables.value.push(tableName)
  }
}

function filteredColumns(columns: any[]) {
  if (!sourceFilter.value) return columns
  const filter = sourceFilter.value.toLowerCase()
  return columns.filter(c => 
    c.src_column_physical_name?.toLowerCase().includes(filter) ||
    c.src_comments?.toLowerCase().includes(filter)
  )
}

function isMatchedColumn(col: any): boolean {
  if (!editingSuggestion.value) return false
  
  // Check if this column is ACTUALLY USED in the changes (not just in vector search results)
  const changes = getChanges(editingSuggestion.value)
  const colName = (col.src_column_physical_name || '').toUpperCase()
  const tableName = (col.src_table_physical_name || '').toUpperCase()
  
  // Check if any change references this column
  for (const change of changes) {
    const newVal = (change.new || '').toUpperCase()
    // Check for TABLE.COLUMN or just COLUMN match
    if (newVal.includes(colName)) {
      // If it has table prefix, verify it matches
      if (newVal.includes('.')) {
        const parts = newVal.split('.')
        const changeTable = parts[0]
        const changeCol = parts[parts.length - 1]
        if (changeCol === colName && changeTable === tableName) {
          return true
        }
      } else if (newVal === colName) {
        return true
      }
    }
  }
  
  // Also check if column appears in the edited SQL (for manual additions)
  const sql = (editedSQL.value || '').toUpperCase()
  const fullRef = `${tableName}.${colName}`
  if (sql.includes(fullRef)) {
    return true
  }
  
  return false
}

function insertColumnToSQL(col: any) {
  const insertion = `${col.src_table_physical_name}.${col.src_column_physical_name}`
  editedSQL.value += (editedSQL.value ? ' ' : '') + insertion
}

function getChanges(suggestion: MappingSuggestion): any[] {
  if (!suggestion.sql_changes) return []
  try {
    return JSON.parse(suggestion.sql_changes)
  } catch {
    return []
  }
}

interface TableChangeGroup {
  alias: string
  patternTable: string
  sourceTable: string
  changes: Array<{
    original: string
    originalColumn: string
    new: string
    newColumn: string
    newTable: string
  }>
}

function getChangesByTable(suggestion: MappingSuggestion): TableChangeGroup[] {
  const changes = getChanges(suggestion)
  if (!changes.length) return []
  
  // Group changes by PATTERN TABLE (not alias) to handle multiple tables → same source
  const groups: Record<string, TableChangeGroup> = {}
  
  // Key by PATTERN table name (not source) to avoid overwrites when multiple patterns → same source
  const tableReplacements: Record<string, { pattern: string, source: string, alias: string }> = {}
  
  // Parse pattern_sql to extract table aliases FIRST
  const aliasFromPatternSQL: Record<string, string> = {}  // alias -> pattern table
  const patternTableToAlias: Record<string, string> = {}  // pattern table -> alias
  
  if (suggestion.pattern_sql) {
    // Simpler regex for common patterns
    const simpleTableAliasRegex = /(?:FROM|JOIN)\s+([\w.]+)\s+(\w{1,3})(?:\s|$|,|ON)/gi
    let match
    while ((match = simpleTableAliasRegex.exec(suggestion.pattern_sql)) !== null) {
      const tableFull = match[1]
      const alias = match[2].toLowerCase()
      // Skip keywords
      if (['on', 'and', 'or', 'where', 'left', 'right', 'as'].includes(alias)) continue
      const tableName = (tableFull.split('.').pop() || tableFull).toUpperCase()
      aliasFromPatternSQL[alias] = tableName
      patternTableToAlias[tableName] = alias
    }
    
    // Also look for subquery patterns: (select * from table where ...)alias
    const subqueryRegex = /\(select[^)]+from\s+([\w.]+)[^)]*\)\s*(\w{1,3})/gi
    while ((match = subqueryRegex.exec(suggestion.pattern_sql)) !== null) {
      const tableFull = match[1]
      const alias = match[2].toLowerCase()
      if (['on', 'and', 'or', 'where', 'left', 'right'].includes(alias)) continue
      const tableName = (tableFull.split('.').pop() || tableFull).toUpperCase()
      if (!aliasFromPatternSQL[alias]) {
        aliasFromPatternSQL[alias] = tableName
        patternTableToAlias[tableName] = alias
      }
    }
  }
  
  // Also try metadata
  try {
    if (suggestion.join_metadata_raw) {
      const metadata = typeof suggestion.join_metadata_raw === 'string' 
        ? JSON.parse(suggestion.join_metadata_raw) 
        : suggestion.join_metadata_raw
      
      if (metadata.unionBranches) {
        for (const branch of metadata.unionBranches) {
          if (branch.bronzeTable?.alias && branch.bronzeTable?.physicalName) {
            const tableName = (branch.bronzeTable.physicalName.split('.').pop() || branch.bronzeTable.physicalName).toUpperCase()
            const alias = branch.bronzeTable.alias.toLowerCase()
            aliasFromPatternSQL[alias] = tableName
            patternTableToAlias[tableName] = alias
          }
        }
      }
      if (metadata.bronzeTable?.alias && metadata.bronzeTable?.physicalName) {
        const tableName = (metadata.bronzeTable.physicalName.split('.').pop() || metadata.bronzeTable.physicalName).toUpperCase()
        const alias = metadata.bronzeTable.alias.toLowerCase()
        aliasFromPatternSQL[alias] = tableName
        patternTableToAlias[tableName] = alias
      }
    }
  } catch (e) {
    // Non-critical
  }
  
  console.log('[getChangesByTable] Aliases:', aliasFromPatternSQL, 'PatternToAlias:', patternTableToAlias)
  
  // First pass: Create groups from table_replace changes
  // Key by PATTERN table to avoid overwrites
  for (const change of changes) {
    if (change.type === 'table_replace' && change.original && change.new) {
      const patternTable = (change.pattern_table || change.original.split('.').pop() || change.original).toUpperCase()
      const sourceTable = (change.new.split('.').pop() || change.new).toUpperCase()
      // Use alias from LLM if provided, otherwise fall back to parsing
      const alias = change.alias?.toLowerCase() || patternTableToAlias[patternTable] || patternTable.substring(0, 1).toLowerCase()
      
      tableReplacements[patternTable] = {
        pattern: patternTable,
        source: sourceTable,
        alias: alias
      }
      
      // Create group for each pattern table
      // Track if this table is mapped to UNKNOWN (unmapped)
      const isUnmapped = sourceTable === 'UNKNOWN'
      groups[patternTable] = {
        alias: alias,
        patternTable: patternTable,
        sourceTable: sourceTable,
        isUnmapped: isUnmapped,
        changes: []
      }
      
      console.log(`[getChangesByTable] Table: ${patternTable} -> ${sourceTable} (alias: ${alias}, from LLM: ${!!change.alias})`)
    }
  }
  
  // Helper function to find ALL PATTERN TABLES for a column from pattern SQL
  // Returns array since a column can appear in multiple tables (e.g., b.ADR_STREET_1 AND a.ADR_STREET_1)
  const findAllPatternTablesForColumn = (columnName: string): string[] => {
    const foundTables: Set<string> = new Set()
    if (!suggestion.pattern_sql) return []
    
    // Look for patterns like "b.COLUMN_NAME" in the pattern SQL
    const escapedCol = columnName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const aliasColRegex = new RegExp(`(\\w{1,3})\\.${escapedCol}\\b`, 'gi')
    let match
    while ((match = aliasColRegex.exec(suggestion.pattern_sql)) !== null) {
      const alias = match[1].toLowerCase()
      const patternTable = aliasFromPatternSQL[alias]
      if (patternTable && groups[patternTable]) {
        foundTables.add(patternTable)
      }
    }
    
    // Also check for unaliased column in WHERE/subquery (like CDE_ADDR_USAGE in subquery)
    // If column appears without alias, check if it's inside a subquery for a specific table
    if (foundTables.size === 0) {
      // Check if column appears in a subquery for any table
      for (const [patternTable, info] of Object.entries(tableReplacements)) {
        const subqueryRegex = new RegExp(`\\(select[^)]*${escapedCol}[^)]*from\\s+[\\w.]*${patternTable.replace(/_/g, '[_]')}[^)]*\\)`, 'gi')
        if (subqueryRegex.test(suggestion.pattern_sql || '')) {
          foundTables.add(patternTable)
        }
      }
    }
    
    return Array.from(foundTables)
  }
  
  // Second pass: assign column changes to pattern table groups
  // Now using structured data from LLM (alias, pattern_table fields) if available
  for (const change of changes) {
    if (change.type === 'column_replace' || (change.original && change.new && change.type !== 'table_replace')) {
      const orig = change.original || ''
      const newVal = change.new || ''
      
      // Parse column names
      let origCol = orig.includes('.') ? orig.split('.').pop() || orig : orig
      let newCol = newVal.includes('.') ? newVal.split('.').pop() || newVal : newVal
      let newTable = newVal.includes('.') ? newVal.split('.')[0].toUpperCase() : ''
      
      // Find target pattern table(s) for this column
      let targetPatternTables: string[] = []
      
      // BEST: Use structured data from LLM if available
      if (change.pattern_table) {
        const pt = change.pattern_table.toUpperCase()
        if (groups[pt]) {
          targetPatternTables = [pt]
          console.log(`[getChangesByTable] Column ${origCol}: Using LLM-provided pattern_table: ${pt}`)
        }
      }
      
      // Option 1: If column has explicit alias prefix in original
      if (targetPatternTables.length === 0 && orig.includes('.')) {
        const alias = orig.split('.')[0].toLowerCase()
        const patternTable = aliasFromPatternSQL[alias]
        if (patternTable && groups[patternTable]) {
          targetPatternTables = [patternTable]
        }
      }
      
      // Option 2: Find ALL occurrences in pattern SQL
      if (targetPatternTables.length === 0) {
        targetPatternTables = findAllPatternTablesForColumn(origCol)
      }
      
      // Option 3: Infer from which pattern tables map to the source table in 'new'
      if (targetPatternTables.length === 0 && newTable) {
        for (const [patternTable, info] of Object.entries(tableReplacements)) {
          if (info.source === newTable && groups[patternTable]) {
            targetPatternTables.push(patternTable)
          }
        }
      }
      
      // Option 4: If still nothing, add to ALL groups (this column affects all tables)
      if (targetPatternTables.length === 0) {
        targetPatternTables = Object.keys(groups)
      }
      
      console.log(`[getChangesByTable] Column ${origCol} -> ${newCol} belongs to tables: ${targetPatternTables.join(', ')}`)
      
      // Add to ALL matching groups
      for (const patternTable of targetPatternTables) {
        if (groups[patternTable]) {
          groups[patternTable].changes.push({
            original: orig,
            originalColumn: origCol,
            new: newVal,
            newColumn: newCol,
            newTable: newTable || groups[patternTable].sourceTable
          })
        }
      }
    }
  }
  
  // If no groups were created (no table_replace changes), create a default one
  if (Object.keys(groups).length === 0) {
    const firstSourceTable = suggestion.suggested_source_expression?.match(/FROM\s+(\w+)/i)?.[1]?.toUpperCase() || 'Unknown'
    groups['default'] = {
      alias: 'main',
      patternTable: 'Source',
      sourceTable: firstSourceTable,
      changes: []
    }
    // Add all column changes to default group
    for (const change of changes) {
      if (change.type !== 'table_replace') {
        const orig = change.original || ''
        const newVal = change.new || ''
        groups['default'].changes.push({
          original: orig,
          originalColumn: orig.includes('.') ? orig.split('.').pop() || orig : orig,
          new: newVal,
          newColumn: newVal.includes('.') ? newVal.split('.').pop() || newVal : newVal,
          newTable: newVal.includes('.') ? newVal.split('.')[0].toUpperCase() : ''
        })
      }
    }
  }
  
  console.log('[getChangesByTable] Final groups:', Object.keys(groups), 'with changes:', Object.values(groups).map(g => g.changes.length))
  
  // Convert to array and sort by pattern table name
  return Object.values(groups).sort((a, b) => a.patternTable.localeCompare(b.patternTable))
}

function formatChange(change: any): string {
  // Handle different change formats from LLM
  if (change.original && change.new) {
    return `${change.original} → ${change.new}`
  }
  if (change.original && change.replacement) {
    return `${change.original} → ${change.replacement}`
  }
  if (change.type && change.original) {
    return `${change.type}: ${change.original}`
  }
  if (change.description) {
    return change.description
  }
  return String(change)
}

function isProblemChange(change: any): boolean {
  // Determine if this change indicates a problem that needs fixing
  const newVal = change.new || change.replacement || ''
  // Problem if: no replacement provided, or replacement contains placeholder/unknown
  return !newVal || 
         newVal.includes('?') || 
         newVal.toLowerCase().includes('unknown') ||
         newVal.toLowerCase().includes('user_') ||
         change.type === 'missing' ||
         change.type === 'not_found'
}

function isSystemColumnChange(change: any): boolean {
  // Check if this change involves a Gainwell system column
  const origCol = change.originalColumn || change.original || ''
  const newCol = change.newColumn || change.new || ''
  const colName = (origCol.includes('.') ? origCol.split('.').pop() : origCol) || ''
  return GAINWELL_SYSTEM_COLUMNS.has(colName.toUpperCase()) || 
         GAINWELL_SYSTEM_COLUMNS.has(newCol.toUpperCase())
}

function getChangeIcon(change: any): string {
  if (isProblemChange(change)) {
    return 'pi pi-exclamation-circle'
  }
  if (change.type === 'replaced' || change.new || change.replacement) {
    return 'pi pi-arrow-right-arrow-left'
  }
  return 'pi pi-info-circle'
}

function highlightInSQL(change: any) {
  if (!change.original || !sqlTextarea.value) return
  
  const sql = editedSQL.value
  const searchTerm = change.original
  const index = sql.toUpperCase().indexOf(searchTerm.toUpperCase())
  
  if (index >= 0) {
    // Select the text in the textarea
    const textarea = sqlTextarea.value.$el?.querySelector('textarea') || sqlTextarea.value
    if (textarea && textarea.setSelectionRange) {
      textarea.focus()
      textarea.setSelectionRange(index, index + searchTerm.length)
    }
  }
}

function highlightWarningField(warning: string) {
  if (!sqlTextarea.value) return
  
  // Extract field name from warning
  let searchTerm = ''
  
  // Try "for FIELD_NAME" pattern
  const forMatch = warning.match(/for\s+([A-Z][A-Z0-9_]+)/i)
  if (forMatch) {
    searchTerm = forMatch[1]
  }
  
  // Try quoted field name
  if (!searchTerm) {
    const quotedMatch = warning.match(/['"`]([A-Za-z_][A-Za-z0-9_]*)['"`]/)
    if (quotedMatch) {
      searchTerm = quotedMatch[1]
    }
  }
  
  if (!searchTerm) return
  
  const sql = editedSQL.value
  const index = sql.toUpperCase().indexOf(searchTerm.toUpperCase())
  
  if (index >= 0) {
    const textarea = sqlTextarea.value.$el?.querySelector('textarea') || sqlTextarea.value
    if (textarea && textarea.setSelectionRange) {
      textarea.focus()
      textarea.setSelectionRange(index, index + searchTerm.length)
    }
  }
}

function hasWarningsOrIssues(suggestion: MappingSuggestion): boolean {
  const warnings = getWarnings(suggestion)
  const confidence = suggestion.confidence_score || 0
  // Has issues if: warnings exist, low confidence, or no matched sources
  return warnings.length > 0 || confidence < 0.9 || !suggestion.matched_source_fields || suggestion.matched_source_fields === '[]'
}

async function handleAIAssist() {
  if (!aiPrompt.value) return
  
  aiGenerating.value = true
  try {
    // Get available column names for context
    const availableColumns = sourceFields.value.map(f => f.src_column_physical_name)
    
    const response = await fetch('/api/v4/suggestions/ai/assist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: aiPrompt.value,
        current_sql: editedSQL.value,
        target_column: editingSuggestion.value?.tgt_column_name,
        target_table: editingSuggestion.value?.tgt_table_name,
        available_columns: availableColumns
      })
    })
    
    if (response.ok) {
      const result = await response.json()
      if (result.success && result.sql) {
        editedSQL.value = result.sql
        toast.add({ 
          severity: 'success', 
          summary: 'SQL Updated', 
          detail: result.explanation || 'AI modified the SQL expression', 
          life: 3000 
        })
      } else {
        toast.add({ 
          severity: 'warn', 
          summary: 'AI Response', 
          detail: result.explanation || 'Could not modify SQL', 
          life: 4000 
        })
      }
    } else {
      const error = await response.json().catch(() => ({}))
      toast.add({ severity: 'error', summary: 'Error', detail: error.detail || 'Failed to call AI', life: 3000 })
    }
  } catch (e) {
    console.error('AI Assist error:', e)
    toast.add({ severity: 'error', summary: 'Error', detail: 'AI service unavailable', life: 3000 })
  } finally {
    aiGenerating.value = false
    showAIAssist.value = false
    aiPrompt.value = ''
  }
}

async function handleEditApprove() {
  if (!editingSuggestion.value || !editedSQL.value) return
  
  saving.value = true
  try {
    await projectsStore.editAndApproveSuggestion(
      editingSuggestion.value.suggestion_id,
      userStore.userEmail || 'unknown',
      editedSQL.value,
      editNotes.value || undefined
    )
    toast.add({ severity: 'success', summary: 'Saved', detail: 'Edited mapping created', life: 2000 })
    showEditDialog.value = false
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  } finally {
    saving.value = false
  }
}

function openRejectDialog(suggestion: MappingSuggestion) {
  rejectingSuggestion.value = suggestion
  rejectReason.value = ''
  showRejectDialog.value = true
}

async function handleReject() {
  if (!rejectingSuggestion.value || !rejectReason.value) return
  
  saving.value = true
  try {
    await projectsStore.rejectSuggestion(
      rejectingSuggestion.value.suggestion_id,
      userStore.userEmail || 'unknown',
      rejectReason.value
    )
    toast.add({ severity: 'info', summary: 'Rejected', detail: 'Feedback recorded', life: 2000 })
    showRejectDialog.value = false
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  } finally {
    saving.value = false
  }
}

async function handleSkip(suggestion: MappingSuggestion) {
  skippingId.value = suggestion.suggestion_id
  try {
    await projectsStore.skipSuggestion(suggestion.suggestion_id, userStore.userEmail || 'unknown')
    toast.add({ severity: 'info', summary: 'Skipped', detail: 'Column skipped', life: 2000 })
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  } finally {
    skippingId.value = null
  }
}

async function handleRegenerate(suggestion: MappingSuggestion) {
  try {
    regeneratingId.value = suggestion.suggestion_id
    await projectsStore.regenerateSuggestion(suggestion.suggestion_id)
    toast.add({ 
      severity: 'success', 
      summary: 'Regenerated', 
      detail: `AI rediscovery complete for ${suggestion.tgt_column_physical_name}`, 
      life: 3000 
    })
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Regeneration Failed', detail: e.message, life: 5000 })
  } finally {
    regeneratingId.value = null
  }
}

// Pattern Alternatives
async function showAlternatives(suggestion: MappingSuggestion) {
  alternativesSuggestion.value = suggestion
  showAlternativesDialog.value = true
  loadingAlternatives.value = true
  patternVariants.value = []
  
  try {
    const response = await fetch(`/api/v4/suggestions/${suggestion.suggestion_id}/alternatives`)
    if (!response.ok) throw new Error('Failed to load alternatives')
    const data = await response.json()
    patternVariants.value = data.variants || []
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
    showAlternativesDialog.value = false
  } finally {
    loadingAlternatives.value = false
  }
}

// Vector Search Candidates
async function showVSCandidates(suggestion: MappingSuggestion) {
  vsCandidatesSuggestion.value = suggestion
  showVSCandidatesDialog.value = true
  loadingVSCandidates.value = true
  vsCandidatesData.value = null
  
  try {
    const response = await fetch(`/api/v4/suggestions/${suggestion.suggestion_id}/vs-candidates`)
    if (!response.ok) throw new Error('Failed to load vector search candidates')
    const data = await response.json()
    
    // Backend now correctly marks was_selected using sql_changes
    // No need to recompute here - just use the data as-is
    vsCandidatesData.value = data
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
    showVSCandidatesDialog.value = false
  } finally {
    loadingVSCandidates.value = false
  }
}

// Helper: Get how many tables use a particular pattern column
function getColumnUsageCount(columnName: string): number {
  if (!vsCandidatesData.value?.column_usage) return 1
  const usages = vsCandidatesData.value.column_usage[columnName.toUpperCase()]
  return usages ? usages.length : 1
}

// Helper: Get all usages of a pattern column (which tables/aliases use it)
function getColumnUsages(columnName: string): any[] {
  if (!vsCandidatesData.value?.column_usage) return []
  return vsCandidatesData.value.column_usage[columnName.toUpperCase()] || []
}

// Helper: Get table name for an alias from alias_to_pattern_table (from join_metadata)
function getTableNameForAlias(alias: string): string {
  // First check alias_to_pattern_table (from join_metadata - most accurate)
  if (vsCandidatesData.value?.alias_to_pattern_table) {
    const tableName = vsCandidatesData.value.alias_to_pattern_table[alias.toLowerCase()]
    if (tableName) return tableName
  }
  // Fallback to changes_by_table
  if (vsCandidatesData.value?.changes_by_table) {
    const group = vsCandidatesData.value.changes_by_table[alias]
    if (group) {
      return group.pattern_table || group.source_table || '?'
    }
  }
  return '?'
}

async function useAlternativePattern(variant: any) {
  if (!alternativesSuggestion.value) return
  
  const patternId = variant.latest_pattern.mapped_field_id
  regeneratingWithPattern.value = patternId
  
  try {
    await projectsStore.regenerateSuggestion(
      alternativesSuggestion.value.suggestion_id,
      patternId
    )
    
    toast.add({ 
      severity: 'success', 
      summary: 'Pattern Applied', 
      detail: `Using ${variant.description} pattern`, 
      life: 3000 
    })
    
    showAlternativesDialog.value = false
    emit('suggestion-updated')
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message, life: 5000 })
  } finally {
    regeneratingWithPattern.value = null
  }
}

function truncateSql(sql: string, maxLen: number): string {
  if (!sql) return ''
  return sql.length > maxLen ? sql.substring(0, maxLen) + '...' : sql
}

function copySQL(sql: string) {
  navigator.clipboard.writeText(sql)
  toast.add({ severity: 'info', summary: 'Copied', detail: 'SQL copied to clipboard', life: 2000 })
}

function formatStatus(status: string): string {
  return status.replace(/_/g, ' ')
}

function getStatusSeverity(status: string): 'success' | 'info' | 'warning' | 'danger' | 'secondary' | 'contrast' {
  switch (status) {
    case 'APPROVED':
    case 'EDITED':
    case 'AUTO_MAPPED': return 'success'
    case 'SYSTEM_COLUMN': return 'contrast'  // Distinctive color for ETL system columns
    case 'PENDING': return 'warning'
    case 'REJECTED': return 'danger'
    case 'SKIPPED': return 'secondary'
    case 'NO_MATCH':
    case 'NO_PATTERN': return 'info'
    default: return 'secondary'
  }
}

function getConfidenceClass(score: number): string {
  if (score >= 0.8) return 'high'
  if (score >= 0.6) return 'medium'
  return 'low'
}

// Match score helper functions
function formatScore(score: number | undefined): string {
  if (score === undefined || score === null) return ''
  // Convert to percentage-like format (scores are typically 0.004-0.02)
  return (score * 100).toFixed(2) + '%'
}

function getScoreSeverity(score: number | undefined): string {
  if (!score) return 'secondary'
  if (score >= 0.01) return 'success'   // Good match
  if (score >= 0.006) return 'info'      // Decent match
  if (score >= 0.004) return 'warning'   // Weak match
  return 'danger'                         // Very weak
}

function getScoreClass(score: number | undefined): string {
  if (!score) return 'score-none'
  if (score >= 0.01) return 'score-high'
  if (score >= 0.006) return 'score-medium'
  if (score >= 0.004) return 'score-low'
  return 'score-poor'
}

function getScoreTooltip(field: { match_score?: number; src_comments?: string }): string {
  const score = field.match_score
  const desc = field.src_comments || 'No description'
  let quality = 'Unknown'
  if (score) {
    if (score >= 0.01) quality = 'High confidence match'
    else if (score >= 0.006) quality = 'Medium confidence match'
    else if (score >= 0.004) quality = 'Low confidence match'
    else quality = 'Very low confidence - review carefully'
  }
  return `${quality}\nScore: ${score ? (score * 100).toFixed(3) : 'N/A'}%\n${desc}`
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.suggestion-review-panel {
  max-height: 70vh;
  overflow-y: auto;
}

/* Summary Bar */
.summary-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  margin-bottom: 1rem;
  position: sticky;
  top: 0;
  z-index: 10;
}

.summary-stats {
  display: flex;
  gap: 2rem;
}

.summary-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-num {
  font-size: 1.5rem;
  font-weight: 600;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
}

.summary-stat.pending .stat-num { color: var(--orange-500); }
.summary-stat.approved .stat-num { color: var(--green-500); }
.summary-stat.rejected .stat-num { color: var(--red-500); }

.summary-actions {
  display: flex;
  gap: 0.5rem;
}

/* Loading */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  gap: 1rem;
}

/* Suggestions List */
.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.suggestion-card {
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 1rem;
  background: white;
  transition: all 0.2s;
}

.suggestion-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.suggestion-card.approved {
  border-left: 4px solid var(--green-500);
  background: #f1f8e9;
}

.suggestion-card.system-column {
  border-left: 4px solid var(--cyan-500);
  background: #e0f7fa;
}

.suggestion-card.rejected {
  border-left: 4px solid var(--red-500);
  opacity: 0.7;
}

.suggestion-card.skipped {
  border-left: 4px solid var(--surface-400);
  opacity: 0.6;
}

.suggestion-card.no-match {
  border-left: 4px solid var(--orange-500);
  background: #fff8e1;
}

/* Clean Card Header */
.suggestion-header-clean {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e0e0e0;
}

.column-info-clean {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.column-info-clean i {
  color: var(--gainwell-secondary);
  font-size: 1.1rem;
}

.column-info-clean strong {
  font-size: 1rem;
  color: var(--text-color);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.suggestion-description-clean {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  margin-bottom: 0.5rem;
  line-height: 1.4;
}

/* Compact AI Reasoning */
.ai-reasoning-compact {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  background: #f3e5f5;
  border-left: 3px solid #7c4dff;
  padding: 0.5rem 0.75rem;
  border-radius: 0 6px 6px 0;
  margin-bottom: 0.5rem;
}

.ai-reasoning-compact i {
  color: #ffc107;
  margin-top: 0.1rem;
}

.reasoning-text-compact {
  font-size: 0.8rem;
  color: #37474f;
  line-height: 1.4;
}

/* Compact Warnings */
.warnings-compact {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
}

.warning-item-compact {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  background: #fff3e0;
  border-left: 3px solid #ff9800;
  padding: 0.4rem 0.6rem;
  border-radius: 0 4px 4px 0;
  font-size: 0.8rem;
  color: #e65100;
}

.warning-item-compact i {
  color: #ff9800;
  font-size: 0.85rem;
  margin-top: 0.05rem;
}

/* Compact SQL Preview */
.sql-preview-compact {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  overflow: hidden;
}

.sql-header-compact {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.3rem 0.5rem;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}

.sql-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #616161;
  text-transform: uppercase;
}

.sql-code-compact {
  margin: 0;
  padding: 0.5rem;
  font-size: 0.75rem;
  font-family: 'Consolas', 'Monaco', monospace;
  color: #263238;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 80px;
  overflow-y: auto;
}

/* Status Messages */
.status-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.status-message.warning {
  background: #fff3e0;
  color: #e65100;
}

.status-message.info {
  background: #e3f2fd;
  color: #1565c0;
}

/* Legacy Card Header (keep for compatibility) */
.suggestion-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}

.column-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.column-info i {
  color: var(--gainwell-secondary);
  font-size: 1.25rem;
}

.column-names {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.column-names strong {
  color: var(--text-color);
}

.column-names .physical {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  font-family: monospace;
}

.suggestion-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.confidence-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.confidence-badge.high {
  background: #c8e6c9;
  color: #2e7d32;
}

.confidence-badge.medium {
  background: #ffe0b2;
  color: #e65100;
}

.confidence-badge.low {
  background: #ffcdd2;
  color: #c62828;
}

.suggestion-description {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

/* Pattern Info */
.pattern-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.pattern-label {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

/* Matched Sources */
.matched-sources {
  margin-bottom: 0.75rem;
}

.matched-sources h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.source-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
}

/* SQL Preview */
.sql-preview {
  margin-bottom: 0.75rem;
}

.sql-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sql-header h4 {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.sql-code {
  background: var(--surface-50);
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 0.75rem;
  font-family: monospace;
  font-size: 0.85rem;
  overflow-x: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 150px;
  overflow-y: auto;
}

/* Messages */
.no-match-message,
.no-pattern-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

.no-match-message {
  background: #fff3e0;
  color: #e65100;
}

.no-pattern-message {
  background: #e3f2fd;
  color: #1565c0;
}

/* AI Reasoning */
.ai-reasoning {
  background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
  border: 1px solid #7c4dff;
  border-radius: 8px;
  padding: 0.75rem;
  margin-bottom: 0.75rem;
}

.reasoning-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #5e35b1;
  font-weight: 600;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.reasoning-header i {
  color: #ffc107;
}

.reasoning-text {
  margin: 0;
  font-size: 0.85rem;
  color: #37474f;
  line-height: 1.5;
}

/* Source field with score */
.source-field-with-score {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-right: 0.5rem;
  margin-bottom: 0.35rem;
}

.match-score {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}

.score-high {
  background: #c8e6c9;
  color: #2e7d32;
}

.score-medium {
  background: #bbdefb;
  color: #1565c0;
}

.score-low {
  background: #fff3e0;
  color: #ef6c00;
}

.score-poor {
  background: #ffcdd2;
  color: #c62828;
}

.score-none {
  background: #f5f5f5;
  color: #757575;
}

/* Enhanced Warnings Panel */
.warnings-panel {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border: 2px solid #ff9800;
  border-radius: 8px;
  padding: 0.75rem;
  margin-bottom: 0.75rem;
}

.warnings-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 0.9rem;
  color: #e65100;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #ffcc80;
}

.warnings-header i {
  font-size: 1.1rem;
}

.warnings-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.warning-item-enhanced {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: white;
  color: #bf360c;
  border-radius: 6px;
  font-size: 0.85rem;
  border-left: 3px solid #ff5722;
}

.warning-item-enhanced i {
  color: #ff5722;
  margin-top: 0.1rem;
}

.warning-text {
  flex: 1;
  line-height: 1.4;
}

/* Legacy warnings (keep for backwards compat) */
.warnings {
  margin-bottom: 0.75rem;
}

.warning-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #fff3e0;
  color: #e65100;
  border-radius: 4px;
  font-size: 0.85rem;
  margin-bottom: 0.35rem;
}

/* Actions */
.suggestion-actions {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
  padding-top: 0.5rem;
  margin-top: 0.5rem;
  border-top: 1px solid #eeeeee;
}

/* Reviewed Info */
.reviewed-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-border);
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  gap: 0.75rem;
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

/* Enhanced Edit Dialog */
.edit-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.edit-header {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  border-left: 4px solid var(--primary-color);
}

.target-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.target-info .datatype {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.target-description {
  margin-top: 0.5rem;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

/* NEW: Three-column layout v2 */
.edit-columns-v2 {
  display: flex;
  gap: 1rem;
  min-height: 500px;
}

/* Left Panel - Collapsible */
.left-panel {
  width: 300px;
  min-width: 300px;
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  background: var(--surface-50);
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  overflow: hidden;
}

.left-panel.collapsed {
  width: 40px;
  min-width: 40px;
}

.panel-toggle {
  padding: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  background: var(--surface-100);
  border-bottom: 1px solid var(--surface-border);
  font-weight: 500;
  font-size: 0.85rem;
  transition: background 0.2s;
}

.panel-toggle:hover {
  background: var(--surface-200);
}

.left-panel.collapsed .panel-toggle {
  justify-content: center;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  padding: 1rem 0.5rem;
  height: 100%;
}

.left-panel-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* Changes Section */
.changes-section {
  border-bottom: 1px solid var(--surface-border);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  cursor: pointer;
  background: var(--surface-100);
  transition: background 0.15s;
}

.section-header:hover {
  background: var(--surface-200);
}

.section-header > i:first-child {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
}

.section-header h4 {
  margin: 0;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--primary-color);
  flex: 1;
}

.changes-section h4 {
  margin: 0;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--primary-color);
}

.change-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.5rem 0.75rem 0.75rem;
}

.change-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem;
  background: white;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid var(--surface-200);
}

.change-item:hover {
  background: var(--primary-50);
  border-color: var(--primary-200);
}

.change-item.is-problem {
  background: #fff3e0;
  border-color: var(--orange-200);
}

.change-item.is-problem i {
  color: var(--orange-500);
}

.change-item.is-warning {
  background: #fff8e1;
  border-color: var(--yellow-300);
}

.change-item.is-warning i {
  color: var(--yellow-700);
}

.change-item.is-system {
  background: #e0f2f1;
  border-color: #26a69a;
}

.change-item.is-system i {
  color: #00695c;
}

.system-badge {
  font-size: 0.6rem;
  background: #26a69a;
  color: white;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  margin-left: 0.25rem;
  font-weight: 600;
  text-transform: uppercase;
}

.change-item i {
  color: var(--primary-color);
  margin-top: 2px;
}

.change-detail {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
}

.change-original {
  font-family: monospace;
  background: #ffcdd2;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  color: #c62828;
  text-decoration: line-through;
}

.change-detail .pi-arrow-right {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
}

.change-new {
  font-family: monospace;
  background: #c8e6c9;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  color: #2e7d32;
}

/* Table Change Header - groups changes by source table */
.table-change-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem;
  padding: 0.5rem 0.5rem;
  background: var(--surface-100);
  border-radius: 6px;
  margin-top: 0.5rem;
  font-size: 0.8rem;
  border-left: 3px solid var(--primary-color);
}

.table-change-header:first-child {
  margin-top: 0;
}

.table-change-header i.pi-database {
  color: var(--primary-color);
  flex-shrink: 0;
}

.table-change-header i.pi-arrow-right {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
  flex-shrink: 0;
}

.table-badge-original,
.table-badge-new {
  font-family: monospace;
  font-size: 0.65rem;
  max-width: 100%;
  word-break: break-all;
  white-space: normal;
  text-align: left;
  line-height: 1.2;
}

.alias-label {
  color: var(--text-color-secondary);
  font-size: 0.7rem;
  font-style: italic;
}

/* Unmapped table styling - tables that couldn't be matched to source */
.table-change-header.is-unmapped {
  border-left: 3px solid #f57c00;
  background: #fff3e0;
}

.table-change-header.is-unmapped i.pi-database {
  color: #f57c00;
}

.unmapped-tag {
  margin-left: 0.25rem;
}

/* Grouped change items have left indent */
.change-item.grouped-change {
  margin-left: 1rem;
  border-left: 2px solid var(--surface-200);
}

/* Source Section */
.source-section {
  flex: 1;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.source-section h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.source-filter {
  width: 100%;
  margin-bottom: 0.5rem;
}

.source-tables {
  flex: 1;
  overflow-y: auto;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: white;
}

.source-table-group {
  border-bottom: 1px solid var(--surface-100);
}

.source-table-group:last-child {
  border-bottom: none;
}

.table-header {
  padding: 0.5rem 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  transition: background 0.15s;
}

.table-header:hover {
  background: var(--surface-50);
}

.table-header i {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
}

.table-header strong {
  flex: 1;
  font-size: 0.8rem;
}

.table-columns {
  padding: 0 0.25rem 0.25rem;
}

.column-item {
  padding: 0.35rem 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
  font-size: 0.8rem;
}

.column-item:hover {
  background: var(--primary-50);
}

.column-item.matched {
  background: var(--green-50);
  border-left: 3px solid var(--green-500);
}

.col-name {
  flex: 1;
  font-family: monospace;
  font-size: 0.8rem;
}

.col-type {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
}

.matched-icon {
  color: var(--green-500);
  font-size: 0.75rem;
}

/* SQL Panel V2 */
.sql-panel-v2 {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 0;
}

.sql-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sql-header label {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sql-actions {
  display: flex;
  gap: 0.35rem;
}

.ai-assist-btn {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  color: white !important;
  border: none !important;
  box-shadow: 0 2px 4px rgba(99, 102, 241, 0.3) !important;
}

.ai-assist-btn:hover {
  background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
  box-shadow: 0 4px 8px rgba(99, 102, 241, 0.4) !important;
}

:deep(.ai-assist-btn) {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  color: white !important;
  border: none !important;
}

:deep(.ai-assist-btn:hover) {
  background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
}

/* Original SQL Section (Pattern with highlights) */
.original-sql-section {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fafafa;
  overflow: hidden;
  margin-bottom: 1rem;
}

.original-sql-section.has-problems {
  border: 2px solid #ff9800;
}

.original-sql-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
  cursor: pointer;
}

.original-sql-header:hover {
  background: #eeeeee;
}

.original-sql-header .header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.original-sql-header .section-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: #616161;
  text-transform: uppercase;
}

.original-sql-header .toggle-icon {
  font-size: 0.75rem;
  color: #9e9e9e;
}

.change-legend {
  display: flex;
  gap: 1rem;
  font-size: 0.7rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.legend-item .dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.legend-item.success .dot {
  background: #2196f3;
}

.legend-item.warning .dot {
  background: #ff9800;
}

.legend-item.system .dot {
  background: #26a69a;
}

.sql-original-highlighted {
  padding: 0.75rem;
  margin: 0;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.8rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  background: white;
  max-height: 200px;
  overflow-y: auto;
}

/* Highlights for original SQL */
.sql-original-highlighted :deep(.original-changed) {
  background: #bbdefb;
  color: #0d47a1;
  padding: 0.1rem 0.2rem;
  border-radius: 3px;
  font-weight: 600;
  border: 1px solid #64b5f6;
}

.sql-original-highlighted :deep(.original-no-match) {
  background: #ffe0b2;
  color: #e65100;
  padding: 0.1rem 0.2rem;
  border-radius: 3px;
  font-weight: 600;
  border: 1px solid #ff9800;
}

/* System columns - Gainwell ETL columns expected in bronze tables */
.sql-original-highlighted :deep(.system-column),
.sql-edited-highlighted :deep(.system-column) {
  background: #e0f2f1;
  color: #00695c;
  padding: 0.1rem 0.2rem;
  border-radius: 3px;
  font-weight: 600;
  border: 1px solid #26a69a;
}

/* New SQL Section */
.new-sql-section {
  border: 1px solid #424242;
  border-radius: 8px;
  overflow: hidden;
  background: #263238;
}

.new-sql-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0.75rem;
  background: #37474f;
  border-bottom: 1px solid #546e7a;
}

.new-sql-header .section-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: #b0bec5;
  text-transform: uppercase;
}

.new-sql-section .sql-editor-container {
  padding: 0;
}

.new-sql-section .sql-editor-v2 {
  background: #263238 !important;
  color: #eceff1 !important;
  border: none !important;
  border-radius: 0 !important;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.8rem;
}

/* Legacy: Highlighted SQL Preview (keep for compatibility) */
.sql-preview-highlighted {
  border: 1px solid var(--surface-300);
  border-radius: 8px;
  background: var(--surface-50);
  overflow: hidden;
}

.sql-preview-highlighted.has-problems {
  border: 2px solid var(--orange-300);
  background: #fffbf5;
}

.preview-label {
  padding: 0.5rem 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  font-weight: 500;
}

.preview-label.warning {
  background: var(--orange-100);
  color: var(--orange-700);
}

.preview-label.info {
  background: var(--blue-50);
  color: var(--blue-700);
}

.preview-label.clickable {
  cursor: pointer;
  transition: background 0.15s;
}

.preview-label.clickable:hover {
  filter: brightness(0.95);
}

.preview-label .toggle-icon {
  font-size: 0.7rem;
  margin-right: 0.25rem;
}

.sql-preview-highlighted.collapsed {
  border-radius: 8px;
}

.sql-highlighted {
  padding: 0.75rem;
  margin: 0;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.85rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 150px;
  overflow-y: auto;
  background: white;
}

.sql-highlighted :deep(.problem-field) {
  background: #ffeb3b;
  color: #c62828;
  padding: 0.1rem 0.25rem;
  border-radius: 3px;
  font-weight: 600;
  border: 1px solid #ff9800;
  animation: pulse-highlight 2s infinite;
}

@keyframes pulse-highlight {
  0%, 100% { background: #ffeb3b; }
  50% { background: #ffc107; }
}

.sql-highlighted :deep(.sql-keyword) {
  color: #1565c0;
  font-weight: 600;
}

.sql-highlighted :deep(.sql-string) {
  color: #2e7d32;
}

.sql-highlighted :deep(.sql-placeholder) {
  color: #7b1fa2;
  font-weight: 500;
  background: #f3e5f5;
  padding: 0.1rem 0.2rem;
  border-radius: 3px;
}

.sql-highlighted :deep(.sql-alias) {
  color: #0097a7;
  font-weight: 500;
}

.sql-highlighted :deep(.sql-column) {
  color: #455a64;
}

/* SQL Editor Container */
.sql-editor-container {
  flex: 1;
  min-height: 300px;
}

.sql-editor-v2 {
  font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
  font-size: 0.9rem;
  background: #1e1e1e !important;
  color: #d4d4d4 !important;
  border-radius: 8px;
  height: 100%;
  resize: vertical;
}

/* Matched Summary Compact */
.matched-summary-compact {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--green-50);
  border-radius: 6px;
  border: 1px solid var(--green-200);
}

.matched-label {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--green-700);
  display: flex;
  align-items: center;
  gap: 0.35rem;
  white-space: nowrap;
}

.matched-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
  flex: 1;
}

.view-alternatives-btn {
  margin-left: auto;
  flex-shrink: 0;
}

/* Notes Row */
.notes-row {
  margin-top: auto;
}

/* Legacy compatibility */
.edit-columns {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1.5rem;
  min-height: 400px;
}

.source-panel {
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 0.75rem;
  background: var(--surface-100);
  border-bottom: 1px solid var(--surface-border);
}

.panel-header h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sql-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.pattern-changes {
  padding: 0.5rem 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
  border: 1px solid var(--surface-border);
}

.changes-inline {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.changes-label {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  gap: 0.35rem;
  white-space: nowrap;
}

.changes-label i {
  font-size: 0.9rem;
}

.changes-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.sql-editor-section {
  flex: 1;
}

.sql-editor {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.9rem;
  background: var(--surface-900);
  color: var(--surface-50);
  border-radius: 8px;
}

.matched-summary {
  padding: 0.75rem;
  background: var(--green-50);
  border-radius: 6px;
  border: 1px solid var(--green-200);
}

.matched-summary h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  color: var(--green-700);
}

/* AI Assist Dialog */
.ai-assist-content p {
  margin: 0 0 1rem 0;
  color: var(--text-color-secondary);
}

/* Reject Dialog */
.reject-dialog-content p {
  margin: 0 0 1rem 0;
  color: var(--text-color-secondary);
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

.w-full {
  width: 100%;
}

/* Pattern Alternatives Dialog */
.loading-alternatives {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  gap: 1rem;
}

.alternatives-intro {
  margin: 0 0 1.5rem 0;
  color: var(--text-color-secondary);
}

.variant-card {
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  transition: border-color 0.2s;
}

.variant-card:hover {
  border-color: var(--primary-color);
}

.variant-card.is-current {
  border-color: var(--green-500);
  background: var(--green-50);
}

.variant-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

.variant-transforms {
  flex: 1;
  font-weight: 500;
  color: var(--text-color);
}

.variant-meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  margin-bottom: 0.75rem;
}

.variant-meta i {
  margin-right: 0.25rem;
}

.variant-sql-preview {
  background: var(--surface-100);
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  margin-bottom: 0.75rem;
  overflow-x: auto;
}

.variant-sql-preview code {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.8rem;
  color: var(--primary-700);
  white-space: pre-wrap;
  word-break: break-word;
}

/* Matched Sources Header */
.matched-sources-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.matched-sources-header h4 {
  margin: 0;
}

/* VS Candidates Dialog */
.vs-candidates-content {
  max-height: 60vh;
  overflow-y: auto;
}

.vs-candidates-intro {
  margin: 0 0 1.5rem 0;
  color: var(--text-color-secondary);
}

.no-candidates-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--surface-100);
  border-radius: 6px;
  color: var(--text-color-secondary);
}

/* Table Mappings Section */
.table-mappings-section {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  border: 1px solid var(--surface-border);
}

.table-mappings-section h4 {
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.table-mappings-list {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.table-mapping-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--surface-0);
  border-radius: 6px;
  border: 1px solid var(--surface-200);
}

.pattern-table-badge {
  font-family: monospace;
  font-size: 0.75rem;
}

.source-table-badge {
  font-family: monospace;
  font-size: 0.75rem;
}

.alias-indicator {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  font-style: italic;
}

.pattern-table {
  font-family: monospace;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.candidates-by-column {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.candidates-by-column h4 {
  margin: 0 0 1rem 0;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.column-candidates {
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  overflow: hidden;
}

.column-candidates-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--surface-100);
  border-bottom: 1px solid var(--surface-border);
}

.column-candidates-header .original-column-badge {
  font-family: monospace;
  font-weight: 600;
}

.column-candidates-header .usage-count {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  font-style: italic;
}

.column-candidates-header .count-badge {
  margin-left: auto;
}

/* Column Usage - shows per-table replacements */
.column-usages {
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-border);
  padding: 0.5rem 1rem;
}

.column-usage-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0;
  font-size: 0.8rem;
}

.column-usage-item .usage-table {
  color: var(--text-color-secondary);
  min-width: 100px;
}

.column-usage-item .original-badge {
  font-family: monospace;
  font-size: 0.7rem;
}

.column-usage-item .selected-badge {
  font-family: monospace;
  font-size: 0.7rem;
}

.column-usage-item .pi-arrow-right {
  font-size: 0.6rem;
  color: var(--text-color-secondary);
}

.candidates-list {
  max-height: 250px;
  overflow-y: auto;
}

.candidate-item {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-border);
  transition: background 0.15s;
}

.candidate-item:last-child {
  border-bottom: none;
}

.candidate-item:hover {
  background: var(--surface-50);
}

.candidate-item.was-selected {
  background: var(--green-50);
  border-left: 3px solid var(--green-500);
}

.candidate-main {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.candidate-column {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--primary-700);
}

.candidate-score {
  margin-left: auto;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.candidate-meta {
  margin-top: 0.35rem;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  padding-left: 0.25rem;
}
</style>


