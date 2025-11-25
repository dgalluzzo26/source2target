# Source-to-Target Mapping Platform V2 - Implementation Plan

## 📋 Current Status

✅ **COMPLETED**: Database schema and migration scripts
- Created 6 new database tables with full DDL
- Created comprehensive migration guide
- Created data migration script with validation
- Created visual schema diagrams
- All committed to git

## 🎯 Overview

This document outlines the complete implementation plan for V2, which adds support for:
- **Multi-source mapping** (multiple source fields → single target field)
- **Field ordering** (drag-and-drop for concatenation order)
- **Concatenation strategies** (SPACE, COMMA, PIPE, CONCAT, CUSTOM)
- **Per-field transformations** (TRIM, UPPER, LOWER, FORMAT_SSN, etc.)
- **Feedback capture** (track ACCEPTED/REJECTED/MODIFIED suggestions)
- **Domain classification** (claims, member, provider, finance, pharmacy)

---

## 📊 Implementation Phases

### Phase 1: Database Migration ✅ COMPLETE
**Status**: Scripts created, documentation complete, ready to run in Databricks

**Files**:
- `database/migration_v2_schema.sql` - Creates V2 tables
- `database/migration_v2_data.sql` - Migrates V1 → V2
- `database/V2_MIGRATION_GUIDE.md` - Comprehensive guide
- `database/V2_SCHEMA_DIAGRAM.md` - Visual documentation
- `database/README.md` - Quick reference

**Next Step**: Review and run in Databricks

---

### Phase 2: Backend Updates (Python/FastAPI)
**Status**: Not started

#### 2.1 Update Pydantic Models

**Files to Update**:

1. **`backend/models/semantic.py`**
   - Add `domain` field to `SemanticRecord`
   - Update field descriptions

2. **`backend/models/mapping.py`**
   - Create `MappedFieldV2` model (replaces `MappedField`)
     - Add: `concat_strategy`, `concat_separator`, `transformation_expression`
     - Add: `mapping_status`, `mapped_by`, `mapped_ts`
   - Create `MappingDetail` model (NEW)
     - Fields: `src_table`, `src_column`, `field_order`, `transformations`, `default_value`
   - Create `UnmappedFieldV2` model (similar to V1, add `domain`)
   - Create `MappingFeedback` model (NEW)
     - Fields: `feedback_action`, `user_comments`, `suggested_*`, `modified_*`
   - Create `Transformation` model (NEW)
     - Fields: `transformation_name`, `transformation_code`, `transformation_expression`, `category`

**Estimated Effort**: 2-3 hours

---

#### 2.2 Update Services

**Files to Update**:

1. **`backend/services/semantic_service.py`**
   - Update queries to use `semantic_fields` table (was `semantic_table`)
   - Add domain filtering support
   - No major logic changes (CRUD remains the same)

2. **`backend/services/mapping_service.py`** (MAJOR CHANGES)
   - **Update `get_all_mapped_fields()`**:
     - Query `mapped_fields` + JOIN `mapping_details`
     - Return nested structure: mapped_field with array of details
   - **Update `get_all_unmapped_fields()`**:
     - Query `unmapped_fields` table (was filtering `combined_fields`)
     - Add domain filtering
   - **Update `save_manual_mapping()`** (MAJOR):
     - Accept array of source fields (not just one)
     - Insert into `mapped_fields` (one record)
     - Insert into `mapping_details` (multiple records)
     - Build `transformation_expression` from concat strategy + transformations
     - Remove mapped fields from `unmapped_fields`
   - **Update `apply_bulk_mappings()`**:
     - Support V2 schema
   - **Add `update_mapping()`** (NEW):
     - Allow editing existing mappings (change order, add/remove fields)
   - **Add `delete_mapping_detail()`** (NEW):
     - Remove a source field from a multi-field mapping

3. **`backend/services/ai_mapping_service.py`**
   - **Update `generate_ai_suggestions()`**:
     - Support domain filtering in vector search
     - Suggest multiple source fields for one target (advanced feature)
   - **Add `record_feedback()`** (NEW):
     - Insert into `mapping_feedback` table
     - Track ACCEPTED/REJECTED/MODIFIED with user comments

