# Admin Interface Structure

## Navigation Flow

```
Sidebar (Admin Only)
├── Home (/)
├── ── Mapping Workflow ──
├── Create Mappings (/unmapped-fields)
├── View Mappings (/mappings)
├── ── Administration ──
├── Semantic Fields (/semantic-fields)
├── Admin Tools (/admin) ← NEW
│   └── Tabs:
│       ├── Transformation Library ← ACTIVE FEATURE
│       ├── System Settings (Coming Soon)
│       ├── User Management (Coming Soon)
│       └── Audit Logs (Coming Soon)
└── Settings (/config)
    └── Database, AI, Vector Search, UI, Security, Support configs
```

## Admin Tools Page Structure

```
┌─────────────────────────────────────────────────────────────┐
│ 🛡️ Administration                                           │
│ System administration and configuration                     │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐  │
│ │ 📋 Tabs:                                             │  │
│ │ [Transformation Library] [System Settings] [Users] [Logs]│
│ └─────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐  │
│ │ 💻 Transformation Library                            │  │
│ │ Manage reusable SQL transformation templates         │  │
│ │                                  [+ Add Transformation]│  │
│ │                                                      │  │
│ │ ┌─────────────────────────────────────────────────┐ │  │
│ │ │ 📊 Data Table                                    │ │  │
│ │ │ ┌──────────┬──────┬───────────┬────────┬───┐   │ │  │
│ │ │ │ Name     │ Code │ Expression│ Category│...│   │ │  │
│ │ │ ├──────────┼──────┼───────────┼────────┼───┤   │ │  │
│ │ │ │ Trim     │TRIM  │TRIM({...})│STRING 🏷│✏️🗑│ │  │
│ │ │ │ Upper    │UPPER │UPPER({...}│STRING 🏷│✏️🗑│ │  │
│ │ │ │ Cast Int │CAST..│CAST({...})│CONVER.. │✏️🗑│ │  │
│ │ │ └──────────┴──────┴───────────┴────────┴───┘   │ │  │
│ │ │                                                  │ │  │
│ │ │ • Search/Filter by name, code, category         │ │  │
│ │ │ • Sort by any column                            │ │  │
│ │ │ • Pagination (10, 25, 50 rows)                  │ │  │
│ │ │ • System transformations marked with SYSTEM tag │ │  │
│ │ └─────────────────────────────────────────────────┘ │  │
│ └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Create/Edit Dialog

```
┌─────────────────────────────────────────────┐
│ ➕ Create Transformation                    │
├─────────────────────────────────────────────┤
│                                             │
│ Name *                                      │
│ ┌─────────────────────────────────────┐   │
│ │ e.g., Trim Whitespace               │   │
│ └─────────────────────────────────────┘   │
│                                             │
│ Code *                                      │
│ ┌─────────────────────────────────────┐   │
│ │ e.g., TRIM                          │   │
│ └─────────────────────────────────────┘   │
│ Unique identifier for this transformation  │
│                                             │
│ SQL Expression *                            │
│ ┌─────────────────────────────────────┐   │
│ │ e.g., TRIM({field})                 │   │
│ │                                     │   │
│ │                                     │   │
│ └─────────────────────────────────────┘   │
│ Use {field} as placeholder for field name  │
│                                             │
│ Description                                 │
│ ┌─────────────────────────────────────┐   │
│ │ Remove leading/trailing whitespace │   │
│ └─────────────────────────────────────┘   │
│                                             │
│ Category                                    │
│ ┌─────────────────────────────────────┐   │
│ │ [Select...        ▼]                │   │
│ └─────────────────────────────────────┘   │
│ • STRING                                    │
│ • DATE                                      │
│ • NUMERIC                                   │
│ • CONVERSION                                │
│ • NULL_HANDLING                             │
│ • CUSTOM                                    │
│                                             │
│ ☐ Mark as system transformation            │
│   System transformations cannot be edited  │
│                                             │
├─────────────────────────────────────────────┤
│           [Cancel]  [Create/Update]         │
└─────────────────────────────────────────────┘
```

## Delete Confirmation Dialog

```
┌─────────────────────────────────────────────┐
│ 🗑️ Delete Transformation                    │
├─────────────────────────────────────────────┤
│                                             │
│             ⚠️ (warning icon)               │
│                                             │
│ Are you sure you want to delete this        │
│ transformation?                             │
│                                             │
│ ┌─────────────────────────────────────┐   │
│ │ Trim Whitespace                     │   │
│ │ TRIM                                │   │
│ └─────────────────────────────────────┘   │
│                                             │
│ ⚠️ This action cannot be undone.            │
│                                             │
├─────────────────────────────────────────────┤
│           [Cancel]  [Delete]                │
└─────────────────────────────────────────────┘
```

## User Interactions

### Creating a Transformation
1. Click **"Add Transformation"** button
2. Fill in required fields (Name, Code, Expression)
3. Optionally add Description and Category
4. Click **"Create"**
5. Success message appears
6. Table refreshes with new transformation

### Editing a Transformation
1. Click **pencil icon** next to transformation
2. Modify fields in the dialog
3. Click **"Update"**
4. Success message appears
5. Table refreshes with updated data

### Deleting a Transformation
1. Click **trash icon** next to transformation
2. Confirm deletion in dialog
3. Click **"Delete"**
4. Success message appears
5. Table refreshes without deleted transformation

### System Transformation Protection
- System transformations show a blue **"SYSTEM"** badge
- Edit and delete buttons are **disabled** (grayed out)
- Hovering shows tooltip: "System transformations cannot be edited/deleted"
- Attempting to edit/delete via API returns **403 Forbidden**

## Category Color Coding

```
STRING         → Green (success)
DATE           → Blue (info)
NUMERIC        → Orange (warn)
CONVERSION     → Purple (primary)
NULL_HANDLING  → Gray (secondary)
CUSTOM         → Dark (contrast)
```

## API Integration

All operations communicate with backend via REST API:

```
Frontend                Backend                Database
   │                       │                      │
   ├─ GET /api/v2/transformations/               │
   ├──────────────────────>│                      │
   │                       ├─ Query table ───────>│
   │                       │<──── Results ────────┤
   │<─ 200 OK + data ──────┤                      │
   │                       │                      │
   ├─ POST /api/v2/transformations/ + data        │
   ├──────────────────────>│                      │
   │                       ├─ Validate + Insert ─>│
   │                       │<──── New ID ─────────┤
   │<─ 200 OK + new item ──┤                      │
   │                       │                      │
   ├─ PUT /api/v2/transformations/{id} + data     │
   ├──────────────────────>│                      │
   │                       ├─ Validate + Update ─>│
   │                       │<──── Success ────────┤
   │<─ 200 OK + updated ───┤                      │
   │                       │                      │
   ├─ DELETE /api/v2/transformations/{id}         │
   ├──────────────────────>│                      │
   │                       ├─ Validate + Delete ─>│
   │                       │<──── Success ────────┤
   │<─ 200 OK ─────────────┤                      │
