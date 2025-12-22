"""
Pattern Service for managing pattern deduplication and selection.

Handles:
- Computing pattern signatures from join_metadata
- Grouping patterns by signature (deduplication)
- Selecting best pattern based on usage count and recency
- Providing alternative patterns for user selection
"""
import hashlib
import json
from typing import Dict, List, Any, Optional
from collections import defaultdict
from databricks import sql as databricks_sql
from backend.services.config_service import ConfigService


class PatternService:
    """Service for pattern management, deduplication, and selection."""
    
    def __init__(self):
        self.config_service = ConfigService()
    
    def _get_db_config(self) -> Dict[str, str]:
        """Get database configuration."""
        config = self.config_service.get_config()
        catalog = config.databricks.catalog
        schema = config.databricks.schema
        return {
            "host": config.databricks.host,
            "http_path": config.databricks.http_path,
            "mapped_fields_table": f"{catalog}.{schema}.mapped_fields"
        }
    
    def compute_signature(self, join_metadata: Optional[Dict]) -> str:
        """
        Compute a signature hash representing the logical structure of a pattern.
        
        Two patterns with the same signature have the same transformation logic,
        just applied to different source fields.
        
        Args:
            join_metadata: The join_metadata JSON from mapped_fields
            
        Returns:
            16-character hex signature hash
        """
        if not join_metadata:
            return "direct_mapping"
        
        # Handle string input
        if isinstance(join_metadata, str):
            try:
                join_metadata = json.loads(join_metadata)
            except:
                return "parse_error"
        
        try:
            signature_parts = []
            
            # 1. Relationship type
            rel_type = join_metadata.get("source_relationship_type", "SINGLE")
            signature_parts.append(f"rel:{rel_type}")
            
            # 2. Number of source tables
            source_tables = join_metadata.get("source_tables", [])
            signature_parts.append(f"tables:{len(source_tables)}")
            
            # 3. Join types used (sorted for consistency)
            join_types = sorted([
                t.get("join_type", "").upper()
                for t in source_tables
                if t.get("join_type")
            ])
            if join_types:
                signature_parts.append(f"joins:{','.join(join_types)}")
            
            # 4. Transformations applied (sorted)
            transformations = join_metadata.get("transformations", [])
            if isinstance(transformations, list) and transformations:
                sorted_transforms = sorted([t.upper() for t in transformations if t])
                signature_parts.append(f"transforms:{','.join(sorted_transforms)}")
            
            # 5. Has aggregation?
            if join_metadata.get("aggregation_logic"):
                agg = join_metadata["aggregation_logic"]
                agg_func = agg.get("function", "").upper() if isinstance(agg, dict) else ""
                signature_parts.append(f"agg:{agg_func}")
            
            # 6. Union branch count
            union_logic = join_metadata.get("union_logic", {})
            if isinstance(union_logic, dict):
                branches = union_logic.get("branches", [])
                if branches:
                    signature_parts.append(f"union:{len(branches)}")
            
            # Create hash
            signature_string = "|".join(signature_parts)
            return hashlib.md5(signature_string.encode()).hexdigest()[:16]
            
        except Exception as e:
            print(f"[PatternService] Error computing signature: {e}")
            return "error"
    
    def get_signature_description(self, join_metadata: Optional[Dict]) -> str:
        """
        Get a human-readable description of the pattern type.
        
        Args:
            join_metadata: The join_metadata JSON
            
        Returns:
            Human-readable description like "JOIN (2 tables) + COALESCE, UPPER"
        """
        if not join_metadata:
            return "Direct mapping"
        
        if isinstance(join_metadata, str):
            try:
                join_metadata = json.loads(join_metadata)
            except:
                return "Unknown"
        
        try:
            parts = []
            
            # Relationship type
            rel_type = join_metadata.get("source_relationship_type", "SINGLE")
            source_tables = join_metadata.get("source_tables", [])
            
            if rel_type == "JOIN" or len(source_tables) > 1:
                parts.append(f"JOIN ({len(source_tables)} tables)")
            elif rel_type == "UNION":
                union_branches = len(join_metadata.get("union_logic", {}).get("branches", []))
                parts.append(f"UNION ({union_branches} sources)")
            elif rel_type == "AGGREGATION":
                agg = join_metadata.get("aggregation_logic", {})
                agg_func = agg.get("function", "AGG") if isinstance(agg, dict) else "AGG"
                parts.append(f"AGGREGATION ({agg_func})")
            else:
                parts.append("Single source")
            
            # Transformations
            transforms = join_metadata.get("transformations", [])
            if isinstance(transforms, list) and transforms:
                parts.append(", ".join(transforms[:3]))  # Show first 3
                if len(transforms) > 3:
                    parts.append(f"+{len(transforms) - 3} more")
            
            return " + ".join(parts) if parts else "Direct mapping"
            
        except Exception as e:
            return "Unknown"
    
    def get_all_patterns_for_column(
        self,
        tgt_table: str,
        tgt_column: str
    ) -> List[Dict[str, Any]]:
        """
        Get all mapped_fields records for a target column.
        
        Args:
            tgt_table: Target table physical name
            tgt_column: Target column physical name
            
        Returns:
            List of pattern dictionaries
        """
        db_config = self._get_db_config()
        
        with databricks_sql.connect(
            server_hostname=db_config["host"],
            http_path=db_config["http_path"]
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT 
                        mapped_field_id,
                        tgt_table_physical_name,
                        tgt_column_physical_name,
                        source_tables,
                        source_columns,
                        source_expression,
                        source_relationship_type,
                        transformations_applied,
                        join_metadata,
                        confidence_score,
                        mapped_ts,
                        created_by,
                        project_id,
                        is_approved_pattern
                    FROM {db_config['mapped_fields_table']}
                    WHERE UPPER(tgt_table_physical_name) = UPPER('{tgt_table}')
                      AND UPPER(tgt_column_physical_name) = UPPER('{tgt_column}')
                      AND mapping_status = 'ACTIVE'
                    ORDER BY mapped_ts DESC
                """)
                
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                patterns = []
                for row in rows:
                    pattern = dict(zip(columns, row))
                    # Parse join_metadata if it's a string
                    if pattern.get("join_metadata") and isinstance(pattern["join_metadata"], str):
                        try:
                            pattern["join_metadata_parsed"] = json.loads(pattern["join_metadata"])
                        except:
                            pattern["join_metadata_parsed"] = None
                    else:
                        pattern["join_metadata_parsed"] = pattern.get("join_metadata")
                    patterns.append(pattern)
                
                return patterns
    
    def group_patterns_by_signature(
        self,
        patterns: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group patterns by their computed signature.
        
        Args:
            patterns: List of pattern dictionaries
            
        Returns:
            Dictionary mapping signature -> list of patterns
        """
        groups = defaultdict(list)
        
        for pattern in patterns:
            join_metadata = pattern.get("join_metadata_parsed") or pattern.get("join_metadata")
            signature = self.compute_signature(join_metadata)
            pattern["_signature"] = signature
            pattern["_signature_description"] = self.get_signature_description(join_metadata)
            groups[signature].append(pattern)
        
        return dict(groups)
    
    def get_pattern_variants(
        self,
        tgt_table: str,
        tgt_column: str
    ) -> List[Dict[str, Any]]:
        """
        Get pattern variants (unique signatures) for a target column.
        
        Args:
            tgt_table: Target table physical name
            tgt_column: Target column physical name
            
        Returns:
            List of variant summaries, sorted by usage count descending
        """
        patterns = self.get_all_patterns_for_column(tgt_table, tgt_column)
        groups = self.group_patterns_by_signature(patterns)
        
        variants = []
        for signature, pattern_list in groups.items():
            # Get latest pattern in this group
            latest = max(pattern_list, key=lambda p: p.get("mapped_ts") or "")
            
            variants.append({
                "signature": signature,
                "description": latest.get("_signature_description", "Unknown"),
                "usage_count": len(pattern_list),
                "latest_mapped_ts": str(latest.get("mapped_ts", "")),
                "latest_pattern": {
                    "mapped_field_id": latest["mapped_field_id"],
                    "source_expression": latest.get("source_expression"),
                    "source_tables": latest.get("source_tables"),
                    "source_columns": latest.get("source_columns"),
                    "source_relationship_type": latest.get("source_relationship_type"),
                    "transformations_applied": latest.get("transformations_applied"),
                    "confidence_score": latest.get("confidence_score"),
                    "created_by": latest.get("created_by")
                }
            })
        
        # Sort by usage count (most used first), then by recency
        variants.sort(key=lambda v: (-v["usage_count"], v["latest_mapped_ts"]), reverse=False)
        
        return variants
    
    def select_best_pattern(
        self,
        patterns: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Select the best pattern from a list.
        
        Strategy: Pick from the signature group with highest usage count,
        then take the most recent pattern within that group.
        
        Args:
            patterns: List of all patterns for a column
            
        Returns:
            The best pattern, or None if no patterns
        """
        if not patterns:
            return None
        
        groups = self.group_patterns_by_signature(patterns)
        
        # Find the group with highest usage count
        best_group = None
        best_count = 0
        
        for signature, pattern_list in groups.items():
            if len(pattern_list) > best_count:
                best_count = len(pattern_list)
                best_group = pattern_list
        
        if not best_group:
            return patterns[0]  # Fallback to first pattern
        
        # Within the best group, pick the most recent
        best_pattern = max(best_group, key=lambda p: p.get("mapped_ts") or "")
        
        # Add metadata about selection
        best_pattern["_selected_from_count"] = best_count
        best_pattern["_total_variants"] = len(groups)
        
        return best_pattern
    
    def get_best_pattern_with_alternatives(
        self,
        tgt_table: str,
        tgt_column: str
    ) -> Dict[str, Any]:
        """
        Get the best pattern for a column along with alternative variants.
        
        Args:
            tgt_table: Target table physical name
            tgt_column: Target column physical name
            
        Returns:
            Dictionary with:
                - pattern: The selected best pattern
                - alternatives: List of alternative variant summaries
                - total_variants: Total number of unique pattern types
        """
        patterns = self.get_all_patterns_for_column(tgt_table, tgt_column)
        
        if not patterns:
            return {
                "pattern": None,
                "alternatives": [],
                "total_variants": 0
            }
        
        best = self.select_best_pattern(patterns)
        variants = self.get_pattern_variants(tgt_table, tgt_column)
        
        # Filter out the selected variant from alternatives
        selected_signature = best.get("_signature") if best else None
        alternatives = [v for v in variants if v["signature"] != selected_signature]
        
        return {
            "pattern": best,
            "alternatives": alternatives,
            "total_variants": len(variants)
        }
    
    def get_pattern_by_id(self, mapped_field_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific pattern by ID.
        
        Args:
            mapped_field_id: The mapped_field_id to fetch
            
        Returns:
            Pattern dictionary or None
        """
        db_config = self._get_db_config()
        
        with databricks_sql.connect(
            server_hostname=db_config["host"],
            http_path=db_config["http_path"]
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT 
                        mapped_field_id,
                        tgt_table_physical_name,
                        tgt_column_physical_name,
                        source_tables,
                        source_columns,
                        source_expression,
                        source_descriptions,
                        source_relationship_type,
                        transformations_applied,
                        join_metadata,
                        confidence_score,
                        mapped_ts,
                        created_by,
                        project_id,
                        is_approved_pattern
                    FROM {db_config['mapped_fields_table']}
                    WHERE mapped_field_id = {mapped_field_id}
                """)
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                columns = [desc[0] for desc in cursor.description]
                pattern = dict(zip(columns, row))
                
                # Parse join_metadata
                if pattern.get("join_metadata") and isinstance(pattern["join_metadata"], str):
                    try:
                        pattern["join_metadata_parsed"] = json.loads(pattern["join_metadata"])
                    except:
                        pattern["join_metadata_parsed"] = None
                
                return pattern


# Singleton instance
pattern_service = PatternService()

