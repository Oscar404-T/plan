from .users import router as users_router
from .orders import router as orders_router
from .operations import router as operations_router
from .capacities import router as capacities_router
from .workshop_capacities import router as workshop_capacities_router

__all__ = ["users_router", "orders_router", "operations_router", "capacities_router", "workshop_capacities_router"]