
from home.templatetags.bangla_filters import convert_to_bangla_number
from .models import *
from datetime import datetime
from collections import defaultdict
def default(request):
    site_info = SiteInfo.objects.first()
    navbar_item = NavbarItem.objects.filter(is_active=True).order_by('position')
    default_pages = Default_pages.objects.all()
    current_date = datetime.now()
    bangla_date = f"{convert_to_bangla_number(current_date.day)}"

    # Group subsections by section
    subsection_map = defaultdict(list)
    for sub in SubSection.objects.filter(is_active=True).select_related('section').order_by('position'):
        if sub.section:
            subsection_map[sub.section.id].append(sub)

    return {
        'site_info': site_info,
        'navbar_item': navbar_item,
        'default_pages': default_pages,
        'bangla_date': bangla_date,
        'current_date': current_date,
        'subsection_map': subsection_map,
    }