from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class CommissionPayment(models.Model):
    _name = 'property.commission.payment'
    _description = 'Commission Payment'

    property_sale_id = fields.Many2one('property.sale', string="Property Sale", required=True)
    user_id = fields.Many2one('res.users', string="User", required=True)  # Link to the user
    amount = fields.Float(string="Commission Amount", required=True)
    payment_date = fields.Date(string="Payment Date", default=fields.Date.today)
    percentage = fields.Float(string="Commission Percentage", required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid'),
    ], string="Status", default='draft')

class CommissionConfiguration(models.Model):
    _name = 'commission.configuration'
    _description = 'Commission Configuration'

    name = fields.Char(string="Commission Name", required=True)
    sales_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
    ], string="Sales Type", required=True, default='internal')
    hierarchy_type = fields.Selection([
        ('wing', 'Wing Manager'),
        ('sales_manager', 'Sales Manager'),
        ('supervisor', 'Sales Supervisor'),
        ('sales_person', 'Sales Person'),
    ], string="Hierarchy Type", required=True)

    commission_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('amount', 'Amount'),
    ], string="Commission Type", required=True, default='percentage')
    amount = fields.Float(string="Commission Amount")
    percentage = fields.Float(string="Commission Percentage")
    self_rate_percentage = fields.Float(string="Self Rate Percentage")
    site_id = fields.Many2one('property.site', string="Site")  # Assuming you have a Site model
    
    @api.onchange('site_id')
    def _onchange_site_id(self):
        if not self.site_id:
            return {'value': {'display_name': ''}}  
        _logger.debug("Site ID selected: %s", self.site_id.id)


