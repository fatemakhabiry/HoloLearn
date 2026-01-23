# 📤 Google Drive File Upload Setup Guide (OAuth2)
## Complete Step-by-Step Instructions - Start to Finish

---

## 🎯 What We're Setting Up

Your backend will upload lecture files to **your personal Google Drive** account.

- ✅ **FREE** - No paid Google Workspace needed
- ✅ Files stored in your personal Drive
- ✅ Automatic uploads from backend
- ✅ No file size limits (up to Drive storage)

---

## 📋 Requirements

Before you start, make sure you have:
- [ ] A Google account
- [ ] Python installed
- [ ] Your FastAPI backend project

**Time needed:** 15-20 minutes

---

## 🚀 PART 1: Google Cloud Setup

### Step 1: Create Google Cloud Project

1. **Open Google Cloud Console**
   - Go to: https://console.cloud.google.com/
   - Sign in with your Google account

2. **Create New Project**
   - Click the project dropdown at the top (says "Select a project")
   - Click **"NEW PROJECT"** button
   - **Project name:** `HoloLearn` (or any name you like)
   - **Location:** Leave as "No organization"
   - Click **"CREATE"**
   - Wait 10-15 seconds for project to be created

3. **Select Your Project**
   - Click the project dropdown again
   - Click on **"HoloLearn"** to select it
   - You should see "HoloLearn" in the top bar now

✅ **Checkpoint:** You should see "HoloLearn" in the top navigation bar

---

### Step 2: Enable Google Drive API

1. **Open API Library**
   - In the left menu, click **"APIs & Services"**
   - Click **"Library"**

2. **Find Google Drive API**
   - In the search box, type: `Google Drive API`
   - Click on **"Google Drive API"** in the results

3. **Enable the API**
   - Click the blue **"ENABLE"** button
   - Wait 5-10 seconds for it to enable
   - You'll see "API enabled" message

✅ **Checkpoint:** You should see "Google Drive API" with a green checkmark

---

### Step 3: Configure OAuth Consent Screen

1. **Go to OAuth Consent Screen**
   - Left menu → **"APIs & Services"**
   - Click **"OAuth consent screen"**

2. **Choose User Type**
   - Select **"External"**
   - Click **"CREATE"**

3. **Fill in App Information**
   
   **App information section:**
   - **App name:** `HoloLearn Backend`
   - **User support email:** Select your email from dropdown
   - **App logo:** Skip (optional)
   
   **App domain section:**
   - Leave all fields empty (not needed for testing)
   
   **Developer contact information:**
   - **Email addresses:** Enter your email
   
   - Click **"SAVE AND CONTINUE"**

