#!/usr/bin/env python3
"""
Automated test script for the authorization refactor.
Tests Sections 0-10 of the GROUP_1-3_TEST_PLAN, plus new Section 5 admin
role-create tests added for the create_role() Administrator fix.

Run with:
    python scripts/test_authz_refactor.py

Assumes Flask dev server already running on localhost:4000.
Company B is seeded directly via seed_data.seed_company() so it gets the
full module/action/permission fan-out.
"""
import sys, os, json, time, requests
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from seed_data import seed_company

DATABASE_URI = os.environ["DATABASE_URL"]
engine   = create_engine(DATABASE_URI)
meta     = MetaData()
meta.reflect(bind=engine)
DBSession = sessionmaker(bind=engine)

BASE = "http://localhost:4000/api"

ADMIN_EMAIL   = "admin@gmail.com"
ADMIN_PASSWORD = "Admin@123"
A_SUPER_EMAIL = "rushiraj@datagrid.co.in"
A_SUPER_PASS  = "admin123"
A_REG_EMAIL   = "john@datagrid.co.in"
A_REG_PASS    = "admin123"

results = []

def record(num, desc, expected_status, resp, extra_check=None):
    actual = resp.status_code
    body   = {}
    try:
        body = resp.json()
    except Exception:
        pass
    passed = (actual == expected_status)
    if passed and extra_check:
        passed = extra_check(body)
    fail_detail = None
    if not passed:
        fail_detail = {
            "url":             resp.url,
            "method":          resp.request.method,
            "request_body":    _safe_body(resp.request),
            "response_status": actual,
            "response_body":   body,
        }
    results.append({"num": num, "desc": desc, "expected": expected_status,
                    "actual": actual, "passed": passed, "fail_detail": fail_detail})
    tag = "PASS" if passed else "FAIL"
    print(f"  [{tag}] {num}: {desc}  (expected {expected_status}, got {actual})")
    return passed, body

def _safe_body(req):
    try:
        return json.loads(req.body or "{}")
    except Exception:
        return str(req.body or "")

def ah(tok):
    return {"Authorization": f"Bearer {tok}"}

def login_user(email, pw, label):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        print(f"  [FATAL] Cannot log in as {label} ({email}): {r.status_code} {r.text}")
        sys.exit(1)
    print(f"  [OK] Logged in as {label} ({email})")
    return r.json()["access_token"]

def login_admin(email, pw):
    r = requests.post(f"{BASE}/auth/administrator/login",
                      json={"email": email, "password": pw})
    if r.status_code != 200:
        print(f"  [FATAL] Cannot log in as Administrator ({email}): {r.status_code} {r.text}")
        sys.exit(1)
    print(f"  [OK] Logged in as Administrator ({email})")
    return r.json()["access_token"]

def get_role_id_by_name(tok, role_name):
    """Fetch the id of a role by name from the active listing."""
    r = requests.get(f"{BASE}/roles/", headers=ah(tok),
                     params={"status": "active", "per_page": 200})
    if r.status_code != 200:
        return None
    for ro in r.json().get("data", []):
        if ro["role_name"].lower() == role_name.lower():
            return ro["id"]
    return None

# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*70)
print("  AUTH REFACTOR TEST SUITE")
print("═"*70)

print("\n── Section 0: Pre-flight ──────────────────────────────────────────────")
r = requests.get(f"{BASE}/health")
record("0.1", "Health check returns 200", 200, r)

print("\n── Acquiring tokens ───────────────────────────────────────────────────")
ADMIN_TOKEN   = login_admin(ADMIN_EMAIL, ADMIN_PASSWORD)
A_SUPER_TOKEN = login_user(A_SUPER_EMAIL, A_SUPER_PASS, "A_SUPER (rushiraj)")
A_REG_TOKEN   = login_user(A_REG_EMAIL,  A_REG_PASS,   "A_REG   (john)")

r_prof = requests.get(f"{BASE}/auth/profile", headers=ah(A_SUPER_TOKEN))
A_COMPANY_ID = r_prof.json().get("company_id") if r_prof.status_code == 200 else None
A_SUPER_USER_ID = r_prof.json().get("id") if r_prof.status_code == 200 else None
print(f"  Company A id = {A_COMPANY_ID}, user_id = {A_SUPER_USER_ID}")

print("\n── Seeding Company B (direct DB) ──────────────────────────────────────")
TS = str(int(time.time()))[-6:]
B_SUPER_EMAIL = f"b_super_{TS}@companyb.test"
B_SUPER_PASS  = "Admin@123"

