from odoo import models, fields, api
from datetime import timedelta
import logging
from lxml import etree
from odoo.osv import expression

_logger = logging.getLogger(__name__)

class TemerLeadInherited(models.Model):
    _inherit = 'temer.lead'

    supervisor_id = fields.Many2one('property.sales.supervisor', string="Sales Supervisor", readonly=True)
    sales_team_id = fields.Many2one('property.sales.team', string="Sales Team", readonly=True)
    wing_id = fields.Many2one('property.sales.wing', string="Sales Wing", readonly=True)

    allowed_user_ids = fields.Many2many('res.users', string="Allowed Users", compute="_compute_allowed_user_ids")
    
    # Computed fields for grouping
    computed_wing_id = fields.Many2one('property.sales.wing', string="Wing (Computed)", compute="_compute_sales_hierarchy", store=True)
    computed_supervisor_id = fields.Many2one('property.sales.supervisor', string="Supervisor (Computed)", compute="_compute_sales_hierarchy", store=True)
    computed_sales_team_id = fields.Many2one('property.sales.team', string="Sales Team (Computed)", compute="_compute_sales_hierarchy", store=True)

    def _get_group_by(self):
        """Override to remove phone_ids from the available groupable fields"""
        group_by_fields = super()._get_group_by()  # Get the original group by fields
        # Ensure 'phone_ids' is removed
        if 'phone_ids' in group_by_fields:
            group_by_fields.remove('phone_ids')
        return group_by_fields
        
    def _compute_allowed_user_ids(self):
        for rec in self:
            group_ids = self.env.ref('ahadubit_crm.crm_res_groups_view_all_activity1').ids
            allowed_users = self.env['res.users'].search([('groups_id', 'in', group_ids)]) 
            allowed_users |= rec.user_id  # Combine recordsets using the | operator
            rec.allowed_user_ids = allowed_users 

    @api.model
    def fields_view_get(self, view_id=None, view_type='pivot', toolbar=False, submenu=False):
        res = super(TemerLeadInherited, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'pivot' and not self.user_has_groups('temer_structure.access_property_dev_admin_group1'):
            doc = etree.XML(res['arch'])
            # Targeting the specific field in the pivot view
            for node in doc.xpath("//field[@name='phone_ids']"):
                node.set('invisible', '1')
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    @api.depends('user_id')
    def _compute_sales_hierarchy(self):
        """Compute sales hierarchy on-the-fly for grouping"""
        for record in self:
            # Initialize computed fields
            computed_wing = False
            computed_supervisor = False
            computed_team = False
            
            # Use stored values if available (for records that have been updated)
            if record.wing_id:
                computed_wing = record.wing_id.id
            if record.supervisor_id:
                computed_supervisor = record.supervisor_id.id
            if record.sales_team_id:
                computed_team = record.sales_team_id.id
            
            # Compute hierarchy if not already available
            if record.user_id and (not computed_supervisor or not computed_team or not computed_wing):
                # Try to find supervisor through mapping
                mapping = self.env['property.salesperson.mapping'].search([
                    ('user_id', '=', record.user_id.id)
                ], limit=1)

                if mapping and mapping.supervisor_id:
                    computed_supervisor = mapping.supervisor_id.id
                    
                    # Find team through supervisor
                    team = self.env['property.sales.team'].search([
                        ('supervisor_ids', 'in', [mapping.supervisor_id.id])
                    ], limit=1)
                    if team:
                        computed_team = team.id
                        
                        # Find wing through team
                        wing = self.env['property.sales.wing'].search([
                            ('team_ids', 'in', [team.id])
                        ], limit=1)
                        if wing:
                            computed_wing = wing.id
                
                # If no mapping found, check if user is a supervisor
                elif not computed_supervisor:
                    supervisor = self.env['property.sales.supervisor'].search([
                        ('name', '=', record.user_id.id)
                    ], limit=1)
                    if supervisor:
                        computed_supervisor = supervisor.id
                        computed_team = supervisor.sales_team_id.id if supervisor.sales_team_id else False
                        computed_wing = supervisor.sales_team_id.wing_id.id if supervisor.sales_team_id and supervisor.sales_team_id.wing_id else False
                
                # If no supervisor found, check if user is a team manager
                elif not computed_team:
                    team = self.env['property.sales.team'].search([
                        ('manager_id', '=', record.user_id.id)
                    ], limit=1)
                    if team:
                        computed_team = team.id
                        computed_wing = team.wing_id.id if team.wing_id else False
                
                # If no team found, check if user is a wing manager
                elif not computed_wing:
                    wing = self.env['property.sales.wing'].search([
                        ('manager_id', '=', record.user_id.id)
                    ], limit=1)
                    if wing:
                        computed_wing = wing.id
            
            # Assign computed values - use IDs, not recordset objects
            record.computed_wing_id = computed_wing
            record.computed_supervisor_id = computed_supervisor
            record.computed_sales_team_id = computed_team

    @api.onchange('user_id')
    def _onchange_user_id_compute_hierarchy(self):
        """Trigger hierarchy computation when user changes"""
        self._compute_sales_hierarchy()

    def _search(self, domain, offset=0, limit=None, order=None):
        """Override search to filter reservations based on user's role"""

        if not self._context.get('my_team_leads'):
            return super()._search(domain, offset=offset, limit=limit, order=order)
        
        user = self.env.user
        my_domain = self._get_domain_for_user_role(user)
        
        if domain:
            domain = expression.AND([domain, my_domain])
        else:
            domain = my_domain
        
        leads = super()._search(domain, offset=offset, limit=limit, order=order)
        return leads

    def _get_domain_for_user_role(self, user):
        """Determine the search domain based on the user's role"""

        if self._is_wing_manager(user):
            return self._domain_for_wing_manager(user)
        elif self._is_team_manager(user):
            return self._domain_for_team_manager(user)
        elif self._is_supervisor(user):
            return self._domain_for_supervisor(user)
        else:
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
            LEFT JOIN property_salesperson_mapping pm ON pm.supervisor_id = s.id
            WHERE w.id = %s
        """, (wing_id,))
        results = self.env.cr.dictfetchall()
        team_ids = {r['team_id'] for r in results if r['team_id']}
        supervisor_ids = {r['supervisor_id'] for r in results if r['supervisor_id']}
        user_ids = {r['salesperson_id'] for r in results if r['salesperson_id']}
        
        domains = []
        if wing_id:
            domains.append(('wing_id', '=', wing_id))
        if team_ids:
            domains.append(('sales_team_id', 'in', list(team_ids)))
        if supervisor_ids:
            domains.append(('supervisor_id', 'in', list(supervisor_ids)))
        if user_ids:
            domains.append(('user_id', 'in', list(user_ids)))
            
        if len(domains) > 1:
            return ['|'] * (len(domains) - 1) + domains
        elif domains:
            return domains
        else:
            return [('id', '=', 0)]  # Return no records if no domain conditions

    def _is_team_manager(self, user):
        self.env.cr.execute("SELECT id FROM property_sales_team WHERE manager_id = %s LIMIT 1", (user.id,))
        return self.env.cr.fetchone()

    def _domain_for_team_manager(self, user):
        team_id = self._is_team_manager(user)[0]
        self.env.cr.execute("""
            SELECT s.id as supervisor_id, pm.user_id as salesperson_id
            FROM property_sales_team t
            LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
            LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
            LEFT JOIN property_salesperson_mapping pm ON pm.supervisor_id = s.id
            WHERE t.id = %s
        """, (team_id,))
        results = self.env.cr.dictfetchall()
        supervisor_ids = {r['supervisor_id'] for r in results if r['supervisor_id']}
        user_ids = {r['salesperson_id'] for r in results if r['salesperson_id']}
        
        domains = []
        if team_id:
            domains.append(('sales_team_id', '=', team_id))
        if supervisor_ids:
            domains.append(('supervisor_id', 'in', list(supervisor_ids)))
        if user_ids:
            domains.append(('user_id', 'in', list(user_ids)))
            
        if len(domains) > 1:
            return ['|'] * (len(domains) - 1) + domains
        elif domains:
            return domains
        else:
            return [('id', '=', 0)]

    def _is_supervisor(self, user):
        self.env.cr.execute("SELECT id FROM property_sales_supervisor WHERE name = %s LIMIT 1", (user.id,))
        return self.env.cr.fetchone()

    def _domain_for_supervisor(self, user):
        supervisor_id = self._is_supervisor(user)[0]
        self.env.cr.execute("SELECT user_id FROM property_salesperson_mapping WHERE supervisor_id = %s", (supervisor_id,))
        user_ids = [r[0] for r in self.env.cr.fetchall() if r[0]]
        domains = []
        if supervisor_id:
            domains.append(('supervisor_id', '=', supervisor_id))
        if user_ids:
            domains.append(('user_id', 'in', user_ids))
            
        if len(domains) > 1:
            return ['|'] * (len(domains) - 1) + domains
        elif domains:
            return domains
        else:
            return [('id', '=', 0)]

    def _domain_for_salesperson(self, user):
        return [('user_id', '=', user.id)]
    
    @api.model
    def create(self, vals):
        # Create the temer lead record
        record = super(TemerLeadInherited, self).create(vals)
        # Trigger update in activity report copy
        self.env['crm.activity.report'].update_activity_report_copy()
        return record

    def write(self, vals):
        # Write changes to the temer lead
        result = super(TemerLeadInherited, self).write(vals)
        # Trigger update in activity report copy
        self.env['crm.activity.report'].update_activity_report_copy()
        return result
    
    @api.depends('user_id')
    def _compute_sales_structure(self):
        """Compute the sales hierarchy structure for the reservation"""
        for record in self:
            if record.user_id and not record.supervisor_id and not record.wing_id:
                record.supervisor_id = False
                record.sales_team_id = False
                record.wing_id = False
                # Find the mapping for the current salesperson
                mapping = self.env['property.salesperson.mapping'].search([
                    ('user_id', '=', record.user_id.id)
                ], limit=1)
                _logger.info(f"==============Mapping: {mapping}")

                if mapping and mapping.supervisor_id:
                    record.supervisor_id = mapping.supervisor_id.id

                    # Find the team associated with the supervisor
                    team = self.env['property.sales.team'].search([
                        ('supervisor_ids', 'in', [record.supervisor_id.id])
                    ], limit=1)

                    if team:
                        record.sales_team_id = team.id

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
        one_hour_ago = fields.Datetime.now() - timedelta(hours=1)

        leads = self.env['temer.lead'].search(['|','|',('supervisor_id', '=',False),('sales_team_id', '=',False),('wing_id', '=',False)],limit=200)
        for record in leads:
            if not record.wing_id or not record.supervisor_id or not record.sales_team_id:
                wing_id = self.env['property.sales.wing'].search([('manager_id', '=',record.user_id.id)], limit=1).id
                team_id = self.env['property.sales.team'].search([('manager_id', '=',record.user_id.id)], limit=1).id

                # Find the mapping for the current salesperson
                mapping = self.env['property.salesperson.mapping'].search([
                    ('user_id', '=', record.user_id.id)
                ], limit=1)

                if team_id:
                    record.supervisor_id = False
                    record.sales_team_id = team_id
                    wing_id = self.env['property.sales.wing'].search([('team_ids', 'in', [team_id])], limit=1).id
                    if wing_id:
                        record.wing_id = wing_id
                elif wing_id:
                    record.supervisor_id = False
                    record.sales_team_id = False
                    record.wing_id = wing_id
            
                elif mapping and mapping.supervisor_id:
                    record.supervisor_id = mapping.supervisor_id.id

                    # Find the team associated with the supervisor
                    team = self.env['property.sales.team'].search([
                        ('supervisor_ids', 'in', [record.supervisor_id.id])
                    ], limit=1)

                    if team:
                        record.sales_team_id = team.id

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

    # Batch Update Methods
    def update_existing_records_sales_structure(self):
        """Update all existing records with sales structure data - Batch version"""
        _logger.info("Starting batch update of sales structure for all leads")
        
        # Process in batches to avoid memory issues
        batch_size = 200
        domain = ['|', '|', ('supervisor_id', '=', False), ('sales_team_id', '=', False), ('wing_id', '=', False)]
        total_leads = self.search_count(domain)
        _logger.info(f"Found {total_leads} leads needing sales structure update")
        
        offset = 0
        processed = 0
        
        while True:
            leads = self.search(domain, offset=offset, limit=batch_size)
            if not leads:
                break
                
            for lead in leads:
                try:
                    # Use the existing _compute_sales_structure logic
                    lead._compute_sales_structure()
                    processed += 1
                    
                    # Log progress every 100 records
                    if processed % 100 == 0:
                        _logger.info(f"Processed {processed}/{total_leads} records")
                        
                except Exception as e:
                    _logger.error(f"Error processing lead {lead.id}: {str(e)}")
                    continue
            
            # Commit after each batch
            self.env.cr.commit()
            offset += batch_size
        
        _logger.info(f"Completed batch update. Processed {processed} leads")

    def update_all_records_sales_structure(self):
        """Update ALL records with sales structure data (including those with existing values)"""
        _logger.info("Starting update of sales structure for ALL leads")
        
        batch_size = 200
        total_leads = self.search_count([])
        _logger.info(f"Total leads to process: {total_leads}")
        
        offset = 0
        processed = 0
        
        while True:
            leads = self.search([], offset=offset, limit=batch_size)
            if not leads:
                break
                
            for lead in leads:
                try:
                    # Force recompute for all records
                    lead._compute_sales_structure()
                    processed += 1
                    
                    if processed % 100 == 0:
                        _logger.info(f"Processed {processed}/{total_leads} records")
                        
                except Exception as e:
                    _logger.error(f"Error processing lead {lead.id}: {str(e)}")
                    continue
            
            self.env.cr.commit()
            offset += batch_size
        
        _logger.info(f"Completed update of all leads. Processed {processed} records")