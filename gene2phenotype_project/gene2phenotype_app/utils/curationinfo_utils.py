from email.message import EmailMessage
from smtplib import SMTP
from django.conf import settings
from django.template.loader import render_to_string
from typing import Dict, Any


class ConfidenceCustomMail:
    """
    Class for the Confidence Email Setup
    """

    def __init__(
        self, instance: object, old_confidence: str, user_updated: str, request: object
    ):
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

        email_body = render_to_string(
            "gene2phenotype_app/confidence_change_email.tpl",
            {
                "url": self.create_url_record(),
                "g2p_record": self.stable_id,
                "old_confidence": self.old_confidence,
                "new_confidence": self.instance.confidence,
                "date": self.instance.date_review,
                "user_updated": self.get_user_info(),
            },
        )

        message = EmailMessage()
        message["From"] = settings.DEFAULT_FROM_EMAIL
        message["To"] = settings.MAILING_LIST
        message["Subject"] = self.get_email_subject()
        message.set_content(email_body, "html")

        try:
            with SMTP(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT) as server:
                server.send_message(message)
        except Exception as e:
            return str(e)

    def get_email_subject(self) -> str:
        """
        Subject line for this email

        Returns:
            str: Subject string
        """
        subject_string = f"Updated confidence for {self.stable_id}"
        if self.host != "www.ebi.ac.uk":
            return f"[THIS IS A TEST] {subject_string}"
        return subject_string

    def create_url_record(self) -> str:
        """
        Create url link to the record

        Returns:
            str: url string
        """
        http_response = self.request.scheme
        host = self.request.get_host()
        self.host = host
        return f"{http_response}://{host}/gene2phenotype/lgd/{self.stable_id}"

    def get_user_info(self) -> str:
        """
        Gets user info from the user object

        Returns:
            str: A string containing the user first name and last name
        """
        user_info = f"{self.user_updated.first_name} {self.user_updated.last_name}"

        return user_info
