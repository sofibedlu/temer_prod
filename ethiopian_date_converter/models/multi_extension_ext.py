from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..utils.converter import to_ethiopian, to_gregorian


class PropertyPaymentExtensionWizardLine(models.TransientModel):
    _inherit = 'property.payment.extension.wizard.line'

    new_date_eth = fields.Char(
        string="New Date (E.C)", 
        compute='_compute_new_date_eth', 
        store=True, 
        readonly=False
    )

    @api.depends('new_date')
    def _compute_new_date_eth(self):
        for rec in self:
            if rec.new_date:
                rec.new_date_eth = to_ethiopian(rec.new_date)
            else:
                rec.new_date_eth = False

    @api.onchange('new_date_eth')
    def _onchange_new_date_eth(self):
        for rec in self:
            if rec.new_date_eth:
                try:
                    rec.new_date = to_gregorian(rec.new_date_eth)
                except UserError as e:
                    return {
                        'warning': {
                            'title': _('Invalid Format'),
                            'message': str(e)
                        }
                    }
            else:
                rec.new_date = False


class CollectionPaymentExtensionRequestLine(models.Model):
    _inherit = 'collection.payment.extension.request.line'

    new_date_eth = fields.Char(
        string="Requested Date (E.C)", 
        compute='_compute_new_date_eth', 
        store=True, 
        readonly=False
    )

    @api.depends('new_date')
    def _compute_new_date_eth(self):
        for rec in self:
            if rec.new_date:
                rec.new_date_eth = to_ethiopian(rec.new_date)
            else:
                rec.new_date_eth = False

    @api.onchange('new_date_eth')
    def _onchange_new_date_eth(self):
        for rec in self:
            if rec.new_date_eth:
                try:
                    rec.new_date = to_gregorian(rec.new_date_eth)
                except UserError as e:
                    return {
                        'warning': {
                            'title': _('Invalid Format'),
                            'message': str(e)
                        }
                    }
            else:
                rec.new_date = False


class CollectionPaymentExtensionRequest(models.Model):
    _inherit = 'collection.payment.extension.request'

    new_date_eth = fields.Char(
        string="Requested Date (E.C)", 
        compute='_compute_new_date_eth', 
        store=True, 
        readonly=False
    )

    @api.depends('new_date')
    def _compute_new_date_eth(self):
        for rec in self:
            if rec.new_date:
                rec.new_date_eth = to_ethiopian(rec.new_date)
            else:
                rec.new_date_eth = False

    @api.onchange('new_date_eth')
    def _onchange_new_date_eth(self):
        for rec in self:
            if rec.new_date_eth:
                try:
                    rec.new_date = to_gregorian(rec.new_date_eth)
                except UserError as e:
                    return {
                        'warning': {
                            'title': _('Invalid Format'),
                            'message': str(e)
                        }
                    }
            else:
                rec.new_date = False


class PropertyPaymentExtensionWizard(models.TransientModel):
    _inherit = 'property.payment.extension.wizard'

    new_date_eth = fields.Char(
        string="New Extended Date (E.C)", 
        compute='_compute_new_date_eth', 
        store=True, 
        readonly=False
    )

    @api.depends('new_date')
    def _compute_new_date_eth(self):
        for rec in self:
            if rec.new_date:
                rec.new_date_eth = to_ethiopian(rec.new_date)
            else:
                rec.new_date_eth = False

    @api.onchange('new_date_eth')
    def _onchange_new_date_eth(self):
        for rec in self:
            if rec.new_date_eth:
                try:
                    rec.new_date = to_gregorian(rec.new_date_eth)
                except UserError as e:
                    return {
                        'warning': {
                            'title': _('Invalid Format'),
                            'message': str(e)
                        }
                    }
            else:
                rec.new_date = False