db_session = DBSession()
try:
    b_ids = seed_company(
        db_session,
        company_name=f"Company B Test {TS}",
        super_admin_email=B_SUPER_EMAIL,
        super_admin_password=B_SUPER_PASS,
        super_admin_name="B Super Admin",
    )
    db_session.commit()
finally:
    db_session.close()

COMPANY_B_ID = b_ids["company_id"]
B_DEPT_ID    = b_ids["department_id"]
print(f"  Company B id = {COMPANY_B_ID}, dept_id = {B_DEPT_ID}")

B_SUPER_TOKEN = login_user(B_SUPER_EMAIL, B_SUPER_PASS, "B_SUPER")

# Ensure AuditLogs module and permissions exist for Company A so their Super Admin can list audit logs.
db_session = DBSession()
try:
    t = meta.tables
    existing_mod = db_session.execute(
        t["modules"].select().where(
            t["modules"].c.company_id == A_COMPANY_ID,
            t["modules"].c.module_name == "AuditLogs"
        )
    ).first()
    
    if not existing_mod:
        now = datetime.now()
        mod_id = db_session.execute(
            t["modules"].insert().values(
                module_name="AuditLogs",
                order_index=16,
                company_id=A_COMPANY_ID,
                status=1,
                created_at=now,
                updated_at=now
            ).returning(t["modules"].c.id)
        ).scalar()
        
        # Get super admin role of Company A
        sa_role = db_session.execute(
            t["roles"].select().where(
                t["roles"].c.company_id == A_COMPANY_ID,
                t["roles"].c.is_super_admin == True
            )
        ).first()
        
        # Add actions
        for act in [{"name": "view", "url": "/view"}, {"name": "create", "url": "/create"}, {"name": "update", "url": "/update"}, {"name": "delete", "url": "/delete"}]:
            act_id = db_session.execute(
                t["module_action"].insert().values(
                    module_id=mod_id,
                    action_name=act["name"],
                    action_url=act["url"],
                    company_id=A_COMPANY_ID,
                    status=1,
                    created_at=now,
                    updated_at=now
                ).returning(t["module_action"].c.id)
            ).scalar()
            
            if sa_role:
                db_session.execute(
                    t["role_permission_mapping"].insert().values(
                        company_id=A_COMPANY_ID,
                        role_id=sa_role.id,
                        module_id=mod_id,
                        action_id=act_id,
                        status=1,
                        created_at=now,
                        updated_at=now
                    )
                )
        db_session.commit()
        print("  [OK] Seeded AuditLogs for Company A")
finally:
    db_session.close()

# Resolve Company A dept — filter strictly to Company A to avoid picking up
# freshly-seeded Company B dept which sorts first by updated_at.
r_depts = requests.get(f"{BASE}/departments/",
                       headers=ah(A_SUPER_TOKEN),
                       params={"company_id": A_COMPANY_ID, "per_page": 100})
depts_a   = [d for d in r_depts.json().get("data", []) if d["company_id"] == A_COMPANY_ID] \
    if r_depts.status_code == 200 else []
A_DEPT_ID = depts_a[0]["id"] if depts_a else None
print(f"  Company A dept_id = {A_DEPT_ID}")

# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Section 1: Administrator Login ────────────────────────────────────")