class PropertySale(models.Model):
    _inherit = "property.sale"

    commission_amount = fields.Float(string="Calculated Commission Amount", readonly=True)
    commission_detail_ids = fields.One2many('property.commission.payment', 'property_sale_id', string="Commission Details")
    sales_person = fields.Many2one('res.users', string="Sales Person")
    supervisor = fields.Many2one('property.sales.supervisor', string="Supervisor")
    team = fields.Many2one('property.sales.team', string="Team")
    wing = fields.Many2one('property.sales.wing', string="Wing")


    @api.depends('commission_detail_ids.amount')
    def _compute_total_commission(self):
        for sale in self:
            sale.commission_amount = sum(sale.commission_detail_ids.mapped('amount'))
    

    def calculate_commission(self):
        """
        Calculate commission based on the hierarchy of the salesperson or manager.
        """
        # Check if a salesperson is assigned
        if self.sales_person:
            # First, check for the salesperson's own commission configuration
            self.env['property.commission.payment'].search([('property_sale_id', '=', self.id)]).unlink()
            # _logger.debug("Existing Commissions: %s", existing_commissions)

            # Now check for the salesperson mapping
            salesperson_mapping = self.env['property.salesperson.mapping'].search([('user_id', '=', self.sales_person.id)], limit=1)
            _logger.debug("Salesperson Mapping: %s", salesperson_mapping)

            if salesperson_mapping:
                # Existing logic for when salesperson mapping is found
                salesperson_commission_config = self.env['commission.configuration'].search([
                    ('hierarchy_type', '=', 'sales_person')
                ], limit=1)
                # salesperson_commission_config = self.env['commission.configuration'].search([
                #     ('hierarchy_type', '=', 'sales_person'),
                #     ('site_id', '=', self.property_id.site.id)
                # ], limit=1)
                _logger.debug("Salesperson Commission Config: %s", salesperson_commission_config)

                if salesperson_commission_config:
                    if salesperson_commission_config.commission_type == 'percentage':
                        commission_amount = (salesperson_commission_config.percentage / 100) * self.sale_price  # Assuming sale_price is defined
                    else:
                        commission_amount = salesperson_commission_config.amount
                    _logger.debug("Commission Amount: %s", commission_amount)

                    # Create a commission payment record for the salesperson
                    self.commission_detail_ids.create({
                        'property_sale_id': self.id,
                        'user_id': self.sales_person.id,
                        'amount': commission_amount,
                        'payment_date': fields.Date.today(),
                        'percentage': salesperson_commission_config.percentage,
                        'state': 'draft',
                    })

                # Calculate commission based on supervisor
                supervisor = salesperson_mapping.supervisor_id
                _logger.debug("Supervisor: %s", supervisor)
                if supervisor:
                    supervisor_user_id = self.env['property.sales.supervisor'].search([('id', '=', supervisor.id)], limit=1).name.id
                    _logger.debug("Supervisor User ID: %s", supervisor_user_id)
                    Supervisor_commission_config = self.env['property.sales.supervisor'].search([('id', '=', supervisor.id)], limit=1).commission_config_id
                    _logger.debug("- Supervisor_commission_config: %s", Supervisor_commission_config)

                    if Supervisor_commission_config:
                        if Supervisor_commission_config.commission_type == 'percentage':
                            commission_amount = (Supervisor_commission_config.percentage / 100) * self.sale_price  # Assuming sale_price is defined
                        else:
                            commission_amount = Supervisor_commission_config.amount
                    _logger.debug("Commission Amount: %s", commission_amount)
                    self.commission_detail_ids.create({
                        'property_sale_id': self.id,
                        'user_id': supervisor_user_id,
                        'amount': commission_amount,
                        'payment_date': fields.Date.today(),
                        'percentage': Supervisor_commission_config.percentage,
                        'state': 'draft',
                    })

                    # Find the Sales Team by searching for the supervisor in the supervisor_ids field
                    team = self.env['property.sales.team'].search([('supervisor_ids', '=', supervisor.id)], limit=1)
                    _logger.debug("Team: %s", team)
                    if team:
                        # Get the commission configuration from the team
                        commission_config = team.commission_config_id
                        _logger.debug("Commission Config: %s", commission_config)
                        if commission_config:
                            if commission_config.commission_type == 'percentage':
                                commission_amount = (commission_config.percentage / 100) * self.sale_price  # Assuming sale_price is defined
                            else:
                                commission_amount = commission_config.amount
                            _logger.debug("Commission Amount: %s", commission_amount)

                            # Create a commission payment record for the supervisor
                            self.commission_detail_ids.create({
                                'property_sale_id': self.id,
                                'user_id': team.manager_id.id,
                                'amount': commission_amount,
                                'payment_date': fields.Date.today(),
                                'percentage': commission_config.percentage,
                                'state': 'draft',
                            })

                    # Find the Sales Wing by searching for the team
                    wing = self.env['property.sales.wing'].search([('team_ids', '=', team.id)], limit=1)
                    _logger.debug("Wing: %s", wing)
                    if wing:
                        commission_config = wing.commission_config_id
                        _logger.debug("Commission Config: %s", commission_config)
                        if commission_config:
                            if commission_config.commission_type == 'percentage':
                                commission_amount = (commission_config.percentage / 100) * self.sale_price  # Assuming sale_price is defined
                            else:
                                commission_amount = commission_config.amount
                            _logger.debug("Commission Amount: %s", commission_amount)
                            # Create a commission payment record for the wing
                            self.commission_detail_ids.create({
                                'property_sale_id': self.id,
                                'user_id': wing.manager_id.id,  # Assuming the wing manager is the user to receive the commission
                                'amount': commission_amount,
                                'payment_date': fields.Date.today(),
                                'percentage': commission_config.percentage,
                                'state': 'draft',
                            })

            else:
                # Logic for when there is no salesperson mapping
                # Check if the user is a manager or supervisor'
                #user = self.env['res.users'].browse(self.sales_person.id)

                # FIX: Find the actual user record associated with the partner
                user = self.env['res.users'].search([('partner_id', '=', self.sales_person.id)], limit=1)

                supervisor = self.env['property.sales.supervisor'].search([('name', '=', user.id)], limit=1)
                team = self.env['property.sales.team'].search([('manager_id', '=', user.id)], limit=1)
                if supervisor:

                    supervisor_user_id = self.env['property.sales.supervisor'].search([('id', '=', supervisor.id)], limit=1).name.id
                    _logger.debug("Supervisor User ID: %s", supervisor_user_id)
                    Supervisor_commission_config = self.env['property.sales.supervisor'].search([('id', '=', supervisor.id)], limit=1).commission_config_id
                    _logger.debug("- Supervisor_commission_config: %s", Supervisor_commission_config)

                    if Supervisor_commission_config:
                        if Supervisor_commission_config.commission_type == 'percentage':
                            commission_amount = (Supervisor_commission_config.self_rate_percentage / 100) * self.sale_price  # Assuming sale_price is defined
                        else:
                            commission_amount = Supervisor_commission_config.amount
                    _logger.debug("Commission Amount: %s", commission_amount)
                    self.commission_detail_ids.create({
                        'property_sale_id': self.id,
                        'user_id': supervisor_user_id,
                        'amount': commission_amount,
                        'payment_date': fields.Date.today(),
                        'percentage': Supervisor_commission_config.self_rate_percentage,
                        'state': 'draft',
                    })

                    if supervisor.type == 'internal':


                        team = self.env['property.sales.team'].search([('supervisor_ids', '=', supervisor.id)], limit=1)
                        if team:
                            commission_config = team.commission_config_id
                        if commission_config:
                            if commission_config.commission_type == 'percentage':
                                commission_amount = (commission_config.percentage / 100) * self.sale_price  # Assuming sale_price is defined
                            else:
                                commission_amount = commission_config.amount

                            # Create a commission payment record for the supervisor
                            self.commission_detail_ids.create({
                                'property_sale_id': self.id,
                                'user_id': supervisor.id,
                                'amount': commission_amount,
                                'payment_date': fields.Date.today(),
                                'percentage': commission_config.percentage,
                                'state': 'draft',
                            })
                        
                        wing = self.env['property.sales.wing'].search([('team_ids', '=', team.id)], limit=1)
                        _logger.debug("Wing: %s", wing)
                        if wing:
                            commission_config = wing.commission_config_id
                            _logger.debug("Commission Config: %s", commission_config)
                            if commission_config:
                                if commission_config.commission_type == 'percentage':
                                    commission_amount = (commission_config.percentage / 100) * self.sale_price  # Assuming sale_price is defined
                                else:
                                    commission_amount = commission_config.amount
                                _logger.debug("Commission Amount: %s", commission_amount)
                                # Create a commission payment record for the wing
                                self.commission_detail_ids.create({
                                    'property_sale_id': self.id,
                                    'user_id': wing.manager_id.id,  # Assuming the wing manager is the user to receive the commission
                                    'amount': commission_amount,
                                    'payment_date': fields.Date.today(),
                                    'percentage': commission_config.percentage,
                                    'state': 'draft',
                                })


                elif team:
               

                    _logger.debug("Team============: %s", team)
                    team = self.env['property.sales.team'].search([('manager_id', '=', user.id)], limit=1)
                    _logger.debug("Team: %s", team)
                    if team:
                        commission_config = team.commission_config_id
                        _logger.debug("teamCommission Config: %s", commission_config)
                        _logger.debug("teamCommission self rate: %s", commission_config.self_rate_percentage)
                        if commission_config:
                            if commission_config.commission_type == 'percentage':
                                commission_amount = (commission_config.self_rate_percentage / 100) * self.sale_price  # Assuming sale_price is defined
                            else:
                                commission_amount = commission_config.amount
                            _logger.debug("Commission Amount: %s", commission_amount)
                            _logger.debug("Team Manager ID: %s", team.manager_id.id)

                            # Create a commission payment record for the manager
                            self.commission_detail_ids.create({
                                'property_sale_id': self.id,
                                'user_id': team.manager_id.id,
                                'amount': commission_amount,
                                'payment_date': fields.Date.today(),
                                'percentage': commission_config.self_rate_percentage,
                                'state': 'draft',
                            })

                    

                        wing = self.env['property.sales.wing'].search([('team_ids', '=', team.id)], limit=1)
                        _logger.debug("Wing: %s", wing)
                        if wing:
                            commission_config = wing.commission_config_id
                            _logger.debug("Commission Config: %s", commission_config)
                            if commission_config:
                                if commission_config.commission_type == 'percentage':
                                    commission_amount = (commission_config.percentage / 100) * self.sale_price  # Assuming sale_price is defined
                                else:
                                    commission_amount = commission_config.amount
                                _logger.debug("Commission Amount: %s", commission_amount)

                                # Create a commission payment record for the wing
                                self.commission_detail_ids.create({
                                    'property_sale_id': self.id,
                                    'user_id': wing.manager_id.id,  # Assuming the wing manager is the user to receive the commission
                                    'amount': commission_amount,
                                    'payment_date': fields.Date.today(),
                                    'percentage': commission_config.percentage,
                                    'state': 'draft',
                                })
                else:
                    wing = self.env['property.sales.wing'].search([('team_ids', '=', team.id)], limit=1)
                    if wing:
                        commission_config = wing.commission_config_id
                        if commission_config:
                            if commission_config.commission_type == 'percentage':
                                commission_amount = (commission_config.self_rate_percentage / 100) * self.sale_price  # Assuming sale_price is defined
                            else:
                                commission_amount = commission_config.amount

                            # Create a commission payment record for the wing
                            self.commission_detail_ids.create({
                                'property_sale_id': self.id,
                                'user_id': wing.manager_id.id,  # Assuming the wing manager is the user to receive the commission
                                'amount': commission_amount,
                                'payment_date': fields.Date.today(),
                                'percentage': commission_config.self_rate_percentage,
                                'state': 'draft',
                            })

            

        return True