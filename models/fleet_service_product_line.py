# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools

class FleetServiceProductLine(models.Model):
    """
    Modelo que representa una línea de producto (refacción, lubricante)
    utilizada dentro de un registro de servicio de la flota.
    """
    
    _name = 'fleet.service.product.line'
    _description = 'Product Line for Fleet Services'
    
    
    def _get_default_category_id(self):
        """
        Retorna la categoría de producto por defecto para 'Automotriz'.
        Este método auxiliar encapsula la referencia al XML ID para mejorar
        la mantenibilidad y facilitar las pruebas.
        """
        return self.env.ref('fleet_product.product_category_automotriz', raise_if_not_found=False)

    # El vínculo maestro. Cada línea DEBE pertenecer a un servicio.
    service_id = fields.Many2one(
        'fleet.vehicle.log.services', 
        string='Service Log',
        required=True, 
        ondelete='cascade'  # Importante: si borras el servicio, estas líneas se borran.
    )
    
    # El producto seleccionado.
    product_id = fields.Many2one(
        'product.product', 
        string='Product', 
        required=True,
        # El domain para el filtro lo pondremos en la vista XML.
    )
    
    # --- Campos de Costo y Cantidad ---

    quantity = fields.Float(
        string='Quantity', 
        required=True,
        default=1.0,
        digits='Product Unit of Measure' # Usa la precisión definida para UoM.
    )
    
    # El precio por unidad. Tomaremos el "Costo" del producto como valor por defecto.
    price_unit = fields.Float(
        string='Unit Price', 
        digits='Product Price' # Usa la precisión estándar de Odoo para precios.
    )
    
    # La moneda la heredamos del servicio al que pertenece esta línea.
    # Es un campo técnico necesario para los campos 'Monetary'.
    currency_id = fields.Many2one(
        related='service_id.currency_id', 
        store=True
    )

    # Subtotal calculado. La pieza clave de este modelo.
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True  # CRUCIAL. Guarda el valor en la BBDD.
    )
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True, default=_get_default_category_id,
        required=True)
    
    # Logica
    
    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        """ Calcula el subtotal para cada línea. """
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit
            

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
        Cuando el usuario selecciona un producto en el formulario,
        este método se ejecuta para autocompletar el precio unitario.
        Si se deselecciona el producto, el precio unitario se limpia.
        """
        if self.product_id:
            # 'standard_price' es el nombre técnico del campo 'Costo' en la ficha del producto.
            self.price_unit = self.product_id.standard_price
        else:
            self.price_unit = 0.0
        
