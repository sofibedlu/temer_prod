# from odoo import models, fields, api

# class PropertyWingConfigSalespersonLine(models.TransientModel):
#     _name = 'property.wing.config.salesperson.line'
#     _description = 'Salesperson Selection Line'

#     salesperson_id = fields.Many2one('res.users', string='Salesperson', required=True)
#     config_id = fields.Many2one('property.wing.config', string='Config')
#     selected = fields.Boolean('Select')

# class PropertyWingConfigSupervisorLine(models.TransientModel):
#     _name = 'property.wing.config.supervisor.line'
#     _description = 'Supervisor Selection Line'

#     supervisor_id = fields.Many2one('property.sales.supervisor', string='Supervisor', required=True)
#     config_id = fields.Many2one('property.wing.config', string='Config')
#     selected = fields.Boolean('Select')

# class PropertyWingConfig(models.Model):
#     _name = 'property.wing.config'
#     _description = 'Wing Configuration'

#     source_id = fields.Many2one(
#         'utm.source',
#         string="Source",
#         required=True,
#         domain="[('name', 'in', ['6033', 'Walk In'])]"
#     )
#     wing_id = fields.Many2one('property.sales.wing', string="Wing", required=True)

#     selection_salesperson_line_ids = fields.One2many(
#         'property.wing.config.salesperson.line', 'config_id', string='Available Salespersons'
#     )
#     selection_supervisor_line_ids = fields.One2many(
#         'property.wing.config.supervisor.line', 'config_id', string='Available Supervisors'
#     )

#     @api.onchange('source_id', 'wing_id')
#     def _onchange_wing_id(self):
#         self.selection_salesperson_line_ids = [(5, 0, 0)]
#         self.selection_supervisor_line_ids = [(5, 0, 0)]

#         if self.source_id and self.wing_id:
#             # Get all leads for this source & wing
#             leads = self.env['crm.lead'].search([
#                 ('wing_id', '=', self.wing_id.id),
#                 ('source_id', '=', self.source_id.id)
#             ])
#             # Get distinct salespersons from leads
#             salespersons = leads.mapped('user_id')
#             salesperson_lines = [
#                 (0, 0, {
#                     'salesperson_id': user.id,
#                     'selected': False
#                 }) for user in salespersons if user
#             ]
#             self.selection_salesperson_line_ids = salesperson_lines

#             # Get distinct supervisors from leads
#             supervisors = leads.mapped('supervisor_id')
#             supervisor_lines = [
#                 (0, 0, {
#                     'supervisor_id': sup.id,
#                     'selected': False
#                 }) for sup in supervisors if sup
#             ]
#             self.selection_supervisor_line_ids = supervisor_lines

#     def action_apply_selection(self):
#         # Optional: save selected records if needed
#         pass








# from odoo import models, fields, api

# class PropertyWingConfigSalespersonLine(models.TransientModel):
#     _name = 'property.wing.config.salesperson.line'
#     _description = 'Salesperson Selection Line'

#     salesperson_id = fields.Many2one('res.users', string='Salesperson', required=True)
#     config_id = fields.Many2one('property.wing.config', string='Config')
#     selected = fields.Boolean('Select')

# class PropertyWingConfigSupervisorLine(models.TransientModel):
#     _name = 'property.wing.config.supervisor.line'
#     _description = 'Supervisor Selection Line'

#     supervisor_id = fields.Many2one('property.sales.supervisor', string='Supervisor', required=True)
#     config_id = fields.Many2one('property.wing.config', string='Config')
#     selected = fields.Boolean('Select')

# class PropertyWingConfig(models.Model):
#     _name = 'property.wing.config'
#     _description = 'Wing Configuration'

#     source_id = fields.Many2one(
#         'utm.source',
#         string="Source",
#         required=True,
#         domain="[('name', 'in', ['6033', 'Walk In', 'website'])]"  # Adjust domain as needed
#     )
#     wing_id = fields.Many2one('property.sales.wing', string="Wing", required=True)

