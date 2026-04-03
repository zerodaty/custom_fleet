# 🚗 Sistema de Gestión de Taller Mecánico para Odoo 18 (`fleet_custom`)

Este módulo transforma la aplicación estándar de Flota de Odoo en un completo sistema de gestión de negocio (ERP) diseñado específicamente para talleres mecánicos. Se extiende la funcionalidad de `fleet`, `sale`, `account` y `analytic` para crear un flujo de trabajo unificado y automatizado, desde la recepción del vehículo hasta la facturación final, pasando por la gestión de seguros y planes de mantenimiento y gestión de servicios.

## ✨ Resumen del Proyecto ✨

El módulo `fleet` de Odoo está diseñado para gestionar una flota de vehículos interna de una empresa. Este proyecto lo rediseña por completo para adaptarlo a un modelo de negocio B2C (Business-to-Consumer), donde el taller presta servicios a vehículos de **clientes externos**.

La "magia" de este módulo reside en la profunda integración y automatización de procesos:

- **Automatiza el estado operativo de los vehículos:** Mueve visualmente los vehículos en el tablero Kanban del taller según el progreso real de sus servicios, sin intervención manual.
- **Inteligencia en la entrada de datos:** Propone automáticamente el último registro del odómetro y valida que no se introduzcan valores inferiores, garantizando la integridad del historial.
- **Generación de Presupuestos con un Clic:** Un solo botón analiza el servicio (costos de mano de obra, repuestos, cobertura de seguro) y genera los documentos de venta correspondientes.
- **Separación de Vistas por Roles:** Ofrece dos vistas Kanban distintas: una estratégica para el **Gerente de Flota** y una operativa para el **Jefe de Taller**.

---

## 🚀 Características Principales

### 1. Gestión de Taller con Kanban Operativo

- **Tablero de Taller Dedicado:** Un nuevo menú `Flota -> Taller` que abre un tablero Kanban con columnas personalizadas que reflejan el flujo de trabajo real del taller (`Patio / Disponible`, `En Diagnóstico`, `En Taller`, `Listo para Entrega`).
- **Modelo de Etapas Propio (`fleet.workshop.stage`):** Arquitectura limpia y modular con un sistema de etapas propio que no entra en conflicto con los estados base de Odoo.
- **Sincronización Automática de Estados:** Al iniciar o finalizar un servicio, el vehículo asociado se mueve automáticamente a la columna correspondiente en el Kanban del taller.

### 2. Sistema Avanzado de Servicios y Costos

- **Costos Desglosados:** El formulario de servicios permite diferenciar entre **costos de mano de obra** y **costos de repuestos** asi como la **poliza del seguro**, que se calculan automáticamente.
- **Líneas de Productos:** Permite añadir múltiples repuestos a un servicio desde el inventario (`product.product`), detallando cantidad y precio.
- **Odómetro Inteligente:** Propone el último valor registrado del odómetro al crear un servicio y valida en el backend que no se puedan guardar valores inferiores, previniendo errores humanos.

### 3. Integración Comercial y Financiera

- **Botón "Crear Presupuesto":** Automatiza la creación de Pedidos de Venta (`sale.order`) a partir de la información del servicio.
- **Gestión de Seguros:** Permite registrar pólizas de seguro por vehículo. Al crear un presupuesto, se puede especificar un monto de cobertura, que se aplica como un descuento automático en la línea del pedido de venta.
- **Facturación Dual (Cliente y Aseguradora):** La lógica de negocio está diseñada para poder generar un presupuesto/factura para el cliente (por el costo neto) y otro para la compañía aseguradora (por el monto cubierto).
- **Contratos para Planes de Mantenimiento:** Utiliza el potente modelo `account.analytic.account` para gestionar planes de mantenimiento. Se pueden asociar vehículos a contratos, sentando las bases para facturación recurrente y análisis de rentabilidad.

### 4. Mejoras en la Experiencia de Usuario (UX)

- **Tarjeta Kanban Enriquecida:** Las tarjetas en las vistas Kanban han sido rediseñadas para mostrar de un vistazo toda la información relevante: Cliente/Propietario, Conductor, Prioridad (con estrellas), Estado Operativo (con insignias) y contadores de contratos y servicios activos.
- **Vistas Adaptadas por Roles:**
  - **Vista de Gerente (`Flota -> Vehículos`):** Mantiene las columnas administrativas de Odoo pero con la tarjeta enriquecida para una visión estratégica.
  - **Vista de Taller (`Flota -> Taller`):** Ofrece el Kanban operativo centrado en el flujo de trabajo.

---

## 📸 ¡El Módulo en Acción!

