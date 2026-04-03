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
        Calcula y devuelve un dominio para el campo `purchaser_id`.
        El dominio restringe la selección de 'res.partner' a solo aquellos
        que están asignados como conductores de al menos un vehículo en la flota.
        Esto asegura que en el registro de servicio solo se puedan seleccionar
        conductores válidos.
        """
        # Busca todos los vehículos que tienen un conductor asignado.
        vehicles_with_driver = self.env['fleet.vehicle'].search([('driver_id', '!=', False)])
        # Extrae los IDs de los conductores de esos vehículos.
        driver_ids = vehicles_with_driver.mapped('driver_id').ids
        # Retorna el dominio para filtrar el campo 'purchaser_id'.
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
    
    def _get_product_ref(self, xml_id):
        """Método auxiliar para obtener una referencia de producto de forma centralizada."""
        return self.env.ref(f'fleet_product.{xml_id}').product_variant_id

    def _prepare_client_order_lines(self):
        """Prepara las líneas del pedido de venta para el cliente."""
        client_order_lines = []
        if self.labor_cost > 0:
            labor_product = self._get_product_ref('product_template_labor')
            client_order_lines.append(Command.create({
                'product_id': labor_product.id,
                'name': f"Mano de Obra del Servicio: {self.description or ''}",
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
            adjustment_product = self._get_product_ref('product_template_insurance_adjustment')
            client_order_lines.append(Command.create({
                'product_id': adjustment_product.id,
                'name': f"Ajuste por Cobertura (Póliza: {self.insurance_policy_id.name})",
                'product_uom_qty': 1,
                'price_unit': -self.insurance_coverage_amount
            }))
        return client_order_lines

    def _create_insurer_sale_order(self):
        """Crea el pedido de venta para la aseguradora si es necesario."""
        if self.insurance_coverage_amount > 0:
            if not self.insurance_policy_id.insurer_id:
                raise UserError("La póliza debe tener una compañía aseguradora asociada.")
            
            coverage_product = self._get_product_ref('product_template_insurance_coverage')
            return self.env['sale.order'].create({
                'partner_id': self.insurance_policy_id.insurer_id.id,
                'order_line': [Command.create({
                    'product_id': coverage_product.id,
                    'name': f"Reclamo Cobertura - Servicio: {self.description or ''} ({self.vehicle_id.name})",
                    'product_uom_qty': 1,
                    'price_unit': self.insurance_coverage_amount,
                })],
                'origin': f"Servicio Flota: {self.description or ''}"
            })
        return None

    def _validate_service_for_so_creation(self):
        """Realiza validaciones antes de crear los pedidos de venta."""
        if self.sale_order_id or self.insurer_sale_order_id:
            raise UserError("Ya se han generado los documentos de venta para este servicio.")
        if not self.purchaser_id:
            raise UserError("Por favor, seleccione un 'Conductor / Cliente' antes de continuar.")
        if self.insurance_policy_id:
            if not (self.insurance_policy_id.start_date <= self.date <= self.insurance_policy_id.end_date):
                raise UserError("La fecha del servicio está fuera de la vigencia de la póliza.")
            if self.insurance_coverage_amount > self.insurance_policy_id.cost:
                raise UserError(f"El monto cubierto ({self.insurance_coverage_amount}) no puede exceder el límite de la póliza ({self.insurance_policy_id.cost}).")

    def action_create_sale_orders(self):
        """
        Orquesta la creación de pedidos de venta para el cliente y la aseguradora.
        Este método está ahora refactorizado para usar métodos auxiliares que
        simplifican la lógica y mejoran la legibilidad.
        """
        self.ensure_one()
        self._validate_service_for_so_creation()

        client_order_lines = self._prepare_client_order_lines()
        if not client_order_lines:
            raise UserError("No hay nada que facturar. Añada mano de obra o productos.")

        client_so = self.env['sale.order'].create({
            'partner_id': self.purchaser_id.id,
            'order_line': client_order_lines,
            'origin': f"Servicio Flota: {self.description or ''}"
        })

        insurer_so = self._create_insurer_sale_order()

        vals_to_write = {'sale_order_id': client_so.id}
        if insurer_so:
            vals_to_write['insurer_sale_order_id'] = insurer_so.id
        
        self.write(vals_to_write)
        return True

    def _get_workshop_stage(self, xml_id):
        """Método auxiliar para obtener una etapa de taller de forma centralizada."""
        return self.env.ref(f'fleet_product.{xml_id}', raise_if_not_found=False)

    def _update_vehicle_workshop_stage(self, new_stage=None):
        """
        Actualiza la etapa de taller del vehículo. Si no se proporciona una
        nueva etapa, se asume que el servicio ha finalizado y se verifica si
        el vehículo puede volver a estar 'Disponible'.
        """
        self.ensure_one()
        vehicle = self.vehicle_id
        if not vehicle:
            return

        if new_stage:
            vehicle.workshop_stage_id = new_stage
        else:
            # Si el servicio termina (done/cancel) y no hay más servicios activos,
            # el vehículo vuelve a la etapa 'Disponible'.
            vehicle.invalidate_recordset(['active_service_count'])
            if vehicle.active_service_count == 0:
                available_stage = self._get_workshop_stage('workshop_stage_available')
                vehicle.workshop_stage_id = available_stage

    def action_in_progress(self):
        self.ensure_one()
        state_available = self._get_workshop_stage('workshop_stage_available')
        if self.vehicle_id.workshop_stage_id == state_available:
            state_in_workshop = self._get_workshop_stage('workshop_stage_in_workshop')
            self._update_vehicle_workshop_stage(new_stage=state_in_workshop)
        self.write({'state': 'running'})
        return True

    def action_done(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError("No se puede completar un servicio sin un presupuesto generado.")
        
        self.write({'state': 'done'})
        self._update_vehicle_workshop_stage()
        return True

    def action_cancel(self):
        for service in self:
            # ... tu lógica de cancelar SOs ...
            service.write({'state': 'cancelled'})
            service._update_vehicle_workshop_stage()
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
    
    @api.onchange('vehicle_id', 'date')
    def _onchange_vehicle_and_date(self):
        """
        Este método unificado gestiona las actualizaciones de campos cuando
        cambia el vehículo o la fecha del servicio, asegurando que los
        datos relacionados (conductor, odómetro, contrato, póliza) se
        mantengan consistentes y actualizados.
        """
        if self.vehicle_id:
            # --- Actualizaciones directas desde el vehículo ---
            self.purchaser_id = self.vehicle_id.driver_id
            self.odometer = self.vehicle_id.odometer
            self.contract_id = self.vehicle_id.maintenance_contract_id
            self.analytic_account_id = self.vehicle_id.maintenance_contract_id

            # --- Lógica para encontrar la póliza de seguro relevante ---
            if self.date:
                domain = [
                    ('vehicle_id', '=', self.vehicle_id.id),
                    ('policy_type', '=', 'owner'),
                    ('start_date', '<=', self.date),
                    ('end_date', '>=', self.date),
                ]
                # Busca la póliza más relevante (la que vence más tarde pero ya está activa).
                relevant_policy = self.env['fleet.vehicle.insurance'].search(
                    domain, order='end_date desc', limit=1
                )
                self.insurance_policy_id = relevant_policy
            else:
                # Si no hay fecha, no podemos determinar la póliza.
                self.insurance_policy_id = False
        else:
            # Si no hay vehículo, reseteamos todos los campos relacionados.
            self.purchaser_id = False
            self.contract_id = False
            self.analytic_account_id = False
            self.insurance_policy_id = False
            self.odometer = False # Asumiendo que el odómetro se resetea si no hay vehículo.