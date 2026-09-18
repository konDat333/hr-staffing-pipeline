{#
  Use the schema from the model config as-is (`staging`, `marts`) instead of
  dbt's default `<target_schema>_<custom_schema>` (`main_staging`).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ (custom_schema_name or target.schema) | trim }}
{%- endmacro %}
