# {{ app }}

Thank you for installing {{ app }}.

{% if url %}

### Resources

{% for name, link in url %}

* [{{ name }}]({{ link }})
{% endfor %}
{% endif %}

{% if uninstall %}

### Uninstall {{ app }}

Run the following command to uninstall {{ app }}.

  $ sudo bash /Library/{{ app }}/{{ version }}/uninstall.sh

{% endif %}
