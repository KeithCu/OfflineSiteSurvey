# Remaining Issues & Improvements

This document tracks the suggestions that were not fully addressed in the recent refactoring pass. It provides context and recommended next steps for each.

## ✅ Global / Architectural

### 1. Schema Constraints & Migration (Suggestion #3)
**Context:** The current schema relies heavily on Pydantic for validation. The database schema lacks some constraints (CHECK, UNIQUE) that could enforce data integrity at the storage level.
**Status:** Partially addressed by fixing Foreign Key restoration in `create_crr_tables`.
**Recommendation:**
- Add explicit `CheckConstraint` to SQLAlchemy models for fields with strict ranges (e.g., coordinates, percentages).
- Use Alembic for migrations to apply these constraints incrementally.

### 2. Application-Level Orphan Checks (Suggestion #6)
**Context:** CRDT requires `PRAGMA foreign_keys=OFF`. While `CRDTService` has some validation, references can still break if syncs arrive out of order.
**Status:** Existing checks verify FK existence during sync, but don't handle "orphaned" records that might exist if a parent is deleted (though cascading deletes are implemented in backend logic, CRDT sync might bypass them).
**Recommendation:**
- Implement a background job (periodic) that scans for orphaned records and either logs them or cleans them up.
- Enhance `CRDTService` to queue changes if dependencies are missing (complex).

### 3. DRY Violations in Models (Suggestion #15)
**Context:** Many models repeat fields like `description` and their sanitization logic.
**Status:** Not addressed.
**Recommendation:**
- Create a `BaseModelMixin` or similar in `shared/models.py` that defines common fields (`description`, `created_at`, `updated_at`).
- Use Pydantic's `model_validator` on a shared base class for common sanitization.

### 4. Sanitize Text Fields vs JSON (Suggestion #17)
**Context:** `sanitize_html` might corrupt fields that store JSON strings (like `conditions` or `section_tags`) if they contain characters resembling HTML tags.
**Status:** Not addressed.
**Recommendation:**
- Identify all JSON-storing fields.
- Exempt them from `sanitize_text_fields` validator, or use a specific JSON validator that ensures valid structure instead of stripping HTML.

### 5. Coordinate Precision (Suggestion #18 & #25)
**Context:** `Float` is used for GPS. Floating point inaccuracies can accumulate.
**Status:** Not addressed.
**Recommendation:**
- Switch to `Decimal` or `String` for storage if high precision is required.
- Given SQLite's dynamic typing, `REAL` (Float) is standard, but `TEXT` can ensure exact preservation.

## ✅ API / CRDT

### 6. CRDT Primary Key Validation (Suggestion #19)
**Context:** CRDT change objects use a raw JSON string for `pk`. Malformed JSON content (e.g. wrong ID type) could pass initial checks.
**Status:** Structural validation exists, but content type validation is minimal.
**Recommendation:**
- Parse the `pk` JSON and validate that the keys/values match the target table's primary key definition (e.g. ensure `Photo.id` is a string, `Project.id` is int).

### 7. CRDT Column Validation (Suggestion #20)
**Context:** Sync accepts any column name for `cid`.
**Status:** Validation checks format (alphanumeric), but not existence in schema.
**Recommendation:**
- Validate `cid` against `table.__table__.columns`.
- Reject changes for unknown columns to prevent database bloat or pollution.

### 8. Conflict Audit Log (Suggestion #21)
**Context:** CR-SQLite resolves conflicts deterministically, but "lost" writes are not tracked.
**Status:** Not addressed.
**Recommendation:**
- Implement a hook or separate table to log when a change is overwritten by a conflict resolution.

## ✅ Photo Management

### 9. Photo Corruption Detection (Suggestion #24)
**Context:** `corrupted` flag exists but isn't automatically managed globally.
**Status:** Not addressed.
**Recommendation:**
- Implement a background integrity checker that verifies file hashes against DB hashes and updates the `corrupted` flag.

### 10. Section Tags Truncation (Suggestion #29)
**Context:** `SectionTagsUpdateRequest` hardcodes a limit of 100 tags.
**Status:** Not addressed.
**Recommendation:**
- Move this limit to `AppConfig` or a constant in `shared/config.py` for easier adjustment.

## ✅ Utilities

### 11. JSON Type for Photo Tags (Suggestion #13)
**Context:** `Photo.tags` is stored as `Text`.
**Status:** `PhotoListResponse` now parses it, but storage is still raw string.
**Recommendation:**
- Use `JSON` type in SQLAlchemy (which maps to proper JSON handling in supported DBs, or Text in SQLite with automatic serialization).