4. **Create `backend/services/transformation_service.py`** (NEW)
   - **`get_all_transformations()`**: Query `transformation_library`
   - **`get_transformations_by_category(category)`**: Filter by TEXT/DATE/NUMERIC
   - **`create_transformation()`**: Add custom transformation
   - **`build_transformation_expression(fields, transformations, concat_strategy)`**:
     - Build SQL expression from selected fields + transformations + concat strategy
     - Example: `CONCAT(TRIM(UPPER(field1)), ' ', TRIM(LOWER(field2)))`

**Estimated Effort**: 8-12 hours

---

#### 2.3 Update API Endpoints

**Files to Update**:

1. **`backend/routers/semantic.py`**
   - Add `domain` query parameter to GET endpoints
   - No major changes

2. **`backend/routers/mapping.py`** (MAJOR CHANGES)
   - **Update `GET /api/mappings/mapped`**:
     - Return nested structure (mapped_fields with details array)
   - **Update `POST /api/mappings/manual`**:
     - Accept array of source fields (not just one)
     - Accept `concat_strategy`, `transformations` per field
   - **Add `PUT /api/mappings/{mapped_field_id}`** (NEW):
     - Update existing mapping (reorder fields, change transformations)
   - **Add `DELETE /api/mappings/details/{detail_id}`** (NEW):
     - Remove a source field from mapping
   - **Add `POST /api/mappings/feedback`** (NEW):
     - Record user feedback on AI suggestions

3. **Create `backend/routers/transformation.py`** (NEW)
   - **`GET /api/transformations`**: Get all transformations
   - **`GET /api/transformations/categories/{category}`**: Filter by category
   - **`POST /api/transformations`**: Create custom transformation
   - **`POST /api/transformations/preview`**: Preview transformation result

4. **`backend/app.py`**
   - Register new transformation router

**Estimated Effort**: 4-6 hours

---

#### 2.4 Update Configuration

**Files to Update**:

1. **`backend/config/default_config.json`**
   ```json
   {
     "database": {
       "semantic_table": "semantic_fields",
       "unmapped_fields_table": "unmapped_fields",
       "mapped_fields_table": "mapped_fields",
       "mapping_details_table": "mapping_details",
       "feedback_table": "mapping_feedback",
       "transformation_library_table": "transformation_library"
     }
   }
   ```

2. **`backend/models/config.py`**
   - Update `DatabaseConfig` model with new table names

**Estimated Effort**: 30 minutes

---

### Phase 3: Frontend Updates (Vue.js/TypeScript)
**Status**: Not started

#### 3.1 Update Store/State Management

**Files to Update**:

1. **`frontend/src/stores/mappingStore.ts`** (MAJOR CHANGES)
   - Update types to match V2 API responses
   - Add `selectedSourceFields: SourceField[]` (array, not single)
   - Add `concatStrategy: string` (NONE, SPACE, COMMA, PIPE, CUSTOM)
   - Add `customSeparator: string`
   - Add `fieldTransformations: Map<string, string[]>` (transformations per field)
   - Update `saveManualMapping()` to send array of fields
   - Add `updateMappingOrder(mappedFieldId, newOrder)` (NEW)
   - Add `removeMappingDetail(detailId)` (NEW)
   - Add `recordFeedback(feedback)` (NEW)

2. **Create `frontend/src/stores/transformationStore.ts`** (NEW)
   - `transformations: Transformation[]`
   - `fetchTransformations()` - Load from API
   - `getTransformationsByCategory(category)` - Filter by TEXT/DATE/NUMERIC
   - `previewTransformation(field, transformations)` - Show preview

**Estimated Effort**: 3-4 hours

---

#### 3.2 Update Views

**Files to Update**:

