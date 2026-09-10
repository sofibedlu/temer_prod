# -*- coding: utf-8 -*-
##############################################################################
#    Ahadubit Technologies
#    Copyright (C) 2024-TODAY Ahadubit Technologies(<https://ahadubit.com>).
#    Author: Ahadubit Technologies (<https://ahadubit.com>)
##############################################################################
import base64
import io
import magic
import cv2
import pytesseract
import re
from datetime import datetime
from PIL import Image
from pdf2image import convert_from_bytes
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
import pytesseract

_logger = logging.getLogger(__name__)

class PropertyReservationPayment(models.Model):
    _name = 'property.reservation.payment'
    _description = 'Property Reservation Payments'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    reservation_id = fields.Many2one('property.reservation', string="Reservation", tracking=True)
    property_id = fields.Many2one('property.property', string="Property", related='reservation_id.property_id', store=True)
    # salesperson_id = fields.Many2one('res.users', string="Salesperson", related='reservation_id.salesperson_id', store=True)
    customer_id = fields.Many2one('res.partner', string="Customer", related='reservation_id.partner_id', store=True)
    payment_receipt = fields.Binary(string="Payment Receipt", required=True)
    document_type_id = fields.Many2one('bank.document.type', string="Document Type", required=True, tracking=True)
    bank_id = fields.Many2one('bank.configuration', string="Bank", required=True, tracking=True)
    ref_number = fields.Char(string="Reference Number", required=True, tracking=True)
    transaction_date = fields.Date(string="Transaction Date", required=True, default=fields.Datetime.now, tracking=True)
    amount = fields.Float(string="Amount", required=True, tracking=True)
    id_editable = fields.Boolean(string="Is Editable", default=False)
    is_verifed = fields.Boolean(string="Verified", default=False)
    is_new_line = fields.Boolean(string="is new line", default=False)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('reserved', 'Reserved'),
        ('canceled', 'Canceled'),
        ('expired', 'Expired'),
        ("pending_sales", "Pending Sales"),
        ('sold', 'Sold'),
    ], string='Status', related='reservation_id.status', default='requested', tracking=True, store=True)
    payment_status = fields.Selection([
        ('draft', 'draft'),
        ('requested', 'Requested'),
        ('approved', 'Verified'),
        ('canceled', 'canceled'),
    ], string='Payment Status',
        default='draft', tracking=True)
    cancel_reason=fields.Char(string="Cancellation Reason", tracking=True)
    canceled_time=fields.Datetime(string="Canceled Time", tracking=True)

    def unlink(self):
        for rec in self:
            if rec.create_uid != self.env.user:
                raise ValidationError(_("You cannot delete a payment."))
        return super(PropertyReservationPayment, self).unlink()

    def add_confirm(self):
        for rec in self:
            rec.is_new_line=False

    def write(self, vals):
        if 'is_verifed' in vals and vals['is_verifed']:
            vals['payment_status'] = 'approved'
        elif self.payment_status in ["canceled","draft"]:
            vals['payment_status']='requested'
            vals['is_verifed']=False
        record = super(PropertyReservationPayment, self).write(vals)
        return record


    @api.onchange('is_verifed')
    def approve_payment(self):
        for rec in self:
            if rec.is_verifed:
                rec.payment_status='approved'
            else:
                rec.payment_status = 'draft'

    def open_form_view(self):
        for rec in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Cancel Payment',
                'res_model': 'property.reservation.payment',
                'view_mode': 'form',
                'target': 'new',
                'res_id':rec.id,

            }


    # Cancellation Methods
    def cancel_payment(self):
        """Cancel an active reservation."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cancel Payment',
            'res_model': 'payment.cancellation.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_id': self.id,
            }
        }



    # @api.model
    # def _get_this_month_domain(self):
    #     first_day_of_month = datetime.today().replace(day=1)
    #     first_day_of_next_month = (first_day_of_month + relativedelta(months=1)).replace(day=1)
    #     return [('transaction_date', '>=', fields.Date.to_string(first_day_of_month)),
    #             ('transaction_date', '<', fields.Date.to_string(first_day_of_next_month))]

    @api.constrains('ref_number')
    def validate_ref_number(self):
        for rec in self:
            payments = self.env['property.reservation.payment'].search([
                ('id', '!=', rec.id),
                ('reservation_id.status', 'not in', ['canceled', 'expired'])
            ])
            payment = payments.filtered(lambda p: p.ref_number.lower() == rec.ref_number.lower())
            if payment:
                raise ValidationError(_("The Reference Number must be unique."))



    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            for val in vals:
                ref_number = val.get('ref_number')
                payments = self.search([('ref_number', '=', ref_number)])
                for payment in payments:
                    if payment.reservation_id.status not in ['canceled', 'expired']:
                        raise ValidationError(_("The Reference Number must be unique."))
        vals['payment_status'] = 'requested'
        record =  super().create(vals)
        if record.reservation_id.status not in ['draft', False]:
            record.is_new_line=True
        # if 'payment_receipt' in vals:
        #     try:
        #         record._check_receipt_data()
        #     except ValidationError as e:
        #         # Delete the record if processing fails
        #         # record.unlink()
        #         raise ValidationError(f"Failed to process the payment receipt: {e}")
        return record
        

    @api.constrains('payment_receipt')
    def _check_file_type(self):
        allowed_image_types = ['jpeg', 'png', 'gif']
        pdf_signature = b'%PDF'
        for record in self:
            if record.payment_receipt:
                file_data = base64.b64decode(record.payment_receipt)
                if file_data.startswith(pdf_signature):
                    continue
                image_type = imghdr.what(None, file_data)
                if image_type not in allowed_image_types:
                    raise ValidationError(_("Only PDF and image files (JPEG, PNG, GIF) are allowed for Payment Receipt."))

    @api.constrains('amount')
    def _validate_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Amount must be greater than zero"))
            

    
    def save_uploaded_file(self, file_data, file_name="uploaded_file"):
        """
        Save the uploaded file locally for debugging purposes.
        Args:
            file_data (bytes): The binary data of the uploaded file.
            file_name (str): The name to save the file as (default is 'uploaded_file').

        Returns:
            str: The full path of the saved file.
        """
        try:
            file_path = f"/tmp/{file_name}"
            with open(file_path, "wb") as f:
                f.write(file_data)
            _logger.info(f"File saved for debugging at: {file_path}")
            return file_path
        except Exception as e:
            _logger.error(f"Error saving file: {e}")
            # raise ValidationError("Failed to save the uploaded file for debugging.")


    @api.constrains('payment_receipt')
    def _check_file_type(self):
        pdf_signature = b"%PDF"
        allowed_image_types = ['jpeg', 'png', 'gif']

        for record in self:
            if record.payment_receipt:
                file_data = base64.b64decode(record.payment_receipt)
                # Save for debugging
                self.save_uploaded_file(file_data, "debug_uploaded_file")

                # Check for PDF
                if file_data.startswith(pdf_signature):
                    _logger.info("Detected file type: PDF")
                    continue

                # Fallback to imghdr for image types
                import imghdr
                image_type = imghdr.what(None, file_data)
                if image_type in allowed_image_types:
                    _logger.info(f"Detected file type: {image_type}")
                    continue

                # If none match, raise an error
                raise ValidationError(_("Unsupported file type. Please upload a valid image (JPEG, PNG, GIF) or PDF."))

    # def preprocess_image_pillow(self, file_bytes):
    #     try:
    #         image = Image.open(io.BytesIO(file_bytes))
    #         image = image.convert("RGB")
    #         buffer = io.BytesIO()
    #         image.save(buffer, format="JPEG")
    #         return buffer.getvalue()
    #     except Exception as e:
    #         _logger.error(f"Error during image preprocessing: {e}")
    #         raise ValidationError("The uploaded image cannot be processed.")
    def extract_text_from_file(self, file_data):
        """
        Process the uploaded binary file, handling both images and PDFs.
        Preprocess the image to improve OCR accuracy.
        """
        try:
            # Save the file for debugging
            file_path = self.save_uploaded_file(file_data, "debug_uploaded_file")
            _logger.info(f"File saved at: {file_path}")

            # Check file type with magic
            mime = magic.Magic(mime=True)
            file_type = mime.from_buffer(file_data)
            _logger.info(f"Detected MIME type: {file_type}")

            if file_type.startswith("image"):
                # Process as an image
                preprocessed_data = self.preprocess_image(file_data)
                image = Image.open(io.BytesIO(preprocessed_data))
                text = pytesseract.image_to_string(image)
                _logger.info(f"Extracted text from image: {text}")
                return text

            elif file_type == "application/pdf":
                # Process as a PDF
                return self.extract_text_from_pdf(file_data)

            elif file_data.startswith(b"%PDF"):
                # Fallback: Detect PDF from signature
                _logger.info("Fallback: Detected PDF from signature.")
                return self.extract_text_from_pdf(file_data)

            elif imghdr.what(None, file_data) in ['jpeg', 'png', 'gif']:
                # Fallback: Detect image from imghdr
                _logger.info("Fallback: Detected image from imghdr.")
                preprocessed_data = self.preprocess_image(file_data)
                image = Image.open(io.BytesIO(preprocessed_data))
                text = pytesseract.image_to_string(image)
                _logger.info(f"Extracted text from fallback image: {text}")
                return text

            else:
                raise ValidationError("Unsupported file type. Please upload a valid image or PDF.")

        except Exception as e:
            _logger.error(f"File processing error: {e}")
            raise ValidationError(f"Failed to process the file. Error: {e}")

    def preprocess_image(self, file_data):
        """
        Preprocess the image to improve OCR accuracy.
        Applies grayscale conversion, thresholding, and denoising.
        """
        try:
            import numpy as np
            np_img = np.frombuffer(file_data, np.uint8)
            img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply adaptive thresholding
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # Denoise the image
            denoised = cv2.fastNlMeansDenoising(binary, h=30)

            # Convert back to bytes for PIL compatibility
            is_success, buffer = cv2.imencode(".jpeg", denoised)
            return buffer.tobytes()
        except Exception as e:
            _logger.error(f"Error during image preprocessing: {e}")
            raise ValidationError("Failed to preprocess the image for OCR.")

    def extract_text_from_pdf(self, file_data):
        """
        Extract text from a PDF file using OCR.
        Converts PDF pages to images and processes each page.
        """
        try:
            pdf_images = convert_from_bytes(file_data)
            text = ""
            for page_number, page in enumerate(pdf_images, start=1):
                page_text = pytesseract.image_to_string(page)
                _logger.info(f"Extracted text from PDF page {page_number}: {page_text}")
                text += page_text + "\n"
            _logger.info(f"Final extracted text from PDF: {text}")
            return text
        except Exception as e:
            _logger.error(f"PDF processing error: {e}")
            raise ValidationError("Failed to process the PDF file. Please ensure it is valid.")

    @api.constrains('payment_receipt')
    def _check_receipt_data(self):
        for record in self:
            if not record.payment_receipt:
                raise ValidationError("Payment receipt is required.")
            file_data = base64.b64decode(record.payment_receipt)
            extracted_text = self.extract_text_from_file(file_data)
            if not extracted_text.strip():
                raise ValidationError("The uploaded file does not contain readable text.")
            if not self.validate_date(extracted_text, record.transaction_date):
                raise ValidationError("Transaction date not found in the receipt.")
            if not self.validate_amount(extracted_text, record.amount):
                raise ValidationError("Transaction amount not found in the receipt.")
            record.is_verified = True

    def validate_date(self, text, transaction_date):
        """
        Validate if the provided transaction_date exists in the extracted text.
        Supports:
        - YYYY-MM-DD format.
        - dd-mm-yyyy, mm-dd-yyyy formats.
        - dd/mm/yyyy, mm/dd/yyyy formats.
        - 2-digit year versions for both '-' and '/'.
        """
        # Normalize the transaction date to all supported formats
        transaction_date_dd_mm_yyyy = transaction_date.strftime('%d/%m/%Y')
        transaction_date_mm_dd_yyyy = transaction_date.strftime('%m/%d/%Y')
        transaction_date_dd_mm_yy = transaction_date.strftime('%d/%m/%y')
        transaction_date_mm_dd_yy = transaction_date.strftime('%m/%d/%y')

        # Replace '/' with '-' for alternate formats
        transaction_date_dd_mm_yyyy_dash = transaction_date_dd_mm_yyyy.replace('/', '-')
        transaction_date_mm_dd_yyyy_dash = transaction_date_mm_dd_yyyy.replace('/', '-')
        transaction_date_dd_mm_yy_dash = transaction_date_dd_mm_yy.replace('/', '-')
        transaction_date_mm_dd_yy_dash = transaction_date_mm_dd_yy.replace('/', '-')

        # Regex pattern to identify dates in all formats
        date_pattern = r'\b(\d{4}-\d{2}-\d{2}|\d{2}[-/]\d{2}[-/]\d{2,4})\b'
        dates = re.findall(date_pattern, text)

        _logger.info(f"Extracted dates: {dates}")
        _logger.info(f"Checking against: {transaction_date_dd_mm_yyyy}, {transaction_date_mm_dd_yyyy}, "
                    f"{transaction_date_dd_mm_yy}, {transaction_date_mm_dd_yy}, "
                    f"{transaction_date_dd_mm_yyyy_dash}, {transaction_date_mm_dd_yyyy_dash}, "
                    f"{transaction_date_dd_mm_yy_dash}, {transaction_date_mm_dd_yy_dash}")

        for date in dates:
            try:
                # Handle formats with '-'
                if '-' in date:
                    if date == transaction_date_dd_mm_yyyy_dash or date == transaction_date_mm_dd_yyyy_dash \
                            or date == transaction_date_dd_mm_yy_dash or date == transaction_date_mm_dd_yy_dash:
                        return True

                # Handle formats with '/'
                if '/' in date:
                    if date == transaction_date_dd_mm_yyyy or date == transaction_date_mm_dd_yyyy \
                            or date == transaction_date_dd_mm_yy or date == transaction_date_mm_dd_yy:
                        return True

                # Check for YYYY-MM-DD format
                if len(date.split('-')) == 3:
                    valid_date_yyyy_mm_dd = datetime.strptime(date, '%Y-%m-%d').date()
                    if valid_date_yyyy_mm_dd == transaction_date:
                        return True

            except ValueError:
                _logger.warning(f"Invalid date format: {date}")
                continue

        return False

    def validate_amount(self, text, amount):
        amount_pattern = r'\b(\d+\.\d{2}|\d+)\b'
        amounts = [float(a) for a in re.findall(amount_pattern, text)]
        return amount in amounts

    # @api.constrains('payment_receipt', 'transaction_date', 'amount')
    def _check_receipt_data(self):
        # _logger.info(f"======Pytesseract version: {pytesseract.get_tesseract_version()}")

        for record in self:
            if not record.payment_receipt:
                raise ValidationError("Payment receipt is required.")
            
            file_data = base64.b64decode(record.payment_receipt)
            _logger.info(f"File size: {len(file_data)} bytes")
            _logger.info(f"First 100 bytes: {file_data[:100]}")


            # Extract text from receipt
            extracted_text = self.extract_text_from_file(file_data)

            # Validate date
            # if not self.validate_date(extracted_text, record.transaction_date):
            #     raise ValidationError("Transaction date is not found in the receipt.")

            # # Validate amount
            # if not self.validate_amount(extracted_text, record.amount):
            #     raise ValidationError("Transaction amount is not found in the receipt.")

            if self.validate_date(extracted_text, record.transaction_date) and self.validate_amount(extracted_text, record.amount):
                record.is_verifed = True