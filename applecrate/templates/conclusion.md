# {{ app }}

Thank you for installing {{ app }}.

{% if url %}
### Resources

{% for name, link in url %}
* [{{ name }}]({{ link }})
{% endfor %}
{% endif %}

{% if url and uninstall %}
<!-- Blank header to insert space between the <ul> and the next header-->
######  
{% endif %}

{% if uninstall %}
### Uninstall {{ app }}

Run the following command in Terminal to uninstall {{ app }}.

  sudo bash "/Library/Application Support/{{ app }}/{{ version }}/uninstall.sh"

{% endif %}
