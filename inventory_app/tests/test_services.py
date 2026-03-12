# tests/test_services.py
"""
Tests para servicios de lógica de negocio.
Cubre: MovementService, SaleService, AlertService, PurchaseService.
"""
from django.test import TestCase
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from inventory_app.models import Product, Category, Supplier, Customer, User, Movement, Sale, Purchase
from inventory_app.models.alert import Alert
from inventory_app.services.movement_service import MovementService
from inventory_app.services.sale_service import SaleService
from inventory_app.services.alert_service import AlertService
from inventory_app.services.purchase_service import PurchaseService


class ServiceBaseTestCase(TestCase):
    """Clase base con datos de prueba para tests de servicios."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='service@test.com',
            password='TestPass1!',
            name='Service User',
            role='Administrator',
            phone='0991234567',
        )
        cls.category = Category.objects.create(name='Electrónica')
        cls.supplier = Supplier.objects.create(
            name='Proveedor Service',
            email='supplier@service.com',
            document_type='ruc',
            tax_id='1710034065001',
            phone='0997654321',
        )
        cls.customer = Customer.objects.create(
            name='Cliente Service',
            email='customer@service.com',
            document_type='cedula',
            document='1710034065',
            phone='0993456789',
        )

    def create_product(self, name='Producto Test', stock=50, price='100.00', min_stock=5):
        """Helper para crear productos de prueba."""
        return Product.objects.create(
            name=name,
            category=self.category,
            price=Decimal(price),
            current_stock=stock,
            minimum_stock=min_stock,
            status='Activo',
            supplier=self.supplier,
        )


# =============================================================================
# Tests de MovementService
# =============================================================================
class TestMovementService(ServiceBaseTestCase):
    """Tests para el servicio de movimientos de inventario."""

    def test_movimiento_entrada_aumenta_stock(self):
        """Una compra crea un movimiento de entrada que aumenta el stock del producto."""
        product = self.create_product(stock=10)
        PurchaseService.create(
            entity_id=self.supplier.id,
            user_id=self.user.id,
            items=[{'product': product.id, 'quantity': 5}],
        )
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 15)

    def test_movimiento_salida_disminuye_stock(self):
        """Una venta crea un movimiento de salida que disminuye el stock del producto."""
        product = self.create_product(stock=20)
        SaleService.create(
            entity_id=self.customer.id,
            user_id=self.user.id,
            items=[{'product': product.id, 'quantity': 8}],
        )
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 12)

    def test_movimiento_salida_sin_stock_falla(self):
        """Una venta con stock insuficiente debe fallar con ValidationError."""
        product = self.create_product(stock=3)
        with self.assertRaises(DjangoValidationError):
            SaleService.create(
                entity_id=self.customer.id,
                user_id=self.user.id,
                items=[{'product': product.id, 'quantity': 10}],
            )

    def test_movimiento_producto_inexistente_falla(self):
        """Un ajuste con producto inexistente debe fallar."""
        with self.assertRaises(DjangoValidationError):
            MovementService.create_movement(
                movement_type='adjustment',
                product_id=99999,
                quantity=5,
                user_id=self.user.id,
                reason='Test producto inexistente',
            )

    def test_create_movement_input_rechazado(self):
        """create_movement('input') debe lanzar ValidationError — usar PurchaseService."""
        product = self.create_product(stock=10)
        with self.assertRaises(DjangoValidationError) as ctx:
            MovementService.create_movement(
                movement_type='input',
                product_id=product.id,
                quantity=5,
                user_id=self.user.id,
            )
        self.assertIn('PurchaseService', str(ctx.exception))

    def test_create_movement_output_rechazado(self):
        """create_movement('output') debe lanzar ValidationError — usar SaleService."""
        product = self.create_product(stock=10)
        with self.assertRaises(DjangoValidationError) as ctx:
            MovementService.create_movement(
                movement_type='output',
                product_id=product.id,
                quantity=5,
                user_id=self.user.id,
            )
        self.assertIn('SaleService', str(ctx.exception))

    def test_movimiento_crea_registro(self):
        """Una compra debe crear un registro Movement de tipo input en la tabla."""
        product = self.create_product(stock=10)
        PurchaseService.create(
            entity_id=self.supplier.id,
            user_id=self.user.id,
            items=[{'product': product.id, 'quantity': 5}],
        )
        movement = Movement.objects.filter(product=product, movement_type='input').first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, 5)
        self.assertEqual(movement.movement_type, 'input')


# =============================================================================
# Tests de SaleService
# =============================================================================
class TestSaleService(ServiceBaseTestCase):
    """Tests para el servicio de ventas."""

    def test_crear_venta_exitosa(self):
        """Debe crear una venta con múltiples productos."""
        product1 = self.create_product(name='Producto 1', stock=20, price='100.00')
        product2 = self.create_product(name='Producto 2', stock=15, price='50.00')

        sale = SaleService.create(
            entity_id=self.customer.id,
            user_id=self.user.id,
            items=[
                {'product': product1.id, 'quantity': 2},
                {'product': product2.id, 'quantity': 3},
            ]
        )

        self.assertIsNotNone(sale)
        self.assertEqual(sale.total, Decimal('350.00'))  # 2*100 + 3*50
        self.assertEqual(sale.movements.count(), 2)

    def test_venta_descuenta_stock(self):
        """La venta debe descontar el stock de los productos."""
        product = self.create_product(stock=30, price='10.00')

        SaleService.create(
            entity_id=self.customer.id,
            user_id=self.user.id,
            items=[{'product': product.id, 'quantity': 5}]
        )

        product.refresh_from_db()
        self.assertEqual(product.current_stock, 25)

    def test_venta_sin_items_falla(self):
        """Una venta sin productos debe fallar."""
        with self.assertRaises(DjangoValidationError):
            SaleService.create(
                entity_id=self.customer.id,
                user_id=self.user.id,
                items=[]
            )

    def test_venta_stock_insuficiente_falla(self):
        """Una venta con stock insuficiente debe fallar sin modificar nada."""
        product = self.create_product(stock=3, price='10.00')

        with self.assertRaises(DjangoValidationError):
            SaleService.create(
                entity_id=self.customer.id,
                user_id=self.user.id,
                items=[{'product': product.id, 'quantity': 10}]
            )

        # Verificar que el stock no cambió (atomicidad)
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 3)

    def test_venta_cliente_inexistente_falla(self):
        """Una venta con cliente inexistente debe fallar."""
        product = self.create_product(stock=10)
        with self.assertRaises(DjangoValidationError):
            SaleService.create(
                entity_id=99999,
                user_id=self.user.id,
                items=[{'product': product.id, 'quantity': 1}]
            )

    def test_venta_usuario_inexistente_falla(self):
        """Una venta con usuario inexistente debe fallar."""
        product = self.create_product(stock=10)
        with self.assertRaises(DjangoValidationError):
            SaleService.create(
                entity_id=self.customer.id,
                user_id=99999,
                items=[{'product': product.id, 'quantity': 1}]
            )

    def test_venta_producto_inexistente_falla(self):
        """Una venta con producto inexistente debe fallar."""
        with self.assertRaises(DjangoValidationError):
            SaleService.create(
                entity_id=self.customer.id,
                user_id=self.user.id,
                items=[{'product': 99999, 'quantity': 1}]
            )

    def test_venta_cantidad_cero_falla(self):
        """Una venta con cantidad 0 debe fallar."""
        product = self.create_product(stock=10)
        with self.assertRaises(DjangoValidationError):
            SaleService.create(
                entity_id=self.customer.id,
                user_id=self.user.id,
                items=[{'product': product.id, 'quantity': 0}]
            )


# =============================================================================
# Tests de AlertService
# =============================================================================
class TestAlertService(ServiceBaseTestCase):
    """Tests para el servicio de alertas de stock."""

    def test_alerta_stock_agotado(self):
        """Debe crear alerta out_of_stock cuando stock es 0."""
        product = self.create_product(stock=0, min_stock=5)
        AlertService.update_stock_alerts(product)

        alert = Alert.objects.filter(product=product, deleted_at__isnull=True).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.type, 'out_of_stock')

    def test_alerta_una_unidad(self):
        """Debe crear alerta one_unit cuando stock es 1."""
        product = self.create_product(stock=1, min_stock=5)
        AlertService.update_stock_alerts(product)

        alert = Alert.objects.filter(product=product, deleted_at__isnull=True).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.type, 'one_unit')

    def test_alerta_stock_bajo(self):
        """Debe crear alerta low_stock cuando stock está bajo el mínimo."""
        product = self.create_product(stock=3, min_stock=10)
        AlertService.update_stock_alerts(product)

        alert = Alert.objects.filter(product=product, deleted_at__isnull=True).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.type, 'low_stock')

    def test_sin_alerta_stock_ok(self):
        """No debe crear alerta si el stock está por encima del mínimo."""
        product = self.create_product(stock=50, min_stock=5)
        AlertService.update_stock_alerts(product)

        alerts = Alert.objects.filter(product=product, deleted_at__isnull=True)
        self.assertEqual(alerts.count(), 0)

    def test_elimina_alerta_cuando_stock_se_recupera(self):
        """Debe eliminar alertas cuando el stock vuelve a estar bien."""
        product = self.create_product(stock=0, min_stock=5)
        AlertService.update_stock_alerts(product)

        # Verificar que se creó la alerta
        self.assertEqual(
            Alert.objects.filter(product=product, deleted_at__isnull=True).count(), 1
        )

        # Simular que el stock se recupera
        product.current_stock = 20
        product.save()
        AlertService.update_stock_alerts(product)

        # La alerta debe estar eliminada (soft delete)
        self.assertEqual(
            Alert.objects.filter(product=product, deleted_at__isnull=True).count(), 0
        )

    def test_no_duplica_alertas(self):
        """No debe crear alertas duplicadas del mismo tipo."""
        product = self.create_product(stock=0, min_stock=5)

        AlertService.update_stock_alerts(product)
        AlertService.update_stock_alerts(product)
        AlertService.update_stock_alerts(product)

        alerts = Alert.objects.filter(product=product, deleted_at__isnull=True)
        self.assertEqual(alerts.count(), 1)


# =============================================================================
# Tests de PurchaseService
# =============================================================================
class TestPurchaseService(ServiceBaseTestCase):
    """Tests para el servicio de compras."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Crear un segundo proveedor para tests de validación
        cls.supplier2 = Supplier.objects.create(
            name='Proveedor Otro',
            email='supplier2@service.com',
            document_type='ruc',
            tax_id='0102030405001',
            phone='0998765432',
        )

    def create_product_for_supplier(self, supplier, name='Producto Test', stock=50, price='100.00'):
        """Helper para crear productos asignados a un proveedor específico."""
        return Product.objects.create(
            name=name,
            category=self.category,
            price=Decimal(price),
            current_stock=stock,
            minimum_stock=5,
            status='Disponible',
            supplier=supplier,
        )

    def test_compra_exitosa(self):
        """Debe crear una compra con múltiples productos."""
        product1 = self.create_product_for_supplier(self.supplier, name='Producto A', price='100.00')
        product2 = self.create_product_for_supplier(self.supplier, name='Producto B', price='50.00')

        purchase = PurchaseService.create(
            entity_id=self.supplier.id,
            user_id=self.user.id,
            items=[
                {'product': product1.id, 'quantity': 3},
                {'product': product2.id, 'quantity': 2},
            ]
        )

        self.assertIsNotNone(purchase)
        self.assertEqual(purchase.total, Decimal('400.00'))  # 3*100 + 2*50

    def test_compra_aumenta_stock(self):
        """La compra debe aumentar el stock de los productos."""
        product = self.create_product_for_supplier(self.supplier, stock=10, price='10.00')

        PurchaseService.create(
            entity_id=self.supplier.id,
            user_id=self.user.id,
            items=[{'product': product.id, 'quantity': 5}]
        )

        product.refresh_from_db()
        self.assertEqual(product.current_stock, 15)

    def test_compra_crea_movimientos(self):
        """La compra debe crear movimientos de entrada."""
        product = self.create_product_for_supplier(self.supplier, stock=10)

        purchase = PurchaseService.create(
            entity_id=self.supplier.id,
            user_id=self.user.id,
            items=[{'product': product.id, 'quantity': 5}]
        )

        movements = Movement.objects.filter(purchase=purchase)
        self.assertEqual(movements.count(), 1)
        self.assertEqual(movements.first().movement_type, 'input')
        self.assertEqual(movements.first().quantity, 5)

    def test_compra_producto_de_otro_proveedor_falla(self):
        """No debe permitir comprar un producto que no pertenece al proveedor."""
        product_supplier2 = self.create_product_for_supplier(self.supplier2, name='Producto Ajeno')

        with self.assertRaises(DjangoValidationError) as ctx:
            PurchaseService.create(
                entity_id=self.supplier.id,
                user_id=self.user.id,
                items=[{'product': product_supplier2.id, 'quantity': 1}]
            )

        self.assertIn('no pertenece al proveedor', str(ctx.exception))

    def test_compra_proveedor_inexistente_falla(self):
        """Una compra con proveedor inexistente debe fallar."""
        product = self.create_product_for_supplier(self.supplier)
        with self.assertRaises(DjangoValidationError):
            PurchaseService.create(
                entity_id=99999,
                user_id=self.user.id,
                items=[{'product': product.id, 'quantity': 1}]
            )

    def test_compra_usuario_inexistente_falla(self):
        """Una compra con usuario inexistente debe fallar."""
        product = self.create_product_for_supplier(self.supplier)
        with self.assertRaises(DjangoValidationError):
            PurchaseService.create(
                entity_id=self.supplier.id,
                user_id=99999,
                items=[{'product': product.id, 'quantity': 1}]
            )

    def test_compra_producto_inexistente_falla(self):
        """Una compra con producto inexistente debe fallar."""
        with self.assertRaises(DjangoValidationError):
            PurchaseService.create(
                entity_id=self.supplier.id,
                user_id=self.user.id,
                items=[{'product': 99999, 'quantity': 1}]
            )


