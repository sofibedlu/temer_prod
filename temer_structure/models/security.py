from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

class PropertyProperty(models.Model):
    _inherit = 'property.property'

class PropertyReservationTransfer(models.Model):
    _inherit = 'property.reservation.transfer.history'

class PropertySpecialDiscount(models.Model):
    _inherit = 'property.special.discount'

class PropertyReservationCancel(models.Model):
    _inherit = 'property.reservation.cancel'

    
class PropertyReservationConfiguration(models.Model):
    _inherit = 'property.reservation.configuration'

class BankDocumentType(models.Model):
    _inherit = 'bank.configuration'

class BankDocumentType(models.Model):
    _inherit = 'bank.document.type'

class PropertyFacility(models.Model):
    _inherit = 'property.facility'

class PropertySite(models.Model):
    _inherit = 'property.site'

class PropertySiteType(models.Model):
    _inherit = 'property.site.type'

class PropertyType(models.Model):
    _inherit = 'property.type'

class PropertySiteSubCity(models.Model):
    _inherit = 'property.site.subcity'

class PropertyBlock(models.Model):
    _inherit = 'property.block'

class PropertyFloor(models.Model):
    _inherit = 'property.floor'

class PropertyImage(models.Model):
    _inherit = 'property.image'

class PropertySiteFacility(models.Model):
    _inherit = 'property.site.facility'

class PropertyReservationPayment(models.Model):
    _inherit = 'property.reservation.payment'

class PropertyReservationExtendHistory(models.Model):
    _inherit = 'property.reservation.extend.history'

class PropertyPaymentTermLine(models.Model):
    _inherit = 'property.payment.term.line'

class ContractPerson(models.Model):
    _inherit = 'contract.person'

class ContractTemplate(models.Model):
    _inherit = 'contract.template'

class ContractApplication(models.Model):
    _inherit = 'contract.application'

class ContractTemplateContent(models.Model):
    _inherit = 'contract.template.content'

class PropertyPaymentLine(models.Model):
    _inherit = 'property.payment.line'

class CrmPhonecall(models.Model):
    _inherit = 'crm.phone'

class PropertyPaymentTerm(models.Model):
    _inherit = 'property.payment.term'

class PropertySalePaymentTermLine(models.Model):
    _inherit = 'property.sale.payment.term.line'

class PropertySiteCity(models.Model):
    _inherit = 'property.site.city'

class PropertySiteType(models.Model):
    _inherit = 'property.site.type'

class PropertyPaymentType(models.Model):
    _inherit = 'property.payment.type'

class SitPropertyTypeLine(models.Model):
    _inherit = 'site.property.type.line'

class PropertyPaymentDiscount(models.Model):
    _inherit = 'property.payment.discount'

class PropertyTag(models.Model):
    _inherit='property.tag'

class PropertyTransferPayment(models.Model):
    _inherit = 'property.transfer.payment'

class MailActivityInherited(models.TransientModel):
    _inherit = 'mail.activity.schedule'

class PropertySaleCancelReason(models.Model):
    _inherit = 'property.sale.cancel.reason'

class CancellationReasonWizard(models.Model):
    _inherit = 'ir.model'

class CancellationReasonWizard(models.TransientModel):
    _inherit = 'cancellation.reason.wizard'

class PropertyReservation(models.Model):
    _inherit = 'property.reservation'


class PaymentCancellationReasonWizard(models.TransientModel):
    _inherit = 'payment.cancellation.reason.wizard'

class PaymentCancellationReason(models.Model):
    _inherit = 'payment.cancellation.reason'
