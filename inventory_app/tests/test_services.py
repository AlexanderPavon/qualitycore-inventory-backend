# tests/test_services.py
"""
Tests para servicios de lógica de negocio.
Cubre: InventoryService, SaleService, AlertService, PurchaseService.
"""
from django.test import TestCase
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.utils import timezone
from decimal import Decimal

from inventory_app.models import Product, Category, Supplier, Customer, User, Movement, Sale, Purchase
from inventory_app.models.alert import Alert
from inventory_app.services.inventory_service import InventoryService
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
            status='Disponible',
            supplier=self.supplier,
        )


# =============================================================================
# Tests de InventoryService
# =============================================================================
class TestInventoryService(ServiceBaseTestCase):
    """Tests para el servicio de inventario."""

    def test_movimiento_entrada_aumenta_stock(self):
        """Un movimiento de entrada debe aumentar el stock del producto."""
        product = self.create_product(stock=10)
        InventoryService.register_movement(
            product_id=product.id,
            quantity=5,
            movement_type='input',
            user=self.user,
        )
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 15)

    def test_movimiento_salida_disminuye_stock(self):
        """Un movimiento de salida debe disminuir el stock del producto."""
        product = self.create_product(stock=20)
        InventoryService.register_movement(
            product_id=product.id,
            quantity=8,
            movement_type='output',
            user=self.user,
            customer=self.customer,
        )
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 12)

    def test_movimiento_salida_sin_stock_falla(self):
        """Un movimiento de salida sin stock suficiente debe fallar."""
        product = self.create_product(stock=3)
        with self.assertRaises(DRFValidationError):
            InventoryService.register_movement(
                product_id=product.id,
                quantity=10,
                movement_type='output',
                user=self.user,
            )

    def test_movimiento_producto_inexistente_falla(self):
        """Un movimiento con producto inexistente debe fallar."""
        with self.assertRaises(DRFValidationError):
            InventoryService.register_movement(
                product_id=99999,
                quantity=5,
                movement_type='input',
                user=self.user,
            )

    def test_movimiento_tipo_invalido_falla(self):
        """Un movimiento con tipo inválido debe fallar."""
        product = self.create_product()
        with self.assertRaises(DRFValidationError):
            InventoryService.register_movement(
                product_id=product.id,
                quantity=5,
                movement_type='invalid',
                user=self.user,
            )

    def test_movimiento_crea_registro(self):
        """Un movimiento debe crear un registro en la tabla Movement."""
        product = self.create_product(stock=10)
        movement = InventoryService.register_movement(
            product_id=product.id,
            quantity=5,
            movement_type='input',
            user=self.user,
        )
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, 5)
        self.assertEqual(movement.movement_type, 'input')

    def test_check_stock_availability_suficiente(self):
        """check_stock_availability debe retornar True si hay stock."""
        product = self.create_product(stock=10)
        available, current = InventoryService.check_stock_availability(product.id, 5)
        self.assertTrue(available)
        self.assertEqual(current, 10)

    def test_check_stock_availability_insuficiente(self):
        """check_stock_availability debe retornar False si no hay stock."""
        product = self.create_product(stock=3)
        available, current = InventoryService.check_stock_availability(product.id, 10)
        self.assertFalse(available)
        self.assertEqual(current, 3)

    def test_check_stock_producto_inexistente(self):
        """check_stock_availability con producto inexistente retorna (False, 0)."""
        available, current = InventoryService.check_stock_availability(99999, 1)
        self.assertFalse(available)
        self.assertEqual(current, 0)

    def test_get_low_stock_products(self):
        """get_low_stock_products debe retornar productos con stock bajo."""
        self.create_product(name='Bajo Stock', stock=2, min_stock=10)
        self.create_product(name='Stock OK', stock=50, min_stock=5)

        low_stock = InventoryService.get_low_stock_products()
        names = [p.name for p in low_stock]
        self.assertIn('Bajo Stock', names)
        self.assertNotIn('Stock OK', names)


