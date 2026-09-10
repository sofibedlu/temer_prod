import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from ethioqen.calendar_conversion import convert_gregorian_to_ethiopian
except ImportError:
    _logger.warning("The 'ethioqen' library is missing. Install via: pip install ethioqen")

class EthiopianCalendarConfig(models.Model):
    _name = 'property.ethiopian.calendar.config'
    _description = 'Ethiopian Calendar Configuration'

    name = fields.Char(default='Ethiopian Naming Configuration', required=True)
    format_string = fields.Char(
        string="Naming Format", 
        default="እስከ {month} {day_num} ቀን {year_num} ዓ.ም",
        required=True,
        help="Variables allowed: {month}, {day} (words), {day_num} (digits), {year} (words), {year_num} (digits)"
    )
    
    month_ids = fields.One2many('property.ethiopian.month', 'config_id', string="Months Mapping")
    number_ids = fields.One2many('property.ethiopian.number', 'config_id', string="Numbers Mapping")

    @api.model
    def safe_gregorian_to_ethiopian(self, gregorian_date):
        """ 
        using the ethioqen library which natively supports Pagume.
        """
        if not gregorian_date:
            return 0, 0, 0
        try:
            eth_year, eth_month, eth_day = convert_gregorian_to_ethiopian(
                gregorian_date.year, gregorian_date.month, gregorian_date.day
            )
            return eth_year, eth_month, eth_day
        except Exception as e:
            raise UserError(_("Conversion Error: %s") % str(e))

    def _get_mappings(self):
        months = {1: "መስከረም", 2: "ጥቅምት", 3: "ህዳር", 4: "ታህሳስ", 5: "ጥር", 6: "የካቲት", 
                  7: "መጋቢት", 8: "ሚያዚያ", 9: "ግንቦት", 10: "ሰኔ", 11: "ሐምሌ", 12: "ነሐሴ", 13: "ጳጉሜ"}
        
        ones = {0: '', 1: 'አንድ', 2: 'ሁለት', 3: 'ሶስት', 4: 'አራት', 5: 'አምስት', 
                6: 'ስድስት', 7: 'ሰባት', 8: 'ስምንት', 9: 'ዘጠኝ'}
        
        tens = {0: '', 10: 'አስር', 20: 'ሃያ', 30: 'ሰላሳ', 40: 'አርባ', 50: 'ሃምሳ', 
                60: 'ስድሳ', 70: 'ሰባ', 80: 'ሰማንያ', 90: 'ዘጠና'}
        
        powers = {0: '', 3: 'ሺህ', 6: 'ሚሊዮን', 9: 'ቢሊዮን'}
        
        specials = {'zero': 'ዜሮ', 'ten_prefix': 'አስራ', 'hundred': 'መቶ'}

        for m in self.month_ids:
            months[m.month_number] = m.name

        for n in self.number_ids:
            if n.category == 'one': ones[n.value] = n.name
            elif n.category == 'ten': tens[n.value] = n.name
            elif n.category == 'power': powers[n.value] = n.name
            elif n.category == 'special': specials[n.special_key] = n.name

        return months, ones, tens, powers, specials

    def convert_date_to_amharic(self, gregorian_date):
        if not gregorian_date:
            return ""
        
        eth_year, eth_month, eth_day = self.safe_gregorian_to_ethiopian(gregorian_date)

        months, ones, tens, powers, specials = self._get_mappings()

        def number_to_words(number):
            if number == 0:
                return specials.get('zero', 'ዜሮ')

            def convert_group(n):
                if n == 0: return ''
                elif n <= 9: return ones.get(n, '')
                elif n == 10: return tens.get(10, 'አስር')
                elif 11 <= n <= 19: 
                    return f"{specials.get('ten_prefix', 'አስራ')} {ones.get(n - 10, '')}".strip()
                elif n <= 99: 
                    return f"{tens.get((n // 10) * 10, '')} {ones.get(n % 10, '')}".strip()
                else: 
                    hundred_word = specials.get('hundred', 'መቶ')
                    rem = convert_group(n % 100)
                    return f"{ones.get(n // 100, '')} {hundred_word} {rem}".strip()

            result = ''
            power = 0
            while number > 0:
                group = number % 1000
                if group != 0:
                    group_text = convert_group(group)
                    if power > 0:
                        group_text += ' ' + powers.get(power, '')
                    result = group_text + (' ' if result else '') + result
                number //= 1000
                power += 3
            return result.strip()

        day_word = number_to_words(eth_day)
        year_word = number_to_words(eth_year)
        month_word = months.get(eth_month, "---")

        return self.format_string.format(
            month=month_word, 
            day=day_word, 
            year=year_word,
            day_num=eth_day,
            year_num=eth_year
        )


class EthiopianMonth(models.Model):
    _name = 'property.ethiopian.month'
    _description = 'Ethiopian Month Mapping'
    _order = 'month_number'

    config_id = fields.Many2one('property.ethiopian.calendar.config', ondelete='cascade')
    month_number = fields.Integer(string="Month (1-13)", required=True)
    name = fields.Char(string="Amharic Name", required=True)


class EthiopianNumber(models.Model):
    _name = 'property.ethiopian.number'
    _description = 'Ethiopian Number Mapping'
    _order = 'category, value'

    config_id = fields.Many2one('property.ethiopian.calendar.config', ondelete='cascade')
    category = fields.Selection([
        ('one', 'Ones (1-9)'),
        ('ten', 'Tens (10-90)'),
        ('power', 'Powers (1000, 1M)'),
        ('special', 'Specials (Zero, 10-prefix, Hundred)')
    ], required=True)
    value = fields.Integer(string="Numeric Value")
    special_key = fields.Char(string="Special Key", help="e.g., 'zero', 'ten_prefix', 'hundred'")
    name = fields.Char(string="Amharic Name", required=True)