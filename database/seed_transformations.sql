-- Insert default system transformations into transformation_library table
-- Run this script ONCE to populate the transformation library

USE oztest_dev.source2target;

-- Insert default transformations
INSERT INTO transformation_library (
  transformation_name,
  transformation_code,
  transformation_expression,
  transformation_description,
  category,
  is_system,
  created_by
) VALUES
  ('Trim Whitespace', 'TRIM', 'TRIM({field})', 'Remove leading and trailing whitespace', 'STRING', true, 'system'),
  ('Upper Case', 'UPPER', 'UPPER({field})', 'Convert to uppercase', 'STRING', true, 'system'),
  ('Lower Case', 'LOWER', 'LOWER({field})', 'Convert to lowercase', 'STRING', true, 'system'),
  ('Initial Caps', 'INITCAP', 'INITCAP({field})', 'Capitalize first letter of each word', 'STRING', true, 'system'),
  ('Cast to String', 'CAST_STRING', 'CAST({field} AS STRING)', 'Convert to string data type', 'CONVERSION', true, 'system'),
  ('Cast to Integer', 'CAST_INT', 'CAST({field} AS INT)', 'Convert to integer data type', 'CONVERSION', true, 'system'),
  ('Cast to Date', 'CAST_DATE', 'CAST({field} AS DATE)', 'Convert to date data type', 'DATE', true, 'system'),
  ('Cast to Timestamp', 'CAST_TIMESTAMP', 'CAST({field} AS TIMESTAMP)', 'Convert to timestamp data type', 'DATE', true, 'system'),
  ('Replace Nulls', 'COALESCE', 'COALESCE({field}, '''')', 'Replace NULL values with empty string', 'NULL_HANDLING', true, 'system'),
  ('Replace Nulls with Zero', 'COALESCE_ZERO', 'COALESCE({field}, 0)', 'Replace NULL values with zero', 'NULL_HANDLING', true, 'system'),
  ('Trim and Upper', 'TRIM_UPPER', 'UPPER(TRIM({field}))', 'Remove whitespace and convert to uppercase', 'STRING', true, 'system'),
  ('Trim and Lower', 'TRIM_LOWER', 'LOWER(TRIM({field}))', 'Remove whitespace and convert to lowercase', 'STRING', true, 'system');

-- Verify insertions
SELECT 
  transformation_id,
  transformation_name,
  transformation_code,
  transformation_expression,
  category,
  is_system
FROM transformation_library
ORDER BY category, transformation_name;