# =============================================================================
# Tests de SaleService
# =============================================================================
class TestSaleService(ServiceBaseTestCase):
    """Tests para el servicio de ventas."""

    def test_crear_venta_exitosa(self):
        """Debe crear una venta con múltiples productos."""
        product1 = self.create_product(name='Producto 1', stock=20, price='100.00')
        product2 = self.create_product(name='Producto 2', stock=15, price='50.00')

        sale = SaleService.create_sale(
            customer_id=self.customer.id,
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

        SaleService.create_sale(
            customer_id=self.customer.id,
            user_id=self.user.id,
            items=[{'product': product.id, 'quantity': 5}]
        )

        product.refresh_from_db()
        self.assertEqual(product.current_stock, 25)

    def test_venta_sin_items_falla(self):
        """Una venta sin productos debe fallar."""
        with self.assertRaises(DjangoValidationError):
            SaleService.create_sale(
                customer_id=self.customer.id,
                user_id=self.user.id,
                items=[]
            )

    def test_venta_stock_insuficiente_falla(self):
        """Una venta con stock insuficiente debe fallar sin modificar nada."""
        product = self.create_product(stock=3, price='10.00')

        with self.assertRaises(DjangoValidationError):
            SaleService.create_sale(
                customer_id=self.customer.id,
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
            SaleService.create_sale(
                customer_id=99999,
                user_id=self.user.id,
                items=[{'product': product.id, 'quantity': 1}]
            )

    def test_venta_usuario_inexistente_falla(self):
        """Una venta con usuario inexistente debe fallar."""
        product = self.create_product(stock=10)
        with self.assertRaises(DjangoValidationError):
            SaleService.create_sale(
                customer_id=self.customer.id,
                user_id=99999,
                items=[{'product': product.id, 'quantity': 1}]
            )

    def test_venta_producto_inexistente_falla(self):
        """Una venta con producto inexistente debe fallar."""
        with self.assertRaises(DjangoValidationError):
            SaleService.create_sale(
                customer_id=self.customer.id,
                user_id=self.user.id,
                items=[{'product': 99999, 'quantity': 1}]
            )

    def test_venta_cantidad_cero_falla(self):
        """Una venta con cantidad 0 debe fallar."""
        product = self.create_product(stock=10)
        with self.assertRaises(DjangoValidationError):
            SaleService.create_sale(
                customer_id=self.customer.id,
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

        purchase = PurchaseService.create_purchase(
            supplier_id=self.supplier.id,
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

        PurchaseService.create_purchase(
            supplier_id=self.supplier.id,
            user_id=self.user.id,
            items=[{'product': product.id, 'quantity': 5}]
        )

        product.refresh_from_db()
        self.assertEqual(product.current_stock, 15)

    def test_compra_crea_movimientos(self):
        """La compra debe crear movimientos de entrada."""
        product = self.create_product_for_supplier(self.supplier, stock=10)

        purchase = PurchaseService.create_purchase(
            supplier_id=self.supplier.id,
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

        with self.assertRaises(ValueError) as ctx:
            PurchaseService.create_purchase(
                supplier_id=self.supplier.id,
                user_id=self.user.id,
                items=[{'product': product_supplier2.id, 'quantity': 1}]
            )

        self.assertIn('no pertenece al proveedor', str(ctx.exception))

    def test_compra_proveedor_inexistente_falla(self):
        """Una compra con proveedor inexistente debe fallar."""
        product = self.create_product_for_supplier(self.supplier)
        with self.assertRaises(ValueError):
            PurchaseService.create_purchase(
                supplier_id=99999,
                user_id=self.user.id,
                items=[{'product': product.id, 'quantity': 1}]
            )

    def test_compra_usuario_inexistente_falla(self):
        """Una compra con usuario inexistente debe fallar."""
        product = self.create_product_for_supplier(self.supplier)
        with self.assertRaises(ValueError):
            PurchaseService.create_purchase(
                supplier_id=self.supplier.id,
                user_id=99999,
                items=[{'product': product.id, 'quantity': 1}]
            )

    def test_compra_producto_inexistente_falla(self):
        """Una compra con producto inexistente debe fallar."""
        with self.assertRaises(ValueError):
            PurchaseService.create_purchase(
                supplier_id=self.supplier.id,
                user_id=self.user.id,
                items=[{'product': 99999, 'quantity': 1}]
            )
