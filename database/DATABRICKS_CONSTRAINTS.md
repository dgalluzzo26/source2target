# Databricks Constraints Guide

## 🚨 Important: Databricks Constraint Limitations

Databricks Delta tables support these constraints with limitations:
- ✅ `PRIMARY KEY` constraints (enforced)
- ✅ `NOT NULL` constraints (enforced)
- ✅ `CHECK` constraints (enforced via Delta table properties)
- ⚠️ `FOREIGN KEY` constraints (allowed but **INFORMATIONAL ONLY** - not enforced)
- ❌ `UNIQUE` constraints (not supported at all)
- ❌ `ON DELETE CASCADE/SET NULL` (not supported)

## ✅ What We Changed in V2 Schema

The V2 migration scripts have been updated for Databricks compatibility:

### Removed UNIQUE Constraints (not supported):
1. `semantic_fields`: (tgt_table, tgt_column) - **must enforce at application level**
2. `unmapped_fields`: (src_table, src_column) - **must enforce at application level**
3. `mapped_fields`: (tgt_table, tgt_column) - **must enforce at application level**
4. `mapping_details`: (mapped_field_id, src_table, src_column) - **must enforce at application level**
5. `transformation_library`: (transformation_code) - **must enforce at application level**

### Kept FOREIGN KEY Constraints (informational only):
1. `mapped_fields.semantic_field_id` → `semantic_fields.semantic_field_id` ⚠️ *not enforced*
2. `mapping_details.mapped_field_id` → `mapped_fields.mapped_field_id` ⚠️ *not enforced*
3. `mapping_details.unmapped_field_id` → `unmapped_fields.unmapped_field_id` ⚠️ *not enforced*
4. `mapping_feedback.mapped_field_id` → `mapped_fields.mapped_field_id` ⚠️ *not enforced*

**Note**: Foreign keys are kept for **documentation purposes** but Databricks **does not enforce** them. You must still validate foreign keys in your application code!

## 🛡️ How to Enforce Constraints at Application Level

### 1. Enforce UNIQUE Constraints in Python

**Example: Prevent duplicate semantic_fields**

```python
# backend/services/semantic_service.py

async def create_record(self, record: SemanticRecordCreate):
    """
    Create a new semantic field record.
    
    Enforces uniqueness on (tgt_table, tgt_column) at application level.
    """
    # Check for existing record with same tgt_table and tgt_column
    check_query = """
        SELECT COUNT(*) as count 
        FROM main.source2target.semantic_fields 
        WHERE tgt_table = ? AND tgt_column = ?
    """
    
    with self._get_sql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                check_query, 
                (record.tgt_table, record.tgt_column)
            )
            result = cursor.fetchone()
            
            if result.count > 0:
                raise ValueError(
                    f"Semantic field already exists: "
                    f"{record.tgt_table}.{record.tgt_column}"
                )
            
            # Proceed with insert
            insert_query = """
                INSERT INTO main.source2target.semantic_fields 
                (tgt_table, tgt_column, ...)
                VALUES (?, ?, ...)
            """
            cursor.execute(insert_query, (...))
```

**Example: Prevent duplicate transformation codes**

```python
# backend/services/transformation_service.py

async def create_transformation(self, transformation: TransformationCreate):
    """
    Create a new transformation template.
    
    Enforces uniqueness on transformation_code at application level.
    """
    # Check for existing transformation with same code
    check_query = """
        SELECT COUNT(*) as count 
        FROM main.source2target.transformation_library 
        WHERE transformation_code = ?
    """
    
    with self._get_sql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(check_query, (transformation.transformation_code,))
            result = cursor.fetchone()
            
            if result.count > 0:
                raise ValueError(
                    f"Transformation code already exists: "
                    f"{transformation.transformation_code}"
                )
            
            # Proceed with insert
            # ...
```

### 2. Enforce FOREIGN KEY Constraints in Python

**Important**: Even though Databricks allows FOREIGN KEY constraint syntax, it **does not enforce** them. You must still validate foreign keys in your application code!

**Example: Validate semantic_field_id exists before creating mapping**

