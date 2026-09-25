from odoo import models, fields, api, _
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class PropertyReservationPayment(models.Model):
    _inherit = 'property.reservation.payment'
    
    @api.onchange('payment_receipt')
    def _onchange_payment_receipt_extract_ai(self):
        if not self.payment_receipt:
            return

        api_key = self.env['ir.config_parameter'].sudo().get_param('property_reservation_receipt_ai.openai_api_key')
        
        if not api_key or api_key == 'put_your_google_api_key_here':
            return {
                'warning': {
                    'title': 'AI Setup Missing',
                    'message': 'Gemini API Key is not configured. Auto-extraction skipped.'
                }
            }

        base64_image = self.payment_receipt.decode('utf-8')

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key 
        }

        # 🌟 UPDATED PROMPT: Added instruction to extract the transaction date in YYYY-MM-DD format
        prompt_text = (
            "You are a financial data extractor. Read this bank deposit slip. "
            "Extract the exact transaction reference number, the total deposit amount, and the transaction date. "
            "Return ONLY a valid JSON object with keys 'reference' (string), 'amount' (number), and 'date' (string formatted strictly as YYYY-MM-DD). "
            "Do not include markdown formatting like ```json."
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_text},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": base64_image
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                _logger.error("Gemini API Error Response: %s", response.text)
                return {'warning': {'title': 'AI Error', 'message': 'Google API rejected the image.'}}

            response_data = response.json()
            ai_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
            
            if ai_text.startswith("```json"):
                ai_text = ai_text[7:-3].strip()
            elif ai_text.startswith("```"):
                ai_text = ai_text[3:-3].strip()

            extracted_data = json.loads(ai_text)

            # 🌟 MAP THE EXTRACTED DATA TO THE ODOO FIELDS
            if extracted_data.get('reference'):
                self.ref_number = str(extracted_data['reference'])
                
            if extracted_data.get('amount'):
                amt = str(extracted_data['amount']).replace(',', '')
                self.amount = float(amt)

            # 🌟 NEW: Map the extracted Date!
            if extracted_data.get('date'):
                self.transaction_date = extracted_data['date']

        except json.JSONDecodeError:
            _logger.error(f"Gemini output wasn't valid JSON: {ai_text}")
            return {'warning': {'title': 'AI Error', 'message': 'Could not read the text from the image clearly.'}}
        except Exception as e:
            return {'warning': {'title': 'AI Error', 'message': f'Extraction failed: {str(e)}'}}


# class PropertyReservationPayment(models.Model):
#     _inherit = 'property.reservation.payment'
    
#     @api.onchange('payment_receipt')
#     def _onchange_payment_receipt_extract_ai(self):
#         if not self.payment_receipt:
#             return

#         # 🌟 Fetch the OpenAI API Key from System Parameters
#         api_key = self.env['ir.config_parameter'].sudo().get_param('property_reservation_receipt_ai.openai_api_key')
        
#         if not api_key or api_key == 'put_your_openai_api_key_here':
#             return {
#                 'warning': {
#                     'title': 'AI Setup Missing',
#                     'message': 'OpenAI API Key is not configured. Auto-extraction skipped.'
#                 }
#             }

#         base64_image = self.payment_receipt.decode('utf-8')

#         # OpenAI API Endpoint
#         url = "https://api.openai.com/v1/chat/completions"
        
#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {api_key}"
#         }

#         # The Prompt
#         prompt_text = (
#             "You are a financial data extractor. Read this bank deposit slip. "
#             "Extract the exact transaction reference number, the total deposit amount, and the transaction date. "
#             "Return a JSON object with keys 'reference' (string), 'amount' (number), and 'date' (string formatted strictly as YYYY-MM-DD)."
#         )

#         # 🌟 Production OpenAI Payload
#         payload = {
#             "model": "gpt-4o-mini",
#             "response_format": {"type": "json_object"}, # 🌟 Forces bulletproof JSON output
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": prompt_text
#                 },
#                 {
#                     "role": "user",
#                     "content": [
#                         {
#                             "type": "image_url",
#                             "image_url": {
#                                 "url": f"data:image/jpeg;base64,{base64_image}"
#                             }
#                         }
#                     ]
#                 }
#             ],
#             "max_tokens": 150,
#             "temperature": 0.0 # Force factual extraction, no guessing
#         }

#         try:
#             response = requests.post(url, headers=headers, json=payload)
            
#             if response.status_code != 200:
#                 _logger.error("OpenAI API Error Response: %s", response.text)
#                 return {'warning': {'title': 'AI Error', 'message': 'OpenAI API rejected the image.'}}

#             response_data = response.json()
            
#             # Extract the pure JSON text generated by OpenAI
#             ai_text = response_data['choices'][0]['message']['content'].strip()
            
#             extracted_data = json.loads(ai_text)

#             # 🌟 Map the extracted data to Odoo fields
#             if extracted_data.get('reference'):
#                 self.ref_number = str(extracted_data['reference'])
                
#             if extracted_data.get('amount'):
#                 # Strip out commas just in case the AI added them to thousands
#                 amt = str(extracted_data['amount']).replace(',', '')
#                 self.amount = float(amt)

#             if extracted_data.get('date'):
#                 self.transaction_date = extracted_data['date']

#         except json.JSONDecodeError:
#             _logger.error(f"OpenAI output wasn't valid JSON: {ai_text}")
#             return {'warning': {'title': 'AI Error', 'message': 'Could not read the text from the image clearly.'}}
#         except Exception as e:
#             _logger.error(f"Extraction failed: {str(e)}")
#             return {'warning': {'title': 'AI Error', 'message': f'Extraction failed: {str(e)}'}}