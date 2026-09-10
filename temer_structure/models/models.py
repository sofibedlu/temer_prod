from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class PropertyReservation(models.Model):
    _inherit = 'property.reservation.configuration'
    _description = 'Property Reservation Configuration'

    number_of_allowed_quick_reservation = fields.Integer(string='Number Of Allowed Quick Reservation', default=0, tracking=True)
    # allow_quick_reservation = fields.Boolean(string='Allow Quick Reservation',)

    # Cancellation Limits
    max_cancellations = fields.Integer(string='Maximum Cancellations Allowed', tracking=True)
    cancellation_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Cancellation Check Period', default='monthly', tracking=True)
    cancellation_penalty_days = fields.Integer(
        string='Cancellation Penalty Days',
        help='Days blocked from new reservations after exceeding cancellation limit',
        tracking=True
    )

    # Transfer Limits
    max_transfers = fields.Integer(string='Maximum Transfers Allowed', tracking=True)
    transfer_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Transfer Check Period', default='monthly', tracking=True)
    transfer_penalty_days = fields.Integer(
        string='Transfer Penalty Days',
        help='Days blocked from transfers after exceeding transfer limit',
        tracking=True
    )

    # Extension Limits
    max_extensions = fields.Integer(string='Maximum Extensions Allowed', tracking=True)
    extension_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Extension Check Period', default='monthly', tracking=True)
    extension_penalty_days = fields.Integer(
        string='Extension Penalty Days',
        help='Days blocked from extensions after exceeding extension limit',
        tracking=True
    )


class PropertySalesWing(models.Model):
    _name = 'property.sales.wing'
    _description = 'Sales Wing'

    name = fields.Char(string="Wing Name")
    manager_id = fields.Many2one('res.users', string="Wing Manager", required=True, 
        domain=lambda self: self._get_available_supervisors_domain())
    # team_ids = fields.Many2many('property.sales.team', string="Teams", domain="['|', ('added', '=', False), ('id', 'in', team_ids)]")
    team_ids = fields.Many2many(
        'property.sales.team', 
        'property_wing_team_rel',  # Relation table name
        'wing_id',                 # Column for this model's id
        'team_id',                 # Column for related model's id
        string="Teams", 
        domain="['|', ('added', '=', False), ('id', 'in', team_ids)]"
    )
    commission_config_id = fields.Many2one('commission.configuration', string="Commission Configuration", default=lambda self: self._get_default_commission_config('wing'))

    @api.model
    def create(self, vals):
        # Create the wing
        wing = super(PropertySalesWing, self).create(vals)

        # Mark related sales teams as added
        if 'team_ids' in vals:
            # Fetch the related sales teams
            sales_teams = self.env['property.sales.team'].browse(vals['team_ids'])
            # Update the added field
            sales_teams.write({'added': True})

        return wing

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(PropertySalesWing, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='team_ids']"):
                node.set('domain', "[('id', 'not in', %s)]" % self._get_assigned_team_ids())
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def _get_assigned_team_ids(self):
        """
        Fetch team IDs currently assigned to any wing.
        """
        assigned_team_ids = self.env['property.sales.wing'].search([]).mapped('team_ids')
        assigned_team_ids = [team.id for team in assigned_team_ids]
        return assigned_team_ids


    @api.model
    def _get_default_commission_config(self, hierarchy_type):
        # Fetch the default commission configuration based on hierarchy type
        config = self.env['commission.configuration'].search([('hierarchy_type', '=', hierarchy_type)], limit=1)
        return config.id if config else False

    def _get_available_supervisors_domain(self):
        """
        Exclude users already assigned as supervisors or as salespersons.
        """
        # Fetch user IDs currently assigned as supervisors
        assigned_team_manager_ids = self.env['property.sales.team'].search([]).mapped('manager_id.id')
        assigned_supervisor_ids = self.env['property.sales.supervisor'].search([]).mapped('name.id')

        wing_managers = self.env['property.sales.wing'].search([]).mapped('manager_id.id')
        
        # Fetch user IDs currently assigned as salespersons
        self.env.cr.execute("""
            SELECT DISTINCT user_id FROM property_salesperson_mapping
        """)
        assigned_salesperson_ids = [row[0] for row in self.env.cr.fetchall()]

        # Combine both lists to exclude
        excluded_ids = list(set(assigned_team_manager_ids + assigned_supervisor_ids + wing_managers +assigned_salesperson_ids))
        return [('id', 'not in', excluded_ids)]

