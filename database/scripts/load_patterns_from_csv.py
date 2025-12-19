"""
V4 Pattern Loader - Load Historical Mappings from CSV using LLM

This script reads historical mapping data from a Unity Catalog staging table,
uses the Databricks Foundation Model to parse SQL expressions and generate
join_metadata, then inserts complete rows into the mapped_fields table.

Features:
- Parallel processing using ThreadPoolExecutor
- Progress tracking
- Error handling with retry logic
- Batch inserts for performance
- Can be run as a Databricks notebook or standalone script

Usage:
    # In Databricks notebook:
    %run ./load_patterns_from_csv
    
    loader = PatternLoader(
        catalog_schema="oztest_dev.smartmapper",
        staging_table="br_scenario_table_1"
    )
    loader.run(max_workers=5, batch_size=10)

    # Or from command line (with proper auth):
    python load_patterns_from_csv.py --catalog-schema oztest_dev.smartmapper --staging-table br_scenario_table_1
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime

# Databricks imports
try:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
    from databricks.sql import connect as sql_connect
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    print("Warning: Databricks SDK not available. Install with: pip install databricks-sdk databricks-sql-connector")


@dataclass
class PatternRow:
    """Represents a row from the staging table."""
    row_id: int
    subject_area: str
    bronze_table_name: str
    bronze_column_name: str
    bronze_column_physical: str
    bronze_column_description: str
    transformation_logic: str
    join_column_description: str
    function: str
    silver_table_name: str
    silver_table_physical: str
    silver_column_name: str
    silver_column_physical: str
    silver_column_definition: str


class PatternLoader:
    """
    Loads historical mapping patterns from CSV staging table into mapped_fields.
    Uses LLM to parse SQL expressions and generate structured metadata.
    """
    
    def __init__(
        self,
        catalog_schema: str,
        staging_table: str,
        llm_endpoint: str = "databricks-meta-llama-3-3-70b-instruct",
        server_hostname: Optional[str] = None,
        http_path: Optional[str] = None
    ):
        """
        Initialize the pattern loader.
        
        Args:
            catalog_schema: Unity Catalog schema (e.g., "oztest_dev.smartmapper")
            staging_table: Name of the staging table with CSV data
            llm_endpoint: Databricks Foundation Model endpoint name
            server_hostname: Databricks SQL warehouse hostname (auto-detected if not provided)
            http_path: Databricks SQL warehouse HTTP path (auto-detected if not provided)
        """
        self.catalog_schema = catalog_schema
        self.staging_table = staging_table
        self.llm_endpoint = llm_endpoint
        
        # Initialize Databricks clients
        self.workspace_client = WorkspaceClient()
        
        # Get SQL warehouse config from environment or parameters
        if server_hostname and http_path:
            self.server_hostname = server_hostname
            self.http_path = http_path
        else:
            # Try to get from config or environment
            import os
            self.server_hostname = os.environ.get("DATABRICKS_SERVER_HOSTNAME", "")
            self.http_path = os.environ.get("DATABRICKS_HTTP_PATH", "")
        
        # Statistics
        self.stats = {
            "total": 0,
            "processed": 0,
            "success": 0,
            "errors": 0,
            "skipped": 0
        }
        self.errors: List[Dict] = []
    
    def _get_sql_connection(self):
        """Get a Databricks SQL connection using OAuth."""
        token = self.workspace_client.config.oauth_token().access_token
        return sql_connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=token
        )
    
    def _escape_sql(self, value: str) -> str:
        """Escape single quotes for SQL."""
        if value is None:
            return ""
        return str(value).replace("'", "''")
    
    def _call_llm(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """
        Call the LLM endpoint with retry logic.
        
        Args:
            prompt: The prompt to send to the LLM
            max_retries: Number of retries on failure
            
        Returns:
            The LLM response text, or None on failure
        """
        for attempt in range(max_retries):
            try:
                response = self.workspace_client.serving_endpoints.query(
                    name=self.llm_endpoint,
                    messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
                    max_tokens=2000
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"LLM call failed after {max_retries} attempts: {e}")
                    return None
        return None
    
    def _generate_join_metadata(self, row: PatternRow) -> Optional[str]:
        """
        Use LLM to parse SQL and generate join_metadata JSON.
        
        Args:
            row: The pattern row with transformation logic
            
        Returns:
            JSON string of join_metadata, or None on failure
        """
        if not row.transformation_logic or row.transformation_logic.strip() == "":
            return None
        
        prompt = f"""Parse this SQL expression and generate a JSON metadata object for a data mapping tool.