#     selection_salesperson_line_ids = fields.One2many(
#         'property.wing.config.salesperson.line', 'config_id', string='Available Salespersons'
#     )
#     selection_supervisor_line_ids = fields.One2many(
#         'property.wing.config.supervisor.line', 'config_id', string='Available Supervisors'
#     )
#     def get_selected_supervisors(self):
#         return self.selection_supervisor_line_ids.filtered(lambda l: l.selected).mapped('supervisor_id')

#     def get_selected_salespersons(self):
#         return self.selection_salesperson_line_ids.filtered(lambda l: l.selected).mapped('salesperson_id')
#     @api.onchange('wing_id')
#     def _onchange_wing_id(self):
#         self.selection_salesperson_line_ids = [(5, 0, 0)]
#         self.selection_supervisor_line_ids = [(5, 0, 0)]

#         if self.wing_id:
#             # Get all leads for this wing (ignore source)
#             leads = self.env['crm.lead'].search([
#                 ('wing_id', '=', self.wing_id.id)
#             ])
#             # Get unique salespersons from leads
#             salespersons = leads.mapped('user_id')
#             salesperson_lines = [
#                 (0, 0, {
#                     'salesperson_id': user.id,
#                     'selected': False
#                 }) for user in salespersons if user
#             ]
#             self.selection_salesperson_line_ids = salesperson_lines

#             # Get unique supervisors from leads
#             supervisors = leads.mapped('supervisor_id')
#             supervisor_lines = [
#                 (0, 0, {
#                     'supervisor_id': sup.id,
#                     'selected': False
#                 }) for sup in supervisors if sup
#             ]
#             self.selection_supervisor_line_ids = supervisor_lines

#     def action_apply_selection(self):
#         # Optional: save selected records if needed
#         pass
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PropertyWingConfigSalespersonLine(models.Model):
    _name = 'property.wing.config.salesperson.line'
    _description = 'Salesperson Selection Line'

    salesperson_id = fields.Many2one('res.users', string='Salesperson', required=True)
    config_id = fields.Many2one('property.wing.config', string='Config')
    selected = fields.Boolean('Select')


class PropertyWingConfigSupervisorLine(models.Model):
    _name = 'property.wing.config.supervisor.line'
    _description = 'Supervisor Selection Line'

    supervisor_id = fields.Many2one('property.sales.supervisor', string='Supervisor', required=True)
    config_id = fields.Many2one('property.wing.config', string='Config')
    selected = fields.Boolean('Select')


