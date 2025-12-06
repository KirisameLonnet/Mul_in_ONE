#!/usr/bin/env python3
"""Milvus Collection Migration Script

This script migrates old Milvus collections from the format:
  {username}_persona_{persona_id}_rag
to the new format:
  u_{username}_persona_{persona_id}_rag

This is required because Milvus collection names must start with a letter or underscore,
not a digit. The old format failed when username started with a number.

Usage:
    python scripts/migrate_milvus_collections.py [--dry-run] [--delete-old]

Options:
    --dry-run: Show what would be migrated without making changes
    --delete-old: Delete old collections after successful migration (use with caution)
"""

import argparse
import logging
import sys
from typing import List, Tuple

try:
    from pymilvus import connections, utility, Collection, CollectionSchema, FieldSchema, DataType
except ImportError:
    print("Error: pymilvus not installed. Install with: pip install pymilvus")
    sys.exit(1)

# Configuration
DEFAULT_MILVUS_URI = "http://localhost:19530"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def identify_old_collections() -> List[str]:
    """Identify collections that need migration.
    
    Returns:
        List of old collection names that start with a digit.
    """
    all_collections = utility.list_collections()
    old_collections = []
    
    for name in all_collections:
        # Check if collection name starts with digit and contains persona pattern
        if name and name[0].isdigit() and '_persona_' in name and '_rag' in name:
            old_collections.append(name)
    
    return old_collections


def generate_new_name(old_name: str) -> str:
    """Generate new collection name with 'u_' prefix.
    
    Args:
        old_name: Old collection name
        
    Returns:
        New collection name with u_ prefix
    """
    return f"u_{old_name}"


def migrate_collection(old_name: str, new_name: str, dry_run: bool = False) -> Tuple[bool, str]:
    """Migrate a single collection to new naming format.
    
    Args:
        old_name: Source collection name
        new_name: Target collection name
        dry_run: If True, don't actually perform migration
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Check if target already exists
        if utility.has_collection(new_name):
            return False, f"Target collection '{new_name}' already exists"
        
        if dry_run:
            return True, f"Would migrate: {old_name} -> {new_name}"
        
        # Load old collection
        old_coll = Collection(old_name)
        old_coll.load()
        
        # Get schema
        old_schema = old_coll.schema
        logger.info(f"Old collection schema: {old_schema.description}")
        
        # Query all data (note: this loads everything into memory)
        # For very large collections, consider batch processing
        logger.info(f"Querying data from {old_name}...")
        results = old_coll.query(
            expr="",
            output_fields=["*"],
            limit=16384  # Milvus query limit
        )
        
        doc_count = len(results)
        logger.info(f"Retrieved {doc_count} documents from {old_name}")
        
        if doc_count == 0:
            logger.warning(f"Collection {old_name} is empty, creating empty target")
        
        # Create new collection with same schema
        logger.info(f"Creating new collection: {new_name}")
        new_schema = CollectionSchema(
            fields=old_schema.fields,
            description=f"Migrated from {old_name} on 2025-12-06",
            enable_dynamic_field=old_schema.enable_dynamic_field
        )
        new_coll = Collection(name=new_name, schema=new_schema)
        
        # Insert data if any exists
        if doc_count > 0:
            logger.info(f"Inserting {doc_count} documents into {new_name}...")
            
            # Prepare column-based data for Milvus
            # Extract field data into columns
            field_data = {}
            for field in old_schema.fields:
                if not field.is_primary and field.dtype != DataType.FLOAT_VECTOR:
                    # Skip auto-generated fields
                    continue
                field_data[field.name] = [row.get(field.name) for row in results]
            
            # Build column list in schema order
            data_columns = []
            for field in old_schema.fields:
                if field.name in field_data:
                    data_columns.append(field_data[field.name])
            
            new_coll.insert(data_columns)
            new_coll.flush()
            logger.info(f"Data insertion completed for {new_name}")
        
        # Copy indexes
        logger.info(f"Copying indexes from {old_name} to {new_name}...")
        for index_info in old_coll.indexes:
            field_name = index_info.field_name
            index_params = index_info.params
            
            logger.info(f"Creating index on field '{field_name}'...")
            new_coll.create_index(
                field_name=field_name,
                index_params=index_params
            )
        
        # Load new collection
        new_coll.load()
        logger.info(f"New collection {new_name} loaded and ready")
        
        return True, f"Successfully migrated {old_name} -> {new_name} ({doc_count} docs)"
        
    except Exception as e:
        logger.exception(f"Error migrating {old_name}")
        return False, f"Migration failed: {str(e)}"


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Milvus collections to new naming format"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show what would be migrated without making changes"
    )
    parser.add_argument(
        '--delete-old',
        action='store_true',
        help="Delete old collections after successful migration (use with caution!)"
    )
    parser.add_argument(
        '--milvus-uri',
        default=DEFAULT_MILVUS_URI,
        help=f"Milvus connection URI (default: {DEFAULT_MILVUS_URI})"
    )
    
    args = parser.parse_args()
    
    # Connect to Milvus
    logger.info(f"Connecting to Milvus at {args.milvus_uri}...")
    connections.connect(alias="default", uri=args.milvus_uri)
    
    # Identify collections to migrate
    logger.info("Scanning for collections to migrate...")
    old_collections = identify_old_collections()
    
    if not old_collections:
        logger.info("No collections found that need migration")
        return 0
    
    logger.info(f"Found {len(old_collections)} collections to migrate:")
    for old_name in old_collections:
        new_name = generate_new_name(old_name)
        logger.info(f"  {old_name} -> {new_name}")
    
    if args.dry_run:
        logger.info("\n[DRY RUN] No changes will be made")
    
    # Confirm before proceeding (skip in dry-run)
    if not args.dry_run:
        response = input("\nProceed with migration? (yes/no): ").strip().lower()
        if response != 'yes':
            logger.info("Migration cancelled by user")
            return 0
    
    # Perform migrations
    logger.info("\n" + "="*60)
    logger.info("Starting migration...")
    logger.info("="*60 + "\n")
    
    success_count = 0
    failed_count = 0
    failed_collections = []
    
    for old_name in old_collections:
        new_name = generate_new_name(old_name)
        logger.info(f"\nMigrating: {old_name} -> {new_name}")
        
        success, message = migrate_collection(old_name, new_name, args.dry_run)
        logger.info(f"Result: {message}")
        
        if success:
            success_count += 1
            
            # Delete old collection if requested
            if not args.dry_run and args.delete_old:
                try:
                    logger.warning(f"Deleting old collection: {old_name}")
                    utility.drop_collection(old_name)
                    logger.info(f"Old collection {old_name} deleted")
                except Exception as e:
                    logger.error(f"Failed to delete old collection {old_name}: {e}")
        else:
            failed_count += 1
            failed_collections.append((old_name, message))
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("Migration Summary")
    logger.info("="*60)
    logger.info(f"Total collections: {len(old_collections)}")
    logger.info(f"Successfully migrated: {success_count}")
    logger.info(f"Failed: {failed_count}")
    
    if failed_collections:
        logger.error("\nFailed migrations:")
        for old_name, reason in failed_collections:
            logger.error(f"  {old_name}: {reason}")
    
    if args.dry_run:
        logger.info("\n[DRY RUN] No actual changes were made")
    else:
        logger.info("\nMigration completed!")
        if args.delete_old:
            logger.warning("Old collections were deleted")
        else:
            logger.info("Old collections are still present. Use --delete-old to remove them.")
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
