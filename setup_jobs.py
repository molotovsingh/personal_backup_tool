"""
Setup script to create the two specific backup jobs mentioned in README:
1. Photos (509GB): Seagate → MacBook network
2. Arq Backup (343GB): Seagate → Google Drive
"""
from core.job_manager import JobManager
from utils.rclone_helper import is_rclone_installed, list_remotes
import sys

print("=" * 60)
print("Backup Manager - Job Configuration Setup")
print("=" * 60)

manager = JobManager()

# Check current jobs
existing_jobs = manager.list_jobs()
print(f"\nCurrent jobs: {len(existing_jobs)}")
for job in existing_jobs:
    print(f"  - {job['name']} ({job['type']}): {job['status']}")

print("\n" + "=" * 60)
print("Job 1: Photos Backup (Seagate → MacBook Network)")
print("=" * 60)

# Prompt for Photos backup configuration
print("\nThis job will backup photos from a Seagate drive to MacBook network share.")
print("Expected size: ~509GB")
print()

create_photos = input("Create Photos backup job? (y/n): ").lower().strip()

if create_photos == 'y':
    print("\nEnter the source path (e.g., /Volumes/Seagate/Photos):")
    photos_source = input("Source: ").strip()

    print("\nEnter the destination path (e.g., /Volumes/MacBookShare/Photos):")
    photos_dest = input("Destination: ").strip()

    print("\nSet bandwidth limit? (optional, helps prevent network saturation)")
    use_bw = input("Set bandwidth limit? (y/n): ").lower().strip()

    settings = {}
    if use_bw == 'y':
        bw_limit = input("Bandwidth limit in KB/s (e.g., 5000 for 5MB/s): ").strip()
        try:
            settings['bandwidth_limit'] = int(bw_limit)
        except ValueError:
            print("Invalid bandwidth, skipping...")

    # Create the job
    success, msg, job = manager.create_job(
        name="Photos Backup",
        source=photos_source,
        dest=photos_dest,
        job_type="rsync",
        settings=settings
    )

    if success:
        print(f"\n✓ {msg}")
        print(f"  Job ID: {job.id}")
        print(f"  Source: {job.source}")
        print(f"  Dest: {job.dest}")
        if settings:
            print(f"  Bandwidth: {settings.get('bandwidth_limit', 'unlimited')} KB/s")
    else:
        print(f"\n✗ Failed: {msg}")
else:
    print("Skipped Photos backup job")

print("\n" + "=" * 60)
print("Job 2: Arq Backup (Seagate → Google Drive)")
print("=" * 60)

# Check if rclone is configured
is_installed, rclone_msg = is_rclone_installed()
if not is_installed:
    print("\n⚠️  rclone is not installed!")
    print("   Install with: brew install rclone")
    print("   Then run: rclone config")
    print("\nSkipping Arq Backup job...")
else:
    remotes = list_remotes()
    if not remotes:
        print("\n⚠️  No rclone remotes configured!")
        print("   Run: rclone config")
        print("   Configure a Google Drive remote (suggest name: 'gdrive')")
        print("\nSkipping Arq Backup job...")
    else:
        print(f"\n✓ rclone is installed with {len(remotes)} remote(s):")
        for i, remote in enumerate(remotes, 1):
            print(f"  {i}. {remote}")

        print("\nThis job will backup Arq data to Google Drive via rclone.")
        print("Expected size: ~343GB")
        print()

        create_arq = input("Create Arq Backup job? (y/n): ").lower().strip()

        if create_arq == 'y':
            print("\nEnter the source path (e.g., /Volumes/Seagate/ArqBackup):")
            arq_source = input("Source: ").strip()

            print("\nSelect the rclone remote for Google Drive:")
            for i, remote in enumerate(remotes, 1):
                print(f"  {i}. {remote}")

            remote_choice = input(f"Enter number (1-{len(remotes)}): ").strip()
            try:
                remote_idx = int(remote_choice) - 1
                if 0 <= remote_idx < len(remotes):
                    selected_remote = remotes[remote_idx]
                else:
                    print("Invalid choice, using first remote")
                    selected_remote = remotes[0]
            except ValueError:
                print("Invalid input, using first remote")
                selected_remote = remotes[0]

            print(f"\nEnter the path on {selected_remote} (e.g., ArqBackup):")
            remote_path = input("Remote path: ").strip()

            arq_dest = f"{selected_remote}:{remote_path}"

            print("\nSet bandwidth limit? (recommended for large cloud uploads)")
            use_bw = input("Set bandwidth limit? (y/n): ").lower().strip()

            settings = {}
            if use_bw == 'y':
                bw_limit = input("Bandwidth limit in KB/s (e.g., 2000 for 2MB/s): ").strip()
                try:
                    settings['bandwidth_limit'] = int(bw_limit)
                except ValueError:
                    print("Invalid bandwidth, skipping...")

            # Create the job
            success, msg, job = manager.create_job(
                name="Arq to Google Drive",
                source=arq_source,
                dest=arq_dest,
                job_type="rclone",
                settings=settings
            )

            if success:
                print(f"\n✓ {msg}")
                print(f"  Job ID: {job.id}")
                print(f"  Source: {job.source}")
                print(f"  Dest: {job.dest}")
                if settings:
                    print(f"  Bandwidth: {settings.get('bandwidth_limit', 'unlimited')} KB/s")
            else:
                print(f"\n✗ Failed: {msg}")
        else:
            print("Skipped Arq Backup job")

print("\n" + "=" * 60)
print("Setup Complete!")
print("=" * 60)

# Show final job list
final_jobs = manager.list_jobs()
print(f"\nTotal configured jobs: {len(final_jobs)}")
for job in final_jobs:
    print(f"  - {job['name']} ({job['type']}): {job['status']}")

print("\nTo manage jobs, run:")
print("  uv run uvicorn fastapi_app:app --host 0.0.0.0 --port 5001 --reload")
print("\nThen navigate to http://localhost:5001/jobs to start your backups!")
