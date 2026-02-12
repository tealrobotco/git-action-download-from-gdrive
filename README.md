# Download from Google Drive Action

A GitHub Action to download a specific file from Google Drive using service account credentials with built-in retry logic for handling indexing delays.

## Features

- 🔄 Automatic retry logic for handling Google Drive indexing delays
- 🔐 Service account authentication
- 📁 Support for both regular folders and Shared Drives
- 🎯 Configurable retry attempts and delays
- 📊 Verbose logging option for debugging
- ⚡ Composite action (no Docker required)

## Usage

```yaml
- name: Download from Google Drive
  uses: tealrobotco/git-action-download-from-gdrive@main
  with:
    credentials: ${{ secrets.DRIVE_CREDENTIALS }}
    folder-id: ${{ secrets.DRIVE_FOLDER_ID }}
    filename: "my-file.zip"
    max-attempts: 3
    retry-delay: 5
```

## Inputs

| Input          | Required | Default          | Description                                     |
| -------------- | -------- | ---------------- | ----------------------------------------------- |
| `credentials`  | Yes      | -                | Base64-encoded service account credentials JSON |
| `folder-id`    | Yes      | -                | Google Drive folder ID to search in             |
| `filename`     | Yes      | -                | Name of the file to download                    |
| `output-path`  | No       | Same as filename | Output path for the downloaded file             |
| `max-attempts` | No       | `3`              | Maximum number of download attempts             |
| `retry-delay`  | No       | `5`              | Delay in seconds between retry attempts         |
| `verbose`      | No       | `false`          | Enable verbose output for debugging             |

## Outputs

| Output      | Description                 |
| ----------- | --------------------------- |
| `file-path` | Path to the downloaded file |

## Google Drive Setup

### 1. Create a Service Account

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Drive API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"
4. Create a Service Account:
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the service account details
   - Click "Create and Continue"
   - Skip optional steps (no roles needed for basic Drive access)
   - Click "Done"

### 2. Generate Service Account Key

1. Click on the newly created service account
2. Go to the "Keys" tab
3. Click "Add Key" > "Create new key"
4. Choose "JSON" format
5. Click "Create" - this downloads a JSON file

The JSON file will look like this:

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "123456789...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/..."
}
```

### 3. Base64 Encode the Credentials

You need to base64-encode the JSON credentials file before adding it to GitHub Secrets:

**Linux/Mac:**

```bash
cat service-account-key.json | base64 -w 0 > encoded-credentials.txt
```

**Windows PowerShell:**

```powershell
[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Content service-account-key.json -Raw))) | Out-File -Encoding ASCII encoded-credentials.txt
```

**Online Tool:**

- Use [base64encode.org](https://www.base64encode.org/) (ensure you trust the site with your credentials)

### 4. Share Your Google Drive Folder

The service account needs access to the Google Drive folder via a shared drive.

Important: Google doesn't allow service accounts to access regular folders, only shared drives:

1. Create a new Shared Drive in Google Drive
2. Click the Shared Drive name's dropdown > "Manage members"
3. Click "Add members"
4. Add the service account email
5. Set role to "Viewer" or higher
6. Click "Send"

### 5. Get the Folder ID

1. Create a new folder in the Shared Drive if you don't have one yet
2. Click into the folder and copy the folder ID from the URL

The folder ID is found in the Google Drive URL:

```
https://drive.google.com/drive/folders/1A2B3C4D5E6F7G8H9I0J
                                          ^^^^^^^^^^^^^^^^^^^^
                                          This is your folder ID
```

### 6. Add Secrets to GitHub

1. Go to your GitHub repository
2. Navigate to "Settings" > "Secrets and variables" > "Actions"
3. Click "New repository secret"
4. Add two secrets:
   - **Name:** `DRIVE_CREDENTIALS`  
     **Value:** The base64-encoded credentials from step 3
   - **Name:** `DRIVE_FOLDER_ID`  
     **Value:** The folder ID from step 5

## Example Workflow

```yaml
name: Download and Deploy

on:
  workflow_dispatch:

jobs:
  download-and-process:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download Build from Google Drive
        id: download
        uses: tealrobotco/git-action-download-from-gdrive@main
        with:
          credentials: ${{ secrets.DRIVE_CREDENTIALS }}
          folder-id: ${{ secrets.DRIVE_FOLDER_ID }}
          filename: "Build-v1.0.0.zip"
          output-path: "build/output.zip"
          max-attempts: 3
          retry-delay: 5
          verbose: true

      - name: Extract Build
        run: |
          unzip ${{ steps.download.outputs.file-path }} -d build/

      - name: Process Build
        run: |
          # Your build processing steps here
          ls -la build/
```

## Retry Logic

This action includes built-in retry logic to handle Google Drive's indexing delays. When a file is uploaded to Google Drive, it may take some time before it becomes searchable via the API. The action will:

1. Search for the specified file
2. If not found, wait for the specified `retry-delay` seconds
3. Retry up to `max-attempts` times
4. On success, download the file
5. On failure, exit with an error

This is particularly useful when you upload a file in one workflow step and need to download it in a subsequent step.

## Troubleshooting

### File Not Found

- Verify the service account has access to the folder (check sharing settings)
- Verify the folder ID is correct
- Enable `verbose: true` to see all files in the folder
- Check if the file name matches exactly (case-sensitive)
- For recently uploaded files, increase `max-attempts` and `retry-delay`

### Authentication Errors

- Verify the credentials are correctly base64-encoded
- Ensure the Google Drive API is enabled in your Google Cloud project
- Check that the service account key hasn't been deleted or revoked
- Verify the secret is named correctly in GitHub

### Shared Drive Issues

- Ensure the service account is added as a member of the Shared Drive
- Verify you're using the folder ID from within the Shared Drive, not the Shared Drive ID itself
- The service account needs at least "Viewer" role

## License

This action is available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