```python
# backend/services/mapping_service.py

async def save_manual_mapping(
    self, 
    semantic_field_id: int,
    source_fields: List[SourceField],
    ...
):
    """
    Create a new mapping.
    
    Enforces foreign key to semantic_fields at application level.
    """
    # Validate semantic_field_id exists
    check_query = """
        SELECT COUNT(*) as count 
        FROM main.source2target.semantic_fields 
        WHERE semantic_field_id = ?
    """
    
    with self._get_sql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(check_query, (semantic_field_id,))
            result = cursor.fetchone()
            
            if result.count == 0:
                raise ValueError(
                    f"Invalid semantic_field_id: {semantic_field_id}. "
                    f"Target field does not exist."
                )
            
            # Proceed with insert into mapped_fields
            # ...
```

**Example: Handle CASCADE DELETE in application**

```python
# backend/services/mapping_service.py

async def delete_mapped_field(self, mapped_field_id: int):
    """
    Delete a mapped field and cascade delete to mapping_details.
    
    Emulates ON DELETE CASCADE behavior at application level.
    """
    with self._get_sql_connection() as conn:
        with conn.cursor() as cursor:
            # First, delete mapping_details (child records)
            cursor.execute(
                """
                DELETE FROM main.source2target.mapping_details 
                WHERE mapped_field_id = ?
                """,
                (mapped_field_id,)
            )
            
            # Then, delete mapped_field (parent record)
            cursor.execute(
                """
                DELETE FROM main.source2target.mapped_fields 
                WHERE mapped_field_id = ?
                """,
                (mapped_field_id,)
            )
            
            conn.commit()
```

**Example: Handle SET NULL in application**

```python
# backend/services/mapping_service.py

async def delete_unmapped_field(self, unmapped_field_id: int):
    """
    Delete an unmapped field and set foreign keys to NULL in mapping_details.
    
    Emulates ON DELETE SET NULL behavior at application level.
    """
    with self._get_sql_connection() as conn:
        with conn.cursor() as cursor:
            # First, set unmapped_field_id to NULL in mapping_details
            cursor.execute(
                """
                UPDATE main.source2target.mapping_details 
                SET unmapped_field_id = NULL
                WHERE unmapped_field_id = ?
                """,
                (unmapped_field_id,)
            )
            
            # Then, delete the unmapped field
            cursor.execute(
                """
                DELETE FROM main.source2target.unmapped_fields 
                WHERE unmapped_field_id = ?
                """,
                (unmapped_field_id,)
            )
            
            conn.commit()
```

### 3. Use Database Merge/Upsert for Idempotency

**Example: Upsert to avoid duplicates**

```python
# backend/services/semantic_service.py

async def upsert_semantic_field(self, record: SemanticRecordCreate):
    """
    Insert or update semantic field (idempotent).
    
    Uses MERGE to avoid duplicate key errors.
    """
    merge_query = """
    MERGE INTO main.source2target.semantic_fields AS target
    USING (
        SELECT 
            ? as tgt_table,
            ? as tgt_column,
            ? as tgt_data_type,
            ? as tgt_comments,
            ? as domain
    ) AS source
    ON target.tgt_table = source.tgt_table 
       AND target.tgt_column = source.tgt_column
    WHEN MATCHED THEN
        UPDATE SET
            tgt_data_type = source.tgt_data_type,
            tgt_comments = source.tgt_comments,
            domain = source.domain,
            updated_by = ?,
            updated_ts = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN
        INSERT (tgt_table, tgt_column, tgt_data_type, tgt_comments, domain, created_by)
        VALUES (source.tgt_table, source.tgt_column, source.tgt_data_type, 
                source.tgt_comments, source.domain, ?)
    """
    
    with self._get_sql_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                merge_query,
                (
                    record.tgt_table,
                    record.tgt_column,
                    record.tgt_data_type,
                    record.tgt_comments,
                    record.domain,
                    'current_user',  # updated_by
                    'current_user',  # created_by
                )
            )
```

## 🔧 Frontend Validation

Add validation in the frontend to catch issues before API calls:

