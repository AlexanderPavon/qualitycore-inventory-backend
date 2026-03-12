# models/movement.py
from django.db import models
from django.db.models import Q
from .product import Product
from .user import User
from .customer import Customer
from inventory_app.managers import SoftDeleteManager
from inventory_app.constants import MovementType, ValidationMessages

class Movement(models.Model):
    # Usar constantes centralizadas
    MOVEMENT_CHOICES = MovementType.CHOICES

    # Flag para que el signal post_save (signals.py) omita el registro automático
    # en AuditLog. Establecer a True cuando el servicio que crea el movimiento
    # llama directamente a AuditLog.log_action() con datos más ricos (stock_before,
    # stock_after, original_movement_id, etc.) que el signal no puede capturar.
    # Convención: siempre asignarlo antes de .save() — movement._skip_audit = True.
    # Ver también: campo `correction` (OneToOneField) que apunta al movimiento de corrección.
    _skip_audit: bool = False

    movement_type = models.CharField(max_length=10, choices=MOVEMENT_CHOICES)  # Optimizado con choices
    date = models.DateTimeField(db_index=True)  # Índice para filtrado y ordenamiento por fecha
    quantity = models.IntegerField()  # Validación por tipo en service layer (ajustes permiten negativos)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements')
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='movements')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Precio histórico al momento del movimiento
    stock_in_movement = models.IntegerField(default=0)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements")
    sale = models.ForeignKey('Sale', null=True, blank=True, on_delete=models.SET_NULL, related_name="movements")
    purchase = models.ForeignKey('Purchase', null=True, blank=True, on_delete=models.SET_NULL, related_name="movements")
    reason = models.CharField(max_length=500, blank=True, default='')  # Motivo del ajuste/corrección
    correction = models.OneToOneField(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='corrected_movement'
    )  # Si no es null, este movimiento fue corregido y apunta al movimiento de corrección.
       # OneToOneField garantiza a nivel DB que ningún movimiento puede ser la corrección de dos originales.
       # Acceso inverso: correction_movement.corrected_movement → movimiento original.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = SoftDeleteManager()  # Filtra automáticamente registros eliminados
    all_objects = models.Manager()  # Acceso a todos los registros

    class Meta:
        indexes = [
            # Historial de movimientos por producto (más frecuente: listado de movimientos de un producto)
            models.Index(fields=['product', '-date'], name='movement_product_date_idx'),
            # Filtrado por tipo de movimiento + orden por fecha (informes, filtros en UI)
            models.Index(fields=['movement_type', '-date'], name='movement_type_date_idx'),
        ]
        constraints = [
            # Una salida siempre debe tener cliente
            models.CheckConstraint(
                check=~Q(movement_type='output') | Q(customer__isnull=False),
                name='output_requires_customer',
            ),
            # Una salida siempre debe pertenecer a una venta
            models.CheckConstraint(
                check=~Q(movement_type='output') | Q(sale__isnull=False),
                name='output_requires_sale',
            ),
            # Una entrada siempre debe pertenecer a una compra
            models.CheckConstraint(
                check=~Q(movement_type='input') | Q(purchase__isnull=False),
                name='input_requires_purchase',
            ),
        ]

    def __str__(self):
        return f"{self.movement_type} - {self.quantity} of {self.product.name}"