SQL EXPRESSION:
```sql
{row.transformation_logic}
```

CONTEXT:
- Target Column: {row.silver_column_physical}
- Target Table: {row.silver_table_physical}
- Source Tables: {row.bronze_table_name}
- Join Descriptions: {row.join_column_description or 'N/A'}
- Function Type: {row.function or 'Direct'}

Generate a JSON object with this EXACT structure:
{{
  "patternType": "SINGLE|JOIN|UNION|UNION_JOIN|CONCAT",
  "outputColumn": "<the column being selected>",
  "description": "<brief description of what this mapping does>",
  "silverTables": [
    {{"alias": "<alias>", "physicalName": "<full table name>", "isConstant": true, "description": "<table purpose>"}}
  ],
  "unionBranches": [
    {{
      "branchId": 1,
      "description": "<what this branch does>",
      "bronzeTable": {{"alias": "<alias>", "physicalName": "<table>", "isConstant": false}},
      "joins": [
        {{"type": "INNER|LEFT", "toTable": "<alias>", "onCondition": "<condition>"}}
      ],
      "whereClause": "<where clause if any>"
    }}
  ],
  "userColumnsToMap": [
    {{"role": "join_key|output|filter", "originalColumn": "<column>", "description": "<what user provides>"}}
  ],
  "userTablesToMap": [
    {{"role": "bronze_primary|bronze_secondary", "originalTable": "<table>", "description": "<what user replaces>"}}
  ]
}}