class PropertyWingConfig(models.Model):
    _name = 'property.wing.config'
    _description = 'Wing Configuration'
    _rec_name = 'wing_id'

    source_id = fields.Many2one(
        'utm.source',
        string="Source",
        required=True,
        domain="[('name', 'in', ['6033', 'Walk In', 'Website','Affiliate'])]"
    )
    wing_id = fields.Many2one('property.sales.wing', string="Wing", required=False)
    def _get_wing_selection(self):
        no_wing = self.env['property.sales.wing'].search([('name', '=', 'No Wing')], limit=1)
        if no_wing:
            return [(str(no_wing.id), 'No Wing')]
        else:
            return [('no_wing', 'No Wing')]

    wing_selection = fields.Selection(
        selection='_get_wing_selection',
        string="Wing",
        required=False,
    )

    selection_salesperson_line_ids = fields.One2many(
        'property.wing.config.salesperson.line', 'config_id', string='Available Salespersons'
    )
    selection_supervisor_line_ids = fields.One2many(
        'property.wing.config.supervisor.line', 'config_id', string='Available Supervisors'
    )
    active_supervisor_id = fields.Many2one(
        'property.sales.supervisor', string="Active Supervisor",
        help="Selected supervisor to be used for round robin"
    )
    active_salesperson_id = fields.Many2one(
        'res.users', string="Active Salesperson",
        help="Selected salesperson to be used for round robin"
    )
    combined_selected_users = fields.Many2many(
        'res.users', compute='_compute_combined_selected_users', string="Selected Persons", store=False
    )
    def get_selected_supervisors(self):
        return self.selection_supervisor_line_ids.filtered(lambda l: l.selected).mapped('supervisor_id')

    def get_selected_salespersons(self):
        return self.selection_salesperson_line_ids.filtered(lambda l: l.selected).mapped('salesperson_id')

    def get_selected_rr_pool(self):
        """Return a combined list of selected supervisors and salespersons (user records)."""
        supervisors = self.get_selected_supervisors().mapped('name')  # .name is the user_id on supervisor
        salespersons = self.get_selected_salespersons()
        return supervisors + salespersons
    @api.depends('selection_supervisor_line_ids.selected', 'selection_supervisor_line_ids.supervisor_id',
             'selection_salesperson_line_ids.selected', 'selection_salesperson_line_ids.salesperson_id')
    
    def _compute_combined_selected_users(self):
        for rec in self:
            # Supervisors: get their user (name field is res.users)
            supervisor_users = rec.selection_supervisor_line_ids.filtered('selected').mapped('supervisor_id.name')
            # Salespersons: are already res.users
            salesperson_users = rec.selection_salesperson_line_ids.filtered('selected').mapped('salesperson_id')
            rec.combined_selected_users = supervisor_users + salesperson_users
    @api.onchange('wing_id')
    def _onchange_wing_id(self):
        self.selection_salesperson_line_ids = [(5, 0, 0)]
        self.selection_supervisor_line_ids = [(5, 0, 0)]
        if self.wing_id:
          
            leads = self.env['crm.lead'].search([('wing_id', '=', self.wing_id.id)])

            salespersons = leads.mapped('user_id')
            salesperson_lines = [(0, 0, {'salesperson_id': user.id, 'selected': False}) for user in salespersons if user]
            self.selection_salesperson_line_ids = salesperson_lines

            supervisors = leads.mapped('supervisor_id')
            supervisor_lines = [(0, 0, {'supervisor_id': sup.id, 'selected': False}) for sup in supervisors if sup]
            self.selection_supervisor_line_ids = supervisor_lines
            
    def action_refresh_sales_supervisors(self):
        for rec in self:
            selected_salesperson_ids = set(rec.selection_salesperson_line_ids.filtered('selected').mapped('salesperson_id').ids)
            selected_supervisor_ids = set(rec.selection_supervisor_line_ids.filtered('selected').mapped('supervisor_id').ids)

            leads = self.env['crm.lead'].search([('wing_id', '=', rec.wing_id.id)])

            salespersons = leads.mapped('user_id')
            supervisors = leads.mapped('supervisor_id')

            salesperson_lines = []
            for user in salespersons:
                if user:
                    salesperson_lines.append((0, 0, {
                        'salesperson_id': user.id,
                        'selected': user.id in selected_salesperson_ids,
                    }))
            supervisor_lines = []
            for sup in supervisors:
                if sup:
                    supervisor_lines.append((0, 0, {
                        'supervisor_id': sup.id,
                        'selected': sup.id in selected_supervisor_ids,
                    }))

            rec.selection_salesperson_line_ids = [(5, 0, 0)] + salesperson_lines
            rec.selection_supervisor_line_ids = [(5, 0, 0)] + supervisor_lines

    def action_apply_selection(self):
        # Update active fields based on the checked lines.
        selected_supers = self.get_selected_supervisors()
        selected_salespersons = self.get_selected_salespersons()
        
        if selected_supers:
            self.active_supervisor_id = selected_supers[0].id
            _logger.info("Applied Selection: Active Supervisor: %s", self.active_supervisor_id.name)
        else:
            self.active_supervisor_id = False
            _logger.info("Applied Selection: No Active Supervisor selected")
        
        if selected_salespersons:
            self.active_salesperson_id = selected_salespersons[0].id
            _logger.info("Applied Selection: Active Salesperson: %s", self.active_salesperson_id.name)
        else:
            self.active_salesperson_id = False
            _logger.info("Applied Selection: No Active Salesperson selected")
        
        return True
    
