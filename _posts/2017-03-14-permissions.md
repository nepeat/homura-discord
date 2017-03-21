---
layout: page
title: Permissions
categories: Help
description: This is a list of all the commands with their permissions.
---

{% for _ in site.data.plugins %}
{% assign name = _[0] %}
{% assign meta = _[1] %}
## {{name}}
{% for command in meta.commands %}
**{{command.name | xml_escape }}** - {{command.permission}}
{% endfor %}
{% endfor %}
