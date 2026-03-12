# tests/test_integration.py
"""
Tests de integración para el flujo completo de transacciones de venta y compra.

Verifica la cadena:
    POST /api/sales/   → SaleService → Movement(output) → stock baja → AuditLog → Alert
    POST /api/purchases/ → PurchaseService → Movement(input) → stock sube → AuditLog
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from inventory_app.models import (
    Product, Category, Supplier, Customer, User, Movement, Sale, Purchase,
)
from inventory_app.models.audit_log import AuditLog
from inventory_app.models.alert import Alert


class TestSaleTransactionChain(TestCase):
    """
    Verifica que POST /api/sales/ dispara toda la cadena de efectos secundarios:
    persistencia, stock, auditoría y alertas.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='integration@test.com',
            password='TestPass1!',
            name='Integration User',
            role='SuperAdmin',
            phone='0991234567',
        )
        cls.category = Category.objects.create(name='Electrónica')
        cls.supplier = Supplier.objects.create(
            name='Proveedor Integración',
            email='supplier@integration.com',
            document_type='ruc',
            tax_id='1710034065001',
            phone='0997654321',
        )
        cls.customer = Customer.objects.create(
            name='Cliente Integración',
            email='customer@integration.com',
            document_type='cedula',
            document='1710034065',
            phone='0993456789',
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        # Producto fresco por test para aislar cambios de stock
        self.product = Product.objects.create(
            name='Producto Integración',
            category=self.category,
            price=Decimal('50.00'),
            current_stock=10,
            minimum_stock=5,
            status='Disponible',
            supplier=self.supplier,
        )

    def _post_sale(self, quantity):
        return self.client.post('/api/sales/', {
            'customer': self.customer.id,
            'items': [
                {'product': self.product.id, 'quantity': quantity, 'price': '50.00'}
            ],
        }, format='json')

    # -------------------------------------------------------------------------
    # 1. Respuesta HTTP
    # -------------------------------------------------------------------------
    def test_post_sale_retorna_201(self):
        """POST /api/sales/ con datos válidos debe retornar HTTP 201 Created."""
        response = self._post_sale(2)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # -------------------------------------------------------------------------
    # 2. Objeto Sale persistido
    # -------------------------------------------------------------------------
    def test_post_sale_persiste_objeto_sale(self):
        """Debe existir exactamente un Sale vinculado al cliente y usuario correctos."""
        self._post_sale(2)
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.first()
        self.assertEqual(sale.customer_id, self.customer.id)
        self.assertEqual(sale.user_id, self.user.id)

    # -------------------------------------------------------------------------
    # 3. Movement de salida creado
    # -------------------------------------------------------------------------
    def test_post_sale_crea_movimiento_output(self):
        """SaleService debe crear un Movement de tipo 'output' con la cantidad correcta."""
        cantidad = 3
        self._post_sale(cantidad)
        movement = Movement.objects.filter(
            product=self.product,
            movement_type='output',
        ).first()
        self.assertIsNotNone(movement, "Debe existir un Movement de tipo 'output'")
        self.assertEqual(movement.quantity, cantidad)
        self.assertEqual(movement.user_id, self.user.id)

    # -------------------------------------------------------------------------
    # 4. Stock decrementado atomicamente
    # -------------------------------------------------------------------------
    def test_post_sale_decrementa_stock(self):
        """El current_stock del producto debe disminuir en la cantidad vendida."""
        stock_inicial = self.product.current_stock
        cantidad = 4
        self._post_sale(cantidad)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, stock_inicial - cantidad)

    # -------------------------------------------------------------------------
    # 5. AuditLog registrado via señal post_save → Celery task (on_commit)
    # -------------------------------------------------------------------------
    def test_post_sale_registra_auditlog(self):
        """
        La señal post_save encola log_audit_action vía transaction.on_commit().
        captureOnCommitCallbacks(execute=True) fuerza los callbacks a correr dentro
        del test (CELERY_TASK_ALWAYS_EAGER=True garantiza ejecución síncrona en dev).
        """
        with self.captureOnCommitCallbacks(execute=True):
            response = self._post_sale(2)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        sale = Sale.objects.first()
        log = AuditLog.objects.filter(
            model_name='Sale',
            action='create',
            object_id=sale.id,
        ).first()
        self.assertIsNotNone(log, "Debe existir un AuditLog action='create' para la venta")

    # -------------------------------------------------------------------------
    # 6. Alerta de stock bajo generada por AlertService
    # -------------------------------------------------------------------------
    def test_post_sale_genera_alerta_stock_bajo(self):
        """
        AlertService debe crear una Alert cuando el stock cae por debajo
        de minimum_stock (stock 10 - 7 = 3 < minimum_stock 5).
        """
        self._post_sale(7)
        self.product.refresh_from_db()
        self.assertLess(
            self.product.current_stock,
            self.product.minimum_stock,
            "El stock debe haber caído bajo el mínimo para disparar la alerta",
        )
        alert_exists = Alert.objects.filter(product=self.product).exists()
        self.assertTrue(alert_exists, "Debe existir una Alert de stock bajo para el producto")

    # -------------------------------------------------------------------------
    # 7. Stock insuficiente → 400, stock sin cambios
    # -------------------------------------------------------------------------
    def test_post_sale_rechaza_cantidad_mayor_al_stock(self):
        """
        Vender más unidades que el stock disponible debe retornar HTTP 400
        y dejar el stock sin modificar (rollback atómico).
        """
        response = self._post_sale(self.product.current_stock + 1)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 10, "El stock no debe cambiar si la venta falla")

    # -------------------------------------------------------------------------
    # 8. Cantidad cero → 400 (QuantityValidator.validate_min_one)
    # -------------------------------------------------------------------------
    def test_post_sale_rechaza_cantidad_cero(self):
        """
        quantity=0 debe retornar HTTP 400 (QuantityValidator.validate_min_one)
        y no crear ningún objeto Sale ni Movement.
        """
        response = self._post_sale(0)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(Movement.objects.count(), 0)


