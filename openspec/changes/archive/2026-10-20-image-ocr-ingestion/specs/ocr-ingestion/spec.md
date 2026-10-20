## Purpose

Ingests invoice and receipt images, performs optical character recognition (OCR) using Python-native libraries, and returns extracted text or a notification when no readable text is found.

## ADDED Requirements

### Requirement: Image file upload validation
The system SHALL accept image uploads in PNG, JPEG, JPG, and WEBP formats via multipart/form-data. Any unsupported file types or corrupted image payloads SHALL be rejected with HTTP 400 Bad Request.

#### Scenario: Supported image format accepted
- **WHEN** a valid PNG or JPEG image is uploaded to `/api/v1/ocr/extract-text`
- **THEN** the system accepts the file and proceeds to OCR processing

#### Scenario: Unsupported file type rejected
- **WHEN** a non-image file (e.g. PDF, ZIP, TXT) is uploaded to `/api/v1/ocr/extract-text`
- **THEN** the system rejects the request with HTTP 400 and an error message indicating invalid format

### Requirement: OCR text extraction
The system SHALL extract text lines from the uploaded image and return the raw text, the number of detected lines, and the execution duration in milliseconds.

#### Scenario: Image with readable text
- **WHEN** an image containing visible text from an invoice or bill is processed
- **THEN** the system returns `has_text: true`, the consolidated `raw_text`, `line_count` > 0, and `processing_time_ms` > 0

### Requirement: Handling images without readable text
When an uploaded image contains no legible text (blank image, blurred photo, or non-text document), the system SHALL return `has_text: false` with an empty text payload and a descriptive message indicating that no text could be recognized.

#### Scenario: Image without text returns informative response
- **WHEN** an image with no legible text is uploaded
- **THEN** the system returns HTTP 200 with `has_text: false`, `raw_text: ""`, `line_count: 0`, and `message: "No se detectó texto legible en el documento"`
