from django import template

register = template.Library()


@register.filter
def wmo_choices(wmo_code_tables, table_id):
    """
    Return the list of (code, label) tuples for a WMO code table.

    Usage in template:
        {% for code, label in wmo_code_tables|wmo_choices:vm.adl_parameter.wmo_code_table %}
    """
    return wmo_code_tables.get(table_id, [])
