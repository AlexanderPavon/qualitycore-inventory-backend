# tests/test_models.py
"""
Tests para modelos del sistema.
Cubre: User, Category, Supplier, Customer, Product, Sale, Movement, Alert.
Incluye tests de soft delete y managers personalizados.
"""
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal

from inventory_app.models import Product, Category, Supplier, Customer, User, Movement, Sale
from inventory_app.models.alert import Alert


class BaseTestCase(TestCase):
    """Clase base con datos de prueba reutilizables."""

    @classmethod
    def setUpTestData(cls):
        """Crea datos de prueba que se comparten entre todos los tests de la clase."""
        cls.user = User.objects.create_user(
            email='test@qualitycore.com',
            password='TestPass1!',
            name='Test User',
            role='Administrator',
            phone='0991234567',
        )
        cls.category = Category.objects.create(name='Electrónica')
        cls.supplier = Supplier.objects.create(
            name='Proveedor Test',
            email='proveedor@test.com',
            document_type='ruc',
            tax_id='1710034065001',
            phone='0997654321',
        )
        cls.customer = Customer.objects.create(
            name='Cliente Test',
            email='cliente@test.com',
            document_type='cedula',
            document='1710034065',
            phone='0993456789',
        )
        cls.product = Product.objects.create(
            name='Laptop Test',
            category=cls.category,
            price=Decimal('999.99'),
            current_stock=50,
            minimum_stock=5,
            status='Disponible',
            supplier=cls.supplier,
        )


