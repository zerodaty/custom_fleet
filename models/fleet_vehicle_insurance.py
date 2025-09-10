# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class FleetVehicleInsurance(models.Model):
    """
    Modelo para gestionar las pólizas de seguro asociadas a los vehículos de la flota.
    Diseñado para ser flexible y manejar tanto las pólizas propietarias de la empresa
    como los seguros temporales asociados a futuros alquileres.
    """
    _name = 'fleet.vehicle.insurance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Póliza de Seguro de Vehículo'
    _order = 'end_date desc, name' # Ordenar por defecto, las más nuevas primero

    

    name = fields.Char(
        string='Número de Póliza', 
        required=True,
        )
    active = fields.Boolean(
        default=True,
        ) 

    policy_type = fields.Selection(
        [
            ('owner', 'Póliza Propietaria'),
        ],
        tracking = True,
        string='Tipo de Póliza', 
        required=True, 
        default='owner'
    )
    
    insurer_id = fields.Many2one(
        'res.partner', 
        string='Aseguradora',
        required=True,
        tracking = True
    )

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo Asegurado',
        required=True,
        tracking = True
    )

    # --- Campos de Vigencia y Costo ---

    start_date = fields.Date(string='Fecha de Inicio', required=True, tracking=True)
    end_date = fields.Date(string='Fecha de Vencimiento', required=True, tracking=True)

    currency_id = fields.Many2one(
        'res.currency', 
        related='vehicle_id.currency_id',
        store=True
    )
    cost = fields.Monetary(string='Costo de la Póliza')

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Asegura que la fecha de inicio no sea posterior a la fecha de fin."""
        for policy in self:
            if policy.start_date > policy.end_date:
                raise ValidationError("La fecha de inicio de la póliza no puede ser posterior a la fecha de vencimiento.")
    
    
