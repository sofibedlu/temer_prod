from odoo import models, fields, api, _
from odoo.osv import expression
import logging
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    salesperson_ids = fields.Many2one('res.users', string="Salesperson" , readonly=True)
    supervisor_id = fields.Many2one('property.sales.supervisor', string="Sales Supervisor", readonly=True)
    team_id = fields.Many2one('property.sales.team', string="Sales Team", readonly=True)
    wing_id = fields.Many2one('property.sales.wing', string="Sales Wing", readonly=True)
    show_sale_button = fields.Boolean(compute='_compute_show_sale_button')

    show_approve_button_permission = fields.Boolean(compute='_compute_show_approve_button_permission')

    @api.depends('status', 'is_sufficient', 'reservation_type_id.is_payment_required','reservation_type_id','property_id')
    def _compute_show_approve_button(self):
        for rec in self:
            if rec.reservation_type_id.reservation_type == 'quick' and rec.status in ['requested', 'draft']:
                rec.show_approve_button = True
            else:
                rec.show_approve_button = False
            # show_button = rec.status == 'requested' and (
            #     not rec.reservation_type_id.is_payment_required or 
            #     (rec.reservation_type_id.is_payment_required and rec.is_sufficient)
            # )
            # rec.show_approve_button = show_button

    def _compute_show_sale_button(self):
        for rec in self:
            rec.show_sale_button = rec.status == 'reserved' and rec.reservation_type_id.reservation_type != 'quick'
    # @api.depends('status', 'is_sufficient', 'reservation_type_id.is_payment_required', 'reservation_type_id.reservation_type')
    
    def read(self, fields=None, load='_classic_read'):
        if 'show_approve_button' in (fields or []):
            self._compute_show_approve_button_permission()
        return super(PropertyReservation, self).read(fields, load)
        
    def _compute_show_approve_button_permission(self):
        _logger.info("----------------#############------self---")
        for rec in self:
            rec.show_approve_button_permission = False
            if rec.reservation_type_id.reservation_type == 'quick' :
                if rec.status in ['draft','requested']:
                    rec.show_approve_button = True
                else:
                    rec.show_approve_button = False
            else:
                # _logger.info("----------------------User GROUP---")
                # _logger.info(self.env.user.groups_id)
                supervisor_group = self.env.ref('temer_structure.access_property_sales_supervisor_group')
                # _logger.info("----------------------supervisor_group---")
                # _logger.info(supervisor_group)
                is_supervisor = supervisor_group in self.env.user.groups_id
                # _logger.info("----------------------is_supervisor---")
                # _logger.info(is_supervisor)
                show_button = rec.status == 'requested' and (
                    not rec.reservation_type_id.is_payment_required or 
                    (rec.reservation_type_id.is_payment_required and rec.is_sufficient)
                ) and is_supervisor
                # _logger.info("------------%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%----------show_button---")
                # _logger.info(show_button)
                rec.show_approve_button = show_button
                rec.show_approve_button_permission = show_button

    #     super(PropertyReservation, self)._compute_show_approve_button()
    # #     # Fetching the groups
    # #     supervisor_group = self.env.ref('temer_structure.access_property_sales_supervisor_group')
    # #     salesperson_group = self.env.ref('temer_structure.access_property_sales_person_group')
        
    #     for rec in self:
    # #         # Check if the user is a member of the supervisor or salesperson group
    #         _logger.info("--------------------------------rec.status")
    #         _logger.info(rec.status)
    #         _logger.info("-----------@@@@@------------------supervisor_group")  
    #         _logger.info(supervisor_group)
    #         _logger.info("-----------@@@@@------------------salesperson_group")  
    #         _logger.info(salesperson_group)
    #         is_supervisor = supervisor_group in self.env.user.groups_id
    #         _logger.info("---***********-------------------------is_supervisor----show_button")
    #         _logger.info(is_supervisor)
    #         _logger.info(self.env.user.groups_id)
    #         is_salesperson = salesperson_group in self.env.user.groups_id
    #         _logger.info("------------########----------------is_salesperson----show_button")
    #         _logger.info(is_salesperson)
    #         _logger.info(rec.is_sufficient)
    #         _logger.info(rec.reservation_type_id.is_payment_required)
    #         _logger.info(rec.status)
            
    #         # General condition for showing the button
    #         show_button = rec.status == 'requested' and (
    #             not rec.reservation_type_id.is_payment_required or 
    #             (rec.reservation_type_id.is_payment_required and rec.is_sufficient)
    #         )
            
    #         _logger.info("----------------------------is_supervisor ----show_button")
    #         _logger.info(is_supervisor)
    #         _logger.info("----------------------------is_salesperson----show_button")
    #         _logger.info(is_salesperson)
    #         _logger.info("--------------------------------show_button")
    #         _logger.info(show_button)
    #         # Additional condition for supervisors
    #         show_button_supervisor = show_button and is_supervisor and rec.reservation_type_id.reservation_type != 'quick'
    #         _logger.info("--------------------------------show_button_supervisor")
    #         _logger.info(show_button_supervisor)
    #         # Additional condition for salespersons
    #         show_button_salesperson = show_button and is_salesperson and rec.reservation_type_id.reservation_type == 'quick'
    #         _logger.info("--------------------------------show_button_salesperson")
    #         _logger.info(show_button_salesperson)
            
    #         # Final condition to show the button
    #         rec.show_approve_button = show_button_supervisor or show_button_salesperson
    # # is_sufficient = fields.Boolean('Is Sufficient', compute='compute_sufficient_amount', default=False)



    @api.depends('reservation_type_id')
    def _compute_show_transfer_extend(self):
        for rec in self:
            if rec.reservation_type_id and rec.reservation_type_id.reservation_type != "quick":
                rec.show_transfer_extend=True
            else:
                rec.show_transfer_extend = False


    @api.onchange('salesperson_ids')
    def _onchange_salesperson_ids(self):
        self._compute_sales_structure()
    # @api.depends('salesperson_ids')
    # def _compute_sales_structure(self):
    #     for record in self:
    #         # Find the mapping for the current salesperson
    #         mapping = self.env['property.salesperson.mapping'].search([('user_id', '=', record.salesperson_ids.id)], limit=1)
    #         if mapping:
    #             record.supervisor_id = mapping.supervisor_id
    #         else:
    #             record.supervisor_id = False
            
    #         # Find the team associated with the supervisor
    #         team = self.env['property.sales.team'].search([('supervisor_ids', 'in', record.supervisor_id.id)], limit=1)
    #         if team:
    #             record.team_id = team
    #         else:
    #             record.team_id = False
            
    #         # Find the wing associated with the team
    #         wing = self.env['property.sales.wing'].search([('team_ids', 'in', team.id if team else [])], limit=1)
    #         record.wing_id = wing if wing else False
    
    @api.depends('salesperson_ids')
    def _compute_sales_structure(self):
        """Compute the sales hierarchy structure for the reservation"""
        for record in self:
            # Initialize all fields as False
            record.supervisor_id = False
            record.team_id = False
            record.wing_id = False

            if record.salesperson_ids:
                # Find the mapping for the current salesperson
                mapping = self.env['property.salesperson.mapping'].search([
                    ('user_id', '=', record.salesperson_ids.id)
                ], limit=1)

                if mapping and mapping.supervisor_id:
                    record.supervisor_id = mapping.supervisor_id

                    # Find the team associated with the supervisor
                    team = self.env['property.sales.team'].search([
                        ('supervisor_ids', 'in', record.supervisor_id.id)
                    ], limit=1)

                    if team:
                        record.team_id = team

                        # Find the wing associated with the team
                        wing = self.env['property.sales.wing'].search([
                            ('team_ids', 'in', team.id)
                        ], limit=1)

                        record.wing_id = wing if wing else False


    
    def _search(self, domain, offset=0, limit=None, order=None):
        """Override search to filter reservations based on user's role"""
        if not self._context.get('my_team_filter'):
            return super()._search(domain, offset=offset, limit=limit, order=order)
            
        user = self.env.user
        # _logger.info(f"Starting search for user: {user.name} (ID: {user.id})")
        
        # Check wing manager
        self.env.cr.execute("""
            SELECT w.id 
            FROM property_sales_wing w
            WHERE w.manager_id = %s
            LIMIT 1
        """, (user.id,))
        wing_manager = self.env.cr.fetchone()
        # _logger.info(f"wing_manager==========: {wing_manager}")
        
        if wing_manager:
            # _logger.info("User is Wing Manager")
            wing_id = wing_manager[0]
            
            # Get all teams and their hierarchy under this wing
            self.env.cr.execute("""
                SELECT 
                    t.id as team_id,
                    t.manager_id as team_manager_id,
                    s.id as supervisor_id,
                    s.name as supervisor_user_id,
                    pm.user_id as salesperson_id
                FROM property_sales_wing w
                JOIN property_wing_team_rel wt ON w.id = wt.wing_id
                JOIN property_sales_team t ON t.id = wt.team_id
                LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
    LEFT JOIN property_salesperson_mapping pm ON pm.user_id = w.id 
                WHERE w.id = %s
            """, (wing_id,))
            results = self.env.cr.dictfetchall()
            
            team_ids = list(set([r['team_id'] for r in results if r['team_id']]))
            supervisor_ids = list(set([r['supervisor_id'] for r in results if r['supervisor_id']]))
            salesperson_ids = list(set([r['salesperson_id'] for r in results if r['salesperson_id']]))
            # _logger.info("--------------------------------salesperson_ids")
            # _logger.info(salesperson_ids)
            # _logger.info("--------------------------------salesperson_ids")
            # _logger.info(user.id)
            my_domain = [
                '|', '|', '|',
                ('wing_id', '=', wing_id),
                ('team_id', 'in', team_ids),
                ('supervisor_id', 'in', supervisor_ids),
                ('salesperson_ids', '=', user.id)
            ]
        
        else:
            # Check team manager
            self.env.cr.execute("""
                SELECT id FROM property_sales_team 
                WHERE manager_id = %s LIMIT 1
            """, (user.id,))
            team_result = self.env.cr.fetchone()
            
            if team_result:
                # _logger.info("User is Team Manager")
                team_id = team_result[0]
                
                # Get all supervisors and salespersons under this team
                self.env.cr.execute("""
                    SELECT DISTINCT 
                        s.id as supervisor_id,
                        s.name as supervisor_user_id,
                        pm.user_id as salesperson_id
                    FROM property_sales_team t
                    LEFT JOIN property_team_supervisor_rel ts ON t.id = ts.team_id
                    LEFT JOIN property_sales_supervisor s ON s.id = ts.supervisor_id
                    LEFT JOIN property_salesperson_mapping pm ON pm.supervisor_id = s.id
                    WHERE t.id = %s
                """, (team_id,))
                results = self.env.cr.dictfetchall()
                
                supervisor_ids = list(set([r['supervisor_id'] for r in results if r['supervisor_id']]))
                salesperson_ids = list(set([r['salesperson_id'] for r in results if r['salesperson_id']]))
                
                my_domain = [
                    '|', '|',
                    ('team_id', '=', team_id),
                    ('supervisor_id', 'in', supervisor_ids),
                    ('salesperson_ids', '=', user.id)
                ]
                
            else:
    
                # Check supervisor
                self.env.cr.execute("""
                    SELECT id FROM property_sales_supervisor 
                    WHERE name = %s LIMIT 1
                """, (user.id,))
                supervisor_id = self.env.cr.fetchone()
                
                if supervisor_id:
                    _logger.info("User is Supervisor")
                    supervisor_id = supervisor_id[0]
                    
                    # Get all salespersons under this supervisor
                    self.env.cr.execute("""
                        SELECT user_id 
                        FROM property_salesperson_mapping 
                        WHERE supervisor_id = %s
                    """, (supervisor_id,))
                    salesperson_ids = [r[0] for r in self.env.cr.fetchall()]
                    
                    my_domain = [
                        '|',
                        ('salesperson_ids', 'in', salesperson_ids),
                        ('supervisor_id', '=', user.id)
                    ]
                    
                else:
                    _logger.info("User is Salesperson")
                    my_domain = [('salesperson_ids', '=', user.id)]
        
        # Combine with existing domain
        if domain:
            domain = expression.AND([domain, my_domain])
        else:
            domain = my_domain
            
        _logger.info(f"Final domain: {domain}")
        return super()._search(domain, offset=offset, limit=limit, order=order)

    def sale_property_reserved(self):
        """Convert reservation to sale."""
        if self.property_id.is_multi:
            payment_term_id =self.property_id.site_payment_structure_id.payment_term_id.id
        else:
            payment_term_id = self.property_id.payment_structure_id.id
        self.ensure_one()
        sale = self.env['property.sale'].create({
            'property_id': self.property_id.id,
            'partner_id': self.partner_id.id,
            'property_payment_term': payment_term_id,
            'reservation_id': self.id,
            'sales_person': self.salesperson_ids.id,
        })
        
        self.sudo().write({'status': 'pending_sales'})
        self.property_id.sudo().write({'state': 'pending_sales'})
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale',
            'res_model': 'property.sale',
            'view_mode': 'form',
            'target': 'current',
            'res_id': sale.id,
        }

    # @api.depends('salesperson_ids')
    # def _compute_sales_structure(self):
    #     for record in self:
    #         # Find the mapping for the current salesperson
    #         mapping = self.env['property.salesperson.mapping'].search([('user_id', '=', record.salesperson_ids.id)], limit=1)
    #         if mapping:
    #             record.supervisor_id = mapping.supervisor_id
    #         else:
    #             record.supervisor_id = False
            
    #         # Find the team associated with the supervisor
    #         team = self.env['property.sales.team'].search([('supervisor_ids', 'in', record.supervisor_id.id)], limit=1)
    #         if team:
    #             record.team_id = team
    #         else:
    #             record.team_id = False
            
    #         # Find the wing associated with the team
    #         wing = self.env['property.sales.wing'].search([('team_ids', 'in', team.id if team else [])], limit=1)
    #         record.wing_id = wing if wing else False



    def _get_period_start_date(self, period):
        """Get start date for the specified period"""
        today = fields.Date.today()
        if period == 'daily':
            return fields.Datetime.now().replace(hour=0, minute=0, second=0)
        elif period == 'weekly':
            return fields.Datetime.now() - timedelta(days=today.weekday())
        elif period == 'monthly':
            return fields.Datetime.now().replace(day=1, hour=0, minute=0, second=0)
        elif period == 'quarterly':
            quarter_start_month = ((today.month - 1) // 3) * 3 + 1
            return fields.Datetime.now().replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0)
        elif period == 'yearly':
            return fields.Datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0)
    
    def _check_operation_limit(self, operation_type):
        """
        Check if operation (cancel/transfer/extension) is allowed based on configuration limits
        :param operation_type: str ('cancel', 'transfer', 'extend')
        :return: bool
        """
        # self.ensure_one()
        config = self.reservation_type_id
        user = self.env.user

        # Map operation type to configuration fields
        operation_map = {
            'canceled': {
                'max_field': 'max_cancellations',
                'period_field': 'cancellation_period',
                'penalty_field': 'cancellation_penalty_days',
                'status': 'canceled',
                'error_message': _('cancellation'),
            },
            'transfer': {
                'max_field': 'max_transfers',
                'period_field': 'transfer_period',
                'penalty_field': 'transfer_penalty_days',
                'status': 'transferred',
                'error_message': _('transfer'),
            },
            'extend': {
                'max_field': 'max_extensions',
                'period_field': 'extension_period',
                'penalty_field': 'extension_penalty_days',
                'status': 'extended',
                'error_message': _('extension'),
            }
        }

        op_config = operation_map[operation_type]
        max_operations = getattr(config, op_config['max_field'])
        check_period = getattr(config, op_config['period_field'])
        penalty_days = getattr(config, op_config['penalty_field'])
        # _logger.info(f"Checking {operation_type} limit for {user.name}")
        # _logger.info(f"Max operations: {max_operations}")
        # _logger.info(f"Check period: {check_period}")
        # _logger.info(f"Penalty days: {penalty_days}")
        if not max_operations:
            return True

        # Get period start date
        period_start = self._get_period_start_date(check_period)
        # _logger.info(f"Period start: {period_start}")
        # Count operations in period
        operation_count = self.search_count([
            ('create_uid', '=', user.id),
            ('status', '=', op_config['status']),
            ('write_date', '>=', period_start)
        ])
        # _logger.info(f"Operation count: {operation_count}")
        if operation_count >= max_operations:
                # Check if user is in penalty period
                last_operation = self.search([
                    ('create_uid', '=', user.id),
                    ('status', '=', op_config['status']),
                    ('write_date', '>=', period_start)
                ], order='write_date desc', limit=1)

                if last_operation:
                    penalty_end = last_operation.write_date + timedelta(days=penalty_days)
                    if fields.Datetime.now() < penalty_end:
                        if operation_type == 'canceled':
                            operation_type = 'Reservation Cancellation or creation'
                        raise ValidationError(_(
                            'You have exceeded the maximum number of {operation_type}s allowed for this period. '
                            'You cannot perform any {operation_type}s until {date}'
                        ).format(
                            operation_type=op_config['error_message'],
                            date=penalty_end.strftime('%Y-%m-%d')
                        ))
                
                raise ValidationError(_(
                    'You have reached the maximum number of {operation_type}s allowed for this {period}'
                ).format(
                    operation_type=op_config['error_message'],
                    period=check_period
                ))

        return True
    
    def cancel_reservation(self):
        """Open cancellation wizard after checking limits"""
        self.ensure_one()
        
        # Check cancellation limits before opening wizard
        try:
            self._check_operation_limit('canceled')
        except ValidationError as e:
            # If limit exceeded, show error message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Cancellation Limit Exceeded'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        _logger.info(f"Opening cancellation wizard for {self.status}")
        return super(PropertyReservation, self).cancel_reservation()
    
    def create(self, vals):
        """Create reservation and update CRM stage"""

        # _logger.info("--@@@@@@@@@@@@@@---%%%%%%%%%%%%%%%-----**************----------------------vals")
        property_id = vals.get('property_id')
        # _logger.info("----------**************----------------------property_id")
        # _logger.info(vals)
        # _logger.info(property_id)
        property_reservation_configuration = self.env['property.reservation.configuration'].search([('id', '=', vals.get('reservation_type_id'))], limit=1)
        # _logger.info("----------**************------------------NAME----property_reservation_configuration")
        # _logger.info(property_reservation_configuration)
        # _logger.info(property_reservation_configuration.reservation_type)
        if property_reservation_configuration.reservation_type == 'quick':
            number_of_allowed_quick_reservation  = property_reservation_configuration.number_of_allowed_quick_reservation
            # _logger.info(number_of_allowed_quick_reservation)
            if number_of_allowed_quick_reservation:
                uid = self.env.user.id
                
                search_quick_reservation = self.env['property.reservation'].search([('reservation_type_id', '=', property_reservation_configuration.id),('property_id', '=', property_id),
                                                                                    ('salesperson_ids', '=', uid),('create_date', '>=', fields.Date.context_today(self))])
                # _logger.info("----------**************----------------------search_quick_reservation")
                # _logger.info(search_quick_reservation)
                if len(search_quick_reservation) >= number_of_allowed_quick_reservation:
                    raise ValidationError(_('You have reached the maximum number of quick reservations allowed for this property'))


        
        # Get values from context if not in vals
        if not vals.get('partner_id') and self._context.get('default_partner_id'):
            vals['partner_id'] = self._context.get('default_partner_id')
        
        if not vals.get('salesperson_ids') and self._context.get('default_salesperson_ids'):
            vals['salesperson_ids'] = self._context.get('default_salesperson_ids')
        
        if not vals.get('crm_lead_id') and self._context.get('default_crm_lead_id'):
            vals['crm_lead_id'] = self._context.get('default_crm_lead_id')

        # Hierarchy logic to determine supervisor_id, team_id, and wing_id
        mapping = self.env['property.salesperson.mapping'].search([('user_id', '=', vals.get('salesperson_ids'))], limit=1)
        # _logger.info("----------**************----------------------mapping")
        # _logger.info(mapping)
        if mapping:
            supervisor_id = mapping.supervisor_id
            vals['supervisor_id'] = supervisor_id.id if supervisor_id else False
            
            # Find the team associated with the supervisor
            team = self.env['property.sales.team'].search([('supervisor_ids', 'in', supervisor_id.id)], limit=1)
            vals['team_id'] = team.id if team else False
            
            # Find the wing associated with the team
            wing = self.env['property.sales.wing'].search([('team_ids', 'in', vals['team_id'])], limit=1)
            vals['wing_id'] = wing.id if wing else False
        else:
            # If no mapping found, search for the salesperson as a supervisor
            supervisor = self.env['property.sales.supervisor'].search([('name', '=', vals.get('salesperson_ids'))], limit=1)
            # _logger.info("--------------------------------supervisor")
            # _logger.info(supervisor)
            if supervisor:
                supervisor_id = supervisor.id
                vals['supervisor_id'] = supervisor_id
                
                # Find the team associated with the supervisor
                team = self.env['property.sales.team'].search([('supervisor_ids', 'in', supervisor_id)], limit=1)
                vals['team_id'] = team.id if team else False
                
                # Find the wing associated with the team
                wing = self.env['property.sales.wing'].search([('team_ids', 'in', vals['team_id'])], limit=1)
                vals['wing_id'] = wing.id if wing else False
            else:
                # If no supervisor found, search for the salesperson as a team manager
                team_manager = self.env['property.sales.team'].search([('manager_id', '=', vals.get('salesperson_ids'))], limit=1)
                # _logger.info("--------------------------------team_manager")
                # _logger.info(team_manager)
                # _logger.info("--------------------------------team_manager")
                # _logger.info(team_manager.id)
                

                wing = self.env['property.sales.wing'].search([('team_ids', 'in',team_manager.id)], limit=1)
                # _logger.info("--------------------------------wing")
                # _logger.info(wing)
                vals['wing_id'] = wing.id if wing else False
                if team_manager:
                    vals['supervisor_id'] = False  # No supervisor_id since it's a team manager
                    vals['team_id'] = team_manager.id  # Directly assign team_id from team manager
                    vals['wing_id'] = wing.id  # No wing search if it's a team manager
                else:
                    vals['supervisor_id'] = False
                    vals['team_id'] = False
                    vals['wing_id'] = False

        # _logger.info("--------------------------------vals")
        # _logger.info(vals)
        # Call the super method to create the record
        rec = super(PropertyReservation, self).create(vals)
        
        if vals.get('crm_lead_id'):
            stage_id = self.env['crm.stage'].search([('is_reservation_stage', '=', True)], limit=1).id
            self.env['crm.lead'].browse(vals['crm_lead_id']).write({'stage_id': stage_id})
        
        return rec
    
    def update_existing_reservations(self):
        """Method to update existing reservations with sales hierarchy"""
        reservations = self.env['property.reservation'].search([
            ('salesperson_ids', '!=', False),
            '|', '|', 
            ('supervisor_id', '=', False),
            ('team_id', '=', False),
            ('wing_id', '=', False)
        ])
        
        updated_count = 0
        for reservation in reservations:
            reservation._compute_sales_structure()
            updated_count += 1
            
            # Commit every 100 records to avoid memory issues
            if updated_count % 100 == 0:
                self.env.cr.commit()
                _logger.info(f"Updated {updated_count} reservations...")
        
        _logger.info(f"Completed updating {updated_count} reservations")
        return True