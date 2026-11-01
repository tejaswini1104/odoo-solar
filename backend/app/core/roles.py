# Roles. "customer" uses the portal; the others use the staff application.
ADMIN = "admin"
SALES = "sales"
TECHNICIAN = "technician"
SUPPORT = "support"
WAREHOUSE = "warehouse"
CUSTOMER = "customer"

STAFF_ROLES = (ADMIN, SALES, TECHNICIAN, SUPPORT, WAREHOUSE)
ALL_ROLES = STAFF_ROLES + (CUSTOMER,)
