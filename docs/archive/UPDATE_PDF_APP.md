# PDF Signature Implementation Plan

## Overview

Add a PDF generation and signed upload step to the application submission workflow. Users will download a generated PDF from the preview page, sign it externally using their qualified electronic signature (DNIe, FNMT certificate, etc.), then upload the signed PDF to complete submission.

## Workflow Change

```
Current Step 6 (Preview):
[Back to Edit] ... [Submit]

New Step 6 (Preview):
[Back to Edit] ... [Download PDF] ... [Upload & Submit] (grayed out until downloaded)
```

The wizard remains 6 steps. Step 6 (Preview) gains new functionality:
- **Back button** - Return to edit the application (existing)
- **Download PDF button** - Generate and download the application PDF (always available)
- **Upload & Submit button** - Upload signed PDF and submit (disabled until PDF downloaded at least once)

Users can return to the preview page multiple times to re-download the PDF if needed. Once uploaded, submission is permanent (only superuser can undo).

## UI Layout on Preview Page

### Download Section
Info box: "You must download the PDF and upload a signed copy to complete your submission."
- **[Download Application PDF]** button

### Submit Section
Info box: "Submit your application by uploading a PDF with your official electronic signature."
- **[Upload & Submit]** button (grayed out with tooltip "Please download the PDF first" until `pdf_generated_at` is set)

## Model Changes

Add to `Application` model in `applications/models.py`:

```python
# Signed document tracking
signed_pdf = models.FileField(
    upload_to=signed_pdf_upload_path,  # callable for organized storage
    null=True,
    blank=True,
    help_text='Uploaded PDF with electronic signature'
)
signed_pdf_uploaded_at = models.DateTimeField(null=True, blank=True)
pdf_generated_at = models.DateTimeField(null=True, blank=True)
signature_affirmation = models.BooleanField(
    default=False,
    help_text='User affirmed valid electronic signature'
)
```

### File Upload Path Function

```python
def signed_pdf_upload_path(instance, filename):
    """
    Generate organized upload path for signed PDFs.
    Format: signed_applications/YYYY/MM/APPLICATION_CODE_signed.pdf
    """
    from django.utils import timezone
    now = timezone.now()
    # Use application code for clear identification
    safe_code = instance.code.replace('-', '_')
    return f'signed_applications/{now.year}/{now.month:02d}/{safe_code}_signed.pdf'
```

## New Views

### 1. `download_application_pdf`
- **URL:** `<int:pk>/download-pdf/`
- **URL name:** `applications:download_pdf`
- **Method:** GET
- **Action:**
  - Generate PDF from application data using WeasyPrint
  - Set `pdf_generated_at = timezone.now()` (updates each download)
  - Return PDF as attachment with filename `{application.code}_application.pdf`
  - Log event to history

### 2. `upload_signed_pdf`
- **URL:** `<int:pk>/upload-signed/`
- **URL name:** `applications:upload_signed_pdf`
- **Method:** POST (with file upload)
- **Action:**
  - Validate `pdf_generated_at` is set (user must download first)
  - Validate file (see Validation Rules below)
  - Save uploaded file to `signed_pdf`
  - Set `signed_pdf_uploaded_at = timezone.now()`
  - Require and save `signature_affirmation = True`
  - Transition application status from `draft` to `submitted`
  - Set `submitted_at = timezone.now()`
  - Log event to history
  - Redirect to application detail page with success message

## PDF Template

Create `templates/applications/application_pdf.html` - a WeasyPrint template matching the official REDIB-APP form layout.

### Sections to Include:
1. **Header** - Call code, submission date, application code
2. **Brief description** - One-line project description
3. **Applicant information** - Name, ORCID, entity, email, phone
4. **Funding source** - Project title, code, agency, type, competitive funding status
5. **Subject area** - AEI classification
6. **Equipment requests** - Table with equipment name, node, hours requested
7. **Service modality** - Selected modality and specialization area
8. **Scientific content** - All six sections:
   - Scientific relevance and originality
   - Methodology and experimental design
   - Expected contributions and results
   - Impact and strengths
   - Socioeconomic significance
   - Opportunity criteria and justification
9. **Declarations** - Checkboxes showing:
   - Technical feasibility confirmation
   - Animal use and ethics status
   - Human subjects and ethics status
   - Data consent