class PropertySalesTeam(models.Model):
    _name = 'property.sales.team'
    _description = 'Sales Team'
    _rec_name = 'manager_id'

    # name = fields.Char(string="Team Name")
    manager_id = fields.Many2one('res.users', string="Sales Manager", required=True, 
        domain=lambda self: self._get_available_supervisors_domain())
    # supervisor_ids = fields.Many2many('property.sales.supervisor', string="Supervisors")
    # wing_id = fields.Many2one('property.sales.wing', string="Wing")

    commission_config_id = fields.Many2one('commission.configuration', string="Commission Configuration", default=lambda self: self._get_default_commission_config('sales_manager'))

    # supervisor_ids = fields.Many2many(
    #     'property.sales.supervisor', 
    #     string="Supervisors",
    #      domain="['|', ('added', '=', False), ('id', 'in', supervisor_ids)]"
    # )
    supervisor_ids = fields.Many2many(
        'property.sales.supervisor', 
        'property_team_supervisor_rel',  # Relation table name
        'team_id',                      # Column for this model's id
        'supervisor_id',                 # Column for related model's id
        string="Supervisors",
        domain="['|', ('added', '=', False), ('id', 'in', supervisor_ids)]"
    )
    wing_id = fields.Many2one('property.sales.wing', string="Wing", compute='_compute_wing_id')

    @api.model
    def create(self, vals):
        # Create the sales team
        team = super(PropertySalesTeam, self).create(vals)

        # Mark related supervisors as added
        if 'supervisor_ids' in vals:
            # Fetch the related supervisors
            supervisors = self.env['property.sales.supervisor'].browse(vals['supervisor_ids'])
            # Update the added field
            supervisors.write({'added': True})

        return team

    def _compute_wing_id(self):
        for record in self:
            wing = self.env['property.sales.wing'].search([
                ('team_ids', 'in', record.id)
            ], limit=1)
            record.wing_id = wing

    @api.model
    def _get_default_supervisors(self):
        """Get supervisors that haven't been added to any team yet"""
        return self.env['property.sales.supervisor'].search([
            ('added', '=', False)
        ])
    added = fields.Boolean(string="Added", default=False)
    computed_added = fields.Boolean(string="Linked", compute='_compute_added',)

    # @api.depends('wing_id', 'wing_id.team_ids')
    def _compute_added(self):
        for record in self:
            # Search for the wing that contains this team
            wing = self.env['property.sales.wing'].search([
                ('team_ids', 'in', record.id)
            ], limit=1)
            
            if wing:
                # If wing is found, this team is added
                record.computed_added = True
                record.added = True
            else:
                record.computed_added = False
                record.added = False
            
    # sales_supervisor_ids = fields.One2many(
    #     'property.sales.supervisor', 
    #     'sales_team_id',
    #     string="Sales Supervisors"
    # )

    # ... existing code ...

    # def _get_available_supervisors_domain(self):
    #     """
    #     Exclude supervisors already assigned to other sales teams.
    #     """
    #     # Fetch supervisor IDs currently assigned to any sales team
    #     all_teams = self.env['property.sales.team'].search([])
    #     assigned_supervisor_ids = set()
    #     for team in all_teams:
    #         assigned_supervisor_ids.update(team.supervisor_ids.ids)

    #     # Exclude supervisors already assigned as supervisors or as salespersons
    #     sales_team_manager_ids = self.env['property.sales.team'].search([]).mapped('manager_id.id')
    #     wing_managers = self.env['property.sales.wing'].search([]).mapped('manager_id.id')
        
    #     self.env.cr.execute("""
    #         SELECT DISTINCT user_id FROM property_salesperson_mapping
    #     """)
    #     assigned_salesperson_ids = [row[0] for row in self.env.cr.fetchall()]

    #     # Combine all lists to exclude
    #     excluded_ids = list(assigned_supervisor_ids.union(sales_team_manager_ids, wing_managers, assigned_salesperson_ids))
    #     return [('id', 'not in', excluded_ids)]
        
    @api.model
    def _get_default_commission_config(self, hierarchy_type):
        # Fetch the default commission configuration based on hierarchy type
        config = self.env['commission.configuration'].search([('hierarchy_type', '=', hierarchy_type)], limit=1)
        return config.id if config else False

    def _get_available_supervisors_domain(self):
        """
        Exclude users already assigned as supervisors or as salespersons.
        """
        # Fetch user IDs currently assigned as supervisors
        sales_team_manager_ids = self.env['property.sales.team'].search([]).mapped('manager_id.id')
        assigned_supervisor_ids = self.env['property.sales.supervisor'].search([]).mapped('name.id')
        wing_managers = self.env['property.sales.wing'].search([]).mapped('manager_id.id')
        
        # Fetch user IDs currently assigned as salespersons
        self.env.cr.execute("""
            SELECT DISTINCT user_id FROM property_salesperson_mapping
        """)
        assigned_salesperson_ids = [row[0] for row in self.env.cr.fetchall()]
        # _logger.info(f"Sales Team Manager IDs: {sales_team_manager_ids}")
        # _logger.info(f"Assigned Supervisor IDs: {assigned_supervisor_ids}")
        # _logger.info(f"Wing Managers: {wing_managers}")
        # _logger.info(f"Assigned Salesperson IDs: {assigned_salesperson_ids}")

        # Combine both lists to exclude
        excluded_ids = list(set(assigned_supervisor_ids + sales_team_manager_ids + wing_managers + assigned_salesperson_ids))
        # _logger.info(f"==========Excluded IDs: {excluded_ids}")
        return [('id', 'not in', excluded_ids)]
    
    @api.model
    def create(self, vals):
        res = super(PropertySalesTeam, self).create(vals)
        return res

    def write(self, vals):
        res = super(PropertySalesTeam, self).write(vals)
        return res


