# Database Migration Scripts - V2

This directory contains SQL scripts and documentation for migrating the Source-to-Target Mapping Platform from V1 to V2.

## 📁 Files

| File | Purpose |
|------|---------|
| `migration_v2_schema.sql` | Creates V2 schema (6 tables + indexes + seed data) |
| `migration_v2_data.sql` | Migrates V1 data to V2 schema with validation |
| `V2_MIGRATION_GUIDE.md` | Comprehensive migration guide with examples |
| `V2_SCHEMA_DIAGRAM.md` | Visual schema diagrams and data flow |

## 🚀 Quick Start

### 1. Review the Changes

Read the migration guide to understand V2 enhancements:
```bash
cat V2_MIGRATION_GUIDE.md
```

### 2. Create V2 Schema

Run in Databricks SQL Editor or notebook:
```sql
%run /path/to/migration_v2_schema.sql
```

### 3. Migrate Data

Run in Databricks SQL Editor or notebook:
```sql
%run /path/to/migration_v2_data.sql
```

### 4. Validate Migration

Check the summary report and data quality checks output from step 3.

## 🎯 What's New in V2

### Major Features

- ✅ **Multi-Source Mapping**: Multiple source fields → Single target field
- ✅ **Field Ordering**: Drag-and-drop ordering for concatenation
- ✅ **Concatenation Strategies**: SPACE, COMMA, PIPE, CONCAT, CUSTOM
- ✅ **Per-Field Transformations**: TRIM, UPPER, LOWER, and 20+ more
- ✅ **Feedback Capture**: Track ACCEPTED/REJECTED/MODIFIED suggestions
- ✅ **Domain Classification**: Domain-aware AI recommendations
- ✅ **Transformation Library**: Reusable, standardized transformations

### Schema Changes

#### V1 (Old)
```
semantic_table (target definitions)
combined_fields (source + mapping, 1:1 only)
```

#### V2 (New)
```
semantic_fields (target definitions)
unmapped_fields (source fields awaiting mapping)
mapped_fields (one record per target field)
mapping_details (multiple source fields per target)
mapping_feedback (audit trail for AI suggestions)
transformation_library (reusable transformations)
```

## 📊 Use Cases

### Simple 1:1 Mapping (V1 Compatible)
```
T_MEMBER.SSN → slv_member.ssn_number
```

### Multi-Field Concatenation (New in V2)
```
T_MEMBER.FIRST_NAME + T_MEMBER.LAST_NAME → slv_member.full_name
(with SPACE separator and TRIM+INITCAP transformations)
```

### Multi-Table Join (New in V2)
```
T_ADDRESS.STREET + T_ADDRESS.CITY + T_STATE.STATE_NAME → slv_member.full_address
(with CUSTOM ", " separator)
```

## 📋 Migration Checklist

- [ ] Review `V2_MIGRATION_GUIDE.md`
- [ ] Review `V2_SCHEMA_DIAGRAM.md`
- [ ] Create project backup (tar.gz)
- [ ] Run `migration_v2_schema.sql`
- [ ] Verify 6 tables created
- [ ] Run `migration_v2_data.sql`
- [ ] Review data quality checks
- [ ] Populate domain classification
- [ ] Update vector search configuration
- [ ] Update application config
- [ ] Test in UI
- [ ] Drop V1 tables (after validation)

## 🔄 Rollback

If needed, V1 backup tables are created automatically:
- `semantic_table_v1_backup`
- `combined_fields_v1_backup`

See `V2_MIGRATION_GUIDE.md` → "Rollback Plan" for restore instructions.

## 📞 Support

Review the detailed documentation:
- **Migration Guide**: `V2_MIGRATION_GUIDE.md` (comprehensive guide)
- **Schema Diagrams**: `V2_SCHEMA_DIAGRAM.md` (visual reference)

## 🎓 Key Concepts

### Concatenation Strategy
Defines how multiple source fields are combined:
- **NONE**: Single field (like V1)
- **SPACE**: Concatenate with space: `"John" + "Doe" = "John Doe"`
- **COMMA**: Concatenate with comma: `"John" + "Doe" = "John,Doe"`
- **PIPE**: Concatenate with pipe: `"John" + "Doe" = "John|Doe"`
- **CONCAT**: Direct concatenation: `"John" + "Doe" = "JohnDoe"`
- **CUSTOM**: User-defined separator

### Transformations
Per-field SQL transformations applied before concatenation:
- **TEXT**: TRIM, UPPER, LOWER, INITCAP, etc.
- **DATE**: DATE_TO_STR, STR_TO_DATE, YEAR, MONTH
- **NUMERIC**: ROUND_2, TO_STRING, TO_INT, TO_DECIMAL
- **CUSTOM**: User-defined SQL expressions

### Feedback Actions
User feedback on AI suggestions:
- **ACCEPTED**: User accepted suggestion as-is
- **REJECTED**: User rejected suggestion (with comments)
- **MODIFIED**: User accepted but changed target/transformations

## 📈 Benefits

1. **Flexibility**: Handle complex real-world mapping scenarios
2. **Standardization**: Reusable transformation patterns
3. **Quality**: Confidence scoring and feedback loop
4. **Transparency**: Full transformation expressions visible
5. **Scalability**: Proper normalization for enterprise scale
6. **Domain-Aware**: Better AI recommendations per domain
7. **Auditability**: Complete trail of mapping decisions

---

**Version**: 2.0  
**Date**: November 20, 2024  
**Status**: Ready for Migration

