# yourapp/templatetags/bangla_filters.py

from django import template
from django.utils.timesince import timesince
from django.utils.timezone import now

register = template.Library()

@register.filter
def bangla_timesince(value):
    # Get English timesince
    time_diff = timesince(value, now())
    
    # Dictionary for English to Bangla number conversion
    bangla_numbers = {
        '0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪',
        '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'
    }
    
    # Dictionary for English to Bangla time units (including plural forms)
    bangla_units = {
        'year': 'বছর',
        'years': 'বছর',
        'month': 'মাস',
        'months': 'মাস',
        'week': 'সপ্তাহ',
        'weeks': 'সপ্তাহ',
        'day': 'দিন',
        'days': 'দিন',
        'hour': 'ঘণ্টা',
        'hours': 'ঘণ্টা',
        'minute': 'মিনিট',
        'minutes': 'মিনিট',
        'second': 'সেকেন্ড',
        'seconds': 'সেকেন্ড',
        'ago': 'আগে'
    }
    
    # First convert numbers to Bangla
    for eng, ban in bangla_numbers.items():
        time_diff = time_diff.replace(eng, ban)
    
    # Split the string to handle multiple time units
    parts = time_diff.split(', ')
    bangla_parts = []
    
    for part in parts:
        # Handle each time unit separately
        for eng, ban in bangla_units.items():
            # Remove any trailing 's' from the English unit before replacement
            part = part.replace(f"{eng}s", eng)
            part = part.replace(eng, ban)
        bangla_parts.append(part)
    
    # Join the parts back together and add 'আগে' at the end
    result = ', '.join(bangla_parts)
    if 'আগে' not in result:
        result = f"{result} আগে"
    
    return result



@register.filter
def bangla_date(value):
    if not value:
        return ''
    
    # Dictionary for English to Bangla number conversion
    bangla_numbers = {
        '0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪',
        '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'
    }
    
    # Dictionary for English to Bangla month names
    bangla_months = {
        'January': 'জানুয়ারি',
        'February': 'ফেব্রুয়ারি',
        'March': 'মার্চ',
        'April': 'এপ্রিল',
        'May': 'মে',
        'June': 'জুন',
        'July': 'জুলাই',
        'August': 'আগস্ট',
        'September': 'সেপ্টেম্বর',
        'October': 'অক্টোবর',
        'November': 'নভেম্বর',
        'December': 'ডিসেম্বর'
    }
    
    # Format the date
    date_str = value.strftime('%d %B %Y')  # e.g., "31 December 2024"
    
    # Split the date string into parts
    day, month, year = date_str.split()
    
    # Convert day to Bangla
    bangla_day = ''.join([bangla_numbers[d] for d in day])
    
    # Convert month to Bangla
    bangla_month = bangla_months[month]
    
    # Convert year to Bangla
    bangla_year = ''.join([bangla_numbers[d] for d in year])
    
    # Combine all parts in Bangla format
    return f"{bangla_day} {bangla_month} {bangla_year}"



def convert_to_bangla_number(number):
    bangla_digits = {
        '0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪',
        '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'
    }
    return ''.join(bangla_digits.get(char, char) for char in str(number))

def get_bangla_month(month):
    bangla_months = {
        1: 'জানুয়ারি', 2: 'ফেব্রুয়ারি', 3: 'মার্চ', 4: 'এপ্রিল',
        5: 'মে', 6: 'জুন', 7: 'জুলাই', 8: 'আগস্ট',
        9: 'সেপ্টেম্বর', 10: 'অক্টোবর', 11: 'নভেম্বর', 12: 'ডিসেম্বর'
    }
    return bangla_months.get(month, '')


@register.filter
def bangla_number(value):
    return convert_to_bangla_number(value)

@register.filter
def bangla_month(value):
    return get_bangla_month(value)