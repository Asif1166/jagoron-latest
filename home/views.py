from django.shortcuts import redirect, render

from home.forms import ReviewForm
from home.models import *
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, get_object_or_404
from django.utils.timezone import now
from django.utils.timesince import timesince
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.utils import timezone
import io
import base64
from home.templatetags.bangla_filters import convert_to_bangla_number
# from rembg import remove
from PIL import Image, ImageEnhance, ImageFilter
import random
from datetime import date, datetime, timedelta
from calendar import monthrange
import json
import os
import uuid
from calendar import monthrange

# Create your views here.

def custom_404_view(request, exception):
    return render(request, '404.html', status=404)

def home(request):
    navbar = NavbarItem.objects.filter(is_active=True)

    # Get all active special news titles
    special_titles = SpecialNewTitle.objects.filter(is_active=True)

    # Get all news IDs that are part of an active special title
    excluded_news_ids = SpecialNewSection.objects.filter(
        special_news_title__is_active=True
    ).values_list('news_id', flat=True)

    # Build special news data (main + side news)
    special_news_data = []
    for title in special_titles:
        main_news = SpecialNewSection.objects.filter(
            special_news_title=title,
            main_news=True
        ).select_related('news').order_by('-created_at')[:2]


        side_news = SpecialNewSection.objects.filter(
            special_news_title=title,
            main_news=False
        ).select_related('news').order_by('-created_at')[:4]

        special_news_data.append({
            'title': title.title,
            'main_news': main_news,
            'side_news': side_news
        })

    # Handle selected section from query param
    selected_section_id = request.GET.get('section')
    news_items = None

    if selected_section_id:
        try:
            selected_section = NavbarItem.objects.get(id=selected_section_id)
            news_items = News.published.filter(section=selected_section).exclude(id__in=excluded_news_ids)
        except NavbarItem.DoesNotExist:
            selected_section = None
            news_items = News.objects.none()
    else:
        selected_section = None
        news_items = News.published.exclude(id__in=excluded_news_ids)

    # Last news
    last_news = News.published.exclude(id__in=excluded_news_ids).order_by('-created_at').first()

    # Live news
    live_news = News.published.filter(category__name="লাইভ").exclude(id__in=excluded_news_ids).order_by('-created_at').first()

    # Hero and secondary news
    hero_news = News.published.exclude(id__in=excluded_news_ids).order_by('-created_at')[1:5]
    secondary_news = News.published.exclude(id__in=excluded_news_ids).order_by('-created_at')[5:9]

    # Categories
    live_category = Category.objects.get(name="লাইভ")
    elected_category = Category.objects.get(name="নির্বাচিত খবর")

    # Elected news
    last_elected_news = News.published.filter(category=elected_category).exclude(id__in=excluded_news_ids).order_by('-created_at').first()
    elected_news = News.published.filter(category=elected_category).exclude(id__in=excluded_news_ids).order_by('-created_at')[1:5]

    # Section list (excluding most-read and active)
    sections = NavbarItem.objects.filter(is_active=False).exclude(title="সর্বাধিক পঠিত").order_by('position')

    # Most read news (based on NewsView model)
    most_read_news_ids = list(
        NewsView.objects.order_by('-count')[:5]
        .values_list('news_id', flat=True)
    )
    most_read_news = News.published.filter(id__in=most_read_news_ids).exclude(id__in=excluded_news_ids)

    # Bangla date conversion
    current_date = datetime.now()
    bangla_date = f"{convert_to_bangla_number(current_date.day)}"

    # Videos
    video_post = VideoPost.objects.all().order_by("-id")

    # Today's most viewed news
    today = now().date()
    todays_most_viewed_news = NewsView.objects.filter(
        news__created_at__date=today
    ).exclude(news__id__in=excluded_news_ids).order_by('-count')[:4]

    # Full URL for meta/sharing
    current_url = request.build_absolute_uri()

    context = {
        'navbar': navbar,
        'news_items': news_items,
        'selected_section': selected_section,
        'hero_news': hero_news,
        'secondary_news': secondary_news,
        'live_category': live_category,
        'elected_news': elected_news,
        'last_elected_news': last_elected_news,
        'sections': sections,
        'most_read_news': most_read_news,
        'last_news': last_news,
        'current_date': current_date,
        'bangla_date': bangla_date,
        'video_post': video_post,
        'todays_most_viewed_news': [view.news for view in todays_most_viewed_news],
        'current_url': current_url,
        'special_news_data': special_news_data
    }

    # Add live_news only if it's the same as last_news
    if last_news == live_news:
        context['live_news'] = live_news

    return render(request, 'home/home.html', context)



