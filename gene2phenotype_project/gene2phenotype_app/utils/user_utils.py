from email.message import EmailMessage
from smtplib import SMTP
from django.conf import settings
from django.template.loader import render_to_string

class CustomMail():

    @staticmethod
    def send_reset_email(user, subject, reset_link, to_email):
        email_body = render_to_string('gene2phenotype_app/password_reset_email.tpl', {
            'user': user,
            'link': reset_link
        })
        message = EmailMessage()
        message['From'] = settings.DEFAULT_FROM_EMAIL
        message['To'] = to_email
        message['Subject'] = subject
        message.set_content(email_body, 'html')
        try:
            with SMTP(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT) as server:
                server.send_message(message)
        except Exception as e:
            return str(e)
        

    @staticmethod
    def send_create_email(data, subject, to_email):
        email_body = render_to_string('gene2phenotype_app/create_user_email.tpl', {
            'user': data.first_name,
            'email': data.email,
            'first_name': data.first_name, 
            'last_name': data.last_name,
            'username': data.username
        })
        message = EmailMessage()
        message['From'] = settings.DEFAULT_FROM_EMAIL
        message['To'] = to_email
        message['Subject'] = subject
        message.set_content(email_body, 'html')
  
        try:
            with SMTP(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT) as server:
                server.send_message(message)
        except Exception as e:
            return str(e)
        
    @staticmethod
    def send_change_password_email(user, user_email, subject, to_email):
        email_body = render_to_string('gene2phenotype_app/change_password_email.tpl', {
            'user': user,
            'email': user_email
        })
        message = EmailMessage()
        message['From'] = settings.DEFAULT_FROM_EMAIL
        message['To'] = to_email
        message['Subject'] = subject
        message.set_content(email_body, 'html')
        try:
            with SMTP(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT) as server:
                server.send_message(message)
        except Exception as e:
            return str(e)