r = requests.post(f"{BASE}/auth/administrator/login",
                  json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
record("1.1", "Admin login → 200 + access_token", 200, r,
       lambda b: "access_token" in b)

r = requests.post(f"{BASE}/auth/administrator/login",
                  json={"email": ADMIN_EMAIL, "password": "wrongpass"})
record("1.2", "Admin login wrong password → 401", 401, r)

r = requests.post(f"{BASE}/auth/administrator/login",
                  json={"email": "nobody@nowhere.com", "password": "x"})
record("1.3", "Admin login unknown email → 401", 401, r)

# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Section 2: Company Creation ───────────────────────────────────────")

r = requests.post(f"{BASE}/companies/", headers=ah(ADMIN_TOKEN),
                  json={"company_name": f"Admin Co {TS}"})
record("2.1", "Admin creates company → 201", 201, r)

r = requests.post(f"{BASE}/companies/", headers=ah(A_SUPER_TOKEN),
                  json={"company_name": f"Super Co {TS}"})
record("2.2", "Company Super Admin cannot create company → 403", 403, r)

r = requests.post(f"{BASE}/companies/", headers=ah(A_REG_TOKEN),
                  json={"company_name": f"Reg Co {TS}"})
record("2.3", "Regular user cannot create company → 403", 403, r)

# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Section 3: Company Listing ────────────────────────────────────────")

r = requests.get(f"{BASE}/companies/", headers=ah(ADMIN_TOKEN))
record("3.1", "Admin sees ≥2 companies", 200, r,
       lambda b: len(b.get("data", [])) >= 2)

r = requests.get(f"{BASE}/companies/", headers=ah(A_SUPER_TOKEN))
record("3.2", "Company A Super Admin sees only own company", 200, r,
       lambda b: all(c["id"] == A_COMPANY_ID for c in b.get("data", [])))

r = requests.get(f"{BASE}/companies/", headers=ah(B_SUPER_TOKEN))
record("3.3", "Company B Super Admin sees only Company B", 200, r,
       lambda b: all(c["id"] == COMPANY_B_ID for c in b.get("data", [])))

# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Section 4: Department Creation ────────────────────────────────────")

r = requests.post(f"{BASE}/departments/", headers=ah(ADMIN_TOKEN),
                  json={"department_name": f"AdminDept4 {TS}", "company_id": A_COMPANY_ID})
record("4.1", "Admin creates dept for Company A → 201", 201, r)

r = requests.post(f"{BASE}/departments/", headers=ah(A_SUPER_TOKEN),
                  json={"department_name": f"SAdminDept4 {TS}"})
record("4.2", "Company A Super Admin creates own dept → 201", 201, r)

r = requests.post(f"{BASE}/departments/", headers=ah(B_SUPER_TOKEN),
                  json={"department_name": f"BDept4 {TS}"})
record("4.3", "Company B Super Admin creates own dept → 201", 201, r)

# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Section 5: Role Creation ──────────────────────────────────────────")

# 5.1 – Company A Super Admin creates a role (original test)
r = requests.post(f"{BASE}/roles/", headers=ah(A_SUPER_TOKEN),
                  json={"role_name": f"TestRole5 {TS}", "department_id": A_DEPT_ID})
record("5.1", "Company A Super Admin creates role → 201", 201, r)
# Fetch id by name because role.id may be null in response before flush (pre-existing in other routes)
test_role_5_id = r.json().get("role_id") or get_role_id_by_name(A_SUPER_TOKEN, f"Testrole5 {TS}")

# 5.2 – Regular user (no create perm) is blocked
r = requests.post(f"{BASE}/roles/", headers=ah(A_REG_TOKEN),
                  json={"role_name": f"RegRole5 {TS}", "department_id": A_DEPT_ID})
record("5.2", "Regular user (no create perm) role create → 403", 403, r)

# 5.3 – Administrator creates a role in Company A with explicit company_id → 201
r = requests.post(f"{BASE}/roles/", headers=ah(ADMIN_TOKEN),
                  json={"role_name": f"AdminRoleA {TS}", "department_id": A_DEPT_ID,
                        "company_id": A_COMPANY_ID})
record("5.3", "Admin creates role in Company A with explicit company_id → 201", 201, r)
admin_role_a_id = r.json().get("role_id") or get_role_id_by_name(ADMIN_TOKEN, f"Adminrolea {TS}")

# 5.4 – Administrator creates a role in Company B with explicit company_id → 201
r = requests.post(f"{BASE}/roles/", headers=ah(ADMIN_TOKEN),
                  json={"role_name": f"AdminRoleB {TS}", "department_id": B_DEPT_ID,
                        "company_id": COMPANY_B_ID})
record("5.4", "Admin creates role in Company B with explicit company_id → 201", 201, r)

# 5.5 – Administrator omits company_id → 400
r = requests.post(f"{BASE}/roles/", headers=ah(ADMIN_TOKEN),
                  json={"role_name": f"NoCompanyRole {TS}", "department_id": A_DEPT_ID})
record("5.5", "Admin omits company_id → 400 'company_id is required for platform Administrators'",
       400, r,
       lambda b: "company_id is required for platform Administrators" in b.get("error", ""))

# 5.6 – Company A Super Admin sends company_id=Company B in body → override ignored or 403
#        Two safe outcomes: (a) 403, or (b) 201 with role landing in Company A (not B)
r = requests.post(f"{BASE}/roles/", headers=ah(A_SUPER_TOKEN),
                  json={"role_name": f"CrossTenantRole {TS}", "department_id": A_DEPT_ID,
                        "company_id": COMPANY_B_ID})
if r.status_code == 403:
    record("5.6", "Company A Super Admin cross-tenant role create → 403 (body company_id ignored)", 403, r)
elif r.status_code == 201:
    # Must land in Company A, not Company B
    created_id = r.json().get("role_id") or get_role_id_by_name(A_SUPER_TOKEN, f"Crosstenantole {TS}")
    if created_id:
        r_check = requests.get(f"{BASE}/roles/{created_id}", headers=ah(A_SUPER_TOKEN))
        landed_in_a = r_check.status_code == 200 and r_check.json().get("company_id") == A_COMPANY_ID
        record("5.6", "Company A Super Admin cross-tenant → 201 but role landed in Company A (override ignored)",
               201, r, lambda b: landed_in_a)
    else:
        record("5.6", "Company A Super Admin cross-tenant → 201 but role landed in Company A (override ignored)",
               201, r)
else:
    record("5.6", "Company A Super Admin cross-tenant role create → 403 or 201-in-A",
           403, r)

# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Section 6: Super Admin Role Guards ────────────────────────────────")

r_roles    = requests.get(f"{BASE}/roles/?status=active&per_page=100", headers=ah(A_SUPER_TOKEN))
roles_a    = r_roles.json().get("data", []) if r_roles.status_code == 200 else []
super_role = next((ro for ro in roles_a if ro.get("role_name") == "Company Super Admin"), None)
super_role_id = super_role["id"] if super_role else None

if super_role_id:
    r = requests.put(f"{BASE}/roles/{super_role_id}", headers=ah(A_SUPER_TOKEN),
                     json={"role_name": "Hacked Name"})
    record("6.1", "Rename Company Super Admin role → 403", 403, r)

    r = requests.delete(f"{BASE}/roles/{super_role_id}", headers=ah(A_SUPER_TOKEN))
    record("6.2", "Delete Company Super Admin role → 403", 403, r)
else:
    print("  [SKIP] 6.1, 6.2 — Company Super Admin role not found")

# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Section 7: Permanent Delete — Departments ─────────────────────────")

r = requests.post(f"{BASE}/departments/", headers=ah(ADMIN_TOKEN),
                  json={"department_name": f"PermDept7 {TS}", "company_id": A_COMPANY_ID})
perm_dept_id = r.json().get("department_id") if r.status_code == 201 else None

if perm_dept_id:
    requests.delete(f"{BASE}/departments/{perm_dept_id}", headers=ah(A_SUPER_TOKEN))

    r = requests.delete(f"{BASE}/departments/{perm_dept_id}/permanent",
                        headers=ah(A_SUPER_TOKEN))
    record("7.1", "Non-admin cannot perm-delete dept → 403", 403, r)

    r = requests.delete(f"{BASE}/departments/{perm_dept_id}/permanent",
                        headers=ah(ADMIN_TOKEN))
    record("7.2", "Admin perm-deletes soft-deleted dept → 200", 200, r)

    r = requests.get(f"{BASE}/departments/{perm_dept_id}", headers=ah(A_SUPER_TOKEN))
    record("7.3", "Perm-deleted dept is 404", 404, r)
else:
    print("  [SKIP] 7.1-7.3 — dept creation failed")

r2 = requests.post(f"{BASE}/departments/", headers=ah(ADMIN_TOKEN),
                   json={"department_name": f"ActiveDept7 {TS}", "company_id": A_COMPANY_ID})
active_dept_id = r2.json().get("department_id") if r2.status_code == 201 else None
if active_dept_id:
    r = requests.delete(f"{BASE}/departments/{active_dept_id}/permanent",
                        headers=ah(ADMIN_TOKEN))
    record("7.4", "Admin perm-delete active dept → 400", 400, r)

# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Section 8: Permanent Delete — Roles [BUG FIX] ────────────────────")

# Create role using ADMIN_TOKEN with fixed create_role() (explicit company_id)
r = requests.post(f"{BASE}/roles/", headers=ah(ADMIN_TOKEN),
                  json={"role_name": f"PermRole8 {TS}", "department_id": A_DEPT_ID,
                        "company_id": A_COMPANY_ID})
perm_role_id = r.json().get("role_id") if r.status_code == 201 else None
if not perm_role_id:
    perm_role_id = get_role_id_by_name(ADMIN_TOKEN, f"Permrole8 {TS}")
    if perm_role_id:
        print(f"  [INFO] role_id fetched by name lookup: {perm_role_id}")

if perm_role_id:
    r = requests.delete(f"{BASE}/roles/{perm_role_id}/permanent",
                        headers=ah(A_SUPER_TOKEN))
    record("8.1", "Non-admin cannot perm-delete role → 403", 403, r)

    r = requests.delete(f"{BASE}/roles/{perm_role_id}/permanent",
                        headers=ah(ADMIN_TOKEN))
    record("8.2", "Admin perm-delete active role → 400", 400, r)

    requests.delete(f"{BASE}/roles/{perm_role_id}", headers=ah(A_SUPER_TOKEN))

    r = requests.delete(f"{BASE}/roles/{perm_role_id}/permanent",
                        headers=ah(ADMIN_TOKEN))
    record("8.3", "Admin perm-deletes soft-deleted role from Company A → 200  [BUG FIX]", 200, r)

    r = requests.delete(f"{BASE}/roles/{perm_role_id}/permanent",
                        headers=ah(ADMIN_TOKEN))
    record("8.4", "Second perm-delete same role → 404", 404, r)
else:
    print(f"  [ERROR] Could not create/find PermRole8 — role creation returned: {r.status_code} {r.text}")

if super_role_id:
    r = requests.delete(f"{BASE}/roles/{super_role_id}/permanent",
                        headers=ah(ADMIN_TOKEN))
    record("8.5", "Admin cannot perm-delete Company Super Admin role → 400 or 403",
           r.status_code if r.status_code in (400, 403) else 403, r)

# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Section 9: Permanent Delete — Users [BUG FIX] ────────────────────")

disp_email = f"disp_{TS}@datagrid.co.in"
r = requests.post(f"{BASE}/users/", headers=ah(ADMIN_TOKEN),
                  json={"name": "Disposable", "email": disp_email,
                        "password": "Admin@123",
                        "company_id": A_COMPANY_ID, "department_id": A_DEPT_ID})
disp_user_id = r.json().get("user_id") if r.status_code == 201 else None

if disp_user_id:
    r = requests.delete(f"{BASE}/users/{disp_user_id}/permanent",
                        headers=ah(A_SUPER_TOKEN))
    record("9.1", "Non-admin cannot perm-delete user → 403", 403, r)

    r = requests.delete(f"{BASE}/users/{disp_user_id}/permanent",
                        headers=ah(ADMIN_TOKEN))
    record("9.2", "Admin perm-delete active user → 400", 400, r)

    requests.delete(f"{BASE}/users/{disp_user_id}", headers=ah(ADMIN_TOKEN))

    r = requests.delete(f"{BASE}/users/{disp_user_id}/permanent",
                        headers=ah(ADMIN_TOKEN))
    record("9.3", "Admin perm-deletes soft-deleted user from Company A → 200  [BUG FIX]", 200, r)

    r = requests.delete(f"{BASE}/users/{disp_user_id}/permanent",
                        headers=ah(ADMIN_TOKEN))
    record("9.4", "Second perm-delete same user → 404", 404, r)
else:
    print(f"  [ERROR] Could not create disposable user: {r.status_code} {r.text}")

# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Section 10: Cross-company Isolation ───────────────────────────────")

r = requests.get(f"{BASE}/users/?per_page=100", headers=ah(B_SUPER_TOKEN))
record("10.1", "Company B Super Admin list-users → 200, no Company A rows", 200, r,
       lambda b: not any(u["company_id"] == A_COMPANY_ID for u in b.get("data", [])))

r = requests.get(f"{BASE}/roles/?per_page=100", headers=ah(B_SUPER_TOKEN))
record("10.2", "Company B Super Admin list-roles → 200, no Company A rows", 200, r,
       lambda b: not any(ro.get("company_id") == A_COMPANY_ID for ro in b.get("data", [])))

r = requests.get(f"{BASE}/companies/{COMPANY_B_ID}", headers=ah(A_SUPER_TOKEN))
record("10.3", "Company A Super Admin cannot view Company B → 403 or 404",
       r.status_code if r.status_code in (403, 404) else 403, r)

r = requests.get(f"{BASE}/users/")
record("10.4", "Unauthenticated request → 401", 401, r)

r = requests.get(f"{BASE}/companies/{COMPANY_B_ID}", headers=ah(ADMIN_TOKEN))
record("10.5", "Admin can view Company B → 200", 200, r)

r = requests.get(f"{BASE}/users/{A_SUPER_USER_ID}", headers=ah(ADMIN_TOKEN))
record("10.6", "Admin views user in Company A → 200", 200, r)

r = requests.put(f"{BASE}/users/{A_SUPER_USER_ID}", headers=ah(ADMIN_TOKEN),
                 json={"name": "Rushiraj"})
record("10.7", "Admin updates user in Company A → 200", 200, r)

r = requests.get(f"{BASE}/roles/{test_role_5_id}", headers=ah(ADMIN_TOKEN))
record("10.8", "Admin views role in Company A → 200", 200, r)

r = requests.put(f"{BASE}/roles/{test_role_5_id}", headers=ah(ADMIN_TOKEN),
                 json={"description": "Updated by Admin"})
record("10.9", "Admin updates role in Company A → 200", 200, r)

# Unified login tests
r1 = requests.post(f"{BASE}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrongpass"})
record("10.10", "Admin login wrong password via unified route → 401", 401, r1)