<!-- ¡ESTA ES LA SECCIÓN MÁS IMPORTANTE! Reemplaza los textos con capturas de pantalla reales o, mejor aún, GIFs cortos que muestren la funcionalidad. -->

**1. Tablero de Taller con Movimiento Automático de Tarjetas**

- _Sugerencia: Un GIF que muestre cómo, al iniciar un servicio, la tarjeta del vehículo salta de "Patio / Disponible" a "En Taller"._
<!-- (Aquí tu screenshot o GIF) -->

**2. Formulario de Servicio Detallado con Cálculo de Costos**

- _Sugerencia: Una captura de pantalla del formulario de un servicio, mostrando las líneas de productos y los campos de seguro._
<!-- (Aquí tu screenshot o GIF) -->

**3. La Magia del Botón "Crear Presupuesto"**

- _Sugerencia: Un GIF corto que muestre el clic en el botón y el Pedido de Venta que se genera, con la línea de descuento del seguro aplicada._
<!-- (Aquí tu screenshot o GIF) -->

**4. El Odómetro Inteligente en Funcionamiento**

- _Sugerencia: Un GIF que muestre cómo se autocompleta el odómetro al seleccionar un vehículo y cómo salta el error si se introduce un valor inferior._
<!-- (Aquí tu screenshot o GIF) -->

---

## 🛠️ Detalles Técnicos

### Estructura del Módulo

fleet_product/
├── init.py
├── manifest.py
├── controllers/
├── data/
│ ├── fleet_product_categories.xml
│ ├── fleet_product_productos.xml
│ ├── fleet_product_service.xml
│ └── fleet_workshop_stage_data.xml <-- ¡NUEVO!
├── models/
│ ├── init.py
│ ├── fleet_vehicle.py
│ ├── fleet_vehicle_insurance.py
│ ├── fleet_vehicle_log_service_extend.py
│ ├── fleet_service_product_line.py
│ └── fleet_workshop_stage.py <-- ¡NUEVO!
├── report/
│ └── fleet_service_report_templates.xml
├── security/
│ └── ir.model.access.csv
└── views/
├── fleet_vehicle_insurance_views.xml
├── fleet_vehicle_log_services_views.xml
├── fleet_vehicle_view.xml
└── fleet_workshop_views.xml <-- ¡NUEVO!
code
Code

### Principales Modelos Involucrados

- **Heredados y Extendidos:**
  - `fleet.vehicle`
  - `fleet.vehicle.log.services`
- **Creados desde Cero:**
  - `fleet.workshop.stage` (para las columnas del Kanban de Taller)
  - `fleet.vehicle.insurance` (para la gestión de pólizas)
  - `fleet.service.product.line` (para las líneas de repuestos en los servicios)

---

## 🔧 Requisitos

- Odoo 18.0
- Módulos de Odoo requeridos (ver `depends` en `__manifest__.py`):
  - `fleet`
  - `account`
  - `sale`
  - `analytic`
  - `contacts`

## 🚀 Instalación y Configuración

1.  Clona este repositorio en tu carpeta de `addons` de Odoo.
2.  Reinicia el servicio de Odoo.
3.  Activa el modo desarrollador y ve a `Aplicaciones`.
4.  Haz clic en "Actualizar lista de aplicaciones".
5.  Busca el módulo **`fleet_product`** y haz clic en "Instalar".

### Configuración Recomendada Post-Instalación

Para aprovechar al máximo las funcionalidades de rentabilidad, asegúrate de tener activada la contabilidad analítica:

1.  Ve a `Contabilidad -> Configuración -> Ajustes`.
2.  Marca la casilla **"Contabilidad Analítica"** y guarda.

---

## 📈 Roadmap (Futuras Mejoras)

Este proyecto tiene un gran potencial para seguir creciendo. Las próximas funcionalidades planeadas son:

- [ ] **Integración Completa con Contratos:** Desarrollar la lógica en `action_create_sale_orders` para que verifique si los productos/servicios están cubiertos por un Plan de Mantenimiento y aplique precios de $0 automáticamente.
- [ ] **Lógica de Alquiler de Vehículos:** Extender el uso de `account.analytic.account` para gestionar contratos de alquiler, con facturación recurrente y seguimiento de los costos de mantenimiento de la flota de alquiler.
- [ ] **Notificaciones Automáticas:** Integrar con WhatsApp o correo para notificar a los clientes cuando su servicio inicia, finaliza o cuando su vehículo está listo para retirar.
- [ ] **Reportes Avanzados:** Crear reportes de rentabilidad por Plan de Mantenimiento.
