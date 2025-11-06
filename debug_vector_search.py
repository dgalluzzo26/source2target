"""
Debug script to test vector search directly and diagnose low scores.
"""
from databricks import sql
from databricks.sdk import WorkspaceClient
import os

# Initialize workspace client
ws = WorkspaceClient()

# Get config from environment or defaults
server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME", "dbc-b4aafe92-6b8c.cloud.databricks.com")
http_path = os.getenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/173ea239ed13be7d")
index_name = "oztest_dev.source_to_target.silver_semantic_full_vs"
semantic_table = "oztest_dev.source_to_target.silver_semantic_full"

# Get OAuth token
headers = ws.config.authenticate()
access_token = headers['Authorization'].replace('Bearer ', '')

# Connect to SQL warehouse
connection = sql.connect(
    server_hostname=server_hostname,
    http_path=http_path,
    access_token=access_token
)

print("=" * 80)
print("VECTOR SEARCH DIAGNOSTIC")
print("=" * 80)

# Test 1: Check what's in the semantic table
print("\n1. Checking semantic table for 'SSN' or 'Manager' records...")
with connection.cursor() as cursor:
    query = f"""
    SELECT 
        tgt_table_name,
        tgt_column_name,
        tgt_comments,
        semantic_field
    FROM {semantic_table}
    WHERE 
        LOWER(tgt_table_name) LIKE '%manag%' OR
        LOWER(tgt_column_name) LIKE '%ssn%'
    LIMIT 5
    """
    cursor.execute(query)
    results = cursor.fetchall_arrow().to_pandas()
    print(f"\nFound {len(results)} records in semantic table:")
    for idx, row in results.iterrows():
        print(f"\nRecord {idx + 1}:")
        print(f"  Table: {row['tgt_table_name']}")
        print(f"  Column: {row['tgt_column_name']}")
        print(f"  Comments: {row['tgt_comments']}")
        print(f"  Semantic Field: {row['semantic_field'][:200]}...")

# Test 2: Check vector search index
print("\n" + "=" * 80)
print("2. Testing vector search with source field query...")
query_text = "TABLE NAME: T_MANGER; COLUMN NAME: SSN; COLUMN DESCRIPTION: Social Security Number; IS COLUMN NULLABLE: Not Null; COLUMN DATATYPE: STRING"
print(f"Query: {query_text}")

with connection.cursor() as cursor:
    escaped_query = query_text.replace("'", "''")
    query = f"""
    SELECT 
        tgt_table_name,
        tgt_column_name,
        semantic_field,
        search_score
    FROM vector_search(
        index => '{index_name}',
        query => '{escaped_query}',
        num_results => 10
    )
    ORDER BY search_score DESC
    """
    cursor.execute(query)
    results = cursor.fetchall_arrow().to_pandas()
    print(f"\nVector search returned {len(results)} results:")
    for idx, row in results.iterrows():
        print(f"\n  Rank {idx + 1}: {row['tgt_table_name']}.{row['tgt_column_name']}")
        print(f"    Score: {row['search_score']:.6f} ({row['search_score'] * 100:.2f}%)")
        print(f"    Semantic: {row['semantic_field'][:150]}...")

# Test 3: Check vector search index status
print("\n" + "=" * 80)
print("3. Checking vector search index status...")
try:
    index_info = ws.vector_search_indexes.get_index(index_name)
    print(f"Index Name: {index_info.name}")
    print(f"Index Status: {index_info.status}")
    print(f"Primary Key: {index_info.primary_key}")
    if hasattr(index_info, 'delta_sync_index_spec') and index_info.delta_sync_index_spec:
        print(f"Source Table: {index_info.delta_sync_index_spec.source_table}")
        if hasattr(index_info.delta_sync_index_spec, 'embedding_source_columns'):
            print(f"Embedding Columns: {index_info.delta_sync_index_spec.embedding_source_columns}")
except Exception as e:
    print(f"Error getting index info: {e}")

connection.close()
print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)

