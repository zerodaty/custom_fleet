from odoo import models, fields, api

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'
    
    # --- CAMPOS PARA CONTRATOS ---
    maintenance_contract_id = fields.Many2one(
        'account.analytic.account',
        string='Plan de Mantenimiento',
        tracking=True,
        # El dominio ayuda a los usuarios a seleccionar solo contratos relevantes
        domain="[('partner_id', '=', customer_id)]"
    )
    
    # --- CAMPOS DE CLIENTE ---
    customer_id = fields.Many2one(
        'res.partner',
        string='Propietario / Cliente',
        tracking=True
    )

    # --- CAMPOS DE SEGUROS ---
    insurance_policy_ids = fields.One2many(
        'fleet.vehicle.insurance',
        'vehicle_id',
        string='Pólizas de Seguro'
    )
    has_active_policies = fields.Boolean(
        string="¿Tiene Pólizas Activas?",
        compute='_compute_has_active_policies'
    )
    
    def _get_default_workshop_stage(self):
        return self.env.ref('fleet_product.workshop_stage_available', raise_if_not_found=False)
    
    workshop_stage_id = fields.Many2one(
        'fleet.workshop.stage',
        string='Etapa de Taller',
        default=_get_default_workshop_stage,
        group_expand='_read_group_expand_full',
        tracking=True,
        copy=False
    )
    # Para la vista kanban
    active_service_count = fields.Integer(compute="_compute_active_service_count", string="Servicios Activos")
    # Estrellas de la vista kanban
    priority = fields.Selection(
        [
            ('0', 'Normal'),
            ('1', 'Alta'),
            ('2', 'Urgente')
        ], 
        string='Prioridad',
        default='0',
        tracking=True
    )
    # Para las alertas de entrega    
    next_delivery_date = fields.Date(
        string="Próxima Entrega",
        compute='_compute_next_delivery_date',
        store=True
    )


    # METODOS PARA ASEGURADORAS
    @api.depends('insurance_policy_ids')
    def _compute_has_active_policies(self):
        """ Verifica si existen pólizas de tipo 'propietaria' activas. """
        for vehicle in self:
            owner_policies = vehicle.insurance_policy_ids.filtered(lambda p: p.policy_type == 'owner')
            vehicle.has_active_policies = bool(owner_policies)


    # METODO PARA VAINA KANBAN (CAMBIOS PROPIOS)
    @api.depends('log_services.state')
    def _compute_active_service_count(self):
        """ Cuenta los servicios que están en estado 'Nuevo' o 'En Curso'. """
        for vehicle in self:
            vehicle.active_service_count = self.env['fleet.vehicle.log.services'].search_count([
                ('vehicle_id', '=', vehicle.id),
                ('state', 'in', ['new', 'running']) 
            ])

    def action_open_services(self):
        """
        Acción para abrir una vista de los servicios activos del vehículo.
        Este método será llamado desde la nueva vista Kanban.
        """
        self.ensure_one()
        active_services_ids = self.log_services.filtered(lambda s: s.state in ['new', 'running']).ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Servicios Activos',
            'res_model': 'fleet.vehicle.log.services',
            'view_mode': 'list,form',
            'domain': [('id', 'in', active_services_ids)],
            'target': 'current',
        }
        
    # Servicios activos del carro
    @api.depends('log_services.estimated_delivery_date', 'log_services.state')
    def _compute_next_delivery_date(self):
        """
        Calcula la fecha de entrega estimada más próxima de todos los
        servicios activos ('En Curso' o 'Nuevo') de este vehículo.
        """
        for vehicle in self:
            active_services_with_date = vehicle.log_services.filtered(
                lambda s: s.state in ['new', 'running'] and s.estimated_delivery_date
            )
            
            if active_services_with_date:
                vehicle.next_delivery_date = min(active_services_with_date, key=lambda s: s.estimated_delivery_date).estimated_delivery_date
            else:
                vehicle.next_delivery_date = False
    
    