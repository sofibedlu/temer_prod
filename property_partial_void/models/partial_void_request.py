from odoo import models, fields, api, _
from odoo.exceptions import UserError
from markupsafe import Markup
import logging
import re

_logger = logging.getLogger(__name__)

class PartialVoidRequest(models.Model):
    _name = 'partial.void.request'
    _description = 'Partial Void Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    collection_id = fields.Many2one('collection.order', string="Collection Order", required=True, readonly=True)
    sale_id = fields.Many2one('property.sale', related='collection_id.sale_id', string="Contract", store=True)
    parent_property_id = fields.Many2one('property.property', related='sale_id.property_id', string="Merged Property", store=True)
    
    reason = fields.Text(string='Reason for Partial Void', required=True, tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('checked', 'Checked'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many('partial.void.request.line', 'request_id', string='Units to Drop')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('partial.void.request') or _('New')
        return super().create(vals_list)

    def action_check(self):
        self.write({'state': 'checked'})

    def _build_merge_reference(self, prop, merged_unit):
        """ Replicates the exact string builder from the Property Merge Wizard """
        if not prop or not prop.site or not merged_unit:
            return ""

        clean_site = re.sub(r"[^A-Za-z0-9]", "", (prop.site.name or "").strip())
        site_code = clean_site[:3].upper() if clean_site else ""
        if not site_code:
            return ""

        owner_code = ""
        if hasattr(prop.site, "company_id") and prop.site.company_id:
            company = prop.site.company_id
            if getattr(company, "abbreviation", False) and company.abbreviation.strip():
                owner_code = re.sub(r"[^A-Za-z0-9]", "", company.abbreviation.strip().upper())
            elif getattr(company, "name", False):
                owner_code = re.sub(r"[^A-Za-z0-9]", "", company.name.strip())[:3].upper()

        project_no = ""
        if hasattr(prop.site, "project_number") and prop.site.project_number:
            project_no = str(prop.site.project_number).strip()

        block_no = ""
        if prop.block and getattr(prop.block, "name", False):
            block_str = str(prop.block.name).strip()
            block_no = block_str.zfill(2) if block_str.isdigit() else block_str.upper()

        floor_no = ""
        if prop.floor_id and prop.floor_id.name is not None:
            floor_no = "F%s" % prop.floor_id.name

        ref_parts = [site_code]
        if owner_code:
            ref_parts.append("-%s" % owner_code)
            if project_no:
                ref_parts.append(project_no)
        if block_no or floor_no:
            ref_parts.append("/%s" % "/".join(part for part in (block_no, floor_no) if part))
        ref_parts.append("-%s" % merged_unit)
        return "".join(ref_parts)

    def action_approve(self):
        for req in self:
            parent_prop = req.parent_property_id
            dropped_child_ids = req.line_ids.mapped('child_property_id').exists()
            
            if not parent_prop or not dropped_child_ids:
                continue

            all_children = self.env['child.property'].search([('parent_property_id', '=', parent_prop.id)])
            remaining_children = all_children - dropped_child_ids

            if not remaining_children:
                raise UserError(_("You are attempting to drop ALL units. Please use the standard Full Void workflow instead."))

            restored_names = []
            
            # 1. RESTORE DROPPED PROPERTIES
            for child in dropped_child_ids:
                restore_vals = {
                    'name': child.name,
                    'site': child.site_id.id,
                    'block': child.block_id.id,
                    'floor_id': child.floor_id.id,
                    'site_property_type_id': child.site_property_type_id.id,
                    'property_type_id': child.property_type_id.id,
                    'property_type': child.property_kind,
                    'unit_number': child.unit_number,
                    'payment_structure_id': child.payment_structure_id.id,
                    'site_payment_structure_id': child.site_payment_structure_id.id,
                    'commercial_location': child.commercial_location,
                    'finishing': child.finishing,
                    'furnishing': child.furnishing,
                    'responsible_id': parent_prop.responsible_id.id,
                    'landlord_id': parent_prop.landlord_id.id,
                    'company_id': parent_prop.company_id.id,
                    'currency_id': parent_prop.currency_id.id,
                    'country_id': parent_prop.country_id.id,
                    'state_id': parent_prop.state_id.id,
                    'city': parent_prop.city,
                    'street': parent_prop.street,
                }

                new_prop = self.env['property.property'].sudo().create(restore_vals)
                
                force_vals = {
                    'state': 'available',
                    'gross_area': child.gross_area,
                    'net_area': child.net_area,
                    'bedroom': child.bedroom,
                    'bathroom': child.bathroom,
                    'commercial_amount': child.commercial_amount,
                    'rate_per_m2': child.rate_per_m2,
                    'price': child.price,
                    'override_price_m2': child.price,
                    'unit_price': child.unit_price,
                    'rent_month': child.rent_month,
                    'manual_unit_price': child.unit_price,
                    'use_manual_sale_price': True,
                    'computed_reference': child.computed_reference, 
                }
                
                new_prop.with_context(skip_reference_recompute=True).sudo().write(force_vals)
                restored_names.append(new_prop.name)
                child.unlink()

            # 2. RECALCULATE PARENT PROPERTY
            new_unit_number = " & ".join([str(c.unit_number or '') for c in remaining_children])
            new_name = "%s-%s-F%s-%s" % (
                parent_prop.site.name if parent_prop.site else '', 
                parent_prop.block.name if parent_prop.block else '', 
                parent_prop.floor_id.name if parent_prop.floor_id else '', 
                new_unit_number
            )

            new_gross = sum(remaining_children.mapped('gross_area'))
            new_net = sum(remaining_children.mapped('net_area'))
            new_bed = sum(remaining_children.mapped('bedroom'))
            new_bath = sum(remaining_children.mapped('bathroom'))
            new_commercial = sum(remaining_children.mapped('commercial_amount'))
            new_unit_price = sum(remaining_children.mapped('unit_price'))
            new_price_m2 = (new_unit_price / new_gross) if new_gross else 0.0
            
            new_merge_reference = self._build_merge_reference(parent_prop, new_unit_number)


            if parent_prop.property_type_id:
                parent_prop.property_type_id.sudo().write({
                    'code': new_unit_number,
                    'gross_area': new_gross,
                    'net_area': new_net,
                    'number_be_room': new_bed,
                    'number_bath_room': new_bath,
                })

            parent_write_vals = {
                'name': new_name,
                'unit_number': new_unit_number,
                'computed_reference': new_merge_reference,
                'gross_area': new_gross,
                'net_area': new_net,
                'bedroom': new_bed,
                'bathroom': new_bath,
                'commercial_amount': new_commercial,
                'unit_price': new_unit_price,
                'rent_month': sum(remaining_children.mapped('rent_month')),
                'price': new_price_m2,
                'override_price_m2': new_price_m2, 
                'manual_unit_price': new_unit_price,
                'use_manual_sale_price': True,
            }

            # Push the shadow fields used by the original merge wizard so they are kept in sync
            if "property_type_gross_area" in parent_prop._fields:
                parent_write_vals["property_type_gross_area"] = new_gross
            if "property_type_net_area" in parent_prop._fields:
                parent_write_vals["property_type_net_area"] = new_net
            if "property_type_bedroom" in parent_prop._fields:
                parent_write_vals["property_type_bedroom"] = new_bed
            if "property_type_bathroom" in parent_prop._fields:
                parent_write_vals["property_type_bathroom"] = new_bath

            parent_prop.with_context(skip_reference_recompute=True).sudo().write(parent_write_vals)

            # 3. Log actions
            msg = Markup(
                f"<b>Partial Void Approved:</b><br/>"
                f"Dropped Units: {', '.join(restored_names)}<br/>"
                f"These units have been restored to inventory as Available.<br/>"
                f"<i>Note: Contract financials must be adjusted manually via Amendment.</i>"
            )
            req.collection_id.message_post(body=msg)
            req.sale_id.message_post(body=msg)
            parent_prop.message_post(body=msg)

            req.write({'state': 'approved'})

    def action_reject(self):
        self.ensure_one()
        return {
            'name': _('Reject Partial Void Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'partial.void.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id}
        }

class PartialVoidRequestLine(models.Model):
    _name = 'partial.void.request.line'
    _description = 'Partial Void Request Line'

    request_id = fields.Many2one('partial.void.request', ondelete='cascade')
    child_property_id = fields.Many2one('child.property', string="Unit to Drop", ondelete='set null')
    
    unit_name = fields.Char(string="Unit Name")
    unit_number = fields.Char(string="House Number")
    gross_area = fields.Float(string="Gross Area")
    unit_price = fields.Monetary(string="Price")
    currency_id = fields.Many2one('res.currency')