```

## Validation Rules

### Frontend Validation
- ✅ Name is required
- ✅ Code is required
- ✅ Expression is required
- ✅ Expression must contain `{field}` placeholder
- ✅ All fields trimmed before submission

### Backend Validation
- ✅ Transformation code must be unique
- ✅ Cannot edit system transformations (403)
- ✅ Cannot delete system transformations (403)
- ✅ Transformation must exist for update/delete (404)
- ✅ All fields properly escaped for SQL injection protection

## Error Handling

### User-Friendly Messages
```
Success:
✅ "Transformation created successfully"
✅ "Transformation updated successfully"
✅ "Transformation deleted successfully"

Errors:
❌ "Name is required"
❌ "Expression must include {field} placeholder"
❌ "Transformation with code 'TRIM' already exists"
❌ "System transformations cannot be modified"
❌ "Transformation 123 not found"
❌ "Failed to connect to server"
```

## Performance Features

- **Lazy Loading**: Component loaded only when accessed
- **Efficient Rendering**: PrimeVue DataTable with virtual scrolling
- **Debounced Search**: Search filters debounced for performance
- **Async Operations**: All API calls are asynchronous
- **Loading States**: Spinners during save/delete operations
- **Optimistic Updates**: UI updates before API confirmation (with rollback)

## Responsive Design

The interface adapts to different screen sizes:
- **Desktop**: Full table with all columns visible
- **Tablet**: Condensed columns, responsive actions
- **Mobile**: Stacked layout with collapsible sections

## Accessibility

- ✅ Keyboard navigation support
- ✅ ARIA labels for screen readers
- ✅ High contrast text and icons
- ✅ Tooltips for context
- ✅ Focus management in dialogs
- ✅ Tab order optimized

---

**Last Updated:** November 24, 2025
**Status:** Complete and Production-Ready

