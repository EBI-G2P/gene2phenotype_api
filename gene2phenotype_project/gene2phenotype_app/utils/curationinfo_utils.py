from email.message import EmailMessage
from smtplib import SMTP
from django.conf import settings
from django.template.loader import render_to_string
from typing import Dict, Any

class ConfidenceCustomMail():

    @staticmethod
    def send_confidence_update_email(instance: object, old_confidence: str, user_updated: str, to_email: str) -> None:
        """
            This function sends confidence updated email to the user associated with the panel

        Args:
            subject (str): Subject of the Email
            to_email (str): The email that will be getting this mail
            data (Dict[Any]): The data that populates the email that will be sent 

        Returns:
           None
        """        

        email_body = render_to_string('gene2phenotype_app/confidence_change_email.tpl', {
            'g2p_record': instance.stable_id.stable_id,
            'old_confidence': old_confidence,
            'new_confidence': instance.confidence,
            'date': instance.date_review,
            'user_updated': user_updated,
        })
        
        message = EmailMessage()
        message['From'] = settings.DEFAULT_FROM_EMAIL
        message['To'] = to_email
        message['Subject'] = ConfidenceCustomMail.subject_confidence(instance)
        message.set_content(email_body, 'html')
        try:
            with SMTP(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT) as server:
                server.send_message(message)
        except Exception as e:
            return str(e)
        
    @staticmethod
    def subject_confidence(instance)-> str:
        return f"Updated confidence for {instance.stable_id.stable_id}"
    
    
        

