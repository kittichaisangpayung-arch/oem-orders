#!/usr/bin/env python
"""
Script to migrate existing PDF files from local storage to Google Cloud Storage.
Run this after setting up GCS credentials and environment variables.

Usage:
    python migrate_to_gcs.py [--dry-run] [--batch-size=100]

Options:
    --dry-run       Show what would be migrated without actually uploading
    --batch-size    Number of files to process at once (default: 100)
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oem_orders.settings')
django.setup()

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files import File
from apps.ingestion.models import PurchaseOrder
from google.cloud import storage
from google.oauth2 import service_account


def get_gcs_client():
    """Initialize and return GCS client."""
    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credentials file not found: {credentials_path}")

    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    return storage.Client(credentials=credentials, project=credentials.project_id)


def migrate_files(dry_run=False, batch_size=100):
    """Migrate all PurchaseOrder PDF files to GCS."""

    print("=" * 70)
    print("PDF MIGRATION TO GOOGLE CLOUD STORAGE")
    print("=" * 70)

    # Check environment
    bucket_name = os.environ.get('GS_BUCKET_NAME')
    use_gcs = os.environ.get('USE_GCS', 'False') == 'True'

    print(f"\n📋 Configuration:")
    print(f"   USE_GCS: {use_gcs}")
    print(f"   Bucket: {bucket_name}")
    print(f"   Dry Run: {dry_run}")
    print(f"   Batch Size: {batch_size}")

    if not use_gcs:
        print("\n⚠️  WARNING: USE_GCS is False. Set USE_GCS=True to enable GCS storage.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return

    if not bucket_name:
        raise ValueError("GS_BUCKET_NAME environment variable not set")

    # Initialize GCS client
    print("\n🔑 Connecting to Google Cloud Storage...")
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)

        # Test bucket access
        if bucket.exists():
            print(f"   ✅ Connected to bucket: {bucket_name}")
        else:
            raise ValueError(f"Bucket '{bucket_name}' does not exist")
    except Exception as e:
        print(f"   ❌ Error connecting to GCS: {e}")
        return

    # Get all PurchaseOrders with files
    print("\n📦 Scanning Purchase Orders...")
    purchase_orders = PurchaseOrder.objects.exclude(source_file='').exclude(source_file__isnull=True)
    total = purchase_orders.count()

    print(f"   Found {total} Purchase Orders with files")

    if total == 0:
        print("\n✅ No files to migrate!")
        return

    # Check which files need migration
    print("\n🔍 Checking which files need migration...")
    to_migrate = []
    already_on_gcs = []
    missing_files = []

    for po in purchase_orders:
        file_path = po.source_file.name

        # Check if file is already on GCS (path doesn't start with local path)
        if file_path.startswith('http') or file_path.startswith('gs://'):
            already_on_gcs.append(po)
            continue

        # Check if local file exists
        local_path = os.path.join(settings.MEDIA_ROOT, file_path)
        if os.path.exists(local_path):
            to_migrate.append((po, local_path, file_path))
        else:
            missing_files.append((po, file_path))

    print(f"\n📊 Summary:")
    print(f"   ✅ Already on GCS: {len(already_on_gcs)}")
    print(f"   📤 Need to migrate: {len(to_migrate)}")
    print(f"   ❌ Missing files: {len(missing_files)}")

    if missing_files:
        print(f"\n⚠️  Missing files:")
        for po, file_path in missing_files[:10]:
            print(f"   - PO #{po.id}: {file_path}")
        if len(missing_files) > 10:
            print(f"   ... and {len(missing_files) - 10} more")

    if not to_migrate:
        print("\n✅ All files are already on GCS!")
        return

    # Calculate total size
    total_size = sum(os.path.getsize(local_path) for _, local_path, _ in to_migrate)
    print(f"\n💾 Total size to migrate: {total_size / (1024*1024):.2f} MB")

    if dry_run:
        print("\n🔍 DRY RUN - Files that would be migrated:")
        for i, (po, local_path, file_path) in enumerate(to_migrate[:20], 1):
            file_size = os.path.getsize(local_path) / 1024
            print(f"   {i}. PO #{po.id}: {file_path} ({file_size:.1f} KB)")
        if len(to_migrate) > 20:
            print(f"   ... and {len(to_migrate) - 20} more")
        print("\n✅ Dry run complete. Run without --dry-run to actually migrate.")
        return

    # Confirm migration
    print("\n⚠️  This will upload files to GCS and update the database.")
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        return

    # Migrate files
    print(f"\n📤 Starting migration...")
    success_count = 0
    error_count = 0

    for i, (po, local_path, file_path) in enumerate(to_migrate, 1):
        try:
            print(f"\r   [{i}/{len(to_migrate)}] Uploading: {file_path[:50]}...", end='', flush=True)

            # Upload to GCS
            blob = bucket.blob(file_path)
            blob.upload_from_filename(local_path)

            # Update database - just verify the path is correct
            # Django with GCS storage will automatically handle the URL
            po.source_file.name = file_path
            po.save(update_fields=['source_file'])

            success_count += 1

        except Exception as e:
            error_count += 1
            print(f"\n   ❌ Error uploading PO #{po.id}: {e}")
            continue

    print(f"\n\n{'=' * 70}")
    print("MIGRATION COMPLETE")
    print("=" * 70)
    print(f"✅ Successfully migrated: {success_count} files")
    print(f"❌ Errors: {error_count} files")
    print(f"💾 Total uploaded: {sum(os.path.getsize(local_path) for _, local_path, _ in to_migrate[:success_count]) / (1024*1024):.2f} MB")

    if success_count > 0:
        print(f"\n🗑️  You can now delete local files to free up space:")
        print(f"   rm -rf {settings.MEDIA_ROOT}/po_pdfs/")
        print(f"\n⚠️  But backup first!")
        print(f"   tar -czf media_backup.tar.gz {settings.MEDIA_ROOT}/")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate PDF files to Google Cloud Storage')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without uploading')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of files to process at once')

    args = parser.parse_args()

    try:
        migrate_files(dry_run=args.dry_run, batch_size=args.batch_size)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
