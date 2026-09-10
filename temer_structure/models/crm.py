from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
from odoo.osv import expression
_logger = logging.getLogger(__name__)
from lxml import etree

from datetime import datetime, timedelta


class crmLeadInherited(models.Model):
    _inherit = 'crm.lead'


    supervisor_id = fields.Many2one('property.sales.supervisor', string="Sales Supervisor", readonly=True)
    sales_team_id = fields.Many2one('property.sales.team', string="Sales Team", readonly=True)
    wing_id = fields.Many2one('property.sales.wing', string="Sales Wing", readonly=True)
    # loading = fields.Boolean('Customer ', default=False, compute='_compute_sales_structure')
    

    allowed_user_ids = fields.Many2many('res.users', string="Allowed Users", compute="_compute_allowed_user_ids")

    def _get_group_by(self):
        """Override to remove phone_ids from the available groupable fields"""
        group_by_fields = super()._get_group_by()  # Get the original group by fields
        # Ensure 'phone_ids' is removed
        if 'phone_ids' in group_by_fields:
            group_by_fields.remove('phone_ids')
        return group_by_fields
        
    # def _compute_allowed_user_ids(self):
    #     for rec in self:
    #         group_ids = self.env.ref('ahadubit_crm.crm_res_groups_view_all_activity1').ids
    #         allowed_users = self.env['res.users'].search([('groups_id', 'in', group_ids)]) 
    #         allowed_users.append(rec.user_id) # Get users in the specified groups
    #         rec.allowed_user_ids = allowed_users 
    def _compute_allowed_user_ids(self):
        for rec in self:
            group_ids = self.env.ref('ahadubit_crm.crm_res_groups_view_all_activity1').ids
            allowed_users = self.env['res.users'].search([('groups_id', 'in', group_ids)]) 
            allowed_users |= rec.user_id  # Combine recordsets using the | operator
            rec.allowed_user_ids = allowed_users 

    @api.model
    def fields_view_get(self, view_id=None, view_type='pivot', toolbar=False, submenu=False):
        res = super(crmLeadInherited, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'pivot' and not self.user_has_groups('temer_structure.access_property_dev_admin_group1'):
            doc = etree.XML(res['arch'])
            # Targeting the specific field in the pivot view
            for node in doc.xpath("//field[@name='phone_ids']"):
                node.set('invisible', '1')
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res


    @api.onchange('user_id')
    def _compute_sales_structure(self):
        for rec in self:
            # rec.loading = True
            rec._compute_sales_structure()

    # def _group_by_full(self, query):
    #     """Override to remove phone_ids from group_by queries."""
    #     _logger.info(f"==============*** _group_by_full: {_group_by_full}")
    #     query = super()._group_by_full(query)
    #     return query.replace("phone_ids,", "").replace(",phone_ids", "")

    def _search(self, domain, offset=0, limit=None, order=None):
        """Override search to filter reservations based on user's role"""

        # _logger.info(f"==============*** Domain: {domain}")
        # _logger.info(f"==============My Domain: {self._context}")
        if not self._context.get('my_team_leads'):
            return super()._search(domain, offset=offset, limit=limit, order=order)
        
        user = self.env.user
        # _logger.info(f"==============Starting search for user: {user.name} (ID: {user.id})")
        
        my_domain = self._get_domain_for_user_role(user)
        # _logger.info(f"==============My Domain: {my_domain}")
        
        if domain:
            domain = expression.AND([domain, my_domain])
        else:
            domain = my_domain
        
        leads = super()._search(domain, offset=offset, limit=limit, order=order)
        return leads

    def _get_domain_for_user_role(self, user):
        """Determine the search domain based on the user's role"""

        # _logger.info("==============_domain_for_supervisor is _domain_for_supervisor")
        # _logger.info(self._is_supervisor(user))
        if self._is_wing_manager(user):
            return self._domain_for_wing_manager(user)
        elif self._is_team_manager(user):
            # _logger.info("==============User is Team Manager")
            return self._domain_for_team_manager(user)
        elif self._is_supervisor(user):
            # _logger.info("==============User is Supervisor")
            # _logger.info(user)
            return self._domain_for_supervisor(user)
        else:
            # _logger.info("==============User is Salesperson")
            return self._domain_for_salesperson(user)

    def _is_wing_manager(self, user):
        self.env.cr.execute("SELECT id FROM property_sales_wing WHERE manager_id = %s LIMIT 1", (user.id,))
        return self.env.cr.fetchone()

    def _domain_for_wing_manager(self, user):
        wing_id = self._is_wing_manager(user)[0]
        self.env.cr.execute("""
            SELECT t.id as team_id, s.id as supervisor_id, pm.user_id as salesperson_id
            FROM property_sales_wing w
            JOIN property_wing_team_rel wt ON w.id = wt.wing_id
            JOIN property_sales_team t ON t.id = wt.team_id
            LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
            LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
            LEFT JOIN property_salesperson_mapping pm ON pm.user_id = w.id 
            WHERE w.id = %s
        """, (wing_id,))
        results = self.env.cr.dictfetchall()
        team_ids = {r['team_id'] for r in results}
        supervisor_ids = {r['supervisor_id'] for r in results}
        user_ids = {r['salesperson_id'] for r in results}
        if team_ids != None and wing_id != None and supervisor_ids != None and user_ids != None:
            return ['|','|','|',('wing_id', '=', wing_id), ('sales_team_id', 'in', list(team_ids)), ('supervisor_id', 'in', list(supervisor_ids)), ('user_id', 'in', list(user_ids))]
        elif wing_id != None and supervisor_ids != None and user_ids != None:   
            return ['|','|','|',('wing_id', '=', wing_id), ('supervisor_id', 'in', list(supervisor_ids)), ('user_id', 'in', list(user_ids))]
        elif  supervisor_ids != None and user_ids != None:
            return ['|','|', ('supervisor_id', 'in', list(supervisor_ids)), ('user_id', 'in', list(user_ids))]
        elif  user_ids != None:
            return [ ('user_id', 'in', list(user_ids))]

    def _is_team_manager(self, user):
        self.env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
        return self.env.cr.fetchone()

    def _domain_for_team_manager(self, user):
        team_id = self._is_team_manager(user)[0]
        # _logger.info(f"==============Team ID: {team_id}")
        self.env.cr.execute("""
            SELECT s.id as supervisor_id, pm.user_id as salesperson_id
            FROM property_sales_team t
            LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
            LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
            LEFT JOIN property_salesperson_mapping pm ON pm.supervisor_id = s.id
            WHERE t.id = %s
        """, (team_id,))
        results = self.env.cr.dictfetchall()
        supervisor_ids = {r['supervisor_id'] for r in results}
        user_ids = {r['salesperson_id'] for r in results}
        # _logger.info(f"==============Supervisor IDs: {supervisor_ids}")
        # _logger.info(f"==============User IDs: {user_ids}")
        return ['|','|',('sales_team_id', '=', team_id), ('supervisor_id', 'in', list(supervisor_ids)), ('user_id', 'in', list(user_ids))]

    def _is_supervisor(self, user):
        self.env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
        return self.env.cr.fetchone()

    def _domain_for_supervisor(self, user):
        supervisor_id = self._is_supervisor(user)[0]
        # _logger.info(f"=======***=======Supervisor ID: {supervisor_id}")
        self.env.cr.execute("SELECT user_id FROM property_salesperson_mapping WHERE supervisor_id = %s", (supervisor_id,))
        user_ids = [r[0] for r in self.env.cr.fetchall()]
        # _logger.info(f"==============User IDs: {user_ids}")
        # _logger.info(f"==============Supervisor ID: {supervisor_id}")
        return ['|',('supervisor_id', '=', supervisor_id), ('user_id', 'in', user_ids)]

    def _domain_for_salesperson(self, user):
        return [('user_id', '=', user.id)]
    


    @api.model
    def create(self, vals):
        # Create the CRM lead record
        record = super(crmLeadInherited, self).create(vals)
        # Trigger update in activity report copy
        self.env['crm.activity.report'].update_activity_report_copy()
        return record

    def write(self, vals):
        # Write changes to the CRM lead
        result = super(crmLeadInherited, self).write(vals)
        # Trigger update in activity report copy
        self.env['crm.activity.report'].update_activity_report_copy()
        return result
    
    # def _search(self, domain, offset=0, limit=None, order=None):
    #     """Override search to filter reservations based on user's role"""
    #     if not self._context.get('my_team_filter'):
    #         return super()._search(domain, offset=offset, limit=limit, order=order)
            
    #     user = self.env.user
    #     _logger.info(f"Starting search for user: {user.name} (ID: {user.id})")
        
    #     # Check wing manager
    #     self.env.cr.execute("""
    #         SELECT w.id 
    #         FROM property_sales_wing w
    #         WHERE w.manager_id = %s
    #         LIMIT 1
    #     """, (user.id,))
    #     wing_manager = self.env.cr.fetchone()
    #     _logger.info(f"wing_manager==========: {wing_manager}")
        
    #     if wing_manager:
    #         _logger.info("User is Wing Manager")
    #         wing_id = wing_manager[0]
            
    #         # Get all teams and their hierarchy under this wing
    #         self.env.cr.execute("""
    #             SELECT 
    #                 t.id as team_id,
    #                 t.manager_id as team_manager_id,
    #                 s.id as supervisor_id,
    #                 s.name as supervisor_user_id,
    #                 pm.user_id as salesperson_id
    #             FROM property_sales_wing w
    #             JOIN property_wing_team_rel wt ON w.id = wt.wing_id
    #             JOIN property_sales_team t ON t.id = wt.team_id
    #             LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
    #             LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
    # LEFT JOIN property_salesperson_mapping pm ON pm.user_id = w.id 
    #             WHERE w.id = %s
    #         """, (wing_id,))
    #         results = self.env.cr.dictfetchall()
            
    #         team_ids = list(set([r['team_id'] for r in results if r['team_id']]))
    #         supervisor_ids = list(set([r['supervisor_id'] for r in results if r['supervisor_id']]))
    #         user_id = list(set([r['salesperson_id'] for r in results if r['salesperson_id']]))
    #         _logger.info("--------------------------------user_id")
    #         _logger.info(user_id)
    #         _logger.info("--------------------------------user_id")
    #         _logger.info(user.id)
    #         my_domain = [
    #             '|', '|', '|',
    #             ('wing_id', '=', wing_id),
    #             ('team_id', 'in', team_ids),
    #             ('supervisor_id', 'in', supervisor_ids),
    #             ('user_id', '=', user.id)
    #         ]
        
    #     else:
    #         # Check team manager
    #         self.env.cr.execute("""
    #             SELECT id FROM property_sales_team 
    #             WHERE manager_id = %s LIMIT 1
    #         """, (user.id,))
    #         team_result = self.env.cr.fetchone()
            
    #         if team_result:
    #             _logger.info("User is Team Manager")
    #             team_id = team_result[0]
                
    #             # Get all supervisors and salespersons under this team
    #             self.env.cr.execute("""
    #                 SELECT DISTINCT 
    #                     s.id as supervisor_id,
    #                     s.name as supervisor_user_id,
    #                     pm.user_id as salesperson_id
    #                 FROM property_sales_team t
    #                 LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
    #                 LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
    #                 LEFT JOIN property_salesperson_mapping pm ON pm.supervisor_id = s.id
    #                 WHERE t.id = %s
    #             """, (team_id,))
    #             results = self.env.cr.dictfetchall()
                
    #             supervisor_ids = list(set([r['supervisor_id'] for r in results if r['supervisor_id']]))
    #             user_id = list(set([r['salesperson_id'] for r in results if r['salesperson_id']]))
                
    #             my_domain = [
    #                 '|', '|',
    #                 ('team_id', '=', team_id),
    #                 ('supervisor_id', 'in', supervisor_ids),
    #                 ('user_id', '=', user.id)
    #             ]
                
    #         else:
    
    #             # Check supervisor
    #             self.env.cr.execute("""
    #                 SELECT id FROM property_sales_supervisor 
    #                 WHERE name = %s LIMIT 1
    #             """, (user.id,))
    #             supervisor_id = self.env.cr.fetchone()
                
    #             if supervisor_id:
    #                 _logger.info("User is Supervisor")
    #                 supervisor_id = supervisor_id[0]
                    
    #                 # Get all salespersons under this supervisor
    #                 self.env.cr.execute("""
    #                     SELECT user_id 
    #                     FROM property_salesperson_mapping 
    #                     WHERE supervisor_id = %s
    #                 """, (supervisor_id,))
    #                 user_id = [r[0] for r in self.env.cr.fetchall()]
                    
    #                 my_domain = [
    #                     '|',
    #                     ('user_id', 'in', user_id),
    #                     ('supervisor_id', '=', user.id)
    #                 ]
                    
    #             else:
    #                 _logger.info("User is Salesperson")
    #                 my_domain = [('user_id', '=', user.id)]
        
    #     # Combine with existing domain
    #     if domain:
    #         domain = expression.AND([domain, my_domain])
    #     else:
    #         domain = my_domain
            
    #     _logger.info(f"Final domain: {domain}")
    #     return super()._search(domain, offset=offset, limit=limit, order=order)

    @api.depends('user_id')
    def _compute_sales_structure(self):
        """Compute the sales hierarchy structure for the reservation"""
        for record in self:
            

            if record.user_id and not record.supervisor_id and not record.wing_id:
                # record.loading = True
                # Initialize all fields as False
                record.supervisor_id = False
                record.team_id = False
                record.wing_id = False
                # Find the mapping for the current salesperson
                mapping = self.env['property.salesperson.mapping'].search([
                    ('user_id', '=', record.user_id.id)
                ], limit=1)
                _logger.info(f"==============Mapping: {mapping}")

                if mapping and mapping.supervisor_id:
                    record.supervisor_id = mapping.supervisor_id

                    # Find the team associated with the supervisor
                    team = self.env['property.sales.team'].search([
                        ('supervisor_ids', 'in', [record.supervisor_id.id])
                    ], limit=1)

                    if team:
                        record.sales_team_id = team

                        # Find the wing associated with the team
                        wing = self.env['property.sales.wing'].search([
                            ('team_ids', 'in', [team.id])
                        ], limit=1)

                        if wing:
                            record.wing_id = wing.id
                else:
                    supervisor = self.env['property.sales.supervisor'].search([
                        ('name', '=', record.user_id.id)
                    ], limit=1)
                    if supervisor:
                        record.supervisor_id = supervisor.id
                        record.sales_team_id = supervisor.sales_team_id.id
                        record.wing_id = supervisor.sales_team_id.wing_id.id
                    else:
                        team = self.env['property.sales.team'].search([
                            ('manager_id', '=', record.user_id.id)
                        ], limit=1)
                        if team:
                            record.sales_team_id = team.id
                            record.wing_id = team.wing_id.id

    
    def compute_sales_structure(self):
        """Compute the sales hierarchy structure for the reservation"""
        # _logger.info("===**----FROM production----***----==***********===compute_sales_structure======Record: {self}")
        one_hour_ago = fields.Datetime.now() - timedelta(hours=1)
        # _logger.info(f"============***==one_hour_ago: {one_hour_ago}")

        # records = self.search([('date', '>=', one_hour_ago)])

        leads = self.env['crm.lead'].search(['|','|',('supervisor_id', '=',False),('team_id', '=',False),('wing_id', '=',False)],limit=200)
        # leads = self.env['crm.lead'].search([])
        # leads = self.env['crm.lead'].search([('create_date', '>=', one_hour_ago)])
        # _logger.info(f"===*****=====compute_sales_structure======Leads: {leads}")
        for record in leads:
            # _logger.info(f"===*****=====compute_sales_structure======Record: {record}")  
            # _logger.info(f"===*****=====compute_sales_structure======Record: {record.user_id}")
            # _logger.info(f"===*****=====compute_sales_structure======Record: {record.supervisor_id}")
            # _logger.info(f"===*****=====compute_sales_structure======Record: {record.wing_id}")
            # _logger.info(f"===*****=====compute_sales_structure=sales_team_id=====Record: {record.sales_team_id}")

            # _logger.info(f"===*****=====compute_sales_structure======Record: {record.wing_id}")
            # _logger.info(f"===*****=====compute_sales_structure=sales_team_id=====Record: {record.sales_team_id}")
            # record.loading = True
            if  not record.wing_id.id or not record.supervisor_id.id or not record.sales_team_id.id:
                wing_id  = self.env['property.sales.wing'].search([('manager_id', '=',record.user_id.id)], limit=1).id
                team_id  = self.env['property.sales.team'].search([('manager_id', '=',record.user_id.id)], limit=1).id
                # _logger.info(f"===**=====compute_sales_structure======Record: {record}")
            

                # Find the mapping for the current salesperson
                mapping = self.env['property.salesperson.mapping'].search([
                    ('user_id', '=', record.user_id.id)
                ], limit=1)
                # _logger.info(f"==============Mapping: {mapping}")
                # _logger.info(f"==============Mapping: {mapping.supervisor_id}")
                # _logger.info(f"===*****=====compute_sales_structure======Team ID: {team_id}")
                # _logger.info(f"===*****=====compute_sales_structure======Wing ID: {wing_id}")
                if team_id:
                    record.supervisor_id = False
                    record.sales_team_id  = team_id
                    wing_id = self.env['property.sales.wing'].search([('team_ids', 'in', team_id)], limit=1).id
                    # _logger.info("--------------------------------wing_id")
                    # _logger.info(wing_id)
                    if wing_id:
                        record.wing_id = wing_id
                elif wing_id:
                        record.supervisor_id = False
                        record.sales_team_id = False
                        record.wing_id = wing_id
            

                elif mapping and mapping.supervisor_id:
                    record.supervisor_id = mapping.supervisor_id

                    # Find the team associated with the supervisor
                    team = self.env['property.sales.team'].search([
                        ('supervisor_ids', 'in', [record.supervisor_id.id])
                    ], limit=1)
                    # _logger.info(f"=======****=======Team: {team}")

                    if team:
                        record.sales_team_id = team

                        # Find the wing associated with the team
                        wing = self.env['property.sales.wing'].search([
                            ('team_ids', 'in', [team.id])
                        ], limit=1)
                        # _logger.info(f"==============Wing: {wing}")

                        if wing:
                            record.wing_id = wing.id
                else:
                    supervisor = self.env['property.sales.supervisor'].search([
                        ('name', '=', record.user_id.id)
                    ], limit=1)
                    if supervisor:
                        record.supervisor_id = supervisor.id
                        record.sales_team_id = supervisor.sales_team_id.id
                        record.wing_id = supervisor.sales_team_id.wing_id.id
                    else:
                        team = self.env['property.sales.team'].search([
                            ('manager_id', '=', record.user_id.id)
                        ], limit=1)
                        if team:
                            record.sales_team_id = team.id
                            record.wing_id = team.wing_id.id


            
            # break


    # @api.depends('user_id')
    # def _compute_sales_structure(self):
    #     """Compute the sales hierarchy structure for the reservation"""
    #     for record in self:
    #         # Initialize all fields as False
    #         record.supervisor_id = False
    #         record.team_id = False
    #         record.wing_id = False

    #         if record.user_id:
    #             # Find the mapping for the current salesperson
    #             mapping = self.env['property.salesperson.mapping'].search([
    #                 ('user_id', '=', record.user_id.id)
    #             ], limit=1)

    #             if mapping and mapping.supervisor_id:
    #                 record.supervisor_id = mapping.supervisor_id

    #                 # Find the team associated with the supervisor
    #                 team = self.env['property.sales.team'].search([
    #                     ('supervisor_ids', 'in', record.supervisor_id.id)
    #                 ], limit=1)

    #                 if team:
    #                     record.sales_team_id = team

    #                     # Find the wing associated with the team
    #                     wing = self.env['property.sales.wing'].search([
    #                         ('team_ids', 'in', team.id)
    #                     ], limit=1).id

    #                     record.wing_id = wing if wing else False
    #             else:
    #                 team = self.env['property.sales.team'].search([
    #                     ('manager_id', '=', record.user_id.id)
    #                 ], limit=1)

    #                 if team:
    #                     record.sales_team_id = team

    #                     # Find the wing associated with the team
    #                     wing = self.env['property.sales.wing'].search([
    #                         ('team_ids', 'in', team.id)
    #                     ], limit=1).id

    #                     record.wing_id = wing if wing else False
    #             else:
    #                 wing = self.env['property.sales.wing'].search([
    #                     ('manager_id', '=', record.user_id.id)
    #                 ], limit=1).id

    #                 record.wing_id = wing if wing else False

    #     record.loading = True


    
    
    # def action_reserve(self):
    #     for rec in self:
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'name': 'Reservation',
    #             'res_model': 'property.reservation',
    #             'view_mode': 'form',
    #             'target': 'new',
    #             'context': {
    #                 'default_partner_id': rec.partner_id.id,
    #                 'default_salesperson_id': rec.user_id.id,
    #                 'default_crm_lead_id': rec.id,
    #                 'default_is_sufficient': False,
    #             }

    #         }

    def is_phone_required(self):
        # _logger.info(f"+++++++++@@@@@@@@@@++********++is_phone_required: {self.phone_ids}")
        for rec in self:
            if len(rec.phone_ids)==1 and rec.phone_ids[0].phone =='duplicated':
                raise ValidationError("phone is required")
            
    def action_reserve(self):
        # _logger.info("--------------------****************------------action_reserve")
        for rec in self:
            rec.is_phone_required()
            # _logger.info("--------------------****************------------action_reserve")
            # _logger.info(rec)

            # Ensure the sales structure is computed before accessing the fields
            # rec._compute_sales_structure()

            return {
                'type': 'ir.actions.act_window',
                'name': 'Reservation',
                'res_model': 'property.reservation',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_partner_id': rec.partner_id.id,
                    'default_salesperson_ids': rec.user_id.id,
                    'default_crm_lead_id': rec.id,
                    'default_is_sufficient': False,
                    'default_property_id_domain':f"[('state', 'in', ['available']),('site', 'in', {rec.site_ids.ids})]"
          

                }

            }
