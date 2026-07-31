# Backend & Automated Testing Playbook

This document provides step-by-step procedures for executing automated backend diagnostic suites and full E2E lifecycle test scripts.

---

## 1. Primary Authorization Diagnostic Suite (`test_authz_refactor.py`)

The project contains a comprehensive automated regression suite located at `backend/scripts/test_authz_refactor.py`.

### **How to Run**:
```bash
cd /home/dev82/Documents/voatz
python3 backend/scripts/test_authz_refactor.py
```

### **What It Tests**:
- **Section 1–9**: Authentication, Company CRUD, User/Role CRUD, Permanent Soft-Delete Guards, Super Admin Protections.
- **Section 10**: Cross-Tenant Isolation (Verifies Company A cannot access Company B resources).
- **Section 11**: Module & Action RBAC Permissions, Dynamic Sidebar & Menu Security.
- **Section 12**: Voter CRUD, Verification & Cross-Tenant Data Isolation.
- **Section 13**: Voter Registration CRUD, Status Transitions (`pending` $\rightarrow$ `approved` $\rightarrow$ `rejected`), Bulk Approvals.
- **Section 14**: Candidates CRUD, Ballot Linking, Candidate Stats & Vote Scoping.

**Mandatory Rule**: All 70+ test cases in `test_authz_refactor.py` MUST pass with `✅ PASS` (100% pass rate) before committing code.

---

## 2. E2E Administrative Lifecycle Verification Script

To test the complete end-to-end operational pipeline (Platform Admin Onboarding $\rightarrow$ Election Setup $\rightarrow$ Voter Voting $\rightarrow$ Tallying $\rightarrow$ Results Publication), run the programmatic verification script:

```bash
python3 -c "
import urllib.request, json, random

def req(url, method='GET', body=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    data = json.dumps(body).encode('utf-8') if body else None
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as res:
            return res.status, json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

rand_tag = random.randint(1000, 9999)

# 1. Platform Admin Login
st, adm = req('http://localhost:4000/api/auth/login', 'POST', {'email': 'admin@gmail.com', 'password': 'Admin@123'})
adm_token = adm['access_token']

# 2. Onboard Company
st, comp = req('http://localhost:4000/api/companies/', 'POST', {'company_name': f'Test Company {rand_tag}', 'code': f'TC{rand_tag}', 'status': 1}, token=adm_token)
company_id = comp['company_id']

# 3. Create Super Admin Role & User
st, role = req('http://localhost:4000/api/roles/', 'POST', {'company_id': company_id, 'role_name': 'Company Super Admin', 'is_super_admin': True}, token=adm_token)
role_id = role['role_id']

st, user = req('http://localhost:4000/api/users/', 'POST', {'company_id': company_id, 'name': 'Super Admin', 'email': f'admin_{rand_tag}@test.com', 'password': 'AdminUser123!'}, token=adm_token)
user_id = user['user_id']
req(f'http://localhost:4000/api/user-roles/user/{user_id}/roles', 'POST', {'role_id': role_id}, token=adm_token)

print('✅ Step 1: Onboarding Complete')
"
```

---

## 3. Pre-Commit QA Validation Checklist

Before submitting code changes, verify:
- [ ] `python3 backend/scripts/test_authz_refactor.py` executes with 100% pass rate.
- [ ] No unhandled datetime timezone exceptions occur (all comparisons use IST aware datetimes).
- [ ] All database write operations use `safe_commit` wrappers.
- [ ] `db.session.flush()` is called when creating objects with parent-child foreign key dependencies.