def get_subsections(request):
    section_id = request.GET.get('section_id')
    subsections = SubSection.objects.filter(section_id=section_id, is_active=True).order_by('position')
    data = [{'id': s.id, 'title': s.title} for s in subsections]
    return JsonResponse(data, safe=False)



def news_page(request):
    navbar = NavbarItem.objects.all()
    selected_section_id = request.GET.get('section')
    selected_subsection_id = request.GET.get('sub_section')
    page = request.GET.get('page', 1)

    selected_section = None
    selected_subsection = None
    subsections = None

    if selected_section_id:
        try:
            selected_section = NavbarItem.objects.get(id=selected_section_id)
            subsections = SubSection.objects.filter(section=selected_section, is_active=True).order_by('position')

            if selected_subsection_id:
                selected_subsection = SubSection.objects.filter(id=selected_subsection_id, section=selected_section).first()
                news_list = News.published.filter(section=selected_section, sub_section=selected_subsection)
            else:
                news_list = News.published.filter(section=selected_section)

        except NavbarItem.DoesNotExist:
            news_list = News.objects.none()
    else:
        news_list = News.published.all()

    news_list = news_list.order_by('-created_at')

    paginator = Paginator(news_list, 20)

    try:
        news_items = paginator.page(page)
    except PageNotAnInteger:
        news_items = paginator.page(1)
    except EmptyPage:
        news_items = paginator.page(paginator.num_pages)

    max_pages = paginator.num_pages
    current_page = news_items.number

    if max_pages <= 7:
        page_range = range(1, max_pages + 1)
    else:
        if current_page <= 4:
            page_range = list(range(1, 8))
        elif current_page > max_pages - 4:
            page_range = list(range(max_pages - 6, max_pages + 1))
        else:
            page_range = list(range(current_page - 3, current_page + 4))

    most_read_news_ids = list(
        NewsView.objects.order_by('-count')[:5].values_list('news_id', flat=True)
    )

    most_read_news = [News.objects.get(id=news_id) for news_id in most_read_news_ids]

    videos = News.published.filter(section__title="ভিডিও")
    
    # Pagination for videos
    video_list = VideoPost.objects.all().order_by("-id")
    video_paginator = Paginator(video_list, 12)  # 12 videos per page
    
    try:
        video_page_num = request.GET.get('video_page', 1)
        video_post = video_paginator.page(video_page_num)
    except PageNotAnInteger:
        video_post = video_paginator.page(1)
    except EmptyPage:
        video_post = video_paginator.page(video_paginator.num_pages)
    
    video_max_pages = video_paginator.num_pages
    video_current_page = video_post.number
    
    if video_max_pages <= 7:
        video_page_range = range(1, video_max_pages + 1)
    else:
        if video_current_page <= 4:
            video_page_range = list(range(1, 8))
        elif video_current_page > video_max_pages - 4:
            video_page_range = list(range(video_max_pages - 6, video_max_pages + 1))
        else:
            video_page_range = list(range(video_current_page - 3, video_current_page + 4))

    context = {
        'navbar': navbar,
        'news_items': news_items,
        'selected_section': selected_section,
        'selected_subsection': selected_subsection,
        'subsections': subsections,
        'page_range': page_range,
        'max_pages': max_pages,
        'current_page': current_page,
        'most_read_news': most_read_news,
        'videos': videos,
        'video_post': video_post,
        'video_page_range': video_page_range,
        'video_max_pages': video_max_pages,
        'video_current_page': video_current_page,
    }

    return render(request, 'pages/news.html', context)