class PropertySalesSupervisor(models.Model):
    _name = 'property.sales.supervisor'
    _description = 'Sales Supervisor'

    name = fields.Many2one('res.users', string="Sales Supervisor", required=True,
        domain=lambda self: self._get_available_supervisors_domain() )
    type = fields.Selection(
        [('internal', 'Internal'), ('agent', 'Agent'), ('freelancer', 'Freelancer')],
        string="Type",
        default='internal'
    )

    salespersons = fields.One2many(
        'property.salesperson.mapping',  # Link to intermediary model
        'supervisor_id',
        string="Salespersons"
    )

    sales_team_id = fields.Many2one('property.sales.team', string="Sales Team")
    
    added = fields.Boolean(string="Added", default=False)
    computed_added = fields.Boolean(string="Linked", compute='_compute_added')

    commission_config_id = fields.Many2one('commission.configuration', string="Commission Configuration", default=lambda self: self._get_default_commission_config('supervisor'))

    sales_team_id = fields.Many2one('property.sales.team', string="Sales Manager", compute='_compute_sales_team_id')
    
    @api.model
    def create(self, vals):
        # Create the salesperson mapping
        supervisor = super(PropertySalesSupervisor, self).create(vals)

        group_to_remove = self.env.ref('website.group_website_designer') 
        group_to_remove2 = self.env.ref('sales_team.group_sale_manager') 

        # Add the user to the access_property_sales_person_group
        if 'name' in vals:
            user = self.env['res.users'].browse(vals['name'])
            group = self.env.ref('temer_structure.access_property_sales_supervisor_group')
            if group and user:
                group_crm = self.env.ref('sales_team.group_sale_salesman_all_leads')
                group_property = self.env.ref('temer_structure.access_property_sales_person_group')
                if group_crm and group_property and user:
                    # user.groups_id = [(4, group_crm.id), (4, group_property.id)]  # Add user to the group
                    user.write({'groups_id': [(6, 0, [group.id, group_crm.id, group_property.id],(3, group_to_remove.id, group_to_remove2.id))],'password': 'temer123'})  # Replaces all groups with only these

                # user.groups_id = [(4, group.id)]  # Add user to the group

        return supervisor
   

    def _compute_sales_team_id(self):
        for record in self:
            team = self.env['property.sales.team'].search([
                ('supervisor_ids', 'in', record.id)
            ], limit=1)
            record.sales_team_id = team

    # @api.depends('sales_team_id', 'sales_team_id.supervisor_ids')
    def _compute_added(self):
        for record in self:
            # Search for teams that have this supervisor
            _logger.info(f"==========Record: {record.id}")
            team = self.env['property.sales.team'].search([
                ('supervisor_ids', 'in', record.id)
            ], limit=1)
            _logger.info(f"==========Team: {team.id}")
            
            if team:
                record.computed_added = True
                record.added = True
            else:
                record.computed_added = False
                record.added = False

    @api.model
    def _get_default_commission_config(self, hierarchy_type):
        # Fetch the default commission configuration based on hierarchy type
        config = self.env['commission.configuration'].search([('hierarchy_type', '=', hierarchy_type)], limit=1)
        return config.id if config else False

    def _get_available_supervisors_domain(self):
        """
        Exclude users already assigned as supervisors or as salespersons.
        """
        # Fetch user IDs currently assigned as supervisors
        assigned_supervisor_ids = self.search([]).mapped('name.id')
        sales_managers = self.env['property.sales.team'].search([]).mapped('manager_id.id')
        wing_managers = self.env['property.sales.wing'].search([]).mapped('manager_id.id')
        
        # Fetch user IDs currently assigned as salespersons
        self.env.cr.execute("""
            SELECT DISTINCT user_id FROM property_salesperson_mapping
        """)
        assigned_salesperson_ids = [row[0] for row in self.env.cr.fetchall()]

        # Combine both lists to exclude
        excluded_ids = list(set(assigned_supervisor_ids + sales_managers + wing_managers +  assigned_salesperson_ids))
        return [('id', 'not in', excluded_ids)]


    @api.constrains('salespersons')
    def _check_salesperson_uniqueness(self):
        """
        Ensure no salesperson is assigned to multiple supervisors.
        """
        all_mappings = self.env['property.salesperson.mapping'].search([])
        for record in self:
            assigned_salespersons = all_mappings.filtered(lambda m: m.supervisor_id != record)
            for salesperson in record.salespersons.mapped('user_id'):
                if salesperson in assigned_salespersons.mapped('user_id'):
                    raise ValidationError(f"The salesperson '{salesperson.name}' is already assigned to another supervisor.")


