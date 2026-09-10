from odoo import models, fields, api
import re
from markupsafe import Markup


class LetterBody(models.Model):
    _name = 'letter.body'
    _description = 'Letter Body'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'sequence, name'

    name = fields.Char(string='Body Name', required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True, tracking=True)

    # ── Model binding ─────────────────────────────────────────────────────────
    # Bound to collection.installment so the HTML editor can offer
    # dynamic_placeholder suggestions for that model's fields.
    model_id = fields.Many2one(
        'ir.model',
        string='Applies To',
        default=lambda self: self.env['ir.model']._get_id('collection.installment'),
    )
    model = fields.Char(
        related='model_id.model',
        string='Model Technical Name',
        readonly=True,
        store=True,
    )

    # ── Content ───────────────────────────────────────────────────────────────
    subject = fields.Char(string='Subject / Title')
    is_dynamic = fields.Boolean(
        string='Dynamic Content',
        default=True,
        help="When enabled, ${placeholder} expressions are resolved at render time.",
    )
    body_html = fields.Html(
        string='Body Content',
        sanitize=False,
        help="Use ${field_name} placeholders for dynamic values.",
    )

    # ── Categorisation ────────────────────────────────────────────────────────
    notes = fields.Text(string='Internal Notes')

    # ── Back-reference to templates that use this body ────────────────────────
    template_ids = fields.Many2many(
        'letter.template',
        'letter_template_body_rel',
        'body_id',
        'template_id',
        string='Used in Templates',
        readonly=True,
    )

    # ── Render ────────────────────────────────────────────────────────────────
    def render_body(self, record=None, extra_values=None):
        """
        Render body_html by substituting ${key} placeholders.
        extra_values: dict of additional keys (e.g. letter_date, letter_number)
        that override / extend the standard placeholder set.
        Returns a Markup-safe string.
        """
        self.ensure_one()
        if not self.body_html:
            return Markup('')
        if not self.is_dynamic:
            return Markup(self.body_html)

        values = self._prepare_placeholder_values(record, extra_values)

        # ── Special: ${sender{ text }} → right-aligned sender block ──────────
        # Syntax: ${sender{ ከሰላምታ ጋር\nአህመድ ነስሩ\nየኮሌክሽን ክፍል ስራ አስኪያጅ }}
        # Renders as a block on the RIGHT side of the page.
        # Uses a full-width table with a right-aligned cell — works reliably
        # in wkhtmltopdf (flexbox is NOT supported in wkhtmltopdf 0.12.x).
        # padding:0 !important overrides the global td { padding: 4px 6px } rule.
        def sender_replacer(m):
            raw = m.group(1).strip()
            # Split on newlines or \n literal
            lines = [l.strip() for l in re.split(r'\n|\\n', raw) if l.strip()]
            lines_html = ''.join(
                f'<div style="text-align:right; line-height:1.8;">{line}</div>'
                for line in lines
            )
            return (
                '<table style="width:100%; border-collapse:collapse; margin-top:24px; margin-bottom:8px;">'
                '<tr>'
                '<td style="text-align:right !important; vertical-align:top; padding:0 !important; border:none;">'
                + lines_html +
                '</td>'
                '</tr>'
                '</table>'
            )

        rendered = re.sub(
            r'\$\{\s*sender\s*\{([^}]*(?:\}[^}]*)*?)\}\s*\}',
            sender_replacer,
            self.body_html,
            flags=re.DOTALL,
        )

        def replacer(match):
            key = match.group(1).strip()
            value = values.get(key)
            if value is None:
                return '—'
            if isinstance(value, (int, float)):
                return f"{value:,.2f}" if value % 1 else f"{int(value):,}"
            return str(value) if value else '—'

        rendered = re.sub(r'\$\{\s*([a-zA-Z0-9_.]+)\s*\}', replacer, rendered)
        return Markup(rendered)

    def _prepare_placeholder_values(self, record=None, extra_values=None):
        """
        Build the placeholder dict from a collection.installment record.

        Available placeholders:
          ${partner_name}            — customer name
          ${property_name}           — property name
          ${property_reference}      — computed reference number (unit ref)
          ${site_name}               — site/project name
          ${due_date}                — this installment's due date
          ${amount_total}            — this installment's total amount
          ${amount_paid}             — this installment's paid amount
          ${amount_residual}         — this installment's remaining amount
          ${selected_amount}         — alias for amount_residual
          ${installment_name}        — this installment description
          ${collection_name}         — collection order reference
          ${contract_number}         — contract number (from sale → contract)
          ${contract_date}           — contract date
          ${sale_amount}             — total sale price
          ${next_installment_name}   — next unpaid installment description
          ${next_installment_amount} — next unpaid installment remaining amount
          ${next_installment_date}   — next unpaid installment due date
          ${letter_date}             — letter date (from wizard)
          ${letter_number}           — letter number (from wizard)

        extra_values (dict) are merged last so callers can override any key.
        """
        values = {
            'partner_name':            '—',
            'property_name':           '—',
            'property_reference':      '—',
            'site_name':               '—',
            'due_date':                '—',
            'amount_total':            0,
            'amount_paid':             0,
            'amount_residual':         0,
            'selected_amount':         0,
            'installment_name':        '—',
            'collection_name':         '—',
            'contract_number':         '—',
            'contract_date':           '—',
            'sale_amount':             0,
            'next_installment_name':   '—',
            'next_installment_amount': 0,
            'next_installment_date':   '—',
            'letter_date':             '—',
            'letter_date_eth':         '—',
            'letter_number':           '—',
        }

        if extra_values:
            values.update({k: v for k, v in extra_values.items() if v is not None})
            
        if values.get('letter_date') and values['letter_date'] != '—':
            try:
                from datetime import datetime, timedelta
                d = datetime.strptime(values['letter_date'], '%Y-%m-%d')
                try:
                    # pyrefly: ignore [missing-import]
                    from ethiopian_date import EthiopianDateConverter
                    eth_date = EthiopianDateConverter.to_ethiopian(d.year, d.month, d.day)
                    eth_month_names = {
                        1: "መስከረም", 2: "ጥቅምት", 3: "ህዳር", 4: "ታህሳስ", 5: "ጥር", 6: "የካቲት",
                        7: "መጋቢት", 8: "ሚያዚያ", 9: "ግንቦት", 10: "ሰኔ", 11: "ሐምሌ", 12: "ነሐሴ", 13: "ጳጉሜ"
                    }
                    values['letter_date_eth'] = f"{eth_month_names.get(eth_date.month, '')} {eth_date.day} ቀን {eth_date.year} ዓ.ም"
                    
                    # Calculate +30 days for due_date
                    d30 = d + timedelta(days=30)
                    eth_d30 = EthiopianDateConverter.to_ethiopian(d30.year, d30.month, d30.day)
                    values['due_date_eth'] = f"{eth_month_names.get(eth_d30.month, '')} {eth_d30.day} ቀን {eth_d30.year} ዓ.ም"
                except ImportError:
                    pass
            except Exception:
                pass

        if not record:
            return values

        # Attempt to get buyer name from collection order
        buyer_name = ''
        try:
            if getattr(record, 'collection_id', False):
                buyer = getattr(record.collection_id, 'buyers_name', False)
                if buyer:
                    buyer_name = buyer.name if not isinstance(buyer, str) and hasattr(buyer, 'name') else str(buyer)
                
                # Ignore literal default text from property_sale_buyer_name
                if "No buyers found" in buyer_name:
                    buyer_name = ''
                    
                # If no buyer, fallback to customer (partner_id) on collection_order
                if not buyer_name:
                    customer = getattr(record.collection_id, 'partner_id', False)
                    if customer and hasattr(customer, 'name'):
                        buyer_name = customer.name
        except Exception:
            pass

        final_partner_name = buyer_name if buyer_name else ((record.partner_id.name or '—') if getattr(record, 'partner_id', False) else '—')

        # ── Basic installment fields ──────────────────────────────────────────
        values.update({
            'partner_name':    final_partner_name,
            'property_name':   (record.property_id.name or '—') if record.property_id else '—',
            'site_name':       (record.site_id.name or '—') if record.site_id else '—',
            'due_date':        values.get('due_date_eth') or (str(record.due_date) if record.due_date else '—'),
            'amount_total':    record.amount_total or 0,
            'amount_paid':     record.amount_paid or 0,
            'amount_residual': record.amount_residual or 0,
            'selected_amount': record.amount_residual or 0,
            'installment_name': record.name or '—',
        })

        # ── Property computed reference ───────────────────────────────────────
        prop = record.property_id
        if prop:
            values['property_reference'] = (
                getattr(prop, 'reference_no', None) or '—'
            )

        # ── Collection order fields ───────────────────────────────────────────
        col = record.collection_id
        if col:
            values['collection_name'] = col.name or '—'
            values['sale_amount'] = col.amount_total or 0

            # contract_number is related to sale_id.contract_number on collection.order
            values['contract_number'] = col.contract_number or '—'

            # contract_date: sale → contract application → contract_date
            sale = col.sale_id
            if sale:
                contract = None
                # contract_id is a One2many on property.sale → contract.application
                if hasattr(sale, 'contract_id') and sale.contract_id:
                    contract = sale.contract_id[:1]  # first contract
                if contract and hasattr(contract, 'contract_date') and contract.contract_date:
                    values['contract_date'] = str(contract.contract_date)
                elif contract and hasattr(contract, 'contract_date_char') and contract.contract_date_char:
                    values['contract_date'] = contract.contract_date_char

        # ── Next installment strictly AFTER the selected one ─────────────────
        # Sort all installments in the collection by (due_date, id) — same
        # order as the model's _order — then find the first one whose
        # position comes after the selected record.
        if col:
            all_sorted = col.installment_ids.sorted(
                lambda i: (str(i.due_date) if i.due_date else '9999-12-31', i.id)
            )
            # Find the index of the selected record in the sorted list
            ids_sorted = [i.id for i in all_sorted]
            try:
                current_pos = ids_sorted.index(record.id)
            except ValueError:
                current_pos = -1

            # Walk forward from current_pos to find the next unpaid/partial/overdue
            nxt = None
            for inst in all_sorted[current_pos + 1:]:
                if inst.state in ('unpaid', 'partial', 'overdue'):
                    nxt = inst
                    break

            if nxt:
                values['next_installment_name']   = nxt.name or '—'
                values['next_installment_amount'] = nxt.amount_residual or 0
                values['next_installment_date']   = str(nxt.due_date) if nxt.due_date else '—'

        # ── Caller-supplied overrides (letter_date, letter_number, etc.) ──────
        if extra_values:
            values.update({k: v for k, v in extra_values.items() if v is not None})

        return values
