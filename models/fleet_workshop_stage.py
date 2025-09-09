
from odoo import fields, models

class FleetWorkshopStage(models.Model):
    _name = 'fleet.workshop.stage'
    _description = 'Etapas del Taller para Vehículos'
    _order = 'sequence asc'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)