4. **Scopes Section**
   - Just click **"SAVE AND CONTINUE"** (we'll add scopes in code)

5. **Test Users Section**
   - Click **"+ ADD USERS"**
   - Enter your email address (the one you're using)
   - Click **"ADD"**
   - Click **"SAVE AND CONTINUE"**

6. **Summary**
   - Review the information
   - Click **"BACK TO DASHBOARD"**

✅ **Checkpoint:** OAuth consent screen is configured

---

### Step 4: Create OAuth2 Credentials

1. **Go to Credentials**
   - Left menu → **"APIs & Services"**
   - Click **"Credentials"**

2. **Create OAuth Client ID**
   - Click **"+ CREATE CREDENTIALS"** at the top
   - Select **"OAuth client ID"**

3. **Configure OAuth Client**
   - **Application type:** Select **"Desktop app"**
   - **Name:** `HoloLearn Drive Uploader`
   - Click **"CREATE"**

4. **Download Credentials**
   - A popup appears: "OAuth client created"
   - Click **"DOWNLOAD JSON"** button
   - Save the file (it will be named something like `client_secret_xxxxx.json`)

5. **Rename the File**
   - Find the downloaded file
   - Rename it to: **`credentials.json`**
   - Remember where you saved it!

✅ **Checkpoint:** You have a file named `credentials.json`

---

## 🚀 PART 2: Backend Setup

### Step 5: Install Required Packages

Open your terminal in your project directory and run:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Wait for installation to complete (30-60 seconds).

✅ **Checkpoint:** No error messages during installation

---

### Step 6: Add Credentials File to Project

1. **Copy `credentials.json` to your project**
   - Put it in your **project root directory** (same folder as `main.py`)

   Your project structure should look like:
   ```
   your_project/
   ├── credentials.json  ← Put it here
   ├── main.py
   ├── app/
   │   ├── api/
   │   ├── models/
   │   └── services/
   └── requirements.txt
   ```

2. **Update `.gitignore`**
   
   Open (or create) `.gitignore` and add these lines:
   ```
   # Google Drive credentials
   credentials.json
   token.pickle
   
   # Don't commit these files to GitHub!
   ```

✅ **Checkpoint:** `credentials.json` is in project root and added to `.gitignore`

---

### Step 7: Create Google Drive Service File

1. **Create the directory** (if it doesn't exist):
   ```bash
   mkdir -p app/services
   ```

2. **Create the file:**
   - Create a new file: `app/services/google_drive.py`

3. **Copy this code into the file:**

```python
"""
Google Drive Service - OAuth2
Uploads files to your personal Google Drive
"""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import os
import pickle
import logging

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Service for uploading files to Google Drive using OAuth2"""
    
    # Scopes required
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self):
        """Initialize Google Drive service with OAuth2 credentials"""
        
        # Paths
        self.credentials_file = 'credentials.json'
        self.token_file = 'token.pickle'
        
        # Get authenticated service
        self.service = self._get_service()
        logger.info("Google Drive service initialized successfully")
    
    def _get_service(self):
        """Get authenticated Google Drive service"""
        
        creds = None
        
        # Check if token already exists
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh expired token
                creds.refresh(Request())
            else:
                # First time authentication
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file '{self.credentials_file}' not found. "
                        "Please download OAuth2 credentials from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, 
                    self.SCOPES
                )
                
                # Run local server for authentication
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for next time
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build and return service
        return build('drive', 'v3', credentials=creds)
    
    def upload_file(
        self, 
        file_path: str, 
        filename: str, 
        mime_type: str = None
    ) -> dict:
        """
        Upload file to Google Drive
        
        Args:
            file_path: Path to the file to upload
            filename: Name for the file in Drive
            mime_type: MIME type of the file
            
        Returns:
            dict: File info including ID and URLs
        """
        
        try:
            # Auto-detect mime type if not provided
            if mime_type is None:
                mime_type = self._get_mime_type(filename)
            
            # File metadata
            file_metadata = {'name': filename}
            
            # Upload file
            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, webContentLink, mimeType, size'
            ).execute()
            
            # Make file publicly readable
            self._make_public(file['id'])
            
            logger.info(f"File uploaded: {file['name']} (ID: {file['id']})")
            
            return {
                'file_id': file['id'],
                'name': file['name'],
                'view_link': file.get('webViewLink'),
                'download_link': file.get('webContentLink'),
                'mime_type': file.get('mimeType'),
                'size': file.get('size')
            }
            
        except HttpError as e:
            logger.error(f"Google Drive API error: {e}")
            raise Exception(f"Failed to upload file to Google Drive: {e}")
        
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file from Google Drive"""
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"File deleted: {file_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            return False
    
    def _make_public(self, file_id: str):
        """Make file publicly accessible"""
        
        try:
            self.service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
        except HttpError as e:
            logger.warning(f"Could not make file public: {e}")
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type based on file extension"""
        
        extension = filename.lower().split('.')[-1]
        
        mime_types = {
            'pdf': 'application/pdf',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'ppt': 'application/vnd.ms-powerpoint',
            'txt': 'text/plain',
        }
        
        return mime_types.get(extension, 'application/octet-stream')


# Singleton instance
_drive_service_instance = None

def get_drive_service():
    """Get or create the Drive service singleton"""
    global _drive_service_instance
    
    if _drive_service_instance is None:
        _drive_service_instance = GoogleDriveService()
    
    return _drive_service_instance


# For backward compatibility
drive_service = get_drive_service()
```

✅ **Checkpoint:** File `app/services/google_drive.py` is created

---

### Step 8: One-Time Authentication

**Important:** You need to authenticate **once** before running your backend.

1. **Open terminal in your project directory**

2. **Run this command:**
   ```bash
   python -c "from app.services.google_drive import drive_service; print('✅ Authentication successful!')"
   ```

3. **What happens next:**
   - A browser window will **automatically open**
   - You'll see Google's sign-in page
   - Sign in with the **same Google account** you used in Step 3

4. **Grant permissions:**
   - You'll see: "HoloLearn Backend wants to access your Google Account"
   - Click **"Continue"** or **"Allow"**
   - Grant access to Google Drive

5. **Success message:**
   - Browser shows: "The authentication flow has completed"
   - Terminal shows: `✅ Authentication successful!`
   - A file named `token.pickle` is created in your project

✅ **Checkpoint:** `token.pickle` file exists in your project root

---

### Step 9: Update Your Lecture Routes

In your `app/api/routes/lecture_routes.py`, add this import at the top:

```python
from app.services.google_drive import drive_service
import os
```

Then update your `/create-draft` endpoint to use Google Drive.

See the complete code in the next section.

---

## 🚀 PART 3: Testing

### Step 10: Test File Upload

1. **Start your FastAPI server:**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Test with cURL:**
   ```bash
   curl -X POST "http://localhost:8000/api/lectures/create-draft" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "title=Test Lecture" \
     -F "course_code=CS101" \
     -F "file=@test.pdf"
   ```

3. **Check Google Drive:**
   - Go to https://drive.google.com/
   - You should see the uploaded file!

✅ **Checkpoint:** File appears in your Google Drive!

---

## 🎯 Complete Endpoint Code

Here's the complete `/create-draft` endpoint with Google Drive upload:

```python
from app.services.google_drive import drive_service
import os

@router.post("/create-draft", response_model=LecturePublic)
async def create_lecture_draft(
    title: str = Form(...),
    course_code: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create lecture draft with Google Drive upload"""
    
    # 1. Verify user is a teacher
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(status_code=403, detail="Only teachers can create lectures")
    
    # 2. Verify course
    course = session.get(Course, course_code)
    if not course or course.teacher_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Invalid course")
    
    # 3. Validate file
    ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".txt"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # 4. Save file temporarily
    temp_dir = "/tmp/hololearn_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_filename = f"temp_{current_user.user_id}_{file.filename}"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    try:
        # Save uploaded file
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 5. Upload to Google Drive
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        drive_filename = f"{course_code}_{title}_{timestamp}{file_ext}"
        
        drive_result = drive_service.upload_file(
            file_path=temp_path,
            filename=drive_filename,
            mime_type=file.content_type
        )
        
        # 6. Create lecture with Drive URL
        lecture = Lecture(
            title=title,
            teacher_id=current_user.user_id,
            course_code=course_code,
            lecture_type=LectureType.PREPARED,
            status=LectureStatus.DRAFT,
            final_content=drive_result['view_link']  # Google Drive URL
        )
        
        session.add(lecture)
        session.commit()
        session.refresh(lecture)
        
        return lecture
        
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create lecture: {str(e)}")
    
    finally:
        # 7. Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
```

---

## 📝 Troubleshooting

### Problem: "credentials.json not found"
**Solution:** Make sure `credentials.json` is in the project root (same folder as `main.py`)

### Problem: "Browser didn't open during authentication"
**Solution:** 
1. Copy the URL from terminal
2. Paste it in your browser manually
3. Complete the authentication

### Problem: "Access denied" when uploading
**Solution:**
1. Delete `token.pickle`
2. Run authentication again: `python -c "from app.services.google_drive import drive_service"`
3. Make sure you grant all permissions

### Problem: "File uploads but not visible in Drive"
**Solution:** Check the permission setting in the code. The `_make_public()` function should be working.

---

## ✅ Final Checklist

- [ ] Google Cloud project created
- [ ] Google Drive API enabled
- [ ] OAuth consent screen configured
- [ ] OAuth credentials downloaded as `credentials.json`
- [ ] Python packages installed
- [ ] `credentials.json` in project root
- [ ] `credentials.json` added to `.gitignore`
- [ ] `google_drive.py` service file created
- [ ] One-time authentication completed
- [ ] `token.pickle` file exists
- [ ] Lecture routes updated
- [ ] Test upload successful
- [ ] File visible in Google Drive

---

## 🎉 You're Done!

Your backend can now upload files to Google Drive automatically!

**What happens when teachers upload:**
1. Teacher uploads file through Flutter app
2. Backend saves it temporarily
3. Backend uploads to your Google Drive
4. Backend gets Drive URL
5. Backend saves URL in database
6. Backend deletes temp file
7. Teacher can access file via Drive link

**Reminder:** Keep `credentials.json` and `token.pickle` secret! Never commit them to GitHub!

---

## 📞 Need Help?

If you get stuck:
1. Check the Troubleshooting section above
2. Make sure all steps were followed in order
3. Verify `credentials.json` and `token.pickle` exist
4. Check terminal for error messages

Good luck! 🚀
