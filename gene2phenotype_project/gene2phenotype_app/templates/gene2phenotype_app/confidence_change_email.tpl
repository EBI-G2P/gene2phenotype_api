{% load static %}  {# Load static at the top #}

{% block subject %}
Hi,
{% endblock %}
{% block html %}
<p>
    The confidence to the record <a href="{{ url }}">{{ g2p_record }}</a> has been changed from
    <strong>{{ old_confidence }}</strong> to <strong>{{ new_confidence }}</strong> by 
    <strong>{{ user_updated }}</strong> on <strong>{{ date }}</strong>
</p>

<p>
    If you have issues with this change, please contact the G2P team at 
    <a href="mailto:g2p-help@ebi.ac.uk">g2p-help@ebi.ac.uk</a>.
</p>

<footer>
    <p>The G2P team</p> 
    <img src="{% static 'gene2phenotype_app/G2P_ALL.png' %}" alt="G2P Logo" />
</footer>
{% endblock %}