# =============================================================================
# Tests de User
# =============================================================================
class TestUserModel(TestCase):
    """Tests para el modelo User."""

    def test_crear_usuario(self):
        """Debe crear un usuario correctamente."""
        user = User.objects.create_user(
            email='nuevo@test.com',
            password='TestPass1!',
            name='Nuevo User',
            role='User',
            phone='0991111111',
        )
        self.assertEqual(user.email, 'nuevo@test.com')
        self.assertEqual(user.name, 'Nuevo User')
        self.assertTrue(user.check_password('TestPass1!'))

    def test_crear_usuario_sin_email(self):
        """Debe fallar al crear usuario sin email."""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email='',
                password='TestPass1!',
                name='Sin Email',
                role='User',
                phone='0992222222',
            )

    def test_crear_superusuario(self):
        """Debe crear un superusuario con is_staff y is_superuser en True."""
        admin = User.objects.create_superuser(
            email='admin@test.com',
            password='AdminPass1!',
            name='Admin',
            role='SuperAdmin',
            phone='0993333333',
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_str_usuario(self):
        """__str__ debe retornar el email."""
        user = User.objects.create_user(
            email='str@test.com',
            password='TestPass1!',
            name='Str User',
            role='User',
            phone='0994444444',
        )
        self.assertEqual(str(user), 'str@test.com')


# =============================================================================
# Tests de Category
# =============================================================================
class TestCategoryModel(TestCase):
    """Tests para el modelo Category."""

    def test_crear_categoria(self):
        """Debe crear una categoría correctamente."""
        cat = Category.objects.create(name='Tecnología')
        self.assertEqual(cat.name, 'Tecnología')
        self.assertIsNotNone(cat.created_at)

    def test_categoria_nombre_unico(self):
        """No debe permitir categorías duplicadas."""
        Category.objects.create(name='Única')
        with self.assertRaises(Exception):
            Category.objects.create(name='Única')

    def test_str_categoria(self):
        """__str__ debe retornar el nombre."""
        cat = Category.objects.create(name='Muebles')
        self.assertEqual(str(cat), 'Muebles')


# =============================================================================
# Tests de Soft Delete
# =============================================================================
class TestSoftDelete(BaseTestCase):
    """Tests para el patrón soft delete."""

    def test_soft_delete_product(self):
        """Producto con deleted_at no debe aparecer en objects."""
        product = Product.objects.create(
            name='Producto a eliminar',
            category=self.category,
            price=Decimal('10.00'),
            current_stock=10,
            minimum_stock=1,
            status='Disponible',
            supplier=self.supplier,
        )
        product_id = product.id

        # Soft delete
        product.deleted_at = timezone.now()
        product.save()

        # No debe aparecer en objects (manager con soft delete)
        self.assertFalse(Product.objects.filter(id=product_id).exists())

        # Sí debe aparecer en all_objects
        self.assertTrue(Product.all_objects.filter(id=product_id).exists())

    def test_soft_delete_customer(self):
        """Cliente con deleted_at no debe aparecer en objects."""
        customer = Customer.objects.create(
            name='Cliente eliminar',
            email='eliminar@test.com',
            document_type='cedula',
            document='0102030405',
            phone='0995555555',
        )
        customer_id = customer.id

        customer.deleted_at = timezone.now()
        customer.save()

        self.assertFalse(Customer.objects.filter(id=customer_id).exists())
        self.assertTrue(Customer.all_objects.filter(id=customer_id).exists())


# =============================================================================
# Tests de Product
# =============================================================================
class TestProductModel(BaseTestCase):
    """Tests para el modelo Product."""

    def test_crear_producto(self):
        """Debe crear un producto correctamente."""
        self.assertEqual(self.product.name, 'Laptop Test')
        self.assertEqual(self.product.price, Decimal('999.99'))
        self.assertEqual(self.product.current_stock, 50)

    def test_str_producto(self):
        """__str__ debe retornar el nombre."""
        self.assertEqual(str(self.product), 'Laptop Test')

    def test_producto_stock_cero(self):
        """Producto puede tener stock 0."""
        product = Product.objects.create(
            name='Sin Stock',
            category=self.category,
            price=Decimal('50.00'),
            current_stock=0,
            minimum_stock=5,
            status='Agotado',
            supplier=self.supplier,
        )
        self.assertEqual(product.current_stock, 0)


# =============================================================================
# Tests de Customer
# =============================================================================
class TestCustomerModel(BaseTestCase):
    """Tests para el modelo Customer."""

    def test_crear_cliente(self):
        """Debe crear un cliente correctamente."""
        self.assertEqual(self.customer.name, 'Cliente Test')
        self.assertEqual(self.customer.document_type, 'cedula')

    def test_email_unico(self):
        """No debe permitir emails duplicados."""
        with self.assertRaises(Exception):
            Customer.objects.create(
                name='Duplicado',
                email='cliente@test.com',
                document_type='cedula',
                document='9999999999',
                phone='0996666666',
            )

    def test_documento_unico(self):
        """No debe permitir documentos duplicados."""
        with self.assertRaises(Exception):
            Customer.objects.create(
                name='Duplicado',
                email='otro@test.com',
                document_type='cedula',
                document='1710034065',
                phone='0997777777',
            )


# =============================================================================
# Tests de Supplier
# =============================================================================
class TestSupplierModel(BaseTestCase):
    """Tests para el modelo Supplier."""

    def test_crear_proveedor(self):
        """Debe crear un proveedor correctamente."""
        self.assertEqual(self.supplier.name, 'Proveedor Test')
        self.assertEqual(self.supplier.document_type, 'ruc')

    def test_str_proveedor(self):
        """__str__ debe retornar el nombre."""
        self.assertEqual(str(self.supplier), 'Proveedor Test')


# =============================================================================
# Tests de Movement
# =============================================================================
class TestMovementModel(BaseTestCase):
    """Tests para el modelo Movement."""

    def test_crear_movimiento_entrada(self):
        """Debe crear un movimiento de entrada."""
        movement = Movement.objects.create(
            movement_type='input',
            product=self.product,
            quantity=10,
            user=self.user,
            date=timezone.now(),
            stock_in_movement=self.product.current_stock,
        )
        self.assertEqual(movement.movement_type, 'input')
        self.assertEqual(movement.quantity, 10)

    def test_crear_movimiento_salida_con_cliente(self):
        """Debe crear un movimiento de salida con cliente."""
        movement = Movement.objects.create(
            movement_type='output',
            product=self.product,
            quantity=5,
            user=self.user,
            customer=self.customer,
            date=timezone.now(),
            stock_in_movement=self.product.current_stock,
        )
        self.assertEqual(movement.customer, self.customer)

    def test_str_movimiento(self):
        """__str__ debe mostrar tipo, cantidad y producto."""
        movement = Movement.objects.create(
            movement_type='input',
            product=self.product,
            quantity=3,
            user=self.user,
            date=timezone.now(),
        )
        self.assertIn('input', str(movement))
        self.assertIn('Laptop Test', str(movement))


# =============================================================================
# Tests de Sale
# =============================================================================
class TestSaleModel(BaseTestCase):
    """Tests para el modelo Sale."""

    def test_crear_venta(self):
        """Debe crear una venta correctamente."""
        sale = Sale.objects.create(
            customer=self.customer,
            user=self.user,
            date=timezone.now(),
            total=Decimal('1999.98'),
        )
        self.assertEqual(sale.total, Decimal('1999.98'))
        self.assertEqual(sale.customer, self.customer)

    def test_str_venta(self):
        """__str__ debe mostrar ID, cliente y total."""
        sale = Sale.objects.create(
            customer=self.customer,
            user=self.user,
            date=timezone.now(),
            total=Decimal('500.00'),
        )
        self.assertIn('Cliente Test', str(sale))
        self.assertIn('500.00', str(sale))


# =============================================================================
# Tests de Alert
# =============================================================================
class TestAlertModel(BaseTestCase):
    """Tests para el modelo Alert."""

    def test_crear_alerta(self):
        """Debe crear una alerta correctamente."""
        alert = Alert.objects.create(
            type='low_stock',
            message='Stock bajo para Laptop Test',
            product=self.product,
        )
        self.assertEqual(alert.type, 'low_stock')
        self.assertEqual(alert.product, self.product)

    def test_tipos_alerta(self):
        """Debe soportar todos los tipos de alerta."""
        for alert_type in ['low_stock', 'one_unit', 'out_of_stock']:
            alert = Alert.objects.create(
                type=alert_type,
                message=f'Alerta {alert_type}',
                product=self.product,
            )
            self.assertEqual(alert.type, alert_type)
