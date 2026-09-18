#!/usr/bin/env python
"""
Quick verification script to check if GCS migration was successful.
This script verifies that all files are accessible on GCS.

Usage:
    python verify_gcs.py
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

from apps.ingestion.models import PurchaseOrder
from google.cloud import storage
from google.oauth2 import service_account


def verify_migration():
    """Verify that all files are accessible on GCS."""

    print("=" * 70)
    print("GCS MIGRATION VERIFICATION")
    print("=" * 70)

    # Check environment
    bucket_name = os.environ.get('GS_BUCKET_NAME')
    use_gcs = os.environ.get('USE_GCS', 'False') == 'True'
    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

    print(f"\n📋 Configuration:")
    print(f"   USE_GCS: {use_gcs}")
    print(f"   Bucket: {bucket_name}")
    print(f"   Credentials: {credentials_path}")

    if not use_gcs:
        print("\n⚠️  WARNING: USE_GCS is False")
        return

    if not bucket_name:
        print("\n❌ ERROR: GS_BUCKET_NAME not set")
        return

    if not credentials_path or not os.path.exists(credentials_path):
        print(f"\n❌ ERROR: Credentials file not found: {credentials_path}")
        return

    # Initialize GCS client
    print("\n🔑 Connecting to Google Cloud Storage...")
    try:
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = storage.Client(credentials=credentials, project=credentials.project_id)
        bucket = client.bucket(bucket_name)

        if bucket.exists():
            print(f"   ✅ Connected to bucket: {bucket_name}")
        else:
            print(f"   ❌ Bucket '{bucket_name}' does not exist")
            return
    except Exception as e:
        print(f"   ❌ Error connecting to GCS: {e}")
        return

    # Get all PurchaseOrders
    print("\n📦 Scanning Purchase Orders...")
    purchase_orders = PurchaseOrder.objects.exclude(source_file='').exclude(source_file__isnull=True)
    total = purchase_orders.count()

    print(f"   Found {total} Purchase Orders with files")

    if total == 0:
        print("\n✅ No files to verify!")
        return

    # Verify files
    print("\n🔍 Verifying files on GCS...")
    verified = 0
    missing = 0
    errors = []

    for i, po in enumerate(purchase_orders, 1):
        try:
            print(f"\r   [{i}/{total}] Checking...", end='', flush=True)

            file_path = po.source_file.name
            blob = bucket.blob(file_path)

            if blob.exists():
                verified += 1
            else:
                missing += 1
                errors.append(f"PO #{po.id}: {file_path} - NOT FOUND")

        except Exception as e:
            missing += 1
            errors.append(f"PO #{po.id}: {file_path} - ERROR: {e}")

    print(f"\n\n{'=' * 70}")
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    print(f"✅ Files verified on GCS: {verified}")
    print(f"❌ Missing files: {missing}")

    if errors:
        print(f"\n⚠️  Errors found:")
        for error in errors[:20]:
            print(f"   - {error}")
        if len(errors) > 20:
            print(f"   ... and {len(errors) - 20} more")
    else:
        print(f"\n🎉 All files are accessible on GCS!")

    # Check bucket storage usage
    print(f"\n💾 Checking bucket storage...")
    try:
        total_size = 0
        file_count = 0

        blobs = bucket.list_blobs(prefix='po_pdfs/')
        for blob in blobs:
            total_size += blob.size
            file_count += 1

        print(f"   Files in bucket: {file_count}")
        print(f"   Total size: {total_size / (1024*1024):.2f} MB")
        print(f"   Average file size: {total_size / file_count / 1024:.1f} KB" if file_count > 0 else "   No files")

    except Exception as e:
        print(f"   ⚠️  Could not check storage: {e}")


def main():
    """Main entry point."""
    try:
        verify_migration()
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
