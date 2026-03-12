# tests/test_views_extended.py
"""
Tests extendidos para vistas/API endpoints.

Cubre lo que test_views.py no tiene:
  - Filtros de productos (search, category, supplier, is_active)
  - Soft-delete oculta registros en lista y detalle
  - CRUD de productos, clientes y proveedores
  - Stock check endpoint
  - Ventas: paginación, filtros de búsqueda/fecha, shape del detalle, idempotencia
  - Compras: filtros y permisos (User no puede crear, solo listar)
  - Movimientos: filtro por tipo, ajustes (admin only), correcciones (admin only)
"""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from inventory_app.models import (
    Category, Customer, Movement, Product, Purchase, Sale, Supplier, User,
)


# =============================================================================
# Base compartida
# =============================================================================

class ExtViewBase(TestCase):
    """
    Clase base con admin + user regular, categoría, proveedor y cliente comunes.
    Los productos NO se crean aquí (stock cambia entre tests → cada test crea el suyo).
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            email='ext_admin@test.com',
            password='TestPass1!',
            name='Ext Admin',
            role='Administrator',
            phone='0991000001',
        )
        cls.regular_user = User.objects.create_user(
            email='ext_user@test.com',
            password='TestPass1!',
            name='Ext User',
            role='User',
            phone='0991000002',
        )
        cls.category = Category.objects.create(name='Ext Category')
        cls.supplier = Supplier.objects.create(
            name='Ext Supplier',
            email='ext_supplier@test.com',
            document_type='ruc',
            tax_id='1710034065001',
            phone='0997000001',
        )
        cls.customer = Customer.objects.create(
            name='Ext Customer',
            email='ext_customer@test.com',
            document_type='cedula',
            document='1710034065',
            phone='0993000001',
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def _make_product(self, name='Producto Ext', stock=20, min_stock=2,
                      status_val='Activo', supplier=None):
        return Product.objects.create(
            name=name,
            category=self.category,
            price=Decimal('50.00'),
            current_stock=stock,
            minimum_stock=min_stock,
            status=status_val,
            supplier=supplier or self.supplier,
        )


# =============================================================================
# Filtros de productos
# =============================================================================

class TestProductFiltersAPI(ExtViewBase):
    """GET /api/products/ con filtros: search, category, supplier, is_active."""

    def setUp(self):
        super().setUp()
        self.product = self._make_product(name='Laptop Principal')

    def test_buscar_productos_por_nombre(self):
        self._make_product(name='Mouse Gamer')
        response = self.client.get('/api/products/?search=Laptop')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p['name'] for p in response.data['results']]
        self.assertIn('Laptop Principal', names)
        self.assertNotIn('Mouse Gamer', names)

    def test_filtrar_por_categoria(self):
        other_cat = Category.objects.create(name='Otra Categoría')
        p_other = Product.objects.create(
            name='Teclado en otra cat', category=other_cat,
            price=Decimal('30.00'), current_stock=5, minimum_stock=1,
            status='Disponible', supplier=self.supplier,
        )
        response = self.client.get(f'/api/products/?category={other_cat.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [p['id'] for p in response.data['results']]
        self.assertIn(p_other.id, ids)
        self.assertNotIn(self.product.id, ids)

    def test_filtrar_por_proveedor(self):
        other_supplier = Supplier.objects.create(
            name='Otro Proveedor', email='otro@sup.com',
            document_type='ruc', tax_id='0990175678001',
            phone='0996543210',
        )
        p_other = Product.objects.create(
            name='Producto otro proveedor', category=self.category,
            price=Decimal('20.00'), current_stock=3, minimum_stock=1,
            status='Disponible', supplier=other_supplier,
        )
        response = self.client.get(f'/api/products/?supplier={other_supplier.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [p['id'] for p in response.data['results']]
        self.assertIn(p_other.id, ids)
        self.assertNotIn(self.product.id, ids)

    def test_filtrar_is_active_true_excluye_inactivos(self):
        p_inactive = self._make_product(name='Inactivo', status_val='Inactivo')  # ProductStatus.INACTIVE
        response = self.client.get('/api/products/?is_active=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [p['id'] for p in response.data['results']]
        self.assertIn(self.product.id, ids)
        self.assertNotIn(p_inactive.id, ids)

    def test_filtrar_is_active_false_solo_inactivos(self):
        p_inactive = self._make_product(name='Solo Inactivo', status_val='Inactivo')  # ProductStatus.INACTIVE
        response = self.client.get('/api/products/?is_active=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [p['id'] for p in response.data['results']]
        self.assertIn(p_inactive.id, ids)
        self.assertNotIn(self.product.id, ids)

    def test_producto_eliminado_no_aparece_en_lista(self):
        p_deleted = self._make_product(name='Eliminado Lista')
        p_deleted.deleted_at = timezone.now()
        p_deleted.save(update_fields=['deleted_at'])
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [p['id'] for p in response.data['results']]
        self.assertNotIn(p_deleted.id, ids)

    def test_producto_eliminado_detalle_retorna_404(self):
        p_deleted = self._make_product(name='Eliminado Detalle')
        p_deleted.deleted_at = timezone.now()
        p_deleted.save(update_fields=['deleted_at'])
        response = self.client.get(f'/api/products/{p_deleted.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_producto_actualiza_nombre(self):
        response = self.client.patch(
            f'/api/products/{self.product.id}/',
            {'name': 'Laptop Actualizada'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Laptop Actualizada')


# =============================================================================
# Stock check endpoint
# =============================================================================

class TestStockCheckAPI(ExtViewBase):
    """POST /api/products/check_stock/"""

    def setUp(self):
        super().setUp()
        self.product = self._make_product(stock=10)

    def test_stock_disponible_retorna_all_available_true(self):
        response = self.client.post('/api/products/check_stock/', {
            'items': [{'product': self.product.id, 'quantity': 5}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['all_available'])
        self.assertEqual(response.data['unavailable'], [])

    def test_stock_insuficiente_retorna_unavailable(self):
        response = self.client.post('/api/products/check_stock/', {
            'items': [{'product': self.product.id, 'quantity': 100}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['all_available'])
        self.assertEqual(len(response.data['unavailable']), 1)
        self.assertEqual(response.data['unavailable'][0]['product_id'], self.product.id)

    def test_stock_check_sin_autenticacion_401(self):
        client = APIClient()
        response = client.post('/api/products/check_stock/', {
            'items': [{'product': self.product.id, 'quantity': 1}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# =============================================================================
# Ventas — listado, filtros, detalle y shape de respuesta
# =============================================================================

class SalesViewBase(TestCase):
    """Base para tests de ventas — crea datos frescos por clase."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='sales_view@test.com',
            password='TestPass1!',
            name='Sales User',
            role='SuperAdmin',
            phone='0991100001',
        )
        cls.category = Category.objects.create(name='Sales Category')
        cls.supplier = Supplier.objects.create(
            name='Sales Supplier', email='sales_sup@test.com',
            document_type='ruc', tax_id='1710034065001',
            phone='0997100001',
        )
        cls.customer = Customer.objects.create(
            name='Ana García',
            email='ana@sales.com',
            document_type='cedula',
            document='1710034065',
            phone='0993100001',
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(
            name='Producto Ventas', category=self.category,
            price=Decimal('50.00'), current_stock=50, minimum_stock=2,
            status='Activo', supplier=self.supplier,
        )

    def _post_sale(self, quantity=2):
        return self.client.post('/api/sales/', {
            'customer': self.customer.id,
            'items': [{'product': self.product.id, 'quantity': quantity, 'price': '50.00'}],
        }, format='json')


class TestSalesListAPI(SalesViewBase):
    """GET /api/sales/ — listado, paginación y filtros."""

    def test_listar_ventas_retorna_200(self):
        response = self.client.get('/api/sales/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_respuesta_tiene_estructura_paginada(self):
        response = self.client.get('/api/sales/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)

    def test_filtrar_por_busqueda_nombre_cliente(self):
        self._post_sale(2)
        response = self.client.get('/api/sales/?search=Ana')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_filtrar_por_busqueda_sin_coincidencia(self):
        self._post_sale(2)
        response = self.client.get('/api/sales/?search=zzz_no_existe_zzz')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_filtrar_por_fecha_hoy(self):
        self._post_sale(2)
        today = timezone.localdate().isoformat()  # local timezone, matches view's __date filter
        response = self.client.get(f'/api/sales/?start_date={today}&end_date={today}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_listar_ventas_sin_autenticacion_401(self):
        response = APIClient().get('/api/sales/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestSalesDetailAPI(SalesViewBase):
    """GET /api/sales/<id>/ — shape del detalle."""

    def test_detalle_venta_tiene_campos_esperados(self):
        create_resp = self._post_sale(2)
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        sale_id = create_resp.data['sale']['id']

        response = self.client.get(f'/api/sales/{sale_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in ('id', 'customer', 'date', 'total', 'movements'):
            self.assertIn(field, response.data, f"Campo '{field}' ausente en detalle de venta")

    def test_detalle_venta_inexistente_404(self):
        response = self.client.get('/api/sales/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_respuesta_create_tiene_mensaje_y_sale(self):
        response = self._post_sale(1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('sale', response.data)
        self.assertIn('id', response.data['sale'])


class TestSalesIdempotencyAPI(SalesViewBase):
    """Idempotency-Key deduplica ventas."""

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    def test_mismo_idempotency_key_no_duplica_venta(self):
        """
        Enviar el mismo Idempotency-Key dos veces debe retornar 201 ambas veces
        pero crear un solo objeto Sale en base de datos.
        """
        idem_key = 'test-idem-venta-001'
        payload = {
            'customer': self.customer.id,
            'items': [{'product': self.product.id, 'quantity': 1, 'price': '50.00'}],
        }
        resp1 = self.client.post(
            '/api/sales/', payload, format='json',
            HTTP_IDEMPOTENCY_KEY=idem_key,
        )
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)

        resp2 = self.client.post(
            '/api/sales/', payload, format='json',
            HTTP_IDEMPOTENCY_KEY=idem_key,
        )
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Sale.objects.count(), 1, "Idempotency-Key debe prevenir duplicado en DB")

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    def test_distinto_idempotency_key_crea_dos_ventas(self):
        """Claves distintas sí crean dos ventas independientes."""
        payload = {
            'customer': self.customer.id,
            'items': [{'product': self.product.id, 'quantity': 1, 'price': '50.00'}],
        }
        self.client.post('/api/sales/', payload, format='json', HTTP_IDEMPOTENCY_KEY='key-A')
        self.client.post('/api/sales/', payload, format='json', HTTP_IDEMPOTENCY_KEY='key-B')
        self.assertEqual(Sale.objects.count(), 2)

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    def test_lock_activo_retorna_409(self):
        """
        Si el lock de la clave está presente (petición anterior en vuelo)
        pero aún no hay respuesta cacheada, debe retornar 409.
        Simula la race condition: dos requests simultáneos con el mismo
        Idempotency-Key donde el primero todavía está procesando.
        """
        from django.core.cache import cache as django_cache
        idem_key = 'test-idem-lock-race'
        lock_key = f'idem:sale:{idem_key}:lock'
        # Simular que otro worker ya adquirió el lock (petición en vuelo)
        django_cache.add(lock_key, True, timeout=30)

        payload = {
            'customer': self.customer.id,
            'items': [{'product': self.product.id, 'quantity': 1}],
        }
        response = self.client.post(
            '/api/sales/', payload, format='json',
            HTTP_IDEMPOTENCY_KEY=idem_key,
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn('detail', response.data)
        self.assertEqual(Sale.objects.count(), 0, "Lock activo no debe crear venta")

        # Limpieza
        django_cache.delete(lock_key)


# =============================================================================
# Compras — listado, filtros y permisos
# =============================================================================

class TestPurchasesViewAPI(TestCase):
    """GET/POST /api/purchases/ — permisos y filtros."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            email='pur_admin@test.com', password='TestPass1!',
            name='Pur Admin', role='Administrator', phone='0991200001',
        )
        cls.regular_user = User.objects.create_user(
            email='pur_user@test.com', password='TestPass1!',
            name='Pur User', role='User', phone='0991200002',
        )
        cls.category = Category.objects.create(name='Pur Category')
        cls.supplier = Supplier.objects.create(
            name='Pur Supplier', email='pur_sup@test.com',
            document_type='ruc', tax_id='1710034065001',
            phone='0997200001',
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        self.product = Product.objects.create(
            name='Producto Pur', category=self.category,
            price=Decimal('80.00'), current_stock=5, minimum_stock=2,
            status='Activo', supplier=self.supplier,
        )

    def _post_purchase(self, quantity=3):
        return self.client.post('/api/purchases/', {
            'supplier': self.supplier.id,
            'items': [{'product': self.product.id, 'quantity': quantity, 'price': '80.00'}],
        }, format='json')

    def test_listar_compras_retorna_200(self):
        response = self.client.get('/api/purchases/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_filtrar_por_busqueda_nombre_proveedor(self):
        self._post_purchase(3)
        response = self.client.get('/api/purchases/?search=Pur Supplier')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_filtrar_por_fecha_hoy(self):
        self._post_purchase(3)
        today = timezone.localdate().isoformat()  # local timezone, matches view's __date filter
        response = self.client.get(f'/api/purchases/?start_date={today}&end_date={today}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_detalle_compra_tiene_campos_esperados(self):
        create_resp = self._post_purchase(3)
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        purchase_id = create_resp.data['purchase']['id']
        response = self.client.get(f'/api/purchases/{purchase_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in ('id', 'supplier', 'date', 'total', 'movements'):
            self.assertIn(field, response.data, f"Campo '{field}' ausente en detalle de compra")

    def test_user_puede_listar_compras(self):
        """User role puede hacer GET (IsAdminForWrite solo bloquea POST/PATCH/DELETE)."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/purchases/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_no_puede_crear_compra_403(self):
        """User role recibe 403 al intentar crear una compra."""
        self.client.force_authenticate(user=self.regular_user)
        response = self._post_purchase(3)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_compra_sin_autenticacion_401(self):
        response = APIClient().get('/api/purchases/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# =============================================================================
# Movimientos — filtros por tipo, ajustes y correcciones
# =============================================================================

class TestMovementsViewAPI(TestCase):
    """GET /api/movements/ y POST endpoints de ajuste y corrección."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            email='mov_admin@test.com', password='TestPass1!',
            name='Mov Admin', role='Administrator', phone='0991300001',
        )
        cls.regular_user = User.objects.create_user(
            email='mov_user@test.com', password='TestPass1!',
            name='Mov User', role='User', phone='0991300002',
        )
        cls.category = Category.objects.create(name='Mov Category')
        cls.supplier = Supplier.objects.create(
            name='Mov Supplier', email='mov_sup@test.com',
            document_type='ruc', tax_id='1710034065001',
            phone='0997300001',
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        self.product = Product.objects.create(
            name='Producto Mov', category=self.category,
            price=Decimal('30.00'), current_stock=50, minimum_stock=5,
            status='Activo', supplier=self.supplier,
        )

    def _post_adjustment(self, quantity=5, reason='Ajuste test'):
        return self.client.post('/api/movements/adjustments/', {
            'product': self.product.id,
            'quantity': quantity,
            'reason': reason,
        }, format='json')

    def _post_purchase(self, quantity=10):
        return self.client.post('/api/purchases/', {
            'supplier': self.supplier.id,
            'items': [{'product': self.product.id, 'quantity': quantity, 'price': '30.00'}],
        }, format='json')

    # ---- listado ----

    def test_listar_movimientos_retorna_200(self):
        response = self.client.get('/api/movements/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_listar_movimientos_sin_autenticacion_401(self):
        response = APIClient().get('/api/movements/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- filtros por tipo ----

    def test_filtrar_movimientos_tipo_adjustment(self):
        """?type=adjustment devuelve solo ajustes."""
        self._post_adjustment(3)
        response = self.client.get('/api/movements/?type=adjustment')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        types = [m['movement_type'] for m in response.data['results']]
        self.assertTrue(
            all(t == 'adjustment' for t in types),
            f"Tipos inesperados en filtro adjustment: {set(types)}",
        )

    def test_filtrar_movimientos_multiples_tipos(self):
        """?type=adjustment,correction filtra por ambos tipos."""
        self._post_adjustment(3)
        response = self.client.get('/api/movements/?type=adjustment,correction')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        types = set(m['movement_type'] for m in response.data['results'])
        self.assertTrue(
            types.issubset({'adjustment', 'correction'}),
            f"Tipos inesperados fuera del filtro: {types}",
        )

    def test_tipo_inexistente_devuelve_lista_vacia(self):
        self._post_adjustment(3)
        response = self.client.get('/api/movements/?type=nonexistent')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    # ---- ajustes ----

    def test_ajuste_admin_retorna_201(self):
        response = self._post_adjustment(5)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('movement', response.data)
        self.assertEqual(response.data['movement']['movement_type'], 'adjustment')

    def test_ajuste_user_recibe_403(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self._post_adjustment(5)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ajuste_cantidad_cero_retorna_400(self):
        response = self._post_adjustment(0)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ajuste_sin_razon_retorna_400(self):
        response = self.client.post('/api/movements/adjustments/', {
            'product': self.product.id,
            'quantity': 5,
            'reason': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ajuste_actualiza_stock(self):
        stock_antes = self.product.current_stock
        self._post_adjustment(7)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, stock_antes + 7)

    # ---- correcciones ----

    def test_correccion_admin_retorna_201(self):
        """Admin puede corregir un movimiento existente."""
        # Crear compra para obtener un movimiento de tipo 'input'
        resp = self._post_purchase(10)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        movement = Movement.objects.filter(
            product=self.product, movement_type='input',
        ).first()
        self.assertIsNotNone(movement, "Debe existir un movement input tras la compra")

        response = self.client.post(f'/api/movements/{movement.id}/correct/', {
            'new_quantity': 8,
            'reason': 'Corrección por error de conteo',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('movement', response.data)
        self.assertEqual(response.data['movement']['movement_type'], 'correction')

    def test_correccion_user_recibe_403(self):
        """User sin rol admin no puede corregir movimientos."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post('/api/movements/99999/correct/', {
            'new_quantity': 5,
            'reason': 'No autorizado',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_correccion_movimiento_inexistente_retorna_error(self):
        """Corregir un ID que no existe → 400 (ValidationError del service) o 404."""
        response = self.client.post('/api/movements/99999/correct/', {
            'new_quantity': 5,
            'reason': 'Movimiento inexistente',
        }, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ])

    def test_correccion_misma_cantidad_retorna_400(self):
        """Corregir con la misma cantidad que el original → 400."""
        self._post_purchase(10)
        movement = Movement.objects.filter(
            product=self.product, movement_type='input',
        ).first()
        self.assertIsNotNone(movement)

        response = self.client.post(f'/api/movements/{movement.id}/correct/', {
            'new_quantity': movement.quantity,  # misma cantidad → inválido
            'reason': 'Corrección con misma cantidad',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# Clientes — CRUD y búsqueda
# =============================================================================

class TestCustomersCRUDAPI(ExtViewBase):
    """POST/PATCH /api/customers/ — crear, actualizar, buscar, soft-delete oculto."""

    def test_crear_cliente_valido_retorna_201(self):
        """Cédula válida → 201 con datos del cliente."""
        response = self.client.post('/api/customers/', {
            'name': 'Nuevo Cliente',
            'email': 'nuevo@cliente.com',
            'document_type': 'cedula',
            'document': '1750000000',  # Cédula con dígito verificador correcto
            'phone': '0991234567',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Nuevo Cliente')

    def test_crear_cliente_cedula_invalida_retorna_400(self):
        """Cédula con dígito verificador incorrecto → 400."""
        response = self.client.post('/api/customers/', {
            'name': 'Cliente Inválido',
            'email': 'invalido@cliente.com',
            'document_type': 'cedula',
            'document': '1234567890',  # Verificador esperado: 7, tiene 0 → inválido
            'phone': '0991234567',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_cliente_actualiza_nombre(self):
        response = self.client.patch(
            f'/api/customers/{self.customer.id}/',
            {'name': 'Cliente Actualizado'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Cliente Actualizado')

    def test_buscar_clientes_por_nombre(self):
        response = self.client.get('/api/customers/?search=Ext Customer')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [c['name'] for c in response.data['results']]
        self.assertIn('Ext Customer', names)

    def test_buscar_clientes_sin_coincidencia_devuelve_vacio(self):
        response = self.client.get('/api/customers/?search=zzz_no_existe_zzz')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_cliente_eliminado_no_aparece_en_lista(self):
        """Soft-delete oculta el cliente de la lista."""
        c_deleted = Customer.objects.create(
            name='Cliente A Eliminar',
            email='eliminar@cliente.com',
            document_type='cedula',
            document='1750000000',
            phone='0991234568',
        )
        c_deleted.deleted_at = timezone.now()
        c_deleted.save(update_fields=['deleted_at'])

        response = self.client.get('/api/customers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [c['id'] for c in response.data['results']]
        self.assertNotIn(c_deleted.id, ids)

    def test_cliente_eliminado_detalle_retorna_404(self):
        c_deleted = Customer.objects.create(
            name='Cliente Detalle Eliminado',
            email='detalle_elim@cliente.com',
            document_type='cedula',
            document='1750000000',
            phone='0991234569',
        )
        c_deleted.deleted_at = timezone.now()
        c_deleted.save(update_fields=['deleted_at'])

        response = self.client.get(f'/api/customers/{c_deleted.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# Proveedores — CRUD
# =============================================================================

class TestSuppliersCRUDAPI(ExtViewBase):
    """POST/PATCH /api/suppliers/ — crear y actualizar."""

    def test_crear_proveedor_valido_retorna_201(self):
        response = self.client.post('/api/suppliers/', {
            'name': 'Nuevo Proveedor',
            'email': 'nuevo@proveedor.com',
            'document_type': 'ruc',
            'tax_id': '1750000000001',  # RUC = cédula válida + '001'
            'phone': '0997654321',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Nuevo Proveedor')

    def test_patch_proveedor_actualiza_nombre(self):
        response = self.client.patch(
            f'/api/suppliers/{self.supplier.id}/',
            {'name': 'Proveedor Actualizado'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Proveedor Actualizado')

    def test_buscar_proveedores_por_nombre(self):
        response = self.client.get('/api/suppliers/?search=Ext Supplier')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [s['name'] for s in response.data['results']]
        self.assertIn('Ext Supplier', names)

    def test_proveedor_eliminado_no_aparece_en_lista(self):
        s_deleted = Supplier.objects.create(
            name='Proveedor Eliminado',
            email='elim@proveedor.com',
            document_type='ruc',
            tax_id='1750000000001',
            phone='0997654322',
        )
        s_deleted.deleted_at = timezone.now()
        s_deleted.save(update_fields=['deleted_at'])

        response = self.client.get('/api/suppliers/')
        ids = [s['id'] for s in response.data['results']]
        self.assertNotIn(s_deleted.id, ids)
