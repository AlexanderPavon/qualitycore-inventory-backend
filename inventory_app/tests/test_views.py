# tests/test_views.py
"""
Tests para vistas/API endpoints.
Cubre: autenticación, CRUD de productos, clientes, proveedores y dashboard.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from inventory_app.models import Product, Category, Supplier, Customer, User


class APIBaseTestCase(TestCase):
    """Clase base con cliente autenticado para tests de API."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='api@test.com',
            password='TestPass1!',
            name='API User',
            role='SuperAdmin',
            phone='0991234567',
        )
        cls.category = Category.objects.create(name='Electrónica')
        cls.supplier = Supplier.objects.create(
            name='Proveedor API',
            email='supplier@api.com',
            document_type='ruc',
            tax_id='1710034065001',
            phone='0997654321',
        )
        cls.customer = Customer.objects.create(
            name='Cliente API',
            email='customer@api.com',
            document_type='cedula',
            document='1710034065',
            phone='0993456789',
        )

    def setUp(self):
        """Configurar cliente autenticado para cada test."""
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)


# =============================================================================
# Tests de Autenticación
# =============================================================================
class TestAuthAPI(TestCase):
    """Tests para endpoints de autenticación (JWT via httpOnly cookies)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='auth@test.com',
            password='TestPass1!',
            name='Auth User',
            role='Administrator',
            phone='0991111111',
        )

    def setUp(self):
        self.client = APIClient()

    # --- Login ---

    def test_login_exitoso_setea_cookies(self):
        """Login exitoso debe setear access_token y refresh_token como cookies httpOnly."""
        response = self.client.post('/api/login/', {
            'email': 'auth@test.com',
            'password': 'TestPass1!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Tokens NO deben estar en el body JSON
        self.assertNotIn('tokens', response.data)
        # Datos del usuario sí deben estar
        self.assertIn('user', response.data)
        # Cookies httpOnly deben estar presentes
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(response.cookies['access_token']['httponly'])
        self.assertTrue(response.cookies['refresh_token']['httponly'])

    def test_login_retorna_datos_usuario(self):
        """Login exitoso debe retornar datos del usuario en el body."""
        response = self.client.post('/api/login/', {
            'email': 'auth@test.com',
            'password': 'TestPass1!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['email'], 'auth@test.com')

    def test_login_password_incorrecto(self):
        """Login con password incorrecto debe fallar."""
        response = self.client.post('/api/login/', {
            'email': 'auth@test.com',
            'password': 'WrongPass1!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_usuario_inexistente(self):
        """Login con usuario inexistente debe fallar."""
        response = self.client.post('/api/login/', {
            'email': 'noexiste@test.com',
            'password': 'TestPass1!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Acceso con cookie ---

    def test_acceso_con_cookie_access_token(self):
        """Endpoint protegido debe funcionar con access_token en cookie."""
        # Primero hacer login para obtener la cookie
        login_resp = self.client.post('/api/login/', {
            'email': 'auth@test.com',
            'password': 'TestPass1!',
        }, format='json')
        access_token = login_resp.cookies['access_token'].value

        # Usar la cookie para acceder a endpoint protegido
        self.client.cookies['access_token'] = access_token
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_endpoint_sin_autenticacion(self):
        """Acceder a endpoint protegido sin cookie debe retornar 401."""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Refresh ---

    def test_refresh_renueva_cookies(self):
        """POST /api/token/refresh/ con refresh cookie debe setear nuevas cookies."""
        # Login para obtener cookies
        login_resp = self.client.post('/api/login/', {
            'email': 'auth@test.com',
            'password': 'TestPass1!',
        }, format='json')
        refresh_token = login_resp.cookies['refresh_token'].value

        # Hacer refresh con la cookie
        self.client.cookies['refresh_token'] = refresh_token
        response = self.client.post('/api/token/refresh/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.cookies)

    def test_refresh_sin_cookie_falla(self):
        """POST /api/token/refresh/ sin refresh cookie debe retornar 401."""
        response = self.client.post('/api/token/refresh/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Logout ---

    def test_logout_borra_cookies(self):
        """POST /api/logout/ debe borrar las cookies de tokens."""
        # Login primero
        login_resp = self.client.post('/api/login/', {
            'email': 'auth@test.com',
            'password': 'TestPass1!',
        }, format='json')
        self.client.cookies['access_token'] = login_resp.cookies['access_token'].value

        # Logout
        response = self.client.post('/api/logout/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Las cookies deben estar "borradas" (max-age=0 o valor vacío)
        self.assertEqual(response.cookies['access_token'].value, '')
        self.assertEqual(response.cookies['refresh_token'].value, '')


# =============================================================================
# Tests de Products API
# =============================================================================
class TestProductsAPI(APIBaseTestCase):
    """Tests para endpoints de productos."""

    def test_listar_productos(self):
        """GET /api/products/ debe retornar lista de productos."""
        Product.objects.create(
            name='Test Product',
            category=self.category,
            price=Decimal('99.99'),
            current_stock=10,
            minimum_stock=5,
            status='Disponible',
            supplier=self.supplier,
        )
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_listar_productos_vacio(self):
        """GET /api/products/ sin productos debe retornar lista vacía."""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# =============================================================================
# Tests de Customers API
# =============================================================================
class TestCustomersAPI(APIBaseTestCase):
    """Tests para endpoints de clientes."""

    def test_listar_clientes(self):
        """GET /api/customers/ debe retornar lista de clientes."""
        response = self.client.get('/api/customers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detalle_cliente(self):
        """GET /api/customers/<id>/ debe retornar detalle del cliente."""
        response = self.client.get(f'/api/customers/{self.customer.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detalle_cliente_inexistente(self):
        """GET /api/customers/99999/ debe retornar 404."""
        response = self.client.get('/api/customers/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# Tests de Suppliers API
# =============================================================================
class TestSuppliersAPI(APIBaseTestCase):
    """Tests para endpoints de proveedores."""

    def test_listar_proveedores(self):
        """GET /api/suppliers/ debe retornar lista de proveedores."""
        response = self.client.get('/api/suppliers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detalle_proveedor(self):
        """GET /api/suppliers/<id>/ debe retornar detalle del proveedor."""
        response = self.client.get(f'/api/suppliers/{self.supplier.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# =============================================================================
# Tests de Dashboard API
# =============================================================================
class TestDashboardAPI(APIBaseTestCase):
    """Tests para endpoint del dashboard."""

    def test_dashboard_summary(self):
        """GET /api/dashboard/summary/ debe retornar resumen con todos los campos."""
        response = self.client.get('/api/dashboard/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_products', response.data)
        self.assertIn('total_customers', response.data)
        self.assertIn('total_movements', response.data)
        self.assertIn('total_entries', response.data)
        self.assertIn('total_exits', response.data)
        self.assertIn('low_stock_alerts', response.data)
        self.assertIn('total_sales', response.data)

    def test_dashboard_sin_autenticacion(self):
        """Dashboard sin autenticación debe retornar 401."""
        client = APIClient()
        response = client.get('/api/dashboard/summary/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_cuenta_productos(self):
        """Dashboard debe contar productos correctamente."""
        Product.objects.create(
            name='Dashboard Product',
            category=self.category,
            price=Decimal('10.00'),
            current_stock=5,
            minimum_stock=1,
            status='Disponible',
            supplier=self.supplier,
        )
        response = self.client.get('/api/dashboard/summary/')
        self.assertEqual(response.data['total_products'], 1)


# =============================================================================
# Tests de Alerts API
# =============================================================================
class TestAlertsAPI(APIBaseTestCase):
    """Tests para endpoints de alertas."""

    def test_listar_alertas(self):
        """GET /api/alerts/ debe retornar lista de alertas."""
        response = self.client.get('/api/alerts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
