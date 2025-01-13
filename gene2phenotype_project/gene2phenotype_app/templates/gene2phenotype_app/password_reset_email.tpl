{% extends "mail_templated/base.tpl" %} {% load static %}

{% block subject %}
Hi {{ user }},
{% endblock %}

{% block html %}
<p>You recently requested a password reset for your G2P account. Please use the link below to reset your password</p>
<a href="{{ link }}">Reset your password</a>
<p> If you believe you received this email in error, please contact the G2P team at <a href="mailto:g2p-help@ebi.ac.uk">g2p-help@ebi.ac.uk</a>.</p>
<p>
  Thank you.
  <br>
  The G2P team
  <br>
   <img src="{% static 'gene2phenotype_app/G2P_ALL.png' %}" alt="G2P Logo" />
</p>
{% endblock %}