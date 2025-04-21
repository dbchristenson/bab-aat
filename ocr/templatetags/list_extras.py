from django import template

register = template.Library()


@register.filter
def index(seq, i):
    try:
        return seq[int(i)]
    except (IndexError, ValueError, TypeError):
        return ""
