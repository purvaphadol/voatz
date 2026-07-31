# Antigravity & Developer Directives

This directive document specifies mandatory rules and pre-flight protocols for any developer or AI assistant working on the Voatz repository.

---

## MANDATORY PRE-FLIGHT CHECKLIST

Before making or proposing any code changes, you MUST:
1. Consult `docs/01_SYSTEM_WORKFLOW_AND_ARCHITECTURE.md` to verify domain model alignment.
2. Adhere to coding and OOP standards in `docs/02_CODING_AND_SECURITY_STANDARDS.md`.
3. Check the database table schemas in `docs/03_DATABASE_SCHEMA_AND_MODELS.md`.

---

## NON-NEGOTIABLE DEVELOPMENT RULES

1. **Centralized Input Validation**:
   - All input validation and type sanitization MUST reside in `app/utils/validators.py`.
   - Do NOT write inline ad-hoc input validation inside route handlers.

2. **OOP & Reusable Functions**:
   - Organize code using clean Object-Oriented Programming and modular helper functions.
   - Use `safe_commit` wrappers for all database commits.

3. **Timezone Standard (IST - UTC+05:30)**:
   - All timestamps and datetime comparisons MUST use Indian Standard Time (IST).
   - Normalize datetime objects before comparing to prevent naive vs. aware timezone errors.

4. **Multi-Tenant Data Isolation**:
   - Every domain query for non-platform admin users MUST filter by `company_id`.
   - Unauthorized cross-tenant access attempts MUST return HTTP 404 or HTTP 403.
   - A Company Super Admin ONLY has access to modules/actions provisioned for their company by the Platform Administrator.

5. **Mandatory Testing Protocol**:
   - Run `python3 backend/scripts/test_authz_refactor.py` after backend modifications.
   - All tests MUST pass with 100% success rate before completing a task.