1. **`frontend/src/views/MappingView.vue`** (MAJOR CHANGES)

   **Current**: Single source field selection
   **V2**: Multi-field selection with ordering

   **New Features**:
   - Multi-select for source fields (with checkboxes)
   - Draggable list for field ordering (use `vue-draggable-next`)
   - Concatenation strategy dropdown (NONE, SPACE, COMMA, PIPE, CUSTOM)
   - Custom separator input (if CUSTOM selected)
   - Per-field transformation dropdown (populated from transformation store)
   - Live transformation preview panel
   - Feedback capture dialog for AI suggestions

   **New Components Needed**:
   - `SourceFieldSelector.vue` (multi-select with search)
   - `FieldOrderingPanel.vue` (draggable list)
   - `TransformationPicker.vue` (per-field dropdown)
   - `TransformationPreview.vue` (shows final SQL expression)
   - `FeedbackDialog.vue` (ACCEPTED/REJECTED/MODIFIED with comments)

   **Layout**:
   ```
   +------------------------------------------------------------------+
   |  Target Field: [slv_member.full_name ▼]                         |
   +------------------------------------------------------------------+
   |  Source Fields:                                                  |
   |  +------------------------------------------------------------+  |
   |  | [✓] T_MEMBER.FIRST_NAME    [Transformations: TRIM, INITCAP] |
   |  | [✓] T_MEMBER.LAST_NAME     [Transformations: TRIM, INITCAP] |
   |  | [ ] T_MEMBER.MIDDLE_NAME   [Transformations: None ▼]         |
   |  +------------------------------------------------------------+  |
   |                                                                  |
   |  Field Order: (drag to reorder)                                 |
   |  +------------------------------------------------------------+  |
   |  | ☰ 1. FIRST_NAME  [TRIM, INITCAP]  [Remove]                  |
   |  | ☰ 2. LAST_NAME   [TRIM, INITCAP]  [Remove]                  |
   |  +------------------------------------------------------------+  |
   |                                                                  |
   |  Concatenation: [SPACE ▼]  Custom Separator: [    ]            |
   |                                                                  |
   |  Preview:                                                        |
   |  +------------------------------------------------------------+  |
   |  | CONCAT(INITCAP(TRIM(T_MEMBER.FIRST_NAME)), ' ',             |
   |  |        INITCAP(TRIM(T_MEMBER.LAST_NAME)))                   |
   |  +------------------------------------------------------------+  |
   |                                                                  |
   |  [Save Mapping]  [Cancel]                                       |
   +------------------------------------------------------------------+
   ```

2. **`frontend/src/views/SemanticView.vue`**
   - Add `domain` field to create/edit forms
   - Add domain filter dropdown
   - Update table to show domain column

**Estimated Effort**: 12-16 hours

---

#### 3.3 Create New Components

**New Components**:

1. **`frontend/src/components/SourceFieldSelector.vue`**
   - Multi-select dropdown with search/filter
   - Shows: src_table.src_column, src_data_type, src_comments
   - Emits: `@select` event with selected fields

2. **`frontend/src/components/FieldOrderingPanel.vue`**
   - Draggable list of selected source fields
   - Show field order number, transformations
   - Emit: `@reorder` event when order changes
   - Emit: `@remove` event when field removed

3. **`frontend/src/components/TransformationPicker.vue`**
   - Dropdown grouped by category (TEXT, DATE, NUMERIC)
   - Multi-select (can apply multiple transformations)
   - Show transformation expression in tooltip
   - Emit: `@change` event with selected transformation codes

4. **`frontend/src/components/TransformationPreview.vue`**
   - Read-only text area showing final SQL expression
   - Syntax highlighting (optional)
   - Copy to clipboard button

5. **`frontend/src/components/FeedbackDialog.vue`**
   - Radio buttons: ACCEPTED, REJECTED, MODIFIED
   - Text area for user comments (required if REJECTED)
   - If MODIFIED: Show what changed (auto-populated)
   - Emit: `@submit` event with feedback data

6. **`frontend/src/components/MappingDetailsCard.vue`**
   - Expandable card showing all source fields for a mapping
   - Show field order, transformations, confidence per field
   - Edit/Delete buttons