class TestPurchaseTransactionChain(TestCase):
    """
    Verifica que POST /api/purchases/ dispara toda la cadena:
    Purchase persistida, Movement(input), stock incrementado, AuditLog creado.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='purchase_integration@test.com',
            password='TestPass1!',
            name='Purchase Integration User',
            role='SuperAdmin',
            phone='0991234568',
        )
        cls.category = Category.objects.create(name='Hardware')
        cls.supplier = Supplier.objects.create(
            name='Proveedor Compras',
            email='supplier@purchase.com',
            document_type='ruc',
            tax_id='1710034065002',
            phone='0997654322',
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(
            name='Producto Compra',
            category=self.category,
            price=Decimal('80.00'),
            current_stock=5,
            minimum_stock=2,
            status='Disponible',
            supplier=self.supplier,
        )

    def _post_purchase(self, quantity):
        return self.client.post('/api/purchases/', {
            'supplier': self.supplier.id,
            'items': [
                {'product': self.product.id, 'quantity': quantity, 'price': '80.00'}
            ],
        }, format='json')

    def test_post_purchase_retorna_201(self):
        """POST /api/purchases/ con datos válidos debe retornar HTTP 201 Created."""
        response = self._post_purchase(3)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_post_purchase_persiste_objeto_purchase(self):
        """Debe existir exactamente una Purchase vinculada al proveedor y usuario correctos."""
        self._post_purchase(3)
        self.assertEqual(Purchase.objects.count(), 1)
        purchase = Purchase.objects.first()
        self.assertEqual(purchase.supplier_id, self.supplier.id)
        self.assertEqual(purchase.user_id, self.user.id)

    def test_post_purchase_crea_movimiento_input(self):
        """PurchaseService debe crear un Movement de tipo 'input' con la cantidad correcta."""
        cantidad = 4
        self._post_purchase(cantidad)
        movement = Movement.objects.filter(
            product=self.product,
            movement_type='input',
        ).first()
        self.assertIsNotNone(movement, "Debe existir un Movement de tipo 'input'")
        self.assertEqual(movement.quantity, cantidad)
        self.assertEqual(movement.user_id, self.user.id)

    def test_post_purchase_incrementa_stock(self):
        """El current_stock del producto debe aumentar en la cantidad comprada."""
        stock_inicial = self.product.current_stock
        cantidad = 6
        self._post_purchase(cantidad)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, stock_inicial + cantidad)

    def test_post_purchase_registra_auditlog(self):
        """La señal post_save encola log_audit_action para la compra creada."""
        with self.captureOnCommitCallbacks(execute=True):
            response = self._post_purchase(3)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        purchase = Purchase.objects.first()
        log = AuditLog.objects.filter(
            model_name='Purchase',
            action='create',
            object_id=purchase.id,
        ).first()
        self.assertIsNotNone(log, "Debe existir un AuditLog action='create' para la compra")

    def test_post_purchase_cantidad_cero_rechazada(self):
        """quantity=0 debe retornar HTTP 400 y no crear ningún objeto."""
        response = self._post_purchase(0)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Purchase.objects.count(), 0)
        self.assertEqual(Movement.objects.count(), 0)
