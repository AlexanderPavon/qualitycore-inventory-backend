# Plan de migración: monolito → múltiples apps Django

## Situación actual
Un solo app `inventory_app` contiene 13 modelos, 17 vistas y 13 serializers (~2 800 LOC total).
Los archivos son pequeños (~65 líneas c/u) y ya están bien organizados por directorio.

**Estimación de esfuerzo por fase: 1–2 semanas con cobertura de tests completa.**

---

## Cuándo hacer esta migración
- El proyecto tiene >30 modelos y el equipo crece a 3+ desarrolladores trabajando en paralelo.
- Se quiere desplegar partes del backend de forma independiente (microservicios).
- Los tiempos de CI superan 5 minutos y la separación en apps ayuda a paralelizar tests.

**Para el tamaño actual del proyecto, la división no es urgente ni necesaria.**

---

## Orden de migración (de menor a mayor riesgo)

### Fase 1 — `products` app (riesgo: bajo)
**Modelos:** `Product`, `Category`
**Dependencias entrantes:** Sale, Purchase, Movement, Alert referencian Product.
**Plan:**
1. Crear `products/` app con `python manage.py startapp products`
2. Mover `models/product.py` y `models/category.py` a `products/models/`
3. Crear nueva migration en `products/` con `initial`
4. En `inventory_app/`, crear migration con `RenameModel` + `SeparateDatabaseAndState` para preservar el nombre de tabla y evitar recrearla
5. Actualizar todos los `from inventory_app.models.product import ...` en vistas, serializers y servicios
6. Verificar: `python manage.py check && python manage.py test`

---

### Fase 2 — `analytics` app (riesgo: bajo)
**Modelos:** `Report`, `Alert`
**Dependencias entrantes:** ninguna crítica (solo lectura desde otras partes)
**Plan:** mismo proceso que Fase 1.

---

### Fase 3 — `sales` app (riesgo: medio)
**Modelos:** `Sale`, `Quotation`, `QuotedProduct`, `Customer`
**Dependencias críticas:**
- `Sale` → `Movement` (crea movimientos de salida en `movement_service.py`)
- `Quotation` → `Product`
**Plan:**
1. Mover modelos y código asociado.
2. El `movement_service.py` importará de `inventory_app.models.movement` y de `products.models` — asegurarse de que no hay circular imports.
3. Tests de integración para el flujo completo de venta.

---

### Fase 4 — `purchasing` app (riesgo: medio)
**Modelos:** `Purchase`, `Supplier`
**Dependencias críticas:**
- `Purchase` → `Movement` (mismo que sales)
- `Product` → `Supplier` (FK)
**Plan:** igual que Fase 3; prestar atención al FK `Product.supplier`.

---

### NO separar (todavía)
| Modelo | Razón |
|--------|-------|
| `Movement` | Central en transacciones; todos los services lo importan |
| `User` | Custom auth model; Django lo requiere en `AUTH_USER_MODEL` |
| `AuditLog` | Middleware y signals lo usan globalmente |

---

## Reglas para cada migración

```
1. Crear nueva app
2. Mover archivos de modelo (sin cambiar el Meta.db_table si ya existe en producción)
3. Nueva migration: SeparateDatabaseAndState para evitar DROP/CREATE table
4. Actualizar todos los imports (grep + sed o IDE refactor)
5. Actualizar INSTALLED_APPS en settings/base.py
6. python manage.py check → 0 errores
7. python manage.py test → todos los tests verdes
8. Desplegar con zero-downtime (la tabla no cambia, solo el import path)
```

## Referencia: SeparateDatabaseAndState
```python
# migrations/0001_initial.py (en la nueva app)
from django.db import migrations

class Migration(migrations.Migration):
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],      # no tocar la DB
            state_operations=[
                migrations.CreateModel(name='Product', fields=[...])
            ],
        ),
    ]
```
