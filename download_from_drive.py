#!/usr/bin/env python3
"""
Download files from Google Drive with retry logic.

This script authenticates with Google Drive using a service account and downloads
a specified file from a folder, with built-in retry logic for handling indexing delays.
"""

import os
import base64
import json
import time
import argparse
import sys
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Download files from Google Drive using service account credentials.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download using environment variables
  python download_from_drive.py --filename "Build-StandaloneWindows64-v0.1.8.zip"
  
  # Download with explicit credentials
  python download_from_drive.py --filename "Build-StandaloneWindows64-v0.1.8.zip" \\
    --credentials-base64 "base64_encoded_creds" \\
    --folder-id "1234567890abcdef"
  
  # Download with custom retry settings
  python download_from_drive.py --filename "Build-StandaloneWindows64-v0.1.8.zip" \\
    --max-attempts 15 --retry-delay 45
        """
    )
    
    parser.add_argument(
        '--filename',
        required=True,
        help='Name of the file to download from Google Drive'
    )
    
    parser.add_argument(
        '--credentials-base64',
        help='Base64-encoded service account credentials JSON (default: from DRIVE_CREDENTIALS env var)'
    )
    
    parser.add_argument(
        '--folder-id',
        help='Google Drive folder ID to search in (default: from DRIVE_FOLDER_ID env var)'
    )
    
    parser.add_argument(
        '--output-path',
        help='Output path for the downloaded file (default: current directory with same filename)'
    )
    
    parser.add_argument(
        '--max-attempts',
        type=int,
        default=3,
        help='Maximum number of attempts (default: 3)'
    )
    
    parser.add_argument(
        '--retry-delay',
        type=int,
        default=5,
        help='Delay in seconds between attempts (default: 5)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()


def get_credentials(credentials_base64):
    """Decode and load service account credentials."""
    try:
        creds_json = base64.b64decode(credentials_base64).decode('utf-8')
        creds_dict = json.loads(creds_json)
        
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        return credentials
    except Exception as e:
        print(f"Error decoding credentials: {e}", file=sys.stderr)
        sys.exit(1)


def list_folder_files(service, folder_id, verbose=False):
    """List all files in the specified folder for debugging."""
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name, createdTime, size)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            print(f"Found {len(files)} file(s) in folder:")
            for f in files:
                size = f.get('size', 'unknown')
                created = f.get('createdTime', 'unknown')
                if verbose:
                    print(f"  - {f['name']} (ID: {f['id']}, Size: {size} bytes, Created: {created})")
                else:
                    print(f"  - {f['name']} (created: {created})")
        else:
            print("No files found in folder")
            
        return files
    except Exception as e:
        print(f"Error listing folder files: {e}", file=sys.stderr)
        return []


def download_file(service, file_id, file_name, output_path):
    """Download a file from Google Drive."""
    try:
        print(f"Downloading {file_name}...")
        
        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            progress = int(status.progress() * 100)
            print(f"Download {progress}%")
        
        # Save file
        with open(output_path, 'wb') as f:
            f.write(fh.getvalue())
        
        print(f"Successfully downloaded to {output_path}")
        return True
    except Exception as e:
        print(f"Error downloading file: {e}", file=sys.stderr)
        return False


def search_and_download(service, folder_id, filename, output_path, max_attempts, retry_delay, verbose):
    """Search for a file in Google Drive and download it with retry logic."""
    print(f"Looking for file: {filename}")
    print(f"In folder ID: {folder_id}")
    
    for attempt in range(max_attempts):
        print(f"\nAttempt {attempt + 1}/{max_attempts}")
        
        # Search for the file
        query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
        try:
            results = service.files().list(
                q=query,
                fields="files(id, name, createdTime, size)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                file_info = files[0]
                file_id = file_info['id']
                file_name = file_info['name']
                file_size = file_info.get('size', 'unknown')
                
                print(f"Found file: {file_name}")
                if verbose:
                    print(f"  ID: {file_id}")
                    print(f"  Size: {file_size} bytes")
                    print(f"  Created: {file_info.get('createdTime', 'unknown')}")
                
                # Download the file
                if download_file(service, file_id, file_name, output_path):
                    return True
                else:
                    print("Download failed, but file was found")
                    return False
            else:
                print(f"File not found yet.")
                if verbose:
                    print("Listing all files in folder to debug...")
                    list_folder_files(service, folder_id, verbose)
                
                if attempt < max_attempts - 1:
                    print(f"Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
        except Exception as e:
            print(f"Error during search: {e}", file=sys.stderr)
            if attempt < max_attempts - 1:
                print(f"Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
    
    print(f"\nFailed to find {filename} after {max_attempts} attempts", file=sys.stderr)
    return False


def main():
    """Main execution function."""
    args = parse_arguments()
    
    # Get credentials from argument or environment variable
    credentials_base64 = args.credentials_base64 or os.environ.get('DRIVE_CREDENTIALS')
    if not credentials_base64:
        print("Error: Credentials not provided. Use --credentials-base64 or set DRIVE_CREDENTIALS env var",
              file=sys.stderr)
        sys.exit(1)
    
    # Get folder ID from argument or environment variable
    folder_id = args.folder_id or os.environ.get('DRIVE_FOLDER_ID')
    if not folder_id:
        print("Error: Folder ID not provided. Use --folder-id or set DRIVE_FOLDER_ID env var",
              file=sys.stderr)
        sys.exit(1)
    
    # Determine output path
    output_path = args.output_path or args.filename
    
    # Authenticate and build service
    credentials = get_credentials(credentials_base64)
    service = build('drive', 'v3', credentials=credentials)
    
    # Search and download the file
    success = search_and_download(
        service=service,
        folder_id=folder_id,
        filename=args.filename,
        output_path=output_path,
        max_attempts=args.max_attempts,
        retry_delay=args.retry_delay,
        verbose=args.verbose
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
