# Phase 05 Specification: Prompt Generation Schemas & API Contracts

## 1. Database Schema

### `audit_prompts` Table
Stores the currently active Google Stitch prompt for an audit.

| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | No | Primary Key (UUIDv4) |
| `audit_id` | `VARCHAR(36)` | No | Foreign Key $\to$ `audits.id` (ON DELETE CASCADE) |
| `version_number` | `INTEGER` | No | Active version sequence number (default: 1) |
| `content` | `TEXT` | No | Current prompt text (may include user edits) |
| `original_content` | `TEXT` | No | Unmodified AI-generated prompt text |
| `user_instructions` | `TEXT` | Yes | Optional user-specified design preferences |
| `selected_finding_ids_json` | `TEXT` | No | JSON array of finding IDs used in generation |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | Creation timestamp |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | Last update timestamp |

### `prompt_versions` Table
Stores immutable snapshots of each generated version of the prompt.

| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `id` | `VARCHAR(36)` | No | Primary Key (UUIDv4) |
| `audit_id` | `VARCHAR(36)` | No | Foreign Key $\to$ `audits.id` (ON DELETE CASCADE) |
| `version_number` | `INTEGER` | No | Version sequence number |
| `content` | `TEXT` | No | Prompt snapshot text at the time of generation |
| `selected_finding_ids_json` | `TEXT` | No | JSON array of finding IDs included in this version |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | Generation timestamp |

---

## 2. API Schemas (Pydantic v2)

### `PromptGenerateRequest`
```python
class PromptGenerateRequest(BaseModel):
    selected_finding_ids: list[str]
    user_instructions: str | None = None
```

### `PromptUpdateRequest`
```python
class PromptUpdateRequest(BaseModel):
    content: str
```

### `PromptVersionRead`
```python
class PromptVersionRead(BaseModel):
    id: str
    audit_id: str
    version_number: int
    content: str
    selected_finding_ids: list[str]
    created_at: datetime
```

### `PromptRead`
```python
class PromptRead(BaseModel):
    id: str
    audit_id: str
    version_number: int
    content: str
    original_content: str
    user_instructions: str | None = None
    selected_finding_ids: list[str]
    versions: list[PromptVersionRead] = []
    created_at: datetime
    updated_at: datetime
```

---

## 3. REST Endpoints

### 1. Generate / Regenerate Prompt
- **Method**: `POST`
- **Path**: `/api/v1/projects/{project_id}/audits/{audit_id}/prompt`
- **Request Body**: `PromptGenerateRequest`
- **Response**: `PromptRead` (Status 200)
- **Errors**:
  - `400 Bad Request`: `{"error": {"code": "invalid_findings", "message": "..."}}` if selected finding IDs do not belong to the audit or list is empty.
  - `404 Not Found`: if project or audit is not found.

### 2. Retrieve Active Prompt & Version History
- **Method**: `GET`
- **Path**: `/api/v1/projects/{project_id}/audits/{audit_id}/prompt`
- **Response**: `PromptRead` (Status 200)
- **Errors**:
  - `404 Not Found`: if no prompt has been generated for this audit yet.

### 3. Save Manual Prompt Edits
- **Method**: `PATCH`
- **Path**: `/api/v1/projects/{project_id}/audits/{audit_id}/prompt/{prompt_id}`
- **Request Body**: `PromptUpdateRequest`
- **Response**: `PromptRead` (Status 200)

### 4. Restore Original Prompt Version
- **Method**: `POST`
- **Path**: `/api/v1/projects/{project_id}/audits/{audit_id}/prompt/{prompt_id}/restore-original`
- **Response**: `PromptRead` (Status 200)
