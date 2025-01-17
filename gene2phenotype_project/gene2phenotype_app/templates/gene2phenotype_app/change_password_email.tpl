{% extends "mail_templated/base.tpl" %} {% load static %}

{% block subject %}
Hi {{ user }},
{% endblock %}

{% block html %}
<p>The password to the account <strong> {{ email }} </strong> has been changed successfully </p>
<p>If you do not recognize this action please contact the G2P team at <a href="mailto:g2p-help@ebi.ac.uk">g2p-help@ebi.ac.uk</a>.</p>
<footer>
<p>The G2P team</p> 
<img src="{% static 'gene2phenotype_app/G2P_ALL.png' %}" alt="G2P Logo" />
</footer>
{% endblock %}