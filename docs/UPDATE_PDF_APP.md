Here's the updated implementation plan:

---

## PDF Signature Implementation Plan

### Overview

Add a PDF generation and signed upload step to the application submission workflow. Users will download a generated PDF, sign it externally using their qualified electronic signature (DNIe, FNMT certificate, etc.), then upload the signed PDF before final submission.

### Workflow Change

```
Current:
Step 5: Declarations → [Submit]

New:
Step 5: Declarations → [Generate PDF] → User signs externally → 
[Upload Signed PDF] + checkbox affirmation → [Submit]
```

### Model Changes

Add to `Application` model:

```python
# Signed document tracking
signed_pdf = models.FileField(upload_to='signed_applications/', null=True, blank=True)
signed_pdf_uploaded_at = models.DateTimeField(null=True, blank=True)
pdf_generated_at = models.DateTimeField(null=True, blank=True)
signature_affirmation = models.BooleanField(default=False)  # User affirmed valid signature
```

### New Views

1. **`download_application_pdf`** - Generates PDF from application data using WeasyPrint, matching official form layout
2. **`upload_signed_pdf`** - Handles file upload with affirmation checkbox

### PDF Template

Create `templates/applications/pdf/application_form.html` that mirrors the official Word form layout (REDIB-APP). Include all sections:
- Header (call, date)
- Brief description
- Applicant info
- Funding source
- Subject area
- Equipment requests with hours
- Service modality and specialization
- All six scientific content sections
- Declarations checkboxes (pre-filled based on form data)
- Signature placeholder box at bottom

### Upload UI

On Step 5 (or new Step 6), after declarations:

1. **Generate PDF button** - Downloads the PDF, sets `pdf_generated_at`
2. **Instructions** - "Sign this PDF using AutoFirma or your electronic certificate, then upload below"
3. **File upload field** - Accepts only `.pdf`
4. **Affirmation checkbox** (required) - "I confirm that the uploaded PDF has been signed with a valid qualified electronic signature"
5. **Submit button** - Only enabled when `signed_pdf` exists AND `signature_affirmation` is True

### Validation Rules

- Cannot submit without `signed_pdf` uploaded
- Cannot submit without `signature_affirmation = True`
- `pdf_generated_at` must be set before upload is allowed (ensures they downloaded the correct PDF)
- File must be `.pdf` extension

### Dependencies

Add `weasyprint` to requirements.txt (if not already present). WeasyPrint requires some system dependencies on Linux (`pango`, `cairo`).

### Files to Create/Modify

| File | Action |
|------|--------|
| `applications/models.py` | Add 4 new fields |
| `applications/views.py` | Add `download_application_pdf`, `upload_signed_pdf` views |
| `applications/urls.py` | Add URL routes for new views |
| `templates/applications/pdf/application_form.html` | New - PDF template matching official form |
| `templates/applications/wizard_step5.html` | Modify - Add generate/upload/affirm UI |
| `requirements.txt` | Add `weasyprint` if missing |

### Migration

One new migration for the 4 model fields.


