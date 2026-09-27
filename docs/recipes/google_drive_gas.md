# Recipe: Export Raw Withings Measurements to Google Drive via Google Apps Script (GAS)

This recipe shows how to securely archive your raw Withings measurements (including Withings Body Scan segmental muscle/fat mass, electrodermal activity / EDA, vascular age, and ECG data) directly into your personal **Google Drive** without saving sensitive health data on disk or in CI/CD runner environments (e.g. GitHub Actions).

---

## 1. How It Works

```
┌─────────────────┐      HTTP POST       ┌────────────────────────┐      Drive API      ┌──────────────────────┐
│  withings-sync  │ ───────────────────> │   Google Apps Script   │ ──────────────────> │     Google Drive     │
│  (CLI / Docker) │   (with secret)      │  (Web App Endpoint)    │                     │  (Health/withings/)  │
└─────────────────┘                      └────────────────────────┘                     └──────────────────────┘
```

1. `withings-sync` fetches raw measurement data from Withings API.
2. It sends an HTTP POST request to the Google Apps Script Web App URL containing the JSON payload and your secret authentication token.
3. Google Apps Script validates the secret token and saves the JSON file into a dedicated folder in your Google Drive (e.g., `Health/data/withings/raw/`).

---

## 2. Setup Google Apps Script (GAS)

### Step 2.1: Create a new Apps Script project
1. Open [Google Drive](https://drive.google.com/).
2. Click **New** > **More** > **Google Apps Script** (or visit [script.google.com](https://script.google.com/)).
3. Name your project (e.g., `Withings Data Receiver`).

### Step 2.2: Paste the Receiver Script
Replace the contents of `Code.gs` with the following:

```javascript
/**
 * Withings Raw Data Receiver for Google Drive
 */
function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "No post data received"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    const payload = JSON.parse(e.postData.contents);
    const expectedSecret = PropertiesService.getScriptProperties().getProperty("WEBHOOK_SECRET");

    // Authenticate request
    if (expectedSecret && payload.secret !== expectedSecret) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "Unauthorized: Invalid secret"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // Target folder in Google Drive (created recursively if missing)
    const folderPath = payload.folder_path || "Health/data/withings/raw";
    const targetFolder = getOrCreateFolderByPath(folderPath);

    const filename = payload.filename || ("withings_raw_" + Utilities.formatDate(new Date(), "UTC", "yyyy-MM-dd_HHmmss") + ".json");
    const jsonString = JSON.stringify(payload.data || payload, null, 2);

    // Update existing file or create new
    const existingFiles = targetFolder.getFilesByName(filename);
    let file;
    if (existingFiles.hasNext()) {
      file = existingFiles.next();
      file.setContent(jsonString);
    } else {
      file = targetFolder.createFile(filename, jsonString, MimeType.PLAIN_TEXT);
    }

    // Optionally keep a latest snapshot file
    if (payload.update_latest !== false) {
      const latestFilename = "withings_raw_latest.json";
      const latestFiles = targetFolder.getFilesByName(latestFilename);
      if (latestFiles.hasNext()) {
        latestFiles.next().setContent(jsonString);
      } else {
        targetFolder.createFile(latestFilename, jsonString, MimeType.PLAIN_TEXT);
      }
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      filename: filename,
      fileId: file.getId(),
      folderPath: folderPath
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Resolves or creates nested folder path under root Drive.
 */
function getOrCreateFolderByPath(pathStr) {
  const parts = pathStr.split("/").map(s => s.trim()).filter(s => s.length > 0);
  let currentFolder = DriveApp.getRootFolder();

  for (const part of parts) {
    const subFolders = currentFolder.getFoldersByName(part);
    if (subFolders.hasNext()) {
      currentFolder = subFolders.next();
    } else {
      currentFolder = currentFolder.createFolder(part);
    }
  }
  return currentFolder;
}
```

### Step 2.3: Set Script Property (`WEBHOOK_SECRET`)
1. In the Apps Script editor, click the gear icon **Project Settings** (left sidebar).
2. Scroll down to **Script Properties** and click **Add script property**.
   - **Property**: `WEBHOOK_SECRET`
   - **Value**: Any strong random string (e.g., 32 characters alphanumeric).
3. Click **Save script properties**.

### Step 2.4: Deploy as Web App
1. Click **Deploy** > **New deployment** (top right).
2. Select type: **Web app** (click the gear next to "Select type").
3. Configure:
   - **Description**: `Withings Webhook Exporter`
   - **Execute as**: `Me (<your-email>)`
   - **Who has access**: `Anyone` *(Note: The request is secured by your `WEBHOOK_SECRET`)*
4. Click **Deploy** and authorize permissions when prompted.
5. Copy the generated **Web app URL** (`https://script.google.com/macros/s/.../exec`).

---

## 3. Usage with withings-sync

### Via CLI Flags:
```bash
withings-sync \
  --webhook-url "https://script.google.com/macros/s/AKfycb.../exec" \
  --webhook-secret "your_secret_token"
```

### Via Environment Variables (.env / Shell):
```bash
export WEBHOOK_URL="https://script.google.com/macros/s/AKfycb.../exec"
export WEBHOOK_SECRET="your_secret_token"

withings-sync
```

### Via Docker Compose:
```yaml
services:
  withings-sync:
    image: ghcr.io/jaroslawhartman/withings-sync:latest
    environment:
      - GARMIN_USERNAME=user@example.com
      - GARMIN_PASSWORD=password
      - WEBHOOK_URL=https://script.google.com/macros/s/AKfycb.../exec
      - WEBHOOK_SECRET=your_secret_token
    volumes:
      - ./config:/config
    command: ["--config-folder", "/config"]
```

---

## 4. Verification

After running the sync, check your Google Drive:
- You will find a folder named `Health/data/withings/raw/`.
- Inside the folder, you will see daily files such as `withings_raw_2026-09-27.json` and a rolling `withings_raw_latest.json`.
- These JSON files contain all raw measurement groups, including all Body Scan segmental measurements and sensor readings from the Withings API.
