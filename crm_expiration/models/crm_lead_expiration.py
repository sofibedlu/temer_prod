from odoo import models, api, fields
from datetime import datetime, timedelta
from lxml import etree
import logging

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def make_expire_lead_acton(self, batch_size=1000):
        _logger.info("==== Running expire_lead_acton ====")
        Param = self.env['ir.config_parameter'].sudo()
        duration_in = Param.get_param('ahadubit_property_base.custom_expiration_duration_in')
        duration = int(Param.get_param('ahadubit_property_base.custom_expiration_duration', default=0))

        if not (duration_in and duration):
            _logger.warning("Expiration duration configuration is missing.")
            return

        if duration_in == 'minutes':
            target_date = datetime.now() - timedelta(minutes=duration)
        elif duration_in == 'hours':
            target_date = datetime.now() - timedelta(hours=duration)
        elif duration_in == 'days':
            target_date = datetime.now() - timedelta(days=duration)
        elif duration_in == 'months':
            target_date = datetime.now() - timedelta(days=duration * 30)
        elif duration_in == 'years':
            target_date = datetime.now() - timedelta(days=duration * 365)
        else:
            target_date = datetime.now()

        won_stage_ids = self.env['crm.stage'].search([('is_won', '=', True)]).ids
        lost_stage_ids = self.env['crm.stage'].search([('is_lost_stage', '=', True)]).ids
        reservation_stage = self.env['crm.stage'].search([('is_reservation_stage', '=', True)], limit=1)
        reservation_stage_id = reservation_stage.id if reservation_stage else False

        domain = [
            ('write_date', '<', target_date),
            ('is_expired', '!=', True),
            ('stage_id', 'not in', won_stage_ids + lost_stage_ids + ([reservation_stage_id] if reservation_stage_id else []))
        ]

        leads = self.env['crm.lead'].search(domain, order='id ASC', limit=batch_size)

        _logger.info(f"Processing {len(leads)} leads.")

        for idx, lead in enumerate(leads, 1):
            try:
                with self.env.cr.savepoint():
                    if lead.is_reserved:
                        _logger.info(f"Lead {lead.id} reserved; skipped.")
                        continue
                    lead.write({'is_expired': True})
                    lead.custom_action_set_leads2_expired()

                    other_leads = self.env['crm.lead'].search([
                        ('id', '!=', lead.id),
                        ('partner_id', '=', lead.partner_id.id),
                        ('is_expired', '!=', True)
                    ])
                    if not other_leads:
                        lead.partner_id.write({'is_expired': True})

                if idx % 50 == 0:
                    self.env.cr.commit()
                    _logger.info(f"Committed after processing {idx} leads.")

            except Exception as e:
                _logger.error(f"Failed processing lead {lead.id}: {e}")

        self.env.cr.commit()
        _logger.info(f"==== Batch completed: {len(leads)} leads processed. ====")



    def custom_action_set_leads2_expired(self):
        lost_stage = self.env['crm.stage'].search([('is_expire_stage', '=', True)], limit=1)
        if not lost_stage:
            _logger.warning("No 'expired' CRM stage found (is_expire_stage=True). Cannot move lead(s) to expired stage.")
            return
        for rec in self:
            rec.stage_id = lost_stage.id
            _logger.info(f"Lead {rec.id} set to expired stage {lost_stage.name} ({lost_stage.id})")


    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super().fields_get(allfields=allfields, attributes=attributes)
        sources = self.env['utm.source'].search([('name', 'in', ['6033', 'Walk In', 'Website'])])
        if sources and 'source_id' in result:
            excluded_ids = [src.id for src in sources]
            result['source_id']['domain'] = "[('id', 'not in', %s)]" % excluded_ids
        return result