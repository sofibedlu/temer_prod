from odoo import models, fields, api
from odoo.exceptions import UserError
from ethiopian_date_converter.ethiopian_date_convertor import to_ethiopian
class ContractSection(models.Model):
    _name = "contract.section"
    _inherit = ["contract.template", "mail.thread", "mail.activity.mixin"]
    _description = "Contract Section"
   
    section_content_ids = fields.Many2many(
        "contract.section.article",  
        "contract_section_content_rel",
        "template_id", 
        "content_id",
        string="Articles",
    )
    ETHIOPIAN_MONTHS = [
    '',        # index 0 unused
    'መስከረም', 'ጥቅምት', 'ኅዳር', 'ታኅሣሥ', 'ጥር', 'የካቲት',
    'መጋቢት', 'ሚያዝያ', 'ግንቦት', 'ሰኔ', 'ሐምሌ', 'ነሐሴ', 'ጳጉሜ',
]
    
    def _prepare_placeholder_values(self, contract=None):
        """
        Prepare ${variable} placeholders using contract.application,
        property.sale, property.property, and contract.person models.
        """
        today = fields.Date.today()
        ethiopian_date_val = (
            self.env["contract.section.article"].get_ethiopian_date() or {}
        ) 
        def safe(value):
         return value if value not in (None, False, "", 0) else "___"

        values = {
            "today": today.strftime("%d/%m/%Y") if today else "—",
            "today_eth": f"{ethiopian_date_val.get('month', '—')} {ethiopian_date_val.get('day', '—')} ቀን {ethiopian_date_val.get('year', '—')} ዓ.ም",
            "contract_number": "—",
            "contract_date": "—",
            "contract_date_eth": "—",
            "buyer_full_name": "—",
            "buyer_name": "—",
            "buyer_father_name": "—",
            "buyer_gfather_name": "—",
            "buyer_phone": "—",
            "buyer_mobile": "—",
            "buyer_email": "—",
            "buyer_id_number": "—",

            "buyer_address": "—",

            "buyer_nationality":"_",
            "buyer_birthplace":"_",
            "buyer_passport_id":"_",
            "buyer_with_legal_representative":"_",
            "representative_full_name": "—",
            "representative_name": "—",
            "representative_father_name": "—",
            "representative_gfather_name": "—",
            "representative_id_number": "—",
            "representative_detail": "",
            "property_name": "—",
            "site_code": "",
            "property_type": "",
            "reference_no":"",
            "site_name": "—",
             "area_range":"",
            "title_deed":"",
            "ploat_area":"",  
            "site_city": "—",
            "site_subcity": "—",
            "site_wereda": "—",
            "site_house_no": "—",
            "site_lessee_name": "—",
            "site_car_parking": "—",
            "payment_structure_id": "—",
            "payment_term": [],
            "has_maid_room": "",
            "bedroom": 0,
            "bathroom": 0,
            "salon": 1,
            "kitchin": 0,
            "sum": 0,
            "block": "—",
            "floor_stract": "—",
            "floor": "—",
            "gross_area": "—",
            "net_area": "—",
            "total_price": 0,
            "total_price_words_am": "—",
            "advance_payment": 0,
            "advance_payment_words_am": "—",
            "developer_name": "—",
            "apartment_details": "",
            "payied_in_percent":"",
            "payied_in_amaount":"",
            "payied_in_amount":"",
            "common_area": "",
            "terrace": "",
        }

        if not contract:
            return values

        buyers = contract.person_ids.filtered(lambda p: p.person_type == "buyers")
        buyer = buyers[:1]
        representatives = contract.person_ids.filtered(lambda p: p.person_type == "legal_representatives")
        representative = representatives[:1]
        sale = contract.property_sale_id
        prop = sale.property_id if sale else None
        site = prop.site if prop else None
        developer = sale.template_id.developer_id if sale and sale.template_id else None

        def get_full_name(person):
            if not person:
                return "—"
            return (
                f"{person.first_name or ''} {person.father_name or ''} {person.gfather_name or ''}".strip()
                or "—"
            )

        if contract.contract_date:
            values["contract_date"] = contract.contract_date.strftime("%d/%m/%Y")
            eth_date_val = self.env["contract.section.article"].convert_to_ethiopian(contract.contract_date)
            values["contract_date_eth"] = f"{eth_date_val.get('month', '—')} {eth_date_val.get('day', '—')} ቀን {eth_date_val.get('year', '—')} ዓ.ም"

        # ── Read from property_type_details fields (authoritative source) ──
        bedroom_count = (
            getattr(prop, 'property_type_bedroom', 0) or
            getattr(prop, 'bedroom', 0) or 0
        ) if prop else 0
        bathroom_count = (
            getattr(prop, 'property_type_bathroom', 0) or
            getattr(prop, 'bathroom', 0) or 0
        ) if prop else 0
        kitchen_count = (
            getattr(prop, 'property_type_no_kitchen', 0) or 0
        ) if prop else 0
        has_maid = (
            prop.property_type_has_maid_room
            if (prop and hasattr(prop, 'property_type_has_maid_room'))
            else (
                prop.site_property_type_id.has_maid_room
                if (prop and prop.site_property_type_id)
                else False
            )
        )
        gross_area = (
            (prop.property_type_gross_area or prop.gross_area or "—") if prop else "—"
        )
        net_area = (
            (prop.property_type_net_area or prop.net_area or "—") if prop else "—"
        )
        

        # salon: always 1 living room
        salon_count = 1
        # maid room counts as 1 room if present
        maid_room = 1 if has_maid else 0

        # total = bedroom + bathroom + salon + kitchen + maid room
        total_rooms = bedroom_count + bathroom_count + salon_count + kitchen_count + maid_room

        payment_term = []
        payied_in_percent = "—"
        payied_in_amount = "—"
        is_time_based = (
            sale and getattr(sale, 'payment_schedule_type', 'progress') == 'time'
           )
        if sale and sale.payment_installment_line_ids:
            sorted_lines = sale.payment_installment_line_ids.sorted("sequence")
            for line in sorted_lines:
                original_name = line.payment_term_id.name or "Installment"

                if is_time_based:
                    due_date_greg = getattr(line, 'due_date', False)
                    if due_date_greg:
                        if isinstance(due_date_greg, str):
                            due_date_greg = fields.Date.from_string(due_date_greg)

                        try:
                            eth_date = to_ethiopian(due_date_greg)
                            eth_month_name = self.ETHIOPIAN_MONTHS[eth_date.month]
                            due_date_eth = f"{eth_month_name} {eth_date.day} ቀን {eth_date.year} ዓ.ም"
                            display_name = f"እስከ {due_date_eth}"
                        except (AttributeError, ValueError, TypeError):
                            display_name = original_name
                    else:
                        display_name = original_name
                else:
                    display_name = original_name

                payment_term.append({
                    "name": display_name,
                    "original_name": original_name,
                    "expected_pct": line.expected or 0,
                    "expected_amount": line.expected_amount or 0.0,
                    "remaining": line.remaining or 0.0,
                    "state": dict(line._fields["state"].selection).get(
                        line.state, "—"
                    ),
                })

            # Set payied_in_percent and payied_in_amount from the "ውል ሲፈረም" line
            # Always match against original_name so time-based renaming doesn't break it
            if payment_term or (sale and getattr(sale, 'total_paid', None)):
                first = payment_term[0] if payment_term else {}
                pct_val = first.get("expected_pct") or 0
                sale_total = getattr(sale, 'total_paid', None)
                amt_val = sale_total if sale and sale_total else (first.get("expected_amount") or 0.0)
                payied_in_percent = f"{float(pct_val):g}%"

                calculated_amt = round(float(amt_val), 2)

                whole = int(calculated_amt)

                cents = int(round((calculated_amt - whole) * 100))

                amt_words = self.env["contract.section.article"].number_to_amharic_words(whole)
                if cents:
                    cents_words = self.env["contract.section.article"].number_to_amharic_words(cents)
                    amt_words = f"{amt_words} ብር እና {cents_words} ሳንቲም"
                else:
                    amt_words = f"{amt_words} ብር"
                payied_in_amount = f"{calculated_amt:,.2f} / {amt_words}"

        values.update(
            {
                "contract_number": contract.name or "—",
                "buyer_full_name": " እና ".join(
                    [get_full_name(b) for b in buyers if b]
                ) if buyers else "—",
                "buyer_with_legal_representative": (
                        lambda b_str, r_str: (
                            f"{b_str} (በህጋዊ ወኪል {r_str})" if r_str else f"{b_str}"
                        )
                    )(
                        " እና ".join([get_full_name(b) for b in buyers if b]) or "—",
                        " እና ".join([get_full_name(r) for r in representatives if r]) or ""
                    ),
                "buyer_name": buyer.first_name if buyer else "—",
                "buyer_father_name": buyer.father_name if buyer else "—",
                "buyer_gfather_name": buyer.gfather_name if buyer else "—",
                "buyer_phone": safe(buyer.phone) if buyer else "___",
                "buyer_mobile": safe(buyer.mobile) if buyer else "___",
                "buyer_email": safe(buyer.email) if buyer else "___",
                "buyer_id_number": buyer.id_number if buyer else "—",
                "buyer_nationality": (getattr(buyer, 'nationality_id', None) or "—") if buyer else "—",
                "buyer_birthplace": (getattr(buyer, 'place_of_birth', None) or "—") if buyer else "—",
                "buyer_passport_id": (f"የፓስፖርት ቁጥር {getattr(buyer, 'passport_id_number', None)}" if getattr(buyer, 'passport_id_number', None) else "—") if buyer else "—",
                "buyer_address": (
                    f"ከተማ: {buyer.city or ''}, ክ/ከተማ: {buyer.subcity or ''}, ወረዳ: {buyer.woreda or ''}, ቤት ቁ: {buyer.house_number or ''}"
                    if buyer
                    else "—"
                ),
                # ── Per-buyer indexed keys (buyer_full_name1, buyer_nationality1, …) ──
                **{
                    f"buyer_full_name{i+1}": get_full_name(b)
                    for i, b in enumerate(buyers) if b
                },
                **{
                    f"buyer_nationality{i+1}": (getattr(b, 'nationality_id', None) or "—")
                    for i, b in enumerate(buyers) if b
                },
                **{
                    f"buyer_birthplace{i+1}": (getattr(b, 'place_of_birth', None) or "—")
                    for i, b in enumerate(buyers) if b
                },
                **{
                    f"buyer_passport_id{i+1}": (
                        f"የፓስፖርት ቁጥር {getattr(b, 'passport_id_number', None)}"
                        if getattr(b, 'passport_id_number', None) else "—"
                    )
                    for i, b in enumerate(buyers) if b
                },
                **{
                    f"buyer_phone{i+1}": safe(b.phone) if b else "___"
                    for i, b in enumerate(buyers) if b
                },
                **{
                    f"buyer_address{i+1}": (
                        f"ከተማ: {b.city or ''}, ክ/ከተማ: {b.subcity or ''}, ወረዳ: {b.woreda or ''}, ቤት ቁ: {b.house_number or ''}"
                    )
                    for i, b in enumerate(buyers) if b
                },
                # ── buyers_detail: buyers block + all representatives (if any) ──
                "buyers_detail": (
                    lambda buyers_str, rep_str: (
                        f"{buyers_str} <br/>  <br/> {rep_str}" if rep_str else buyers_str
                    )
                )(
                    " <br/> እና <br/> ".join([
                        f"{f'በ{i+1}ኛ ገዢ፡ ' if len([x for x in buyers if x]) > 1 else 'በገዢ፡ '}"
                        f"{get_full_name(b)} / "
                        f"ዜግነት {getattr(b, 'nationality_id', None) or '—'}/"
                        f"ትውልድ {getattr(b, 'place_of_birth', None) or '—'}/ "
                        f"{'የፓስፖርት ቁጥር ' + getattr(b, 'passport_id_number', '') if getattr(b, 'passport_id_number', None) else ''} "
                        f"አድራሻ: ከተማ: {b.city or ''}, ክ/ከተማ: {b.subcity or ''}, ወረዳ: {b.woreda or ''}, ቤት ቁ: {b.house_number or ''} "
                        f"ስልክ ቁጥር፡ {safe(b.phone)}"
                        for i, b in enumerate(buyers) if b
                    ]) or "—",
                    " <br/> እና <br/> ".join([
                        f"{f'በ{i+1}ኛ በህጋዊ ወኪል፡ ' if len([x for x in representatives if x]) > 1 else 'በህጋዊ ወኪል፡ '}"
                        f"{get_full_name(r)} / "
                        f"ዜግነት {getattr(r, 'nationality_id', None) or '—'}/"
                        f"ትውልድ {getattr(r, 'place_of_birth', None) or '—'}/ "
                        f"{'የፓስፖርት ቁጥር ' + getattr(r, 'passport_id_number', '') if getattr(r, 'passport_id_number', None) else ''} "
                        f"አድራሻ: ከተማ: {r.city or ''}, ክ/ከተማ: {r.subcity or ''}, ወረዳ: {r.woreda or ''}, ቤት ቁ: {r.house_number or ''} "
                        f"ስልክ ቁጥር፡ {safe(r.phone)}"
                        for i, r in enumerate(representatives) if r
                    ]) if representatives else ""
                ),
                # ── representative_detail: all representatives block ──
                "representative_detail": " <br/> እና <br/> ".join([
                    f"{f'በ{i+1}ኛ ወኪል፡ ' if len([x for x in representatives if x]) > 1 else 'በወኪል፡ '}"
                    f"{get_full_name(r)} / "
                    f"ዜግነት {getattr(r, 'nationality_id', None) or '—'}/"
                    f"ትውልድ {getattr(r, 'place_of_birth', None) or '—'}/ "
                    f"{'የፓስፖርት ቁጥር ' + getattr(r, 'passport_id_number', '') if getattr(r, 'passport_id_number', None) else ''} "
                    f"አድራሻ: ከተማ: {r.city or ''}, ክ/ከተማ: {r.subcity or ''}, ወረዳ: {r.woreda or ''}, ቤት ቁ: {r.house_number or ''} "
                    f"ስልክ ቁጥር፡ {safe(r.phone)}"
                    for i, r in enumerate(representatives) if r
                ]) if representatives else "",
                "representative_full_name": " እና ".join(
                    [get_full_name(r) for r in representatives if r]
                ) if representatives else "—",
                "representative_name": representative.first_name if representative else "—",
                "representative_father_name": representative.father_name if representative else "—",
                "representative_gfather_name": representative.gfather_name if representative else "—",
                "representative_id_number": representative.id_number if representative else "—",
                "property_name": prop.name if prop else "—",
                "site_name": site.name if site else "—",
                "property_type": prop.property_type if prop else "—",
                "apartment_type_label": f"ባለ {bedroom_count} መኝታ ቤት" if bedroom_count else "—",
                "site_house_no": prop.unit_number or "—" if prop else "—",
                "block": prop.block.name if (prop and prop.block) else "—",
                "site_city": site.city_id.name if (site and site.city_id) else "—",
                "site_subcity": (
                    site.sub_city_id.name if (site and site.sub_city_id) else "—"
                ),
                "site_wereda": site.wereda if site else "—",
               
                "site_lessee_name": site.lessee_name if site else "—",
                "site_car_parking": site.car_parking if site else "—",
                "title_deed": site.title_deed_no if site else "—",
                "ploat_area": site.plot_area if site else "—",
                "payment_structure_id": (
                    site.payment_structure_id.payment_line
                    if (site and site.payment_structure_id)
                    else "—"
                ),
                "payment_term": payment_term,
                "has_maid_room": "1 የሰራተኛ ክፍል" if has_maid else "",
                "salon": salon_count,
                "kitchin": kitchen_count,
                "bedroom": bedroom_count,
                "bathroom": bathroom_count,
                "sum": total_rooms,
                "floor_stract": site.floor_structure if site else "—",
                "floor": prop.floor_id.name if (prop and prop.floor_id) else "—",
                "site_code": prop.code if prop else "—",
                "reference_no": prop.computed_reference if prop else "",
                "area_range": prop.commercial_rate_range_id.display_name if (prop and getattr(prop, 'commercial_rate_range_id', None)) else "",
                "gross_area": (prop.commercial_gross_range_id.display_name if prop.property_type == 'commercial' and prop.commercial_gross_range_id else prop.gross_area) if prop else "—",
                "net_area": prop.net_area if prop else "—",
                "total_price": contract.payment_amount or 0,
                "total_price_words_am": self.env[
                    "contract.section.article"
                ].number_to_amharic_words(int(contract.payment_amount or 0)),
                "advance_payment": contract.advance_payment or 0,
                "advance_payment_words_am": self.env[
                    "contract.section.article"
                ].number_to_amharic_words(int(contract.advance_payment or 0)),
                "developer_name": developer.name if developer else "—",
                "payied_in_percent": payied_in_percent,
                "payied_in_amaount": payied_in_amount,
                "payied_in_amount": payied_in_amount,
            }
        )
 
        return values

    def render_full_contract(self, contract=None,Archive= None):
            self.ensure_one()
            import re

            if not self.section_content_ids:
                raise UserError("No sections/articles defined in this template.")

            values = self._prepare_placeholder_values(contract)
            rendered_parts = []
            article_counter = 1

            for content in Archive.article_ids.sorted("sequence"):
                if not content.is_active or not content.content:
                    continue
                html_content = content.content

                if content.is_dynamic_content:

                    def replacer(match):
                        key = match.group(1).strip()
                       
                        value = values.get(key)
                      
                        if key.endswith('%'):
                            try:
                                percent_val = float(key[:-1])
                                calculated_amt = (contract.payment_amount * percent_val) / 100

                                amount_number = f"{calculated_amt:,.2f}"
                                whole = int(calculated_amt)
                                cents = round((calculated_amt - whole) * 100)
                                amount_words = self.env["contract.section.article"].number_to_amharic_words(whole)
                                if cents:
                                    cents_words = self.env["contract.section.article"].number_to_amharic_words(cents)
                                    amount_words = f"{amount_words} ብር እና {cents_words} ሳንቲም"
                                else:
                                    amount_words = f"{amount_words} ብር"

                                return f"{amount_number} / {amount_words}"

                            except (ValueError, TypeError):
                                return "—"

                        value = values.get(key)


                        if key == "payment_term" and isinstance(value, list):
                            valid_items = []
                            for item in value or []:
                                if item.get("name") == "ውል ሲፈረም":
                                    continue
                                try:
                                    if float(item.get("expected_pct") or 0.0) > 0:
                                        valid_items.append(item)
                                except (ValueError, TypeError):
                                    pass
                            
                            value = valid_items

                            if not value:
                                return "—"

                            # remove the first row with name "ውል ሲፈረም"
                            value = [item for item in value if item.get("name") != "ውል ሲፈረም"]
                            table_html = """
                                <table style="width:100%; border-collapse: collapse; margin: 15px 0; font-size: 17px !important; font-family: 'Nyala', 'Abyssinica SIL', sans-serif;">
                                    <thead>
                                        <tr style="background-color: #f2f2f2;">
                                            <th style="border: 1px solid black; padding: 8px; text-align: center; width: 8%;">ተቁ</th>
                                            <th style="border: 1px solid black; padding: 8px; text-align: left; width: 32%;">የክፍያ ደረጃ</th>
                                            <th style="border: 1px solid black; padding: 8px; text-align: center; width: 10%;">%</th>
                                            <th style="border: 1px solid black; padding: 8px; text-align: right; width: 15%;">መጠን</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                            """

                            total_expected = 0.0

                            for index, item in enumerate(value, start=2):
                                try:
                                    amt = float(item.get("expected_amount") or 0.0)
                                    pct = float(item.get("expected_pct") or 0.0)
                                except (ValueError, TypeError):
                                    amt = pct = 0.0

                                total_expected += amt

                                table_html += f"""
                                    <tr>
                                        <td style="border: 1px solid black; padding: 8px; text-align: center;">{index}ኛው</td>
                                        <td style="border: 1px solid black; padding: 8px;">{item.get('name', '—')}</td>
                                        <td style="border: 1px solid black; padding: 8px; text-align: center;">{pct:.2f}%</td>
                                        <td style="border: 1px solid black; padding: 8px; text-align: right;">{amt:,.2f}</td>
                                    </tr>
                                """

                            table_html += f"""
                                    <tr style="background-color: #f9f9f9; font-size: 17px !important; font-weight: bold;">
                                        <td colspan="3" style="border: 1px solid black; padding: 8px; text-align: right;">ጠቅላላ ድምር:</td>
                                        <td style="border: 1px solid black; padding: 8px; text-align: right;">{total_expected:,.2f}</td>
                                    </tr>
                                </tbody>
                            </table>"""

                            return table_html

                        if key == "apartment_details":
                            ts  = "border: 1px solid black; padding: 6px 8px; text-align: center;"
                            th  = f"background-color: #f2f2f2; font-weight: bold; {ts}"

                            # ── Gather values ──────────────────────────────
                            floor        = values.get('floor') or ''
                            apt_type     = values.get('apartment_type_label') or ''
                            total_rooms  = values.get('sum') or ''
                            ref_no       = values.get('reference_no') or ''
                            net_area     = values.get('net_area') or ''
                            gross_area   = values.get('gross_area') or ''
                            car_parking  = values.get('site_car_parking') or ''
                            common_area  = values.get('common_area') or ''
                            # block        = values.get('block') or ''
                            site_name    = values.get('site_name') or ''
                            terrace      = values.get('terrace') or ''
                            is_blue_point = site_name.strip().upper() == 'BLUE POINT'

                            # ── Build header + data rows dynamically ───────
                            # Each column: (header_label, cell_value, show_condition)
                            columns = [
                                ("ወለል",                          floor,       True),
                                # ("ብሎክ",                          block,       bool(block)),
                                ("የአፓርታማው አይነት",                apt_type,    True),
                                ("ጠቅላላ የክፍል ብዛት",              total_rooms, True),
                                ("መኖሪያ ቤት ቁጥር",                ref_no,      True),
                                ("የተጣራ የወለል ስፋት (ካ.ሜ)",        net_area,    True),
                                ("ቴራስ (ካ.ሜ)",                   terrace,     is_blue_point),
                                ("የጋራ መጠቀሚያዎች (ካ.ሜ)",          common_area, True),
                                ("የመኪና ማቆሚያ (ካ.ሜ)",             car_parking, bool(car_parking)),
                                ("አጠቃላይ የወለል ስፋት (ካ.ሜ)",       gross_area,  True),
                            ]

                            # Filter to only columns that should show
                            visible = [(label, val) for label, val, show in columns if show]

                            header_cells = "".join(
                                f'<th style="{th}">{label}</th>' for label, _ in visible
                            )
                            data_cells = "".join(
                                f'<td style="{ts}">{val if val not in (None, False, "") else "—"}</td>'
                                for _, val in visible
                            )

                            return (
                                f'<table style="width:100%; border-collapse:collapse; margin:15px 0;'
                                f' font-size:14px; font-family:\'Nyala\',\'Abyssinica SIL\',sans-serif;">'
                                f'<thead><tr>{header_cells}</tr></thead>'
                                f'<tbody><tr>{data_cells}</tr></tbody>'
                                f'</table>'
                            )
                        if isinstance(value, (int, float)):
                            return f"{value:,.2f}" if value % 1 else f"{int(value):,}"
                        if key in ("has_maid_room", "representative_detail"):
                            return str(value)  # allow empty string — no entry means blank
                        return str(value) if value else "—"

                   
                    html_content = re.sub(
                    r"\$\{\s*([a-zA-Z0-9_.%]+)\s*\}", replacer, html_content
                    )

                # if content.is_title_printed and content.main_title:
                #     title_html = f'<h2 class="article-title" style="margin-top: 20px;">{article_counter}. {content.main_title}</h2>'
                #     html_content = f"{title_html}{html_content}"
                #     article_counter += 1

                # Strip ALL inline background-color styles that cause blackish patches
                html_content = re.sub(
                    r'background-color\s*:\s*[^;"\'>]+;?', '', str(html_content)
                )
                # Strip dark inline color values (anything that looks like a dark hex or rgb)
                html_content = re.sub(
                    r'(?<![a-z-])color\s*:\s*(?:rgb\(\s*0\s*,\s*0\s*,\s*0[^)]*\)|#(?:0{3,6}|1[0-9a-f]{2,5}|2[0-9a-f]{2,5}|3[0-9a-f]{2,5}))\s*;?',
                    '', str(html_content)
                )

                section_wrapped = f'<div class="contract-section" style="margin-bottom: 15px;">{html_content}</div>'
                rendered_parts.append(section_wrapped)

            return fields.Markup("".join(rendered_parts))

class ContractSectionArticle(models.Model):
    _name = "contract.section.article"
    _inherit = ["contract.template.content"]
    _rec_name = "main_title"  
    _description = "Contract Section Article"

    section_ids = fields.Many2many(
        "contract.section",
        "contract_section_content_rel",
        "content_id",
        "template_id",
        string="Contract Templates",
    )

