from email.message import EmailMessage
from smtplib import SMTP
from django.conf import settings
from django.template.loader import render_to_string
from typing import Dict, Any

class ConfidenceCustomMail():
    """
        Class for the Confidence Email Setup
    """    

    def __init__(self, instance: object, old_confidence: str, user_updated: str, request: object):
        """
            Initialization of the confidence email setup 

            Args:
                instance (object): Instance of the record to be updated 
                old_confidence (str): confidence to be updated from
                user_updated (str): User that updated the confidence
                request (object): Request object
        """        
        self.instance = instance
        self.stable_id = instance.stable_id.stable_id
        self.old_confidence = old_confidence
        self.user_updated = user_updated
        self.request = request
    
    def send_confidence_update_email(self) -> None:
        """
            Confidence email update mail setup

            Returns:
                An exception, if there is an error in sending the mail or returns None
        """

        stable_id = self.stable_id
        g2p_url = self.create_url_record()
        email_body = render_to_string('gene2phenotype_app/confidence_change_email.tpl', {
            'url': g2p_url,
            'g2p_record': stable_id,
            'old_confidence': self.old_confidence,
            'new_confidence': self.instance.confidence,
            'date': self.instance.date_review,
            'user_updated':self.user_updated,
        })
        
        message = EmailMessage()
        message['From'] = settings.DEFAULT_FROM_EMAIL
        message['To'] = settings.MAILING_LIST
        message['Subject'] = self.subject_confidence()
        message.set_content(email_body, 'html')
        try:
            with SMTP(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT) as server:
                server.send_message(message)
        except Exception as e:
            return str(e)
        
    def subject_confidence(self)-> str:
        """
        Subject confidence for this email

        Returns:
            str: Subject string
        """        
        return f"Updated confidence for {self.stable_id}"
    

    def create_url_record(self) -> str:
        """
        Create url link to the record

        Returns:
            str: url string
        """        
        http_response = self.request.scheme
        host = self.request.get_host()
        return f"{http_response}://{host}/gene2phenotype/api/lgd/{self.stable_id}"

    
        

