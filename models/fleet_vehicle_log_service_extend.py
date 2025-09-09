# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from odoo.exceptions import UserError

class FleetVehicleLogServices(models.Model):
    """
    Heredamos el modelo de servicios de flota para agregar campos
    y lógica de negocio relacionados con los costos de productos.
    """
    
    _inherit = 'fleet.vehicle.log.services'

    service_classification = fields.Selection(
        [
            ('preventive', 'Preventivo'),
            ('corrective', 'Correctivo')
        ],
        string='Clasificación de Servicio',
        default='preventive',
        required=True
    )

    labor_cost = fields.Monetary(
        'Costo de Mano de Obra',
        tracking=True 
    )

    product_line_ids = fields.One2many(
        'fleet.service.product.line', 
        'service_id',               
        string='Productos Utilizados'
    )

    parts_cost = fields.Monetary(
        string='Costo de Productos',
        compute='_compute_parts_cost',
        store=True, 
        tracking=True
    )
    
    amount = fields.Monetary(
        'Costo Total',  
        compute='_compute_total_cost',
        store=True, 
        readonly=False, 
        inverse='_inverse_amount',
    )
    
    insurance_policy_id = fields.Many2one(
        'fleet.vehicle.insurance',
        string='Póliza Utilizada',
        tracking=True
    )

    insurance_coverage_amount = fields.Monetary(
        string='Monto Cubierto por Seguro',
        tracking=True
    )
    
    net_cost = fields.Monetary(
        string='Costo Neto para la Empresa',
        compute='_compute_net_cost',
        store=True,
        tracking=True
    )
    
    vehicle_id_has_active_policies = fields.Boolean(
        related='vehicle_id.has_active_policies',
        string="El Vehículo Tiene Pólizas"
    )
    
    purchaser_id = fields.Many2one(
        'res.partner',
        string="Driver", 
        domain=lambda self: self._get_drivers_with_vehicle_domain(),
    )
    
    @api.onchange('purchaser_id')
    def _onchange_purchaser_id_set_vehicle(self):
        """
        CUANDO el usuario selecciona un conductor (`purchaser_id`) en el formulario,
        este método se dispara para buscar y asignar automáticamente el vehículo asociado.
        """
        if self.purchaser_id:
            vehicle = self.env['fleet.vehicle'].search([
                ('driver_id', '=', self.purchaser_id.id)
            ], limit=1)

            if vehicle:
                self.vehicle_id = vehicle

    def _get_drivers_with_vehicle_domain(self):
       """
       Dominio para el campo purchaser_id
       Devuelve un filtro que es solo pa los que tienen carro TOCA REVISAR ESTA VAINA Pq no estoy seguro
       """
       vehicles_with_driver = self.env['fleet.vehicle'].search([('driver_id', '!=', False)])
       driver_ids = vehicles_with_driver.mapped('driver_id').ids
       return [('id', 'in', driver_ids)]
    
    sale_order_id = fields.Many2one(
        'sale.order', 
        string='Pedido de Venta', 
        readonly=True,
        copy=False, 
        tracking=True
    )
    insurer_sale_order_id = fields.Many2one(
        'sale.order', 
        string='Presupuesto Aseguradora', 
        readonly=True, 
        copy=False,
        tracking=True
    )
    sale_order_count = fields.Integer(
        string="Cuenta de Presupuestos", 
        compute='_compute_sale_order_count'
    )  
    
    estimated_delivery_date = fields.Date(
        string='Fecha de Entrega Estimada',
        tracking=True,
        default=fields.Date.context_today
    )
    
    @api.depends('product_line_ids.price_subtotal')
    def _compute_parts_cost(self):
        """
        Suma los subtotales de todas las líneas de producto asociadas.
        """
        for service in self:
            service.parts_cost = sum(line.price_subtotal for line in service.product_line_ids)


    @api.depends('labor_cost', 'parts_cost')
    def _compute_total_cost(self):
        """
        Calcula el costo total sumando mano de obra y productos. 
        """
        for service in self:
            service.amount = service.labor_cost + service.parts_cost
    
            
    def _inverse_amount(self):
        """
        Método inverso para el campo 'amount'. Si alguien edita el 'Costo Total' manualmente, 
        la diferencia se asignará a 'Costo de Mano de Obra'.
        Esto mantiene la compatibilidad y un comportamiento intuitivo.
        """
        for service in self:
            service.labor_cost = service.amount - service.parts_cost
    
    @api.depends('amount', 'insurance_coverage_amount')
    def _compute_net_cost(self):
        """Calcula el costo real que asume la empresa."""
        for service in self:
            service.net_cost = service.amount - service.insurance_coverage_amount
    
    @api.onchange('vehicle_id', 'date')
    def _onchange_vehicle_set_policy(self):
        """
        Cuando se selecciona un vehículo, busca automáticamente la póliza propietaria
        más relevante (la que vence más tarde pero que ya está activa) y la propone.
        """
        if self.vehicle_id and self.date:
            domain = [
                ('vehicle_id', '=', self.vehicle_id.id),
                ('policy_type', '=', 'owner'),
                ('start_date', '<=', self.date),
                ('end_date', '>=', self.date),
            ]
            relevant_policy = self.env['fleet.vehicle.insurance'].search(domain, order='end_date desc', limit=1)
            self.insurance_policy_id = relevant_policy
        else:
            self.insurance_policy_id = False

    def action_create_sale_orders(self):
        """
        Este método se llama desde el botón 'Crear Presupuesto'.
        Crea un nuevo Pedido de Venta (sale.order) basado en los datos
        de este registro de servicio. REVISAR
        """
        self.ensure_one() 
        if self.sale_order_id or self.insurer_sale_order_id:
            raise UserError("Ya se han generado los documentos de venta para este servicio.")
        if not self.purchaser_id:
            raise UserError("Por favor, seleccione un 'Conductor / Cliente' antes de continuar.")
        
    
        if self.insurance_policy_id:
            if not (self.insurance_policy_id.start_date <= self.date <= self.insurance_policy_id.end_date):
                raise UserError("La fecha de este servicio está fuera del periodo de vigencia de la póliza de seguro seleccionada.")
            if self.insurance_coverage_amount > self.insurance_policy_id.cost:
                raise UserError(f"El monto de la cobertura del seguro ({self.insurance_coverage_amount}) no puede exceder el límite de la póliza ({self.insurance_policy_id.cost}).")
    
        client_order_lines = []
        
        if self.labor_cost > 0:
            labor_product = self.env.ref('fleet_product.product_template_labor').product_variant_id
            client_order_lines.append(Command.create({
                'product_id': labor_product.id,
                'name': 'Mano de Obra del Servicio: ' + (self.description or ''),
                'product_uom_qty': 1,
                'price_unit': self.labor_cost
            }))
            
        for line in self.product_line_ids:
            client_order_lines.append(Command.create({
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'product_uom_qty': line.quantity,
                'price_unit': line.product_id.list_price
            }))
            
        if self.insurance_coverage_amount > 0:
            adjustment_product = self.env.ref('fleet_product.product_template_insurance_adjustment').product_variant_id
            client_order_lines.append(Command.create({
                'product_id': adjustment_product.id,
                'name': f"Ajuste por Cobertura (Póliza: {self.insurance_policy_id.name})",
                'product_uom_qty': 1,
                'price_unit': -self.insurance_coverage_amount
            }))
            
        if not client_order_lines:
             raise UserError("No hay nada que facturar. Añada un costo de mano de obra o productos al servicio.")
    
        # Crear SO del Cliente
        client_so = self.env['sale.order'].create({
            'partner_id': self.purchaser_id.id,
            'order_line': client_order_lines,
            'origin': f"Servicio Flota: {self.description or ''}"
        })
        
        # Crear SO de la Aseguradora (si aplica)
        insurer_so = False
        if self.insurance_coverage_amount > 0:
            if not self.insurance_policy_id.insurer_id:
                raise UserError("La póliza debe tener una compañía aseguradora asociada para poder generar su presupuesto.")
            
            coverage_product = self.env.ref('fleet_product.product_template_insurance_coverage').product_variant_id
            insurer_so = self.env['sale.order'].create({
                'partner_id': self.insurance_policy_id.insurer_id.id,
                'order_line': [Command.create({
                    'product_id': coverage_product.id,
                    'name': f"Reclamo Cobertura - Servicio: {self.description or ''} ({self.vehicle_id.name})",
                    'product_uom_qty': 1,
                    'price_unit': self.insurance_coverage_amount,
                })],
                'origin': f"Servicio Flota: {self.description or ''}"
            })
    
        # Asignar los nuevos IDs al servicio EN UNA SOLA OPERACIÓN DE ESCRITURA
        vals_to_write = {'sale_order_id': client_so.id}
        if insurer_so:
            vals_to_write['insurer_sale_order_id'] = insurer_so.id
        
        self.write(vals_to_write)
        return True
    
    
    @api.onchange('vehicle_id')
    def _onchange_vehicle_id_set_contacts(self):
        if self.vehicle_id:
            self.purchaser_id = self.vehicle_id.driver_id
        else:
            self.purchaser_id = False

    def action_in_progress(self):
        self.ensure_one()
        # Ahora referenciamos nuestros NUEVOS DATOS del NUEVO MODELO
        state_available = self.env.ref('fleet_product.workshop_stage_available')
        state_in_workshop = self.env.ref('fleet_product.workshop_stage_in_workshop')
        
        # Y escribimos en nuestro NUEVO CAMPO 'workshop_stage_id'
        if self.vehicle_id.workshop_stage_id == state_available:
            self.vehicle_id.write({'workshop_stage_id': state_in_workshop.id})
        
        self.write({'state': 'running'})
        return True
    
    def action_done(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError("...")
        
        vehicle = self.vehicle_id
        self.write({'state': 'done'})
        
        vehicle.invalidate_recordset(['active_service_count'])
        
        if vehicle.active_service_count == 0:
            # Usamos nuestros NUEVOS DATOS
            state_available = self.env.ref('fleet_product.workshop_stage_available')
            # Y escribimos en nuestro NUEVO CAMPO
            vehicle.write({'workshop_stage_id': state_available.id})
            
        return True
    
    def action_cancel(self):
        for service in self:
            vehicle = service.vehicle_id
            # ... tu lógica de cancelar SOs ...
            service.write({'state': 'cancelled'})
            vehicle.invalidate_recordset(['active_service_count'])
            if vehicle.active_service_count == 0:
                # Usamos nuestros NUEVOS DATOS
                state_available = self.env.ref('fleet_product.workshop_stage_available')
                # Y escribimos en nuestro NUEVO CAMPO
                vehicle.write({'workshop_stage_id': state_available.id})
        return True

    def _compute_sale_order_count(self):
        """ Cuenta cuántos pedidos de venta están vinculados a este servicio. """
        for service in self:
            count = 0
            if service.sale_order_id:
                count += 1
            if service.insurer_sale_order_id:
                count += 1
            service.sale_order_count = count
            
    def action_view_sale_orders(self):
        '''
        Función para mostrar los pedidos de venta generados por el servicio
        '''
        self.ensure_one()

        domain = [('id', 'in', (self.sale_order_id.id, self.insurer_sale_order_id.id))]

        return {
            'name': 'Presupuestos Generados',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    # MÉTODO WRITE PARA EL READONLY (Limpio y simple)
    def write(self, vals):
        for service in self:
            # Si no se está intentando cambiar el estado (para permitir el flujo de trabajo)...
            if 'state' not in vals and service.state in ['done', 'cancelled']:
                raise UserError("Acción no permitida: No se puede modificar un servicio que ya está finalizado o cancelado.")
        return super(FleetVehicleLogServices, self).write(vals)
    
    # MÉTODO CREATE PARA EL ODÓMETRO (El que ya funciona)
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('vehicle_id') and 'odometer' in vals and vals['odometer']:
                odometer_log = self.env['fleet.vehicle.odometer'].create({
                    'value': vals['odometer'],
                    'date': vals.get('date', fields.Date.context_today(self)),
                    'vehicle_id': vals['vehicle_id']
                })
                vals['odometer_id'] = odometer_log.id
                # El inverse en el campo base 'odometer' a veces necesita esto para evitar
                # que intente crear el registro dos veces. Es una medida de seguridad.
                # del vals['odometer']
        return super(FleetVehicleLogServices, self).create(vals_list)
    
    # VALIDACIÓN DEL ODÓMETRO CON CONSTRAINS (Más limpio que en el write)
    @api.constrains('odometer')
    def _check_odometer_value(self):
        for service in self:
            if service.odometer and service.vehicle_id:
                last_odometer_val = service.vehicle_id.odometer
                if service.odometer < last_odometer_val:
                    # Al editar, el valor máximo puede ser el propio registro. Necesitamos comparar con el anterior.
                    previous = self.env['fleet.vehicle.odometer'].search([
                        ('vehicle_id', '=', service.vehicle_id.id),
                        ('id', '!=', service.odometer_id.id)
                    ], limit=1, order='value desc')
                    if previous and service.odometer < previous.value:
                        raise UserError(
                            "Error: El valor del odómetro (%s) no puede ser inferior al registro anterior (%s)." %
                            (service.odometer, previous.value)
                        )

    
    # Este campo permite vincular un contrato de mantenimiento específico al servicio. 
    contract_id = fields.Many2one(
        'account.analytic.account',
        string='Contrato Aplicado',
        tracking=True,
        # El dominio asegura que solo podamos elegir contratos del cliente del vehículo
        domain="[('partner_id', '=', vehicle_id.customer_id)]"
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 
        string='Cuenta Analítica',
        # Este campo debería ser de solo lectura para el usuario normal,
        # ya que lo rellenaremos automáticamente.
        readonly=True,
        copy=False, # No queremos copiar la cuenta analítica al duplicar un servicio
        help="Cuenta analítica vinculada al contrato aplicado, para seguimiento de costos."
    )
    
    @api.onchange('vehicle_id')
    def _onchange_vehicle_id_set_contacts_and_contract(self):
        if self.vehicle_id:
            # Lógica existente: proponer el contacto
            self.purchaser_id = self.vehicle_id.driver_id

            self.odometer = self.vehicle_id.odometer

            # Lógica existente: proponer el plan de mantenimiento
            self.contract_id = self.vehicle_id.maintenance_contract_id
    
            # Copiamos el contrato a la cuenta analítica.
            self.analytic_account_id = self.vehicle_id.maintenance_contract_id
            
        else:
            self.purchaser_id = False
            self.contract_id = False
            self.analytic_account_id = False