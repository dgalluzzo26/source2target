-- Check current status of tgt_comments in semantic_fields
SELECT 
    tgt_table_name,
    tgt_column_name,
    tgt_comments,
    CASE 
        WHEN tgt_comments IS NULL THEN 'NULL'
        WHEN tgt_comments = '' THEN 'EMPTY'
        ELSE 'HAS DATA'
    END as status
FROM oztest_dev.source2target.semantic_fields
LIMIT 20;

-- Count records by comment status
SELECT 
    CASE 
        WHEN tgt_comments IS NULL THEN 'NULL'
        WHEN tgt_comments = '' THEN 'EMPTY'
        ELSE 'HAS DATA'
    END as status,
    COUNT(*) as count
FROM oztest_dev.source2target.semantic_fields
GROUP BY status;

-- Example: Update tgt_comments for specific fields
-- Modify these examples to match your actual data

UPDATE oztest_dev.source2target.semantic_fields
SET tgt_comments = 'Unique identifier for the member record',
    updated_ts = CURRENT_TIMESTAMP()
WHERE tgt_table_name = 'T_MEMBER' AND tgt_column_name = 'MEMBER_ID';

UPDATE oztest_dev.source2target.semantic_fields
SET tgt_comments = 'First name of the member',
    updated_ts = CURRENT_TIMESTAMP()
WHERE tgt_table_name = 'T_MEMBER' AND tgt_column_name = 'FIRST_NAME';

UPDATE oztest_dev.source2target.semantic_fields
SET tgt_comments = 'Last name of the member',
    updated_ts = CURRENT_TIMESTAMP()
WHERE tgt_table_name = 'T_MEMBER' AND tgt_column_name = 'LAST_NAME';

UPDATE oztest_dev.source2target.semantic_fields
SET tgt_comments = 'Date of birth of the member',
    updated_ts = CURRENT_TIMESTAMP()
WHERE tgt_table_name = 'T_MEMBER' AND tgt_column_name = 'DATE_OF_BIRTH';

-- After updating, you should sync the vector search index
-- The app will do this automatically when you edit semantic fields through the UI,
-- but if you bulk update via SQL, you may need to manually sync:
-- (This is done via Python/Databricks API, not SQL)