RULES:
1. silverTables = tables from silver_* schemas (CONSTANT, user does NOT replace)
2. bronzeTables = tables from bronze_* schemas (user REPLACES with their tables)
3. For UNION, create separate unionBranches for each SELECT
4. If no JOINs/UNIONs, use patternType "SINGLE" and omit unionBranches
5. Return ONLY the JSON object, no explanation"""

        response = self._call_llm(prompt)
        if not response:
            return None
        
        # Extract JSON from response
        try:
            # Find JSON in response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                # Validate it's valid JSON
                json.loads(json_str)
                return json_str
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON for {row.silver_column_physical}: {e}")
        
        return None
    
    def _determine_relationship_type(self, sql: str, bronze_columns: str) -> str:
        """Determine the source relationship type from SQL."""
        if not sql:
            return "SINGLE"
        
        sql_upper = sql.upper()
        
        if "UNION" in sql_upper and "JOIN" in sql_upper:
            return "UNION_JOIN"
        elif "UNION" in sql_upper:
            return "UNION"
        elif "JOIN" in sql_upper:
            return "JOIN"
        elif bronze_columns and "|" in bronze_columns:
            return "CONCAT"
        else:
            return "SINGLE"
    
    def _process_row(self, row: PatternRow) -> Dict[str, Any]:
        """
        Process a single row: generate metadata and prepare for insert.
        
        Args:
            row: The pattern row to process
            
        Returns:
            Dict with processed data and status
        """
        result = {
            "row_id": row.row_id,
            "target_column": row.silver_column_physical,
            "status": "pending",
            "error": None,
            "data": None
        }
        
        try:
            # Skip rows without transformation logic
            if not row.transformation_logic or row.transformation_logic.strip() == "":
                result["status"] = "skipped"
                result["error"] = "No transformation logic"
                return result
            
            # Generate join_metadata using LLM
            join_metadata = self._generate_join_metadata(row)
            
            # Determine relationship type
            relationship_type = self._determine_relationship_type(
                row.transformation_logic,
                row.bronze_column_physical
            )
            
            # Build source descriptions
            source_descriptions = row.bronze_column_description or ""
            if row.join_column_description:
                source_descriptions += f" | Join Info: {row.join_column_description}"
            
            # Prepare the insert data
            result["data"] = {
                "tgt_table_name": row.silver_table_name,
                "tgt_table_physical_name": row.silver_table_physical,
                "tgt_column_name": row.silver_column_name,
                "tgt_column_physical_name": row.silver_column_physical,
                "tgt_comments": row.silver_column_definition,
                "source_expression": row.transformation_logic,
                "source_tables": row.bronze_table_name,
                "source_tables_physical": row.bronze_table_name.lower().replace(" ", "_") if row.bronze_table_name else None,
                "source_columns": row.bronze_column_name,
                "source_columns_physical": row.bronze_column_physical,
                "source_descriptions": source_descriptions,
                "source_domain": row.subject_area,
                "source_relationship_type": relationship_type,
                "transformations_applied": row.function or "Direct",
                "join_metadata": join_metadata,
                "is_approved_pattern": True,
                "confidence_score": 0.95,
                "mapping_source": "HISTORICAL"
            }
            
            result["status"] = "success"
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result
    
    def _insert_batch(self, rows: List[Dict[str, Any]]) -> int:
        """
        Insert a batch of processed rows into mapped_fields.
        
        Args:
            rows: List of processed row data
            
        Returns:
            Number of rows inserted
        """
        if not rows:
            return 0
        
        connection = self._get_sql_connection()
        inserted = 0
        
        try:
            with connection.cursor() as cursor:
                for row_data in rows:
                    if row_data["status"] != "success" or not row_data["data"]:
                        continue
                    
                    data = row_data["data"]
                    
                    # Look up semantic_field_id
                    cursor.execute(f"""
                        SELECT semantic_field_id 
                        FROM {self.catalog_schema}.semantic_fields 
                        WHERE UPPER(tgt_column_physical_name) = UPPER('{self._escape_sql(data['tgt_column_physical_name'])}')
                          AND UPPER(tgt_table_physical_name) = UPPER('{self._escape_sql(data['tgt_table_physical_name'])}')
                        LIMIT 1
                    """)
                    result = cursor.fetchone()
                    semantic_field_id = result[0] if result else 0
                    
                    # Insert into mapped_fields
                    cursor.execute(f"""
                        INSERT INTO {self.catalog_schema}.mapped_fields (
                            semantic_field_id,
                            project_id,
                            tgt_table_name,
                            tgt_table_physical_name,
                            tgt_column_name,
                            tgt_column_physical_name,
                            tgt_comments,
                            source_expression,
                            source_tables,
                            source_tables_physical,
                            source_columns,
                            source_columns_physical,
                            source_descriptions,
                            source_domain,
                            source_relationship_type,
                            transformations_applied,
                            join_metadata,
                            is_approved_pattern,
                            pattern_approved_by,
                            pattern_approved_ts,
                            confidence_score,
                            mapping_source,
                            ai_generated,
                            mapping_status,
                            mapped_by,
                            mapped_ts
                        ) VALUES (
                            {semantic_field_id},
                            NULL,
                            '{self._escape_sql(data['tgt_table_name'])}',
                            '{self._escape_sql(data['tgt_table_physical_name'])}',
                            '{self._escape_sql(data['tgt_column_name'])}',
                            '{self._escape_sql(data['tgt_column_physical_name'])}',
                            {f"'{self._escape_sql(data['tgt_comments'])}'" if data['tgt_comments'] else 'NULL'},
                            '{self._escape_sql(data['source_expression'])}',
                            {f"'{self._escape_sql(data['source_tables'])}'" if data['source_tables'] else 'NULL'},
                            {f"'{self._escape_sql(data['source_tables_physical'])}'" if data['source_tables_physical'] else 'NULL'},
                            {f"'{self._escape_sql(data['source_columns'])}'" if data['source_columns'] else 'NULL'},
                            {f"'{self._escape_sql(data['source_columns_physical'])}'" if data['source_columns_physical'] else 'NULL'},
                            {f"'{self._escape_sql(data['source_descriptions'])}'" if data['source_descriptions'] else 'NULL'},
                            {f"'{self._escape_sql(data['source_domain'])}'" if data['source_domain'] else 'NULL'},
                            '{data['source_relationship_type']}',
                            {f"'{self._escape_sql(data['transformations_applied'])}'" if data['transformations_applied'] else 'NULL'},
                            {f"'{self._escape_sql(data['join_metadata'])}'" if data['join_metadata'] else 'NULL'},
                            TRUE,
                            'historical_import@gainwell.com',
                            CURRENT_TIMESTAMP(),
                            {data['confidence_score']},
                            'HISTORICAL',
                            FALSE,
                            'ACTIVE',
                            'historical_import@gainwell.com',
                            CURRENT_TIMESTAMP()
                        )
                    """)
                    inserted += 1
                    
        except Exception as e:
            print(f"Error inserting batch: {e}")
        finally:
            connection.close()
        
        return inserted
    
    def load_staging_data(self) -> List[PatternRow]:
        """
        Load rows from the staging table.
        
        Returns:
            List of PatternRow objects
        """
        connection = self._get_sql_connection()
        rows = []
        
        try:
            with connection.cursor() as cursor:
                # Query staging table (BR Scenario format)
                cursor.execute(f"""
                    SELECT 
                        ROW_NUMBER() OVER (ORDER BY `Silver_TABLE NAME`, `Silver Attribute Column Physical Name`) as row_id,
                        `Subject Area`,
                        `BRONZE_TABLE NAME`,
                        `Bronze_Attribute Column Name`,
                        `Bronze_Attribute Column Physical Name`,
                        `Bronze_Attribute Column Description`,
                        `Transformation Logic`,
                        `Join Column Description`,
                        `Function`,
                        `Silver_TABLE NAME`,
                        `Silver Table Physical Name`,
                        `Silver Attribute Column  Name`,
                        `Silver Attribute Column Physical Name`,
                        `Silver Attribute Column Definition`
                    FROM {self.catalog_schema}.{self.staging_table}
                    WHERE `Silver Attribute Column Physical Name` IS NOT NULL
                      AND TRIM(`Silver Attribute Column Physical Name`) != ''
                    ORDER BY `Silver_TABLE NAME`, `Silver Attribute Column Physical Name`
                """)
                
                for row in cursor.fetchall():
                    rows.append(PatternRow(
                        row_id=row[0],
                        subject_area=row[1],
                        bronze_table_name=row[2],
                        bronze_column_name=row[3],
                        bronze_column_physical=row[4],
                        bronze_column_description=row[5],
                        transformation_logic=row[6],
                        join_column_description=row[7],
                        function=row[8],
                        silver_table_name=row[9],
                        silver_table_physical=row[10],
                        silver_column_name=row[11],
                        silver_column_physical=row[12],
                        silver_column_definition=row[13]
                    ))
                    
        finally:
            connection.close()
        
        return rows
    
    def run(
        self,
        max_workers: int = 5,
        batch_size: int = 10,
        limit: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Run the pattern loading process.
        
        Args:
            max_workers: Number of parallel workers for LLM calls
            batch_size: Number of rows to insert in each batch
            limit: Optional limit on number of rows to process
            dry_run: If True, don't insert, just process and return results
            
        Returns:
            Statistics dictionary
        """
        print(f"Loading staging data from {self.catalog_schema}.{self.staging_table}...")
        rows = self.load_staging_data()
        
        if limit:
            rows = rows[:limit]
        
        self.stats["total"] = len(rows)
        print(f"Found {len(rows)} rows to process")
        
        if len(rows) == 0:
            return self.stats
        
        # Process rows in parallel
        print(f"Processing with {max_workers} workers...")
        processed_rows = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._process_row, row): row for row in rows}
            
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                processed_rows.append(result)
                
                self.stats["processed"] += 1
                
                if result["status"] == "success":
                    self.stats["success"] += 1
                elif result["status"] == "error":
                    self.stats["errors"] += 1
                    self.errors.append(result)
                else:
                    self.stats["skipped"] += 1
                
                # Progress update
                if (i + 1) % 10 == 0:
                    print(f"Progress: {i + 1}/{len(rows)} - Success: {self.stats['success']}, Errors: {self.stats['errors']}, Skipped: {self.stats['skipped']}")
        
        print(f"\nProcessing complete. Success: {self.stats['success']}, Errors: {self.stats['errors']}, Skipped: {self.stats['skipped']}")
        
        # Insert in batches
        if not dry_run and self.stats["success"] > 0:
            print(f"\nInserting {self.stats['success']} rows in batches of {batch_size}...")
            
            success_rows = [r for r in processed_rows if r["status"] == "success"]
            total_inserted = 0
            
            for i in range(0, len(success_rows), batch_size):
                batch = success_rows[i:i + batch_size]
                inserted = self._insert_batch(batch)
                total_inserted += inserted
                print(f"Inserted batch {i // batch_size + 1}: {inserted} rows")
            
            print(f"\nTotal inserted: {total_inserted}")
            self.stats["inserted"] = total_inserted
        
        return self.stats


# =============================================================================
# MAIN - For running as a script
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Load historical mapping patterns from CSV")
    parser.add_argument("--catalog-schema", required=True, help="Unity Catalog schema (e.g., oztest_dev.smartmapper)")
    parser.add_argument("--staging-table", required=True, help="Staging table name with CSV data")
    parser.add_argument("--llm-endpoint", default="databricks-meta-llama-3-3-70b-instruct", help="LLM endpoint name")
    parser.add_argument("--max-workers", type=int, default=5, help="Number of parallel workers")
    parser.add_argument("--batch-size", type=int, default=10, help="Insert batch size")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't insert, just process")
    
    args = parser.parse_args()
    
    loader = PatternLoader(
        catalog_schema=args.catalog_schema,
        staging_table=args.staging_table,
        llm_endpoint=args.llm_endpoint
    )
    
    stats = loader.run(
        max_workers=args.max_workers,
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run
    )
    
    print("\n=== Final Statistics ===")
    print(json.dumps(stats, indent=2))


