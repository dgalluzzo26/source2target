# Restricted Mapping Edit Implementation

## ✅ Backend Complete

### API Endpoint
**PUT /api/v2/mappings/{mapping_id}**

### What Can Be Edited:
1. **Concatenation Strategy** - SPACE, COMMA, PIPE, CUSTOM, NONE
2. **Concatenation Separator** - Custom separator when strategy is CUSTOM
3. **Transformations** - SQL transformation expressions for each existing source field
4. **Join Conditions** - Add/update/remove join conditions

### What CANNOT Be Edited (requires delete + recreate):
1. ❌ Target field
2. ❌ Source fields list (add/remove fields)
3. ❌ Field order

### Example Request:
```json
{
  "concat_strategy": "PIPE",
  "concat_separator": null,
  "transformation_updates": {
    "1": "UPPER(TRIM(first_name))",
    "2": "UPPER(TRIM(last_name))"
  },
  "mapping_joins": [
    {
      "left_table": "t_member",
      "left_column": "member_id",
      "right_table": "t_address",
      "right_column": "member_id",
      "join_type": "LEFT"
    }
  ]
}
```

## 🔄 Frontend Implementation Needed

### Edit Dialog Structure:

```
┌─────────────────────────────────────────────────────────────┐
│ ✏️ Edit Mapping                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 📌 Target Field (Read-Only)                                │
│ ┌─────────────────────────────────────────────────────┐  │
│ │ Table: slv_member                                   │  │
│ │ Column: full_name                                   │  │
│ └─────────────────────────────────────────────────────┘  │
│                                                             │
│ 📋 Source Fields                                           │
│ ┌─────────────────────────────────────────────────────┐  │
│ │ ⚠️ Cannot add/remove/reorder fields                  │  │
│ │                                                      │  │
│ │ 1. FIRST_NAME  (t_member)                           │  │
│ │    Transformation: [TRIM(first_name)           ▼]  │  │
│ │                                                      │  │
│ │ 2. LAST_NAME   (t_member)                           │  │
│ │    Transformation: [TRIM(last_name)            ▼]  │  │
│ └─────────────────────────────────────────────────────┘  │
│                                                             │
│ 🔗 Concatenation                                           │
│ ┌─────────────────────────────────────────────────────┐  │
│ │ Strategy: [SPACE ▼]                                 │  │
│ │ Separator: [        ] (for CUSTOM only)            │  │
│ └─────────────────────────────────────────────────────┘  │
│                                                             │
│ 🔀 Join Conditions                                          │
│ ┌─────────────────────────────────────────────────────┐  │
│ │ [+ Add Join]                                        │  │
│ │                                                      │  │
│ │ Left: [t_member    ▼] . [member_id     ▼]         │  │
│ │ Right: [t_address  ▼] . [member_id     ▼]         │  │
│ │ Type: [LEFT        ▼]                    [🗑️ Remove]│  │
│ └─────────────────────────────────────────────────────┘  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                            [Cancel]  [Save Changes]         │
└─────────────────────────────────────────────────────────────┘
```

### Key Features:
1. **Visual Indicators** - Clear markers showing what can/cannot be changed
2. **Transformation Dropdown** - Select from transformation library or enter custom
3. **Join Management** - Add/edit/remove join conditions
4. **Concat Strategy** - Dropdown with SPACE, COMMA, PIPE, CUSTOM, NONE options

## 📝 Implementation Steps:

1. Add edit dialog to `MappingsListView.vue`
2. Fetch transformation library for dropdown
3. Build update request from form data
4. Call PUT /api/v2/mappings/{id} endpoint
5. Refresh mapping list on success
6. Show appropriate success/error messages

## 🧪 Testing:

1. Edit a mapping - change transformations
2. Edit a mapping - change concat strategy
3. Edit a mapping - add/modify joins
4. Verify changes are saved correctly
5. Verify target field and source fields list cannot be changed

---

**Status**: Backend ✅ Complete | Frontend ⏳ To Be Implemented
**Date**: November 24, 2025