def get_relevant_news(current_news, limit=8):
    """
    Get relevant news articles based on multiple factors:
    1. Same categories (highest priority)
    2. Same section
    3. Same subsection
    4. Title similarity
    5. Recent news (recency boost)
    """
    from django.db.models import Q, Count
    
    # Get current news categories
    current_categories = current_news.category.all()
    current_section = current_news.section
    current_subsection = current_news.sub_section
    
    # Base queryset - exclude current news and only published
    base_query = News.published.exclude(id=current_news.id)
    
    # Build relevance scoring
    relevant_news_list = []
    
    # Priority 1: Same categories AND same section (most relevant)
    if current_categories.exists() and current_section:
        category_news = base_query.filter(
            category__in=current_categories,
            section=current_section
        ).distinct()[:limit * 2]
        
        for item in category_news:
            if item.id not in [n.id for n in relevant_news_list]:
                relevant_news_list.append(item)
                if len(relevant_news_list) >= limit:
                    break
    
    # Priority 2: Same categories (even if different section)
    if len(relevant_news_list) < limit and current_categories.exists():
        category_news = base_query.filter(
            category__in=current_categories
        ).exclude(id__in=[n.id for n in relevant_news_list]).distinct()[:limit * 2]
        
        for item in category_news:
            if item.id not in [n.id for n in relevant_news_list]:
                relevant_news_list.append(item)
                if len(relevant_news_list) >= limit:
                    break
    
    # Priority 3: Same section and subsection
    if len(relevant_news_list) < limit and current_section and current_subsection:
        subsection_news = base_query.filter(
            section=current_section,
            sub_section=current_subsection
        ).exclude(id__in=[n.id for n in relevant_news_list]).distinct()[:limit * 2]
        
        for item in subsection_news:
            if item.id not in [n.id for n in relevant_news_list]:
                relevant_news_list.append(item)
                if len(relevant_news_list) >= limit:
                    break
    
    # Priority 4: Same section
    if len(relevant_news_list) < limit and current_section:
        section_news = base_query.filter(
            section=current_section
        ).exclude(id__in=[n.id for n in relevant_news_list]).distinct()[:limit * 2]
        
        for item in section_news:
            if item.id not in [n.id for n in relevant_news_list]:
                relevant_news_list.append(item)
                if len(relevant_news_list) >= limit:
                    break
    
    # Priority 5: Title similarity (if we still need more)
    if len(relevant_news_list) < limit and current_news.title:
        # Get words from current title
        current_title_words = set(current_news.title.lower().split())
        
        # Get recent news and check title similarity
        recent_news = base_query.exclude(id__in=[n.id for n in relevant_news_list]).order_by('-created_at')[:50]
        
        scored_news = []
        for item in recent_news:
            if item.title:
                item_title_words = set(item.title.lower().split())
                # Calculate similarity based on common words
                common_words = current_title_words.intersection(item_title_words)
                if common_words:
                    similarity = len(common_words) / max(len(current_title_words), len(item_title_words))
                    scored_news.append((item, similarity))
        
        # Sort by similarity and add top matches
        scored_news.sort(key=lambda x: x[1], reverse=True)
        for item, score in scored_news[:limit - len(relevant_news_list)]:
            if item.id not in [n.id for n in relevant_news_list]:
                relevant_news_list.append(item)
                if len(relevant_news_list) >= limit:
                    break
    
    # Priority 6: Recent news (fill remaining slots)
    if len(relevant_news_list) < limit:
        recent_news = base_query.exclude(id__in=[n.id for n in relevant_news_list]).order_by('-created_at')[:limit - len(relevant_news_list)]
        for item in recent_news:
            if item.id not in [n.id for n in relevant_news_list]:
                relevant_news_list.append(item)
                if len(relevant_news_list) >= limit:
                    break
    
    return relevant_news_list[:limit]


