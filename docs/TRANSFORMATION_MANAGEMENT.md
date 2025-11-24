# Transformation Library Management

## Overview

Administrators can now manage the transformation library through an intuitive web interface. This feature allows admins to create, edit, and delete custom SQL transformation templates that can be applied to field mappings throughout the application.

## Features

### 1. View All Transformations
- Browse all available transformations in a sortable, filterable table
- Search by name, code, category, or description
- View transformation expressions and metadata
- System transformations are clearly marked and protected

### 2. Create New Transformations
- Add custom transformation templates
- Define SQL expressions with `{field}` placeholders
- Categorize transformations (STRING, DATE, NUMERIC, CONVERSION, NULL_HANDLING, CUSTOM)
- Optional: Mark as system transformation (prevents editing/deletion)

### 3. Edit Existing Transformations
- Update custom transformation details
- Modify names, codes, expressions, descriptions, and categories
- System transformations cannot be edited (protected)

### 4. Delete Transformations
- Remove custom transformations that are no longer needed
- Confirmation dialog prevents accidental deletions
- System transformations cannot be deleted (protected)

## Access

1. Navigate to the **Administration** page (admin-only access)
2. Click on the **Transformation Library** tab
3. Use the interface to manage transformations

## Creating a Transformation

### Required Fields
- **Name**: Display name (e.g., "Trim Whitespace")
- **Code**: Unique identifier (e.g., "TRIM")
- **SQL Expression**: Template with `{field}` placeholder (e.g., "TRIM({field})")

### Optional Fields
- **Description**: Human-readable explanation
- **Category**: Grouping for organization
- **System**: Mark as system transformation (immutable)

### Example: Creating a Custom Transformation

```
Name: Remove Special Characters
Code: REMOVE_SPECIAL
Expression: REGEXP_REPLACE({field}, '[^A-Za-z0-9 ]', '')
Description: Remove all special characters, keeping only alphanumeric and spaces
Category: STRING
```

## Categories

Transformations can be organized into the following categories:

- **STRING**: Text manipulation (TRIM, UPPER, LOWER, etc.)
- **DATE**: Date/time operations (CAST_DATE, CAST_TIMESTAMP, etc.)
- **NUMERIC**: Number operations (CAST_INT, ROUND, etc.)
- **CONVERSION**: Type conversions (CAST_STRING, TO_CHAR, etc.)
- **NULL_HANDLING**: NULL value handling (COALESCE, IFNULL, etc.)
- **CUSTOM**: User-defined categories

## System Transformations

System transformations are pre-configured templates that cannot be modified or deleted. These include:

- Trim Whitespace (TRIM)
- Upper Case (UPPER)
- Lower Case (LOWER)
- Initial Caps (INITCAP)
- Cast to String/Integer/Date/Timestamp
- Replace Nulls (with empty string or zero)
- Combined operations (TRIM_UPPER, TRIM_LOWER)

## Technical Details

### Backend API Endpoints

```
GET    /api/v2/transformations/          - Get all transformations
GET    /api/v2/transformations/{id}      - Get specific transformation
POST   /api/v2/transformations/          - Create new transformation
PUT    /api/v2/transformations/{id}      - Update transformation
DELETE /api/v2/transformations/{id}      - Delete transformation
```

### Database Table

Transformations are stored in the `transformation_library` table with the following schema:

```sql
transformation_id (INT, AUTO_INCREMENT)
transformation_name (STRING)
transformation_code (STRING, UNIQUE)
transformation_expression (STRING)
transformation_description (STRING, NULLABLE)
category (STRING, NULLABLE)
is_system (BOOLEAN)
created_ts (TIMESTAMP)
created_by (STRING)
```

### Components

- **Frontend**: `TransformationManager.vue` - Full CRUD interface
- **Backend Router**: `transformation.py` - API endpoints
- **Backend Service**: `transformation_service.py` - Business logic
- **Models**: `mapping_v2.py` - Data models

## Security

- Only administrators can access the transformation management interface
- System transformations are protected from modification and deletion
- Transformation codes must be unique
- SQL expressions are validated to include `{field}` placeholder

## Usage in Mappings

Once created, transformations can be applied to field mappings:

1. In the mapping interface, select a source field
2. Choose a transformation from the library
3. The transformation expression replaces `{field}` with the actual field name
4. Multiple transformations can be chained together

Example: Applying "TRIM_UPPER" to field "customer_name" results in:
```sql
UPPER(TRIM(customer_name))
```

## Best Practices

1. **Use clear, descriptive names** - Make it easy to find the right transformation
2. **Keep codes short and consistent** - Follow naming conventions (e.g., TRIM, UPPER, CAST_INT)
3. **Add detailed descriptions** - Explain what the transformation does and when to use it
4. **Categorize appropriately** - Helps users find related transformations
5. **Test expressions** - Verify SQL syntax before creating
6. **Don't mark custom transformations as system** - Keep flexibility to modify later

## Troubleshooting

### Cannot Edit/Delete Transformation
- Check if it's a system transformation (marked with "SYSTEM" badge)
- System transformations are protected and cannot be modified

### Duplicate Code Error
- Transformation codes must be unique
- Choose a different code or edit the existing transformation

### Expression Validation Error
- Ensure the SQL expression includes `{field}` placeholder
- This placeholder will be replaced with the actual field name at runtime

## Future Enhancements

Potential improvements for future versions:

- Expression syntax validation
- Preview/test transformation results
- Import/export transformation libraries
- Version history and rollback
- Usage statistics (which transformations are most used)
- Bulk operations (import multiple transformations at once)

