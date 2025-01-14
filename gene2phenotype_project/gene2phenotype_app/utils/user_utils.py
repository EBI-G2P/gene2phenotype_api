from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.template.loader import render_to_string

class CustomMail():

    @staticmethod
    def send_reset_email(user, subject, reset_link, to_email):
        email_body = render_to_string('gene2phenotype_app/password_reset_email.tpl', {
            'user': user,
            'link': reset_link
        })
        message = Mail(
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=email_body
        )
        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            return response.status_code
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
        message = Mail(
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=email_body
            )
        try: 
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            return response.status_code
        except Exception as e:
            return str(e)
        
    @staticmethod
    def send_change_password_email(user, user_email, subject, to_email):
        email_body = render_to_string('gene2phenotype_app/change_password_email.tpl', {
            'user': user,
            'email': user_email
        })
        message = Mail(
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=email_body
            )
        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            return response.status_code
        except Exception as e:
            return str(e)