10. **Signature placeholder** - Box at bottom with text "Firma electrónica / Electronic Signature"

## Upload UI (Modal or Inline Form)

When user clicks "Upload & Submit", show:

1. **File upload field** - Accepts `.pdf` only, max 5MB
2. **Affirmation checkbox** (required):
   > "I declare that the uploaded PDF has been signed with a valid qualified electronic certificate (certificado digital cualificado) in accordance with eIDAS regulations."
3. **Submit button** - "Upload & Submit Application"
4. **Cancel button** - Return to preview

## Validation Rules

| Rule | Error Message |
|------|---------------|
| `pdf_generated_at` must be set | "Please download the application PDF before uploading." |
| File must have `.pdf` extension | "Only PDF files are accepted." |
| File MIME type must be `application/pdf` | "The uploaded file is not a valid PDF." |
| File size must be ≤ 5MB | "File size exceeds the 5MB limit." |
| `signature_affirmation` must be True | "You must confirm that the PDF has been signed." |

### Error Handling
- If any validation fails, display the error message to the user
- Leave the application in its current state (no partial changes)
- User can retry the upload with a corrected file

## Dependencies

### Python Package
Add to `requirements.txt`:
```
weasyprint>=60.0
```

### System Dependencies (CRITICAL)

WeasyPrint requires system libraries that must be installed on the server:

**Ubuntu/Debian:**
```bash
sudo apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info
```

**Alpine (Docker):**
```bash
apk add --no-cache \
    pango \
    cairo \
    gdk-pixbuf \
    fontconfig \
    ttf-freefont
```

**macOS (development):**
```bash
brew install pango
```

**Important Notes:**
- These dependencies must be added to the production Docker image
- Font availability affects PDF rendering - ensure appropriate fonts are installed
- See WeasyPrint documentation: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `applications/models.py` | Modify | Add `signed_pdf_upload_path` function and 4 new fields |
| `applications/views.py` | Modify | Add `download_application_pdf` and `upload_signed_pdf` views |
| `applications/urls.py` | Modify | Add URL routes: `download-pdf/` and `upload-signed/` |
| `applications/forms.py` | Modify | Add `SignedPdfUploadForm` for file upload + affirmation |
| `templates/applications/application_pdf.html` | Create | WeasyPrint PDF template |
| `templates/applications/preview.html` | Modify | Update preview page with new buttons and info boxes |
| `templates/applications/upload_signed_modal.html` | Create | Upload form (modal or inline) |
| `requirements.txt` | Modify | Add `weasyprint>=60.0` |
| `Dockerfile` (or deployment scripts) | Modify | Add system dependencies for WeasyPrint |
| `docs/DEPLOYMENT.md` | Modify | Document WeasyPrint system requirements |
| `README.md` | Modify | Note WeasyPrint dependencies for local development |

## Migration

One new migration for the 4 model fields:
- `signed_pdf` (FileField, nullable)
- `signed_pdf_uploaded_at` (DateTimeField, nullable)
- `pdf_generated_at` (DateTimeField, nullable)
- `signature_affirmation` (BooleanField, default=False)

## Audit Trail

The following events should be logged via Django's `HistoricalRecords` (already configured on Application model):
- PDF generation (when `pdf_generated_at` is set/updated)
- Signed PDF upload (when `signed_pdf` and `signed_pdf_uploaded_at` are set)
- Submission (status transition to `submitted`)

## Implementation Checklist

- [ ] Add model fields and migration
- [ ] Create `SignedPdfUploadForm`
- [ ] Implement `download_application_pdf` view
- [ ] Implement `upload_signed_pdf` view
- [ ] Add URL routes
- [ ] Create `application_pdf.html` WeasyPrint template
- [ ] Update preview template with new buttons and info boxes
- [ ] Create upload modal/form template
- [ ] Add `weasyprint` to requirements.txt
- [ ] Update Dockerfile with system dependencies
- [ ] Update deployment documentation
- [ ] Update README with local development requirements
- [ ] Test PDF generation locally
- [ ] Test upload flow end-to-end

## Future Improvements (Out of Scope)

The following were considered but deferred for simplicity:
- Server-side signature validation (verify PDF contains valid digital signature)
- PDF content hash verification (ensure uploaded PDF matches generated content)
- Multiple signature support
- Signature timestamp verification