def news_detail(request, news_id):
    # Allow viewing scheduled news in detail (for preview), but check if published
    try:
        news = News.objects.get(id=news_id)
        # If news is scheduled and user is not staff, return 404
        if news.is_scheduled and not request.user.is_staff:
            from django.http import Http404
            raise Http404("News not found")
    except News.DoesNotExist:
        from django.http import Http404
        raise Http404("News not found")

    news_view, created = NewsView.objects.get_or_create(news=news)
    news_view.count += 1
    news_view.save()

    navbar = NavbarItem.objects.all()
    
    # Smart relevant news algorithm
    related_news = get_relevant_news(news, limit=8)
  
    main_news = News.published.filter(section=news.section, category__name="প্রধান খবর").exclude(id=news_id).order_by('-created_at')[:3]
    elected_news = News.published.filter(section=news.section, category__name="নির্বাচিত খবর").exclude(id=news_id).order_by('-created_at')[:5]

    most_read_news_ids = list(
        NewsView.objects.order_by('-count')[:5]
        .values_list('news_id', flat=True)
    )

    most_read_news = [News.published.get(id=news_id) for news_id in most_read_news_ids if News.published.filter(id=news_id).exists()]


    reaction_counts = NewsReaction.objects.filter(news=news)\
        .values('reaction')\
        .annotate(count=Count('reaction'))

    # Convert to dict: {'love': 10, 'clap': 5, ...}
    counts = {r['reaction']: r['count'] for r in reaction_counts}
    total = sum(counts.values())


    reviews = news.reviews.select_related('user').order_by('-created_at')
    form = ReviewForm()

    if request.method == 'POST':
        if request.user.is_authenticated:
            form = ReviewForm(request.POST)
            if form.is_valid():
                review = form.save(commit=False)
                review.news = news
                review.user = request.user
                review.save()
                return redirect('news_detail', news_id=news.pk)
        else:
            form.add_error(None, "মন্তব্য করতে হলে আপনাকে লগইন করতে হবে।")

    context = {
        'news': news,
        'navbar': navbar,
        'related_news': related_news,
        'main_news': main_news,
        'elected_news': elected_news,
        'most_read_news': most_read_news,
        'reaction_counts': counts,
        'reaction_total': total,
        'reviews': reviews,
        'form': form,
    }
    return render(request, 'pages/news_detail.html', context)



def default_page_detail(request, link):
    page = get_object_or_404(Default_pages, link=link)

    main_news = News.published.filter(category__name="প্রধান খবর").order_by('-created_at')[:3]
    elected_news = News.published.filter(category__name="নির্বাচিত খবর").order_by('-created_at')[:5]


    most_read_news_ids = list(
        NewsView.objects.order_by('-count')[:5]
        .values_list('news_id', flat=True)
    )

    most_read_news = [News.published.get(id=news_id) for news_id in most_read_news_ids if News.published.filter(id=news_id).exists()]



    context = {
        'page': page,
   
        'main_news': main_news,
        'elected_news': elected_news,
        'most_read_news': most_read_news,
    }

    return render(request, 'pages/default_page_detail.html', context)


