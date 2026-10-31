from fastapi import APIRouter
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
    profitability
)

api_router = APIRouter(prefix="/api")

api_router.include_router(dashboard.router)
api_router.include_router(customers.router)
api_router.include_router(leads.router)
api_router.include_router(surveys.router)
api_router.include_router(packages.router)
api_router.include_router(quotations.router)
api_router.include_router(payments.router)
api_router.include_router(orders.router)
api_router.include_router(dispatch.router)
api_router.include_router(installations.router)
api_router.include_router(warranties.router)
api_router.include_router(tickets.router)
api_router.include_router(invoices.router)
api_router.include_router(inventory.router)
api_router.include_router(profitability.router)