class PropertySalespersonMapping(models.Model):
    _name = 'property.salesperson.mapping'
    _description = 'Mapping of Sales Supervisors and Salespersons'

    supervisor_id = fields.Many2one(
        'property.sales.supervisor', string="Supervisor", required=True, ondelete="cascade"
    )
    user_id = fields.Many2one(
        'res.users', string="Salesperson", required=True,
        domain=lambda self: self._get_available_salespersons_domain()
    )
    
    @api.model
    def create(self, vals):
        # Create the salesperson mapping
        mapping = super(PropertySalespersonMapping, self).create(vals)
        group_to_remove = self.env.ref('website.group_website_designer')  # Replace with your group's XML ID


        # Add the user to the access_property_sales_person_group
        if 'user_id' in vals:
            user = self.env['res.users'].browse(vals['user_id'])
            group_crm = self.env.ref('sales_team.group_sale_salesman')
            group_property = self.env.ref('temer_structure.access_property_sales_person_group')
            if group_crm and group_property and user:
                # user.groups_id = [(4, group_crm.id), (4, group_property.id)]  # Add user to the group
                user.write({'groups_id': [(6, 0, [group_crm.id, group_property.id],(3, group_to_remove.id))],'password': 'temer123'})  # Replaces all groups with only these


        return mapping

    def _get_available_salespersons_domain(self):
        """
        Exclude already assigned salespersons from the selection.
        """

        assigned_supervisor_ids = self.env['property.sales.supervisor'].search([]).mapped('name.id')
        sales_managers = self.env['property.sales.team'].search([]).mapped('manager_id.id')
        wing_managers = self.env['property.sales.wing'].search([]).mapped('manager_id.id')
        # Fetch all user IDs already assigned to any supervisor
        self.env.cr.execute("""
            SELECT DISTINCT user_id FROM property_salesperson_mapping
        """)
        assigned_ids = [row[0] for row in self.env.cr.fetchall()]

        excluded_ids = list(set(assigned_supervisor_ids + sales_managers + wing_managers + assigned_ids))
        return [('id', 'not in', excluded_ids)]

    _sql_constraints = [
        ('unique_salesperson_supervisor', 'unique(supervisor_id, user_id)',
         'A salesperson cannot be assigned to the same supervisor multiple times.')
    ]
