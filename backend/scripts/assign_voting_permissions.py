#!/usr/bin/env python3
"""
Deprecation Notice:
Module provisioning and permission assignments must be performed by a Platform Administrator
using the audited application flow (/api/modules/provision and /api/permissions).
Direct script manipulation of company_modules or role_permission_mapping is prohibited.
"""

import sys

def main():
    print("⚠️  NOTICE: Direct permission assignment via script is deprecated.")
    print("👉 Module provisioning and permission management must be executed by a Platform Administrator through the audited API endpoints.")
    sys.exit(0)

if __name__ == '__main__':
    main()