**Estimated Effort**: 10-12 hours

---

#### 3.4 Update Types

**Files to Update**:

1. **`frontend/src/types/mapping.ts`**
   ```typescript
   export interface MappedFieldV2 {
     mapped_field_id: number;
     semantic_field_id: number;
     tgt_table: string;
     tgt_column: string;
     concat_strategy: 'NONE' | 'SPACE' | 'COMMA' | 'PIPE' | 'CONCAT' | 'CUSTOM';
     concat_separator?: string;
     transformation_expression: string;
     confidence_score?: number;
     mapping_source: 'AI' | 'MANUAL' | 'BULK_UPLOAD' | 'SYSTEM';
     ai_reasoning?: string;
     mapping_status: 'ACTIVE' | 'INACTIVE' | 'PENDING_REVIEW';
     details: MappingDetail[];
     mapped_by?: string;
     mapped_ts?: string;
   }

   export interface MappingDetail {
     mapping_detail_id: number;
     mapped_field_id: number;
     src_table: string;
     src_column: string;
     field_order: number;
     transformations?: string;
     default_value?: string;
     field_confidence_score?: number;
   }

   export interface MappingFeedback {
     suggested_src_table: string;
     suggested_src_column: string;
     suggested_tgt_table: string;
     suggested_tgt_column: string;
     ai_confidence_score?: number;
     ai_reasoning?: string;
     vector_search_score?: number;
     suggestion_rank?: number;
     feedback_action: 'ACCEPTED' | 'REJECTED' | 'MODIFIED';
     user_comments?: string;
     modified_src_table?: string;
     modified_src_column?: string;
     modified_transformations?: string;
   }
   ```

2. **Create `frontend/src/types/transformation.ts`** (NEW)
   ```typescript
   export interface Transformation {
     transformation_id: number;
     transformation_name: string;
     transformation_code: string;
     transformation_expression: string;
     transformation_description?: string;
     category: 'TEXT' | 'DATE' | 'NUMERIC' | 'CUSTOM';
     is_system: boolean;
   }
   ```

**Estimated Effort**: 1-2 hours

---

#### 3.5 Update Dependencies

**Files to Update**:

1. **`frontend/package.json`**
   - Add `vue-draggable-next` for drag-and-drop field ordering
   ```bash
   npm install vue-draggable-next
   ```

**Estimated Effort**: 15 minutes

---

### Phase 4: Testing & Validation
**Status**: Not started

#### 4.1 Backend Testing

**Test Cases**:
1. Create simple 1:1 mapping (V1 compatible)
2. Create multi-field mapping with 2 fields
3. Create multi-field mapping with 3+ fields
4. Test all concatenation strategies (NONE, SPACE, COMMA, PIPE, CUSTOM)
5. Test per-field transformations
6. Test field reordering
7. Test removing a field from mapping
8. Test feedback capture (ACCEPTED/REJECTED/MODIFIED)
9. Test transformation library queries
10. Test domain filtering

**Estimated Effort**: 4-6 hours

---

#### 4.2 Frontend Testing

**Test Cases**:
1. Select multiple source fields
2. Drag-and-drop to reorder fields
3. Change concatenation strategy
4. Apply transformations to fields
5. Preview transformation expression
6. Save multi-field mapping
7. Edit existing mapping (add/remove/reorder fields)
8. Accept AI suggestion
9. Reject AI suggestion with comments
10. Modify AI suggestion
11. Filter by domain

**Estimated Effort**: 4-6 hours

---

#### 4.3 Integration Testing

**Test Cases**:
1. End-to-end: Unmapped field → AI suggestion → Accept → Mapped
2. End-to-end: Unmapped field → Manual multi-field mapping → Save
3. End-to-end: Edit mapping → Reorder fields → Save → Verify in DB
4. End-to-end: Create custom transformation → Use in mapping → Verify expression
5. Vector search with domain filtering

**Estimated Effort**: 3-4 hours

---

### Phase 5: Documentation & Training
**Status**: Not started

#### 5.1 Update Documentation

