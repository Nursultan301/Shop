from django import template
from django.utils.safestring import mark_safe



register = template.Library()

TABLE_HEAD = """
                <table class="table">
                    <tbody>
             """

TABLE_TAIL = """
                </tbody>
                    </table>
             """

TABLE_CONTENT = """
                <tr>
                    <td>{name}</td>
                    <td>{value}</td>
                </tr>
                """


PRODUCT_SPEC = {
    'notebook': {
        'Диагональ': 'diagonal',
        'Тип дисплея': 'display_type',
        'Частота процессора': 'processor_freq',
        'Опаративная память': 'ram',
        'Видеокарта': 'video',
        'Время работы аккумулятора': 'time_without_charge',

    },
    'smartphone': {
        'Диагональ': 'diagonal',
        'Тип дисплея': 'display_type',
        'Разрешение экрана': 'resolution',
        'Объем батереи': 'accum_volume',
        'Опаративная память': 'ram',
'Фронтальная камера (МП)': 'frontal_cam_mp',
        'Камера (МП)': 'main_cam_mp',
        'Наличие слота для SD карты': 'sd_v',
        'Максимальный объем SD карты': 'sd_volume_max',
    }
}


@register.filter
def product_spec(product):
    content = ''
    model_name = product.__class__._meta.model_name
    sd_bool = True if model_name == 'smartphone' and product.sd else False
    for name, value in PRODUCT_SPEC[model_name].items():
        if not sd_bool and name == 'Максимальный объем SD карты':
            continue
        else:
            content += TABLE_CONTENT.format(name=name, value=getattr(product, value))
    return mark_safe(TABLE_HEAD + content + TABLE_TAIL)

