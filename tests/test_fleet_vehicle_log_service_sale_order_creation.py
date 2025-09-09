# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, Form
from odoo.exceptions import UserError
from datetime import date, timedelta
from odoo.fields import Command 

class TestFleetServiceSaleOrderCreation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """
        Método de preparación. Se ejecuta UNA SOLA VEZ para toda la clase.
        Es más eficiente para crear datos que no cambian entre pruebas.
        """
        super().setUpClass()

        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        Partner = cls.env['res.partner']
        cls.partner_customer = Partner.create({'name': 'Cliente de Prueba'})
        cls.partner_insurer = Partner.create({'name': 'Aseguradora de Prueba'})

        cls.product_labor = cls.env.ref('fleet_product.product_template_labor').product_variant_id
        cls.product_labor.write({'taxes_id': [Command.clear()]})
        cls.product_adjustment = cls.env.ref('fleet_product.product_template_insurance_adjustment').product_variant_id
        cls.product_coverage = cls.env.ref('fleet_product.product_template_insurance_coverage').product_variant_id

        cls.product_spare_1 = cls.env['product.product'].create({'name': 'Filtro de Aceite', 'list_price': 50.0, 'standard_price': 25.0})
        cls.product_spare_2 = cls.env['product.product'].create({'name': 'Pastillas de Freno', 'list_price': 120.0, 'standard_price': 70.0})


        VehicleModel = cls.env['fleet.vehicle.model']
        brand = cls.env['fleet.vehicle.model.brand'].create({'name': 'Test Brand'})
        test_model = VehicleModel.create({'name': 'Test Car', 'brand_id': brand.id})
        cls.test_vehicle = cls.env['fleet.vehicle'].create({'model_id': test_model.id})
        
 
        cls.today = date.today()

    def test_happy_path_labor_only_no_insurance(self):
        """
        Prueba el escenario más simple:
        - Un servicio con solo costo de mano de obra.
        - No hay repuestos.
        - No hay seguro involucrado.
        - Se debe crear UN solo presupuesto para el cliente.
        """
        # --- 1. ARRANGE (Preparar el registro de servicio específico) ---
        # Partimos de un registro mínimo y válido
        service = self.env['fleet.vehicle.log.services'].create({
            'vehicle_id': self.test_vehicle.id,
            'purchaser_id': self.partner_customer.id,
            'date': self.today,
            'description': 'Mantenimiento Básico',
            'labor_cost': 150.0,
        })
        self.assertEqual(service.state, 'new', "El servicio debe empezar en estado borrador.")
        
        # --- 2. ACT (Ejecutar la acción que queremos probar) ---
        service.action_create_sale_orders()
        
        # --- 3. ASSERT (Verificar que todo ha salido como esperábamos) ---
        
        # 3.1 - El registro de servicio se actualizó correctamente
        self.assertTrue(service.sale_order_id, "El campo 'Pedido de Venta del Cliente' debería haberse rellenado.")
        self.assertFalse(service.insurer_sale_order_id, "No debería haberse creado un Pedido de Venta para la aseguradora.")
        
        # 3.2 - Se creó el Pedido de Venta del Cliente con los datos correctos
        client_so = service.sale_order_id
        self.assertEqual(len(client_so.order_line), 1, "El SO del cliente debería tener UNA sola línea.")
        
        labor_line = client_so.order_line[0]
        self.assertEqual(labor_line.product_id, self.product_labor, "La línea no usa el producto de mano de obra correcto.")
        self.assertEqual(labor_line.price_unit, 150.0, "El precio de la mano de obra en el presupuesto es incorrecto.")
        self.assertEqual(client_so.partner_id, self.partner_customer, "El cliente del presupuesto es incorrecto.")
        self.assertEqual(client_so.amount_total, 150.0, "El total del presupuesto es incorrecto.")