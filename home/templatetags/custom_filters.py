from django import template
from bs4 import BeautifulSoup

register = template.Library()

@register.filter(is_safe=True)
def clean_rich_text(value):
    if not value:
        return ''
    
    soup = BeautifulSoup(value, 'html.parser')
    
    for tag in soup.find_all(True):
        if 'style' in tag.attrs:
            del tag.attrs['style']
            
        if tag.name == 'div':
            tag.name = 'p'
    
    return str(soup)



@register.filter
def to_bengali(value):
    bengali_digits = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯']
    value_str = str(value)
    bengali_value = ''.join([bengali_digits[int(digit)] for digit in value_str if digit.isdigit()])
    return bengali_value


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)
