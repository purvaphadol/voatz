# Frontend Architecture & UI Testing Playbook

This document details the React frontend architecture, persona-based UI routing, and step-by-step UI testing workflows.

---

## 1. Frontend Architecture & Persona Navigation

The frontend application (`/frontend`) is a single-page React app built with Material-UI (MUI), DataGrid, and Recharts.

### **Navigation & Context Flow**:
```
User Login → AuthContext (Stores JWT & user details) → PermissionContext (Loads permissions & sidebar)
  │
  ├── User is Platform Administrator (is_administrator === true)
  │     └── Renders Platform Admin Navigation:
  │           • Companies Management (/companies)
  │           • System Modules & Actions (/modules)
  │           • System Audit Logs (/audit)
  │
  └── User is Company Super Admin / Staff
        └── Renders Dynamic Company Navigation:
              • Elections (/elections)
              • Ballots (/ballots)
              • Candidates (/candidates)
              • Voters (/voters)
              • Voter Registrations (/voter-registrations)
              • Votes & Stats (/votes)
              • Users & Roles (/users, /roles)
```

---

## 2. Step-by-Step UI Manual & Automated QA Test Plan

### **Test Scenario 1: Platform Admin Onboarding**
1. **Navigate to**: `http://localhost:3000/login`
2. **Credentials**: `admin@gmail.com` / `Admin@123`
3. **Verify UI**:
   - Sidebar displays **Companies**, **Modules**, **Module Actions**, and **Audit Logs**.
   - Navigate to **Companies** $\rightarrow$ Click **Add Company** $\rightarrow$ Submit form.
   - Verify new company appears in MUI DataGrid.

---

### **Test Scenario 2: Company Super Admin Login & Setup**
1. **Log Out** of Platform Admin account.
2. **Log In** with Company Super Admin credentials (e.g. `apex_admin@apex.com`).
3. **Verify UI**:
   - **Companies** menu item is hidden (tenant isolation guard).
   - Sidebar displays **Elections**, **Ballots**, **Candidates**, **Voters**, **Registrations**, **Users**, **Roles**.
4. **Election Setup**:
   - Navigate to **Elections** $\rightarrow$ Click **Create Election**.
   - Input Title, Category, Start Date, End Date (IST).
   - Click **Save**. Verify status chip reads `Draft`.
5. **Ballot & Candidate Creation**:
   - Navigate to **Ballots** $\rightarrow$ Create Ballot linked to the election.
   - Navigate to **Candidates** $\rightarrow$ Add 2 candidates to the ballot.
6. **Workflow Activation**:
   - Return to **Elections** $\rightarrow$ Open **Election Workflow Stepper**.
   - Click **Activate Election**. Status chip changes to `Active` (Green).

---

### **Test Scenario 3: Voter Registration & Voting**
1. **Navigate to Voters**: Add voter details (Name, Phone).
2. **Navigate to Voter Registrations**: Add registration for active election $\rightarrow$ Click **Approve**.
3. **Cast Vote**: Submit ballot vote.
4. **Run Tallying**: Open **Elections** $\rightarrow$ Click **Tally Votes**.
5. **Publish Results**: Click **Publish Results**.
6. **View Results Dashboard**:
   - Click **View Results** (Assessment Icon).
   - Verify Recharts Bar Charts render candidate vote totals correctly.
   - Verify Turnout percentage cards and Winner highlighting.

---

## 3. UI Component Testing Checklist

- [ ] `PermissionGuard.js` correctly blocks unauthorized module routes.
- [ ] MUI DataGrid components correctly support sorting, filtering, and pagination.
- [ ] Modals for creation/editing reset state cleanly on close.
- [ ] Alert banners display server error messages cleanly without crashing the UI.
