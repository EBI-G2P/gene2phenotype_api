{% extends "mail_templated/base.tpl" %} {% load static %}

{% block subject %}
Account Created: Welcome to G2P, {{ first_name }} {{ last_name }},
{% endblock %}

{% block html %}
<p>A user account has been created using your email <strong>{{ email }}</strong> with the following details:</p>
<ul>
  <li><strong>First name:</strong> {{ first_name }}</li>
  <li><strong>Last name:</strong> {{ last_name }}</li>
  <li><strong>Username:</strong> {{ username }}</li>
</ul>

<p>If you did not create a user or you are receiving this message in error, please contact the G2P team at <a href="mailto:g2p-help@ebi.ac.uk">g2p-help@ebi.ac.uk</a></p>
<p>To reset the password used in the creation of your account, please follow this link {{ email_verification_link }}</p>

<p>Thank you for using G2P</p>
<footer>
<p>The G2P team</p> 
<img src="{% static 'gene2phenotype_app/G2P_ALL.png' %}" alt="G2P Logo" />
</footer>
{% endblock %}