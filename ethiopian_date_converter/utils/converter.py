import datetime
from odoo.exceptions import UserError
from odoo import _

try:
    from ethiopian_date import EthiopianDateConverter
except ImportError:
    raise ImportError("Please install the ethiopian-date library")

def to_ethiopian(gregorian_date):
    if not gregorian_date:
        return ""
    
    eth_date_obj = EthiopianDateConverter.to_ethiopian(
        gregorian_date.year, 
        gregorian_date.month, 
        gregorian_date.day
    )
    return f"{eth_date_obj.day:02d}/{eth_date_obj.month:02d}/{eth_date_obj.year:04d}"

def to_gregorian(ethiopian_str):
    if not ethiopian_str:
        return False
        
    ethiopian_str = ethiopian_str.strip()
    parts = ethiopian_str.split('/')
    
    if len(parts) != 3:
        raise UserError(_("Please use the exact format dd/mm/yyyy (e.g., 17/10/2016)."))
        
    try:
        eth_day = int(parts[0])
        eth_month = int(parts[1])
        eth_year = int(parts[2])
    except ValueError:
        raise UserError(_("Day, month, and year must be valid numbers."))

    if eth_year < 1800 or eth_year > 3000:
        raise UserError(_("Please enter a valid 4-digit Ethiopian year (e.g., 2016)."))

    if eth_month < 1 or eth_month > 13:
        raise UserError(_("Month must be between 1 and 13."))

    if eth_day < 1 or eth_day > 30:
        raise UserError(_("Day must be between 1 and 30."))
        
    if eth_month == 13 and eth_day > 6:
        raise UserError(_("Pagumē cannot have more than 6 days."))
        
    try:
        gregorian_date = EthiopianDateConverter.to_gregorian(eth_year, eth_month, eth_day)
        return gregorian_date
    except Exception:
        raise UserError(_("The date you entered is invalid. Please check your entry."))