r2 = requests.post(f"{BASE}/auth/login", json={"email": "nonexistent_email_12345@nowhere.com", "password": "x"})
record("10.11", "Nonexistent email login via unified route → 401 (identical body)", 401, r2,
       lambda b: r1.text == r2.text and b.get("error") == "Invalid credentials")

r3 = requests.post(f"{BASE}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
record("10.12", "Unified admin login → 200 with is_administrator: true", 200, r3,
       lambda b: b.get("is_administrator") is True and "access_token" in b)

new_admin_token = r3.json().get("access_token") if r3.status_code == 200 else None
r4 = requests.get(f"{BASE}/companies/{COMPANY_B_ID}", headers=ah(new_admin_token)) if new_admin_token else r3
record("10.13", "Admin token from unified login allows admin access → 200", 200, r4)

r5 = requests.post(f"{BASE}/auth/login", json={"email": A_SUPER_EMAIL, "password": A_SUPER_PASS})
record("10.14", "Regular user unified login regression check → 200", 200, r5,
       lambda b: "access_token" in b and "user" in b and b.get("is_administrator") is not True)

# Module import shadowing regression checks
r6 = requests.get(f"{BASE}/menu/permissions", headers=ah(A_SUPER_TOKEN))
record("10.15", "Regular user get-permissions loads successfully (no UnboundLocalError) → 200", 200, r6,
       lambda b: "permissions" in b and isinstance(b["permissions"], dict))

r7 = requests.get(f"{BASE}/menu/sidebar", headers=ah(A_SUPER_TOKEN))
record("10.16", "Regular user get-sidebar loads successfully → 200", 200, r7,
       lambda b: "menu" in b and isinstance(b["menu"], list))

r8 = requests.get(f"{BASE}/users/?per_page=100", headers=ah(ADMIN_TOKEN))
record("10.17", "Admin list-users (across all companies) → 200, contains multiple company records", 200, r8,
       lambda b: "data" in b and len(b["data"]) > 0 and any(u.get("company_id") == A_COMPANY_ID for u in b["data"]))

r9 = requests.get(f"{BASE}/roles/", headers=ah(ADMIN_TOKEN))
record("10.18", "Admin list-roles (across all companies) → 200, contains multiple company records", 200, r9,
       lambda b: "data" in b and len(b["data"]) > 0 and any(ro.get("company_id") == A_COMPANY_ID for ro in b["data"]))

# Section 10: Department Cross-company Isolation Checks [PART A]
r_dept_a = requests.get(f"{BASE}/departments/?per_page=100", headers=ah(A_SUPER_TOKEN))
record("10.19", "Company A Super Admin list-depts → 200, no Company B rows", 200, r_dept_a,
       lambda b: "data" in b and not any(d["company_id"] == COMPANY_B_ID for d in b["data"]))

r_dept_b = requests.get(f"{BASE}/departments/?per_page=100", headers=ah(B_SUPER_TOKEN))
record("10.20", "Company B Super Admin list-depts → 200, no Company A rows", 200, r_dept_b,
       lambda b: "data" in b and not any(d["company_id"] == A_COMPANY_ID for d in b["data"]))

r_get_dept_b = requests.get(f"{BASE}/departments/{B_DEPT_ID}", headers=ah(A_SUPER_TOKEN))
record("10.21", "Company A Super Admin cannot get Company B dept → 404", 404, r_get_dept_b)

r_put_dept_b = requests.put(f"{BASE}/departments/{B_DEPT_ID}", headers=ah(A_SUPER_TOKEN), json={"department_name": "HackName"})
record("10.22", "Company A Super Admin cannot update Company B dept → 404", 404, r_put_dept_b)

r_del_dept_b = requests.delete(f"{BASE}/departments/{B_DEPT_ID}", headers=ah(A_SUPER_TOKEN))
record("10.23", "Company A Super Admin cannot delete Company B dept → 404", 404, r_del_dept_b)

# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Section 11: Extra Cross-company isolation checks ───────────────────")

# Fetch some IDs from DB for Company A and Company B
session = DBSession()
try:
    # Get a module from Company A
    mod_a = session.execute(
        meta.tables["modules"].select().where(meta.tables["modules"].c.company_id == A_COMPANY_ID)
    ).first()
    mod_a_id = mod_a.id if mod_a else None

    # Get a module from Company B
    mod_b = session.execute(
        meta.tables["modules"].select().where(meta.tables["modules"].c.company_id == COMPANY_B_ID)
    ).first()
    mod_b_id = mod_b.id if mod_b else None

    # Get an action from Company B
    act_b = session.execute(
        meta.tables["module_action"].select().where(meta.tables["module_action"].c.company_id == COMPANY_B_ID)
    ).first()
    act_b_id = act_b.id if act_b else None

    # Get user role mapping from Company B
    urm_b = session.execute(
        meta.tables["user_role_mapping"].select().where(meta.tables["user_role_mapping"].c.company_id == COMPANY_B_ID)
    ).first()
    urm_b_id = urm_b.id if urm_b else None
    
    # Get super admin role of Company B
    role_b = session.execute(
        meta.tables["roles"].select().where(
            meta.tables["roles"].c.company_id == COMPANY_B_ID,
            meta.tables["roles"].c.is_super_admin == True
        )
    ).first()
    role_b_id = role_b.id if role_b else None

    # Get regular user of Company B
    user_b_id = b_ids["regular_user_id"] or b_ids["super_user_id"]
finally:
    session.close()

# 11.1 - Modules Listing for Company A Super Admin
r_mods_a = requests.get(f"{BASE}/modules/?per_page=100", headers=ah(A_SUPER_TOKEN))
record("11.1", "Company A Super Admin list-modules → 200, no Company B rows", 200, r_mods_a,
       lambda b: "data" in b and not any(m["company_id"] == COMPANY_B_ID for m in b["data"]))

# 11.2 - Modules Listing for Company B Super Admin
r_mods_b = requests.get(f"{BASE}/modules/?per_page=100", headers=ah(B_SUPER_TOKEN))
record("11.2", "Company B Super Admin list-modules → 200, no Company A rows", 200, r_mods_b,
       lambda b: "data" in b and not any(m["company_id"] == A_COMPANY_ID for m in b["data"]))

# 11.3 - Company A Super Admin cannot get Company B module
r_get_mod_b = requests.get(f"{BASE}/modules/{mod_b_id}", headers=ah(A_SUPER_TOKEN))
record("11.3", "Company A Super Admin cannot get Company B module → 404", 404, r_get_mod_b)

# 11.4 - Company A Super Admin cannot update Company B module
r_put_mod_b = requests.put(f"{BASE}/modules/{mod_b_id}", headers=ah(A_SUPER_TOKEN), json={"module_name": "HackName"})
record("11.4", "Company A Super Admin cannot update Company B module → 404", 404, r_put_mod_b)

# 11.5 - Company A Super Admin cannot delete Company B module
r_del_mod_b = requests.delete(f"{BASE}/modules/{mod_b_id}", headers=ah(A_SUPER_TOKEN))
record("11.5", "Company A Super Admin cannot delete Company B module → 404", 404, r_del_mod_b)

# 11.6 - Company A Super Admin gets module actions of Company A module
r_act_a = requests.get(f"{BASE}/module-actions/module/{mod_a_id}/actions", headers=ah(A_SUPER_TOKEN))
record("11.6", "Company A Super Admin get-module-actions for own module → 200", 200, r_act_a)

# 11.7 - Company A Super Admin cannot get module actions of Company B module
r_act_b = requests.get(f"{BASE}/module-actions/module/{mod_b_id}/actions", headers=ah(A_SUPER_TOKEN))
record("11.7", "Company A Super Admin cannot get Company B module actions → 404", 404, r_act_b)

# 11.8 - Company A Super Admin cannot update Company B module action
r_put_act_b = requests.put(f"{BASE}/module-actions/action/{act_b_id}", headers=ah(A_SUPER_TOKEN), json={"action_name": "HackAct"})
record("11.8", "Company A Super Admin cannot update Company B module action → 404", 404, r_put_act_b)

# 11.9 - Company A Super Admin cannot view Company B user permissions
r_perm_b = requests.get(f"{BASE}/permissions/user/{user_b_id}", headers=ah(A_SUPER_TOKEN))
record("11.9", "Company A Super Admin cannot view Company B user permissions → 404", 404, r_perm_b)

# 11.10 - Company A Super Admin cannot update Company B user permissions
r_put_perm_b = requests.post(f"{BASE}/permissions/user/{user_b_id}", headers=ah(A_SUPER_TOKEN), json={"permissions": {}})
record("11.10", "Company A Super Admin cannot update Company B user permissions → 404", 404, r_put_perm_b)

# 11.11 - Company A Super Admin cannot assign Company B role permission
r_crud_b = requests.post(f"{BASE}/permissions/role", headers=ah(A_SUPER_TOKEN), json={
    "role_id": role_b_id,
    "module_id": mod_b_id,
    "action_id": act_b_id,
    "company_id": COMPANY_B_ID
})
record("11.11", "Company A Super Admin cannot assign Company B role permission → 404", 404, r_crud_b)

# 11.12 - Company A Super Admin cannot update Company B user-role mapping
r_urm_b = requests.put(f"{BASE}/user-roles/user-role/{urm_b_id}", headers=ah(A_SUPER_TOKEN), json={"status": 1})
record("11.12", "Company A Super Admin cannot update Company B user-role mapping → 404", 404, r_urm_b)

# 11.13 - Company A Super Admin cannot assign Company B role to Company B user
r_assign_b = requests.post(f"{BASE}/user-roles/user/{user_b_id}/roles", headers=ah(A_SUPER_TOKEN), json={
    "role_id": role_b_id,
    "department_id": B_DEPT_ID
})
record("11.13", "Company A Super Admin cannot assign Company B role → 404", 404, r_assign_b)

# 11.14 - Company A Super Admin gets audit logs. Verify no Company B audit logs are returned.
r_audit_a = requests.get(f"{BASE}/audit/logs?per_page=100", headers=ah(A_SUPER_TOKEN))
record("11.14", "Company A Super Admin list-audit-logs → 200, no Company B logs", 200, r_audit_a,
       lambda b: "logs" in b and not any(log.get("user", {}).get("id") == user_b_id for log in b["logs"]))

# 11.15 - Company A Super Admin cannot view Company B user audit logs
r_user_audit_b = requests.get(f"{BASE}/audit/user/{user_b_id}", headers=ah(A_SUPER_TOKEN))
record("11.15", "Company A Super Admin cannot view Company B user audit logs → 404", 404, r_user_audit_b)

# ═══════════════════════════════════════════════════════════════════════════════
passed_count = sum(1 for r in results if r["passed"])
total        = len(results)
failed       = [r for r in results if not r["passed"]]

print("\n" + "═"*70)
print(f"  RESULTS: {passed_count}/{total} PASSED   {len(failed)} FAILED")
print("═"*70)
print(f"  {'TEST':<8} {'EXP':<6} {'ACT':<6} {'STATUS':<10}  DESCRIPTION")
print(f"  {'────':<8} {'───':<6} {'───':<6} {'──────':<10}  ───────────")
for r in results:
    tag = "✅ PASS" if r["passed"] else "❌ FAIL"
    print(f"  {str(r['num']):<8} {str(r['expected']):<6} {str(r['actual']):<6} {tag:<12} {r['desc']}")

if failed:
    print("\n" + "─"*70)
    print("  FAILURE DETAILS")
    print("─"*70)
    for r in failed:
        fd = r["fail_detail"]
        print(f"\n  ❌ Test {r['num']}: {r['desc']}")
        print(f"     URL     : {fd['url']}")
        print(f"     Method  : {fd['method']}")
        print(f"     ReqBody : {json.dumps(fd['request_body'], indent=6)}")
        print(f"     Status  : {fd['response_status']}")
        print(f"     RespBody: {json.dumps(fd['response_body'], indent=6)}")

print("\n" + "═"*70)
sys.exit(0 if not failed else 1)
