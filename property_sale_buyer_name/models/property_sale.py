from odoo import models, fields, api

class PropertySale(models.Model):
    _inherit = 'property.sale'

    buyers_name = fields.Html(
        string='Buyers Name',
        compute='_compute_buyers_name',
        store=True,
        help="List of all buyers from the contract application."
    )

    buyers_name_text = fields.Char(
        string='Buyers Name (Text)',
        compute='_compute_buyers_name',
        store=True,
        help="Plain text list of buyers for searching and grouping."
    )

    @api.depends(
        'contract_id.person_ids.first_name',
        'contract_id.person_ids.father_name',
        'contract_id.person_ids.gfather_name',
        'contract_id.person_ids.person_type'
    )
    def _compute_buyers_name(self):
        for sale in self:
            buyers = sale.contract_id.mapped('person_ids').filtered(lambda p: p.person_type == 'buyers')
            
            names = []
            for buyer in buyers:
                name_parts = [buyer.first_name, buyer.father_name, buyer.gfather_name]
                full_name = " ".join([str(n).strip() for n in name_parts if n and str(n).strip()])
                if full_name:
                    names.append(full_name)
            
            if not names:
                sale.buyers_name = "<p class='text-muted'>No buyers found.</p>"
                sale.buyers_name_text = "No buyers found"
            else:
                list_items = "".join([f"<li><i class='fa fa-user text-primary'></i>&nbsp;&nbsp;{name}</li>" for name in names])
                sale.buyers_name = f"<ul class='list-unstyled mb-0' style='margin-left: 0; padding-left: 0;'>{list_items}</ul>"
                sale.buyers_name_text = ", ".join(names)


class CollectionOrder(models.Model):
    _inherit = 'collection.order'

    buyers_name = fields.Html(
        related='sale_id.buyers_name', 
        string='Buyers Name', 
        readonly=True
    )

    buyers_name_text = fields.Char(
        related='sale_id.buyers_name_text', 
        string='Buyers Name (Text)', 
        store=True
    )