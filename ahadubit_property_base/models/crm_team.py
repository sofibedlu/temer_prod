# -*- coding: utf-8 -*-
##############################################################################
#
#    Ahadubit Technologies
#    Copyright (C) 2024-TODAY Ahadubit Technologies(<https://ahadubit.com>).
#    Author: Ahadubit Technologies (<https://ahadubit.com>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)



class CrmTeam(models.Model):
    _inherit = "crm.team"


    
    user_id = fields.Many2one('res.users', string='Supervisor', check_company=True)
    manager = fields.Many2one('res.users')

class CrmTeamMember(models.Model):
    _inherit = "crm.team.member"
    

    @api.model_create_multi
    def create(self, vals_list):
        res = super(CrmTeamMember, self).create(vals_list)
        # _logger.info('vals_list')
        # _logger.info(vals_list)
        # _logger.info(res)
        for vals in vals_list:
            partner_id = self.env['res.users'].search([('id', '=', vals['user_id'])]).partner_id
            # _logger.info('partner_id')
            # _logger.info(partner_id)
            # partner = self.env['res.partner'].search([('id', '=', partner_id.id)])
            # for pr in partner:
            #     pr.write({'crm_team':vals['crm_team_id']})
            partner_id.sudo().write({'crm_team':vals['crm_team_id']})
        return res
