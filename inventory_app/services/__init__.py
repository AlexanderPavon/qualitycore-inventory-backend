# services/__init__.py
"""
Capa de servicios - Contiene la lógica de negocio del sistema.

Los servicios encapsulan operaciones de negocio complejas que involucran
múltiples modelos o reglas de negocio. Separan la lógica de negocio
de la capa de presentación (views/serializers).
"""

from .quotation_service import QuotationService
from .movement_service import MovementService
from .sale_service import SaleService
from .purchase_service import PurchaseService

__all__ = ['QuotationService', 'MovementService', 'SaleService', 'PurchaseService']
