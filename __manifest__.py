{       # Theme information
        'name': "fleet_product",
        'version': '5.0',
        'category': 'Services',
        'summary': "Extension de Fleet",
        'description': """Extension del modulo fleet """,

        # Author
        'author': "Frany Velasquez",
        'website': "https://github.com/zerodaty",
        'license': 'LGPL-3',
                
        #Dependencies
        'depends': [
            'base','fleet','product','sale','contacts','analytic',
        ],
        # always loaded
        'data': [
            # ~ # security
            'security/ir.model.access.csv',
            # ~ # data
            'data/fleet_product_categories.xml',
            'data/fleet_product_productos.xml',
            'data/fleet_product_service.xml',
            'data/fleet_workshop_stage_data.xml',
            # ~ # views
            'views/fleet_workshop_views.xml',
            'views/fleet_vehicle_log_services_views.xml',
            'views/fleet_vehicle_insurance_views.xml',
            'views/fleet_vehicle_view.xml',
            # ~ # reports
            'report/fleet_service_report_templates.xml',
        ],
        'demo': [
            'demo/demo.xml',
        ],
        # Technical
        'installable':True,
        'application':True,
        'auto_install':False,
}