**Files to Update**:
1. **`README.md`** - Add V2 features
2. **`frontend/public/help/user_guide.html`** - Update with multi-field mapping instructions
3. **`frontend/public/help/admin-config-help.html`** - Update with transformation library
4. **Create `frontend/public/help/multi_field_mapping_demo.html`** - Interactive demo

**Estimated Effort**: 3-4 hours

---

#### 5.2 Create User Training Materials

**Materials Needed**:
1. Video walkthrough: Creating multi-field mapping
2. Video walkthrough: Using transformations
3. Video walkthrough: Providing feedback on AI suggestions
4. Quick reference card: Transformation codes
5. Quick reference card: Concatenation strategies

**Estimated Effort**: 4-6 hours

---

## 📊 Total Effort Estimate

| Phase | Effort | Priority |
|-------|--------|----------|
| 1. Database Migration (DONE) | 0 hours | ✅ COMPLETE |
| 2. Backend Updates | 15-22 hours | HIGH |
| 3. Frontend Updates | 26-34 hours | HIGH |
| 4. Testing & Validation | 11-16 hours | HIGH |
| 5. Documentation & Training | 7-10 hours | MEDIUM |
| **TOTAL** | **59-82 hours** | |

**Estimated Timeline**: 2-3 weeks (assuming 1 developer, 30-40 hours/week)

---

## 🚀 Recommended Approach

### Option A: Big Bang (All at once)
- Implement all changes in one go
- Switch from V1 to V2 in one deployment
- **Pros**: Clean cut, no hybrid state
- **Cons**: High risk, long development time before deployment

### Option B: Phased Rollout (Recommended)
**Phase 1**: Backend + Database (Week 1)
- Run database migration
- Update backend to support V2 schema
- Keep V1 API endpoints working (backward compatibility)
- Test thoroughly

**Phase 2**: Frontend Basic (Week 2)
- Update UI to support V2 schema for simple 1:1 mappings
- Add domain filtering
- Add feedback capture
- Deploy and validate

**Phase 3**: Frontend Advanced (Week 3)
- Add multi-field selection UI
- Add field ordering
- Add per-field transformations
- Add transformation preview
- Deploy and train users

**Pros**: Lower risk, incremental value, easier to debug
**Cons**: Longer total timeline

---

## 🎯 Next Steps

1. **Review this plan** with stakeholders
2. **Run database migration** in Databricks (test environment first!)
3. **Choose implementation approach** (Big Bang vs. Phased)
4. **Start with backend updates** (models → services → API)
5. **Test backend thoroughly** before touching frontend
6. **Implement frontend incrementally** (one feature at a time)
7. **Test each feature** before moving to next
8. **Update documentation** as you go
9. **Train users** on new features

---

## 📞 Questions to Consider

Before starting implementation:

1. **Domain Classification**: How will you populate domain fields?
   - Manual review?
   - Automated based on table naming conventions?
   - Import from external source?

2. **Vector Search**: Will you create separate indexes per domain?
   - Single index with domain filtering?
   - Multiple domain-specific indexes?

3. **Transformation Library**: Will users be able to create custom transformations?
   - Admin-only?
   - All users?
   - Approval process?

4. **Feedback**: What will you do with feedback data?
   - Analytics dashboard?
   - Model retraining?
   - Just for audit trail?

5. **Multi-Table Joins**: How will users define join conditions?
   - Manual SQL?
   - Visual join builder?
   - Pre-defined join relationships?

6. **Testing Strategy**: Will you test in dev environment first?
   - Parallel V1/V2 deployment?
   - Shadow mode (V2 running but not visible to users)?

---

## 📝 Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2024-11-20 | Use Phased Rollout approach | Lower risk, incremental value |
| 2024-11-20 | Create 6 new tables instead of modifying V1 | Clean separation, easy rollback |
| 2024-11-20 | Pre-seed transformation_library | Faster adoption, standardization |
| | | |

---

**Document Version**: 1.0  
**Last Updated**: November 20, 2024  
**Status**: Ready for Review

