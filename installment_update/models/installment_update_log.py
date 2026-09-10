from odoo import models, fields, api

class InstallmentUpdateLog(models.Model):
    _name = 'installment.update.log'
    _description = 'Installment Substitution Log'
    _order = 'substitution_date desc, id desc'
    _rec_name = 'site_id'

    site_id = fields.Many2one(
        'property.site',
        string='Site / Project',
        required=True,
        ondelete='restrict',
        index=True,
    )
    old_installment = fields.Char(
        string='Old Installment',
        required=True,
        trim=False,
    )
    new_installment = fields.Char(
        string='New Installment',
        required=True,
        trim=False,
    )
    substitution_date = fields.Datetime(
        string='Date & Time',
        required=True,
        default=fields.Datetime.now,
    )
    performed_by = fields.Many2one(
        'res.users',
        string='Performed By',
        required=True,
        default=lambda self: self.env.user,
        ondelete='restrict',
    )
    collection_count = fields.Integer(string='Collection Installments Updated')
    sale_line_count = fields.Integer(string='Property Sale Lines Updated')
    legacy_line_count = fields.Integer(string='Legacy Sale Lines Updated')
    collection_installment_id = fields.Many2one(
        'collection.installment',
        string='Collection Installment',
        compute='_compute_collection_installment_id',
        store=False,
    )

    @api.depends('site_id', 'old_installment')
    def _compute_collection_installment_id(self):
        for rec in self:
            if rec.site_id and rec.old_installment:
                installment = self.env['collection.installment'].search([
                    ('collection_id.site_id', '=', rec.site_id.id),
                    ('name', '=', rec.old_installment),
                ], limit=1)
                rec.collection_installment_id = installment.id
            else:
                rec.collection_installment_id = False