# =============================================================================
# Tests de MovementService.create_correction
# =============================================================================
class TestMovementServiceCorrection(ServiceBaseTestCase):
    """
    Tests para create_correction en MovementService.
    Cubre: ajuste de stock, validaciones de negocio y marcado del original.
    """

    def _make_input(self, product, quantity=5, days_ago=0):
        """Crea un movimiento de entrada via PurchaseService (cumple constraint input_requires_purchase)."""
        purchase = PurchaseService.create(
            entity_id=self.supplier.id,
            user_id=self.user.id,
            items=[{'product': product.id, 'quantity': quantity}],
        )
        movement = Movement.objects.filter(purchase=purchase, movement_type='input').first()
        if days_ago > 0:
            movement.date = timezone.now() - timedelta(days=days_ago)
            movement.save(update_fields=['date'])
        return movement

    def _make_output(self, product, quantity=5, days_ago=0):
        """Crea un movimiento de salida via SaleService (cumple constraint output_requires_sale)."""
        sale = SaleService.create(
            entity_id=self.customer.id,
            user_id=self.user.id,
            items=[{'product': product.id, 'quantity': quantity}],
        )
        movement = Movement.objects.filter(sale=sale, movement_type='output').first()
        if days_ago > 0:
            movement.date = timezone.now() - timedelta(days=days_ago)
            movement.save(update_fields=['date'])
        return movement

    def test_correccion_input_ajusta_stock_correcto(self):
        """INPUT qty=5 → stock +5. Corregir a qty=3 → diff -2 → stock final -2."""
        product = self.create_product(stock=10)
        movement = self._make_input(product, quantity=5)
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 15)

        MovementService.create_correction(
            original_movement_id=movement.id,
            new_quantity=3,
            reason='Ajuste de entrada errada',
            user_id=self.user.id,
        )

        product.refresh_from_db()
        self.assertEqual(product.current_stock, 13)  # 15 + (3-5) = 13

    def test_correccion_output_ajusta_stock_correcto(self):
        """OUTPUT qty=8 → stock -8. Corregir a qty=3 → diff +5 → stock sube."""
        product = self.create_product(stock=20)
        movement = self._make_output(product, quantity=8)
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 12)

        MovementService.create_correction(
            original_movement_id=movement.id,
            new_quantity=3,
            reason='Salida excesiva corregida',
            user_id=self.user.id,
        )

        product.refresh_from_db()
        self.assertEqual(product.current_stock, 17)  # 12 + (8-3) = 17

    def test_correccion_marca_original_como_corregido(self):
        """El movimiento original debe quedar con correction apuntando a la corrección."""
        product = self.create_product(stock=20)
        movement = self._make_input(product, quantity=5)

        correction = MovementService.create_correction(
            original_movement_id=movement.id,
            new_quantity=2,
            reason='Verificación campo correction',
            user_id=self.user.id,
        )

        movement.refresh_from_db()
        self.assertIsNotNone(movement.correction_id)
        self.assertEqual(movement.correction_id, correction.id)

    def test_correccion_movimiento_ya_corregido_falla(self):
        """Intentar corregir dos veces el mismo movimiento debe fallar."""
        product = self.create_product(stock=20)
        movement = self._make_input(product, quantity=5)

        MovementService.create_correction(
            original_movement_id=movement.id,
            new_quantity=3,
            reason='Primera corrección',
            user_id=self.user.id,
        )

        with self.assertRaises(DjangoValidationError) as ctx:
            MovementService.create_correction(
                original_movement_id=movement.id,
                new_quantity=2,
                reason='Segunda corrección',
                user_id=self.user.id,
            )
        self.assertIn('ya fue corregido', str(ctx.exception))

    def test_correccion_movimiento_antiguo_falla(self):
        """Movimiento de más de 30 días no puede corregirse."""
        product = self.create_product(stock=20)
        movement = self._make_input(product, quantity=5, days_ago=31)

        with self.assertRaises(DjangoValidationError) as ctx:
            MovementService.create_correction(
                original_movement_id=movement.id,
                new_quantity=3,
                reason='Corrección tardía',
                user_id=self.user.id,
            )
        self.assertIn('días de antigüedad', str(ctx.exception))

    def test_correccion_ajuste_no_permitido(self):
        """Solo INPUT y OUTPUT pueden corregirse; ADJUSTMENT debe fallar."""
        product = self.create_product(stock=20)
        adjustment = MovementService.create_movement(
            movement_type='adjustment',
            product_id=product.id,
            quantity=5,
            user_id=self.user.id,
            reason='Ajuste manual',
        )

        with self.assertRaises(DjangoValidationError) as ctx:
            MovementService.create_correction(
                original_movement_id=adjustment.id,
                new_quantity=3,
                reason='Intento inválido',
                user_id=self.user.id,
            )
        self.assertIn('Solo se pueden corregir', str(ctx.exception))

    def test_correccion_misma_cantidad_falla(self):
        """La cantidad corregida no puede ser igual a la original."""
        product = self.create_product(stock=20)
        movement = self._make_input(product, quantity=5)

        with self.assertRaises(DjangoValidationError) as ctx:
            MovementService.create_correction(
                original_movement_id=movement.id,
                new_quantity=5,
                reason='Igual a original',
                user_id=self.user.id,
            )
        self.assertIn('igual a la original', str(ctx.exception))

    def test_correccion_stock_negativo_falla(self):
        """Una corrección que dejaría stock negativo debe fallar con rollback."""
        product = self.create_product(stock=5)
        movement = self._make_output(product, quantity=5)
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 0)

        # Corregir a qty=10: diff = 5-10 = -5 → stock -5 → inválido
        with self.assertRaises(DjangoValidationError) as ctx:
            MovementService.create_correction(
                original_movement_id=movement.id,
                new_quantity=10,
                reason='Corrección que deja negativo',
                user_id=self.user.id,
            )
        self.assertIn('negativo', str(ctx.exception))
        # Stock no cambia (atomicidad)
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 0)
