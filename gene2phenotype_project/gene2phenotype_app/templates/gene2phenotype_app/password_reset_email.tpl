{% extends "mail_templated/base.tpl" %}

{% block subject %}
Hi {{ user }},
{% endblock %}

{% block html %}
<p>You recently requested a password reset for your G2P account. Please use the link below to reset your password</p>
<a href="{{ link }}">Reset your password</a>
<p> If you think you received this email in error, please contact the G2P team at <a href="mailto:g2p-help@ebi.ac.uk">g2p-help@ebi.ac.uk</a>.</p>
<p>Thank you</p>
<footer>
<p>The G2P team</p> 
<img src="cid:g2p_logo" alt="G2P Logo" width="56" height="56" style="width:56px;height:56px;" />
</footer>
{% endblock %}