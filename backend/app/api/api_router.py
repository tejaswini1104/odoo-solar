from fastapi import APIRouter, Depends
from backend.app.api.deps import role_gate
from backend.app.core.roles import ADMIN, SALES, SUPPORT, TECHNICIAN, WAREHOUSE
from backend.app.api.endpoints import (
    dashboard,
    customers,
    leads,
    surveys,
    packages,
    quotations,
    payments,
    orders,
    dispatch,
    installations,
    warranties,
    tickets,
    invoices,
    inventory,
    profitability,
    admin_users,
    reports,
    payroll,
    subsidies,
    stock,
    auth,
    portal,
    portal_billing,
    portal_after_sales,
    notifications,
)

api_router = APIRouter(prefix="/api")

ALL_STAFF = (ADMIN, SALES, TECHNICIAN, SUPPORT, WAREHOUSE)


def gate(read=(), write=()):
    """Who may read (GET) and who may change (POST, PUT and so on) everything in a staff router."""
    return [Depends(role_gate(read=read, write=write))]


# ----- Staff application. Customers are in no list, so they cannot reach any of these. -----
api_router.include_router(dashboard.router, dependencies=gate(read=(ADMIN,)))
api_router.include_router(profitability.router, dependencies=gate(read=(ADMIN,)))
api_router.include_router(admin_users.router, dependencies=gate(read=(ADMIN,), write=(ADMIN,)))
api_router.include_router(reports.router, dependencies=gate(read=(ADMIN,)))
api_router.include_router(payroll.router, dependencies=gate(read=(ADMIN,), write=(ADMIN,)))
api_router.include_router(subsidies.router, dependencies=gate(read=(ADMIN, SALES, SUPPORT), write=(SALES,)))
api_router.include_router(stock.router, dependencies=gate(read=(ADMIN, WAREHOUSE), write=(WAREHOUSE,)))

api_router.include_router(customers.router, dependencies=gate(read=(ADMIN, SALES, SUPPORT, TECHNICIAN), write=(SALES,)))
api_router.include_router(leads.router, dependencies=gate(read=(ADMIN, SALES, SUPPORT), write=(SALES,)))
api_router.include_router(surveys.router, dependencies=gate(read=(ADMIN, SALES, TECHNICIAN), write=(SALES, TECHNICIAN)))
api_router.include_router(packages.router, dependencies=gate(read=ALL_STAFF))
api_router.include_router(quotations.router, dependencies=gate(read=(ADMIN, SALES), write=(SALES,)))
api_router.include_router(payments.router, dependencies=gate(read=(ADMIN, SALES, SUPPORT), write=(SALES, SUPPORT)))
api_router.include_router(orders.router, dependencies=gate(read=(ADMIN, SALES, WAREHOUSE), write=(SALES,)))
api_router.include_router(dispatch.router, dependencies=gate(read=(ADMIN, SALES, WAREHOUSE), write=(WAREHOUSE,)))
api_router.include_router(inventory.router, dependencies=gate(read=(ADMIN, SALES, WAREHOUSE)))
api_router.include_router(installations.router, dependencies=gate(read=(ADMIN, SALES, TECHNICIAN), write=(SALES, TECHNICIAN)))
api_router.include_router(warranties.router, dependencies=gate(read=(ADMIN, SALES, SUPPORT)))
api_router.include_router(tickets.router, dependencies=gate(read=(ADMIN, SALES, SUPPORT), write=(SUPPORT,)))
api_router.include_router(invoices.router, dependencies=gate(read=(ADMIN, SALES, SUPPORT), write=(SALES, SUPPORT)))

# ----- Sign in, and the customer portal (each endpoint checks its own access) -----
api_router.include_router(auth.router)
api_router.include_router(notifications.router)
api_router.include_router(portal.router)
api_router.include_router(portal_billing.router)
api_router.include_router(portal_after_sales.router)