```typescript
// frontend/src/stores/semanticStore.ts

async createSemanticField(field: SemanticRecordCreate) {
  // Check for duplicate in local state first
  const exists = this.semanticFields.some(
    (f) => 
      f.tgt_table === field.tgt_table && 
      f.tgt_column === field.tgt_column
  );
  
  if (exists) {
    throw new Error(
      `Field ${field.tgt_table}.${field.tgt_column} already exists`
    );
  }
  
  // Call API
  const response = await api.post('/api/semantic', field);
  // ...
}
```

## 📊 Data Quality Monitoring

Since constraints aren't enforced at the database level, add monitoring queries:

### Check for Duplicate Semantic Fields:
```sql
SELECT 
  tgt_table, 
  tgt_column, 
  COUNT(*) as duplicate_count
FROM main.source2target.semantic_fields
GROUP BY tgt_table, tgt_column
HAVING COUNT(*) > 1;
-- Expected: 0 rows
```

### Check for Invalid Foreign Keys in mapped_fields:
```sql
SELECT 
  mf.mapped_field_id,
  mf.semantic_field_id,
  mf.tgt_table,
  mf.tgt_column
FROM main.source2target.mapped_fields mf
LEFT JOIN main.source2target.semantic_fields sf 
  ON mf.semantic_field_id = sf.semantic_field_id
WHERE sf.semantic_field_id IS NULL;
-- Expected: 0 rows
```

### Check for Orphaned mapping_details:
```sql
SELECT 
  md.mapping_detail_id,
  md.mapped_field_id
FROM main.source2target.mapping_details md
LEFT JOIN main.source2target.mapped_fields mf 
  ON md.mapped_field_id = mf.mapped_field_id
WHERE mf.mapped_field_id IS NULL;
-- Expected: 0 rows
```

### Check for Duplicate transformation codes:
```sql
SELECT 
  transformation_code, 
  COUNT(*) as duplicate_count
FROM main.source2target.transformation_library
GROUP BY transformation_code
HAVING COUNT(*) > 1;
-- Expected: 0 rows
```

## 🧪 Testing Recommendations

Add unit tests to verify constraint enforcement:

```python
# tests/test_semantic_service.py

async def test_duplicate_semantic_field_raises_error():
    """Test that creating duplicate semantic field raises ValueError."""
    service = SemanticService()
    
    # Create first record
    record = SemanticRecordCreate(
        tgt_table="slv_member",
        tgt_column="first_name",
        tgt_data_type="STRING"
    )
    await service.create_record(record)
    
    # Try to create duplicate - should raise ValueError
    with pytest.raises(ValueError, match="already exists"):
        await service.create_record(record)

async def test_invalid_foreign_key_raises_error():
    """Test that invalid semantic_field_id raises ValueError."""
    service = MappingService()
    
    # Try to create mapping with non-existent semantic_field_id
    with pytest.raises(ValueError, match="Invalid semantic_field_id"):
        await service.save_manual_mapping(
            semantic_field_id=99999,  # doesn't exist
            source_fields=[...]
        )
```

## 📝 Summary

Databricks constraint support:
- ✅ **PRIMARY KEY**: Enforced by Databricks
- ✅ **NOT NULL**: Enforced by Databricks
- ⚠️ **FOREIGN KEY**: Allowed but **INFORMATIONAL ONLY** (not enforced)
- ❌ **UNIQUE**: Not supported at all
- ❌ **ON DELETE CASCADE/SET NULL**: Not supported

Since constraints are not fully enforced:

1. ✅ **Application-Level Validation**: Add validation logic in Python services for uniqueness and FK validation
2. ✅ **Frontend Validation**: Catch issues early in the UI
3. ✅ **Data Quality Monitoring**: Run periodic checks for constraint violations
4. ✅ **Unit Tests**: Verify constraint enforcement logic
5. ✅ **MERGE Statements**: Use for idempotent upserts
6. ✅ **Explicit CASCADE/SET NULL**: Handle in application code

**Foreign keys are kept in schema for documentation but you must still validate them in code!**

---

**Document Version**: 1.0  
**Last Updated**: November 20, 2024  
**Related**: `migration_v2_schema.sql`, `V2_IMPLEMENTATION_PLAN.md`