def generate_photo(request):
    if request.method == 'POST':
        try:
            
            from rembg import remove
            
            uploaded_image = request.FILES.get('image')

            uploaded = Image.open(uploaded_image)

            # uploaded_no_bg = remove(uploaded) 

            uploaded_bw = uploaded_no_bg.convert('LA').convert('RGBA')

            background = Image.new('RGB', (1000, 1000), 'white')

            width_ratio = 1000 / uploaded_bw.width
            height_ratio = 1000 / uploaded_bw.height
            scale_ratio = max(width_ratio, height_ratio)

            new_width = int(uploaded_bw.width * scale_ratio)
            new_height = int(uploaded_bw.height * scale_ratio)

            uploaded_bw = uploaded_bw.resize((new_width, new_height), Image.LANCZOS)

            transparent_layer = Image.new('RGBA', (new_width, new_height), (255, 255, 255, 120))  # 100 = more transparent
            uploaded_bw = Image.alpha_composite(uploaded_bw, transparent_layer)

            upload_position = (
                (1000 - new_width) // 2,
                (1000 - new_height) // 2
            )

            temp_layer = Image.new('RGBA', (1000, 1000), (0, 0, 0, 0))

            temp_layer.paste(uploaded_bw, upload_position, uploaded_bw)

            background.paste(temp_layer, (0, 0), temp_layer)

            logo = Image.open('static/image/fav-logo1.png')

            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')

            logo = logo.resize((1000, 1000), Image.LANCZOS)

            logo_data = list(logo.getdata())
            new_logo_data = []

            TARGET_RED = (130, 0, 0)

            for r, g, b, a in logo_data:
                if a > 0:
                    if r > g and r > b:
                        new_logo_data.append((max(0, r - 40), 0, 0, int(a * 0.6)))
                    else:
                        new_logo_data.append((r, g, b, int(a * 0.6)))
                else:
                    new_logo_data.append((r, g, b, a))

            logo.putdata(new_logo_data)

            combined = Image.new('RGB', (1000, 1000), 'white')
            combined.paste(background, (0, 0))
            combined.paste(logo, (0, 0), logo)

            enhancer = ImageEnhance.Contrast(combined)
            combined = enhancer.enhance(1.5)
            
            # 🆕 Step: Apply a Sharpen filter
            combined = combined.filter(ImageFilter.SHARPEN)

            buffer = io.BytesIO()
            # combined.save(buffer, format='PNG', quality=95)
            combined.save(buffer, format='PNG', quality=95, optimize=True)
            image_str = base64.b64encode(buffer.getvalue()).decode()

            return JsonResponse({
                'status': 'success',
                'image': f'data:image/png;base64,{image_str}'
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    return render(request, 'pages/generate_photo.html')



def search_news(request):
    query = request.GET.get('q', '')
    results = News.published.filter(title__icontains=query) if query else []
    return render(request, 'pages/search_results.html', {'results': results, 'query': query})


def redirect_short_url(request, short_code):
    short_url = get_object_or_404(ShortURL, short_code=short_code)
    short_url.clicks += 1
    short_url.save()
    return redirect(short_url.original_url)

def create_short_url(request):
    if request.method == 'POST':
        original_url = request.POST.get('url')
        if not original_url:
            return JsonResponse({'error': 'URL is required'}, status=400)
            
        short_url = ShortURL.create_short_url(original_url)
        short_url_full = request.build_absolute_uri(f'/s/{short_url.short_code}/')
        
        return JsonResponse({
            'original_url': original_url,
            'short_url': short_url_full
        })
    return JsonResponse({'error': 'POST method required'}, status=400)


@csrf_exempt
def ckeditor_upload(request):
    """Handle CKEditor image uploads"""
    if request.method == 'POST' and request.FILES.get('upload'):
        upload = request.FILES['upload']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if upload.content_type not in allowed_types:
            return JsonResponse({
                'error': {
                    'message': 'Invalid file type. Only images are allowed.'
                }
            }, status=400)
        
        # Generate unique filename
        file_ext = os.path.splitext(upload.name)[1]
        filename = f"{uuid.uuid4()}{file_ext}"
        
        # Save file to media/uploads/ directory
        upload_path = os.path.join('uploads', filename)
        file_path = default_storage.save(upload_path, ContentFile(upload.read()))
        
        # Get the URL
        file_url = default_storage.url(file_path)
        
        # Return CKEditor expected response
        return JsonResponse({
            'url': file_url,
            'uploaded': 1,
            'fileName': filename
        })
    
    return JsonResponse({
        'error': {
            'message': 'No file uploaded'
        }
    }, status=400)

@staff_member_required
def admin_dashboard(request):
    """Admin dashboard view with charts"""
    return render(request, 'admin/dashboard.html')

@staff_member_required
def dashboard_image_stats(request):
    """API endpoint for image upload statistics by month"""
    month = request.GET.get('month', None)
    year = request.GET.get('year', None)
    
    if month and year:
        try:
            month = int(month)
            year = int(year)
            start_date = timezone.make_aware(datetime(year, month, 1))
            if month == 12:
                end_date = timezone.make_aware(datetime(year + 1, 1, 1))
            else:
                end_date = timezone.make_aware(datetime(year, month + 1, 1))
        except (ValueError, TypeError):
            month = None
            year = None
    
    if not month or not year:
        # Default to current month
        now = timezone.now()
        month = now.month
        year = now.year
        start_date = timezone.make_aware(datetime(year, month, 1))
        if month == 12:
            end_date = timezone.make_aware(datetime(year + 1, 1, 1))
        else:
            end_date = timezone.make_aware(datetime(year, month + 1, 1))
    
    # Get all days in the month
    days_in_month = monthrange(year, month)[1]
    labels = [str(day) for day in range(1, days_in_month + 1)]
    
    # Count images uploaded per day
    heading_images = News.objects.filter(
        created_at__year=year,
        created_at__month=month,
        heading_image__isnull=False
    ).exclude(heading_image='').values('created_at__day').annotate(count=Count('id'))
    
    main_images = News.objects.filter(
        created_at__year=year,
        created_at__month=month,
        main_image__isnull=False
    ).exclude(main_image='').values('created_at__day').annotate(count=Count('id'))
    
    # Create data arrays
    heading_data = [0] * days_in_month
    main_data = [0] * days_in_month
    
    for item in heading_images:
        day = item['created_at__day'] - 1
        heading_data[day] = item['count']
    
    for item in main_images:
        day = item['created_at__day'] - 1
        main_data[day] = item['count']
    
    return JsonResponse({
        'labels': labels,
        'datasets': [
            {
                'label': 'Heading Images',
                'data': heading_data,
                'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'borderWidth': 1
            },
            {
                'label': 'Main Images',
                'data': main_data,
                'backgroundColor': 'rgba(255, 99, 132, 0.5)',
                'borderColor': 'rgba(255, 99, 132, 1)',
                'borderWidth': 1
            }
        ]
    })

@staff_member_required
def dashboard_reporter_stats(request):
    """API endpoint for daily news count per reporter (created_by user)"""
    month = request.GET.get('month', None)
    year = request.GET.get('year', None)
    
    if month and year:
        try:
            month = int(month)
            year = int(year)
        except (ValueError, TypeError):
            month = None
            year = None
    
    if not month or not year:
        # Default to current month
        now = timezone.now()
        month = now.month
        year = now.year
    
    # Get all unique users (reporters) who created news in this month
    # Use distinct() properly and convert to set to ensure uniqueness
    reporter_ids = set(News.objects.filter(
        created_at__year=year,
        created_at__month=month
    ).exclude(created_by__isnull=True).values_list('created_by_id', flat=True).distinct())
    
    days_in_month = monthrange(year, month)[1]
    labels = [str(day) for day in range(1, days_in_month + 1)]
    
    datasets = []
    colors = [
        {'bg': 'rgba(54, 162, 235, 0.5)', 'border': 'rgba(54, 162, 235, 1)'},
        {'bg': 'rgba(255, 99, 132, 0.5)', 'border': 'rgba(255, 99, 132, 1)'},
        {'bg': 'rgba(255, 206, 86, 0.5)', 'border': 'rgba(255, 206, 86, 1)'},
        {'bg': 'rgba(75, 192, 192, 0.5)', 'border': 'rgba(75, 192, 192, 1)'},
        {'bg': 'rgba(153, 102, 255, 0.5)', 'border': 'rgba(153, 102, 255, 1)'},
        {'bg': 'rgba(255, 159, 64, 0.5)', 'border': 'rgba(255, 159, 64, 1)'},
    ]
    
    # Import User model
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Convert to list and limit to 10 reporters
    reporter_ids_list = list(reporter_ids)[:10]
    
    for idx, user_id in enumerate(reporter_ids_list):
        if not user_id:  # Skip None values
            continue
            
        try:
            user = User.objects.get(id=user_id)
            # Use a combination of ID and name to ensure uniqueness in the chart
            reporter_name = user.get_full_name() or user.username or f'User {user_id}'
            # Add user ID to make it unique if needed
            display_name = f"{reporter_name} (ID: {user_id})"
        except User.DoesNotExist:
            display_name = f'Unknown User {user_id}'
        
        color = colors[idx % len(colors)]
        data = [0] * days_in_month
        
        news_items = News.objects.filter(
            created_at__year=year,
            created_at__month=month,
            created_by_id=user_id
        ).values('created_at__day').annotate(count=Count('id'))
        
        for item in news_items:
            day = item['created_at__day'] - 1
            data[day] = item['count']
        
        datasets.append({
            'label': display_name,
            'data': data,
            'backgroundColor': color['bg'],
            'borderColor': color['border'],
            'borderWidth': 1
        })
    
    return JsonResponse({
        'labels': labels,
        'datasets': datasets
    })

@staff_member_required
def dashboard_content_stats(request):
    """API endpoint for total content statistics (weekly/monthly/yearly)"""
    try:
        view_type = request.GET.get('view', 'monthly')  # weekly, monthly, yearly
        month = request.GET.get('month', None)
        year = request.GET.get('year', None)
        
        now = timezone.now()
        if not month or not year:
            month = now.month
            year = now.year
        
        try:
            month = int(month)
            year = int(year)
        except (ValueError, TypeError):
            month = now.month
            year = now.year
        
        # Calculate date ranges based on view type
        if view_type == 'weekly':
            # Get the start of the month
            month_start = timezone.make_aware(datetime(year, month, 1))
            days_in_month = monthrange(year, month)[1]
            month_end = timezone.make_aware(datetime(year, month, days_in_month, 23, 59, 59))
            
            # Generate labels for 4 weeks
            labels = []
            datasets = {
                'news': [],
                'videos': [],
                'images': []
            }
            
            # Calculate week boundaries
            for week in range(4):
                week_start = month_start + timedelta(weeks=week)
                week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
                
                # Make sure we don't go beyond the month
                if week_start > month_end:
                    # No more weeks in this month
                    break
                if week_end > month_end:
                    week_end = month_end
                
                week_label = f"Week {week + 1}\n({week_start.strftime('%d/%m')}-{week_end.strftime('%d/%m')})"
                labels.append(week_label)
                
                # Count news
                news_count = News.objects.filter(
                    created_at__gte=week_start,
                    created_at__lte=week_end
                ).count()
                datasets['news'].append(news_count)
                
                # Count videos
                video_count = VideoPost.objects.filter(
                    created_at__gte=week_start,
                    created_at__lte=week_end
                ).count()
                datasets['videos'].append(video_count)
                
                # Count images (heading + main)
                heading_images = News.objects.filter(
                    created_at__gte=week_start,
                    created_at__lte=week_end,
                    heading_image__isnull=False
                ).exclude(heading_image='').count()
                
                main_images = News.objects.filter(
                    created_at__gte=week_start,
                    created_at__lte=week_end,
                    main_image__isnull=False
                ).exclude(main_image='').count()
                
                datasets['images'].append(heading_images + main_images)
        
        elif view_type == 'yearly':
            # Generate labels for 12 months
            labels = []
            datasets = {
                'news': [],
                'videos': [],
                'images': []
            }
            
            for m in range(1, 13):
                month_start = timezone.make_aware(datetime(year, m, 1))
                if m == 12:
                    month_end = timezone.make_aware(datetime(year + 1, 1, 1))
                else:
                    month_end = timezone.make_aware(datetime(year, m + 1, 1))
                
                labels.append(datetime(year, m, 1).strftime('%b'))
                
                # Count news
                news_count = News.objects.filter(
                    created_at__gte=month_start,
                    created_at__lt=month_end
                ).count()
                datasets['news'].append(news_count)
                
                # Count videos
                video_count = VideoPost.objects.filter(
                    created_at__gte=month_start,
                    created_at__lt=month_end
                ).count()
                datasets['videos'].append(video_count)
                
                # Count images
                heading_images = News.objects.filter(
                    created_at__gte=month_start,
                    created_at__lt=month_end,
                    heading_image__isnull=False
                ).exclude(heading_image='').count()
                
                main_images = News.objects.filter(
                    created_at__gte=month_start,
                    created_at__lt=month_end,
                    main_image__isnull=False
                ).exclude(main_image='').count()
                
                datasets['images'].append(heading_images + main_images)
        
        else:  # monthly (default)
            # Generate labels for days in the month
            days_in_month = monthrange(year, month)[1]
            labels = [str(day) for day in range(1, days_in_month + 1)]
            
            datasets = {
                'news': [0] * days_in_month,
                'videos': [0] * days_in_month,
                'images': [0] * days_in_month
            }
            
            # Count news per day
            news_items = News.objects.filter(
                created_at__year=year,
                created_at__month=month
            ).values('created_at__day').annotate(count=Count('id'))
            
            for item in news_items:
                day = item['created_at__day'] - 1
                datasets['news'][day] = item['count']
            
        # Count videos per day
        video_items = VideoPost.objects.filter(
            created_at__year=year,
            created_at__month=month
        ).values('created_at__day').annotate(count=Count('id'))
        
        for item in video_items:
            day = item['created_at__day'] - 1
            datasets['videos'][day] = item['count']
            
            # Count images per day
            heading_images = News.objects.filter(
                created_at__year=year,
                created_at__month=month,
                heading_image__isnull=False
            ).exclude(heading_image='').values('created_at__day').annotate(count=Count('id'))
            
            main_images = News.objects.filter(
                created_at__year=year,
                created_at__month=month,
                main_image__isnull=False
            ).exclude(main_image='').values('created_at__day').annotate(count=Count('id'))
            
            for item in heading_images:
                day = item['created_at__day'] - 1
                datasets['images'][day] += item['count']
            
            for item in main_images:
                day = item['created_at__day'] - 1
                datasets['images'][day] += item['count']
        
        return JsonResponse({
            'labels': labels,
            'datasets': [
                {
                    'label': 'News Articles',
                    'data': datasets['news'],
                    'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                    'borderColor': 'rgba(54, 162, 235, 1)',
                    'borderWidth': 2
                },
                {
                    'label': 'Videos',
                    'data': datasets['videos'],
                    'backgroundColor': 'rgba(255, 99, 132, 0.5)',
                    'borderColor': 'rgba(255, 99, 132, 1)',
                    'borderWidth': 2
                },
                {
                    'label': 'Images',
                    'data': datasets['images'],
                    'backgroundColor': 'rgba(255, 206, 86, 0.5)',
                    'borderColor': 'rgba(255, 206, 86, 1)',
                    'borderWidth': 2
                }
            ]
        })
    except Exception as e:
        import traceback
        error_message = str(e)
        traceback.print_exc()
        return JsonResponse({
            'error': error_message,
            'labels': [],
            'datasets': []
        }, status=500)

def react_to_news(request, news_id):
    if request.method == "POST":
        reaction = request.POST.get('reaction')
        news = News.objects.get(id=news_id)

        # Prevent multiple reactions per user per news
        existing = NewsReaction.objects.filter(news=news, user=request.user)
        if existing.exists():
            existing.update(reaction=reaction)
        else:
            NewsReaction.objects.create(news=news, user=request.user, reaction=reaction)

        return JsonResponse({'status': 'ok'})