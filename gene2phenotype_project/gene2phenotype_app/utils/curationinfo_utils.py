from email.message import EmailMessage
from smtplib import SMTP
from django.conf import settings
from django.template.loader import render_to_string
from typing import Dict, Any

class ConfidenceCustomMail():

    @staticmethod
    def send_confidence_update_email(instance: object, old_confidence: str, user_updated: str, request: object) -> None:
        """
            Confidence email update mail setup

            Args:
                instance (object): Instance object
                old_confidence (str): old confidence object
                user_updated (str): user that updated the confidence
                request (object): the request object

            Returns:
                An exception, if there is an error in sending the mail or returns None
        """

        stable_id = instance.stable_id.stable_id
        g2p_url = ConfidenceCustomMail.create_url_record(stable_id,request)
        email_body = render_to_string('gene2phenotype_app/confidence_change_email.tpl', {
            'url': g2p_url,
            'g2p_record': stable_id,
            'old_confidence': old_confidence,
            'new_confidence': instance.confidence,
            'date': instance.date_review,
            'user_updated': user_updated,
        })
        
        message = EmailMessage()
        message['From'] = settings.DEFAULT_FROM_EMAIL
        message['To'] = settings.MAILING_LIST
        message['Subject'] = ConfidenceCustomMail.subject_confidence(stable_id)
        message.set_content(email_body, 'html')
        try:
            with SMTP(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT) as server:
                server.send_message(message)
        except Exception as e:
            return str(e)
        
    @staticmethod
    def subject_confidence(stable_id: str)-> str:
        """
        Subject confidence for this email

        Args:
            instance (object): Instance object

        Returns:
            str: Subject string
        """        
        return f"Updated confidence for {stable_id}"
    

    @staticmethod
    def create_url_record(stable_id: str, request: object) -> str:
        """
        Create url link to the record

        Args:
            stable_id (str): stable id for the object
            request (object): Request objet

        Returns:
            str: url string
        """        
        http_response = request.scheme
        host = request.get_host()
        return f"{http_response}://{host}gene2phenotype/api/lgd/{stable_id}"
    
        

