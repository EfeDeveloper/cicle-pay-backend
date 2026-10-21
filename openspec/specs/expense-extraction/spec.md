# expense-extraction

## Purpose

Provides AI-powered extraction of structured additional expense data from OCR text payloads, producing validated entities directly compatible with CyclePay expense contracts.

## Requirements

### Requirement: AI Expense Extraction from OCR Text
The system SHALL provide an endpoint `POST /api/v1/ai/extract-expense` that accepts OCR-extracted text and optional context (such as preferred periodKey) and sends a structured prompt to the configured local AI model (Ollama) to infer financial transaction details.

#### Scenario: Successful extraction from complete receipt text
- **WHEN** a valid OCR text containing vendor "Supermercado Éxito", date "2026-10-15", and total amount "145000" is submitted
- **THEN** the system returns HTTP 200 with `name: "Supermercado Éxito"`, `amount: 145000.0`, `category: "Alimentación"`, `dueDay: 15`, `periodKey: "2026-10"`, `status: "paid"`, and a brief `description` <= 140 characters

#### Scenario: Extraction from bill with missing dueDay
- **WHEN** an OCR text does not specify a clear due day or payment date
- **THEN** the system returns HTTP 200 with `dueDay: null`, maintaining valid values for `name`, `amount`, `category`, and `periodKey`

### Requirement: Strict CyclePay Contract Validation
The system SHALL validate all AI-extracted payloads using Pydantic v2 before returning them to the client. The output MUST conform strictly to CyclePay's additional expense contract (`CreateManualExpenseInput`). It MUST NOT output recurring template schemas.

#### Scenario: Valid categories enforced
- **WHEN** the AI model categorizes an expense
- **THEN** the `category` attribute MUST be exactly one of the 10 allowed categories: `Vivienda`, `Servicios`, `Alimentación`, `Transporte`, `Salud`, `Educación`, `Entretenimiento`, `Seguros`, `Suscripciones`, `Otros`

#### Scenario: Amount and period constraints enforced
- **WHEN** the extracted payload is validated
- **THEN** `amount` MUST be a positive number greater than 0, `dueDay` MUST be null or an integer between 1 and 31, and `periodKey` MUST strictly match the `YYYY-MM` format

### Requirement: Error Handling and Fallbacks for AI Ingestion
The system SHALL handle AI connection failures, timeouts, and unparseable model responses gracefully without crashing the backend service.

#### Scenario: Ollama service unavailable
- **WHEN** the local Ollama server is unreachable or fails to respond within the configured timeout
- **THEN** the system returns HTTP 503 Service Unavailable with a descriptive error message indicating AI service unavailability

#### Scenario: OCR text contains no financial data
- **WHEN** the provided OCR text contains random text or lacks identifiable merchant, amount, or expense data
- **THEN** the system returns HTTP 422 Unprocessable Entity with a clear message indicating that an expense could not be reliably extracted from the provided text
