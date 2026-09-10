from odoo import models, fields, api, _

class SupportReportWizard(models.TransientModel):
    _name = 'support.report.wizard'
    _description = 'Task Report Wizard'

    support_id = fields.Many2one('support.management', string='Support Job', required=True)
    work_update = fields.Text(string='Work Update')
    achievement_ids = fields.One2many('support.report.achievement', 'wizard_id', string='Main Achievements')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        support_id = self._context.get('default_support_id')
        if support_id and 'achievement_ids' in fields_list:
            achievements = self.env['support.management.achievement'].search([
                ('support_id', '=', support_id)
            ], order='sequence, id')
            res['achievement_ids'] = [
                (0, 0, {'text': a.text, 'sequence': a.sequence})
                for a in achievements
            ]
        return res

    def action_confirm(self):
        self.ensure_one()
        # Write work update to the job order
        self.support_id.write({'work_update': self.work_update})
        # Replace all achievements on the job with the wizard's current list
        self.env['support.management.achievement'].search([
            ('support_id', '=', self.support_id.id)
        ]).unlink()
        for idx, ach in enumerate(self.achievement_ids):
            if ach.text:
                self.env['support.management.achievement'].create({
                    'support_id': self.support_id.id,
                    'text': ach.text,
                    'sequence': idx * 10,
                })
        return {'type': 'ir.actions.act_window_close'}


class SupportReportAchievement(models.TransientModel):
    _name = 'support.report.achievement'
    _description = 'Task Report Achievement Line (Wizard)'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('support.report.wizard', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    text = fields.Char(string='Achievement', required=True)


