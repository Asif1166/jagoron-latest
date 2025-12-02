from django.shortcuts import redirect, render

from home.forms import ReviewForm
from home.models import *
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, get_object_or_404
from django.utils.timezone import now
from django.utils.timesince import timesince
from django.http import JsonResponse
import io
import base64
from home.templatetags.bangla_filters import convert_to_bangla_number
# from rembg import remove
from PIL import Image, ImageEnhance, ImageFilter
import random
from datetime import date
from datetime import datetime
from django.db.models import Count
import json

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
            news_items = News.objects.filter(section=selected_section).exclude(id__in=excluded_news_ids)
        except NavbarItem.DoesNotExist:
            selected_section = None
            news_items = News.objects.none()
    else:
        selected_section = None
        news_items = News.objects.exclude(id__in=excluded_news_ids)

    # Last news
    last_news = News.objects.exclude(id__in=excluded_news_ids).order_by('-id').first()

    # Live news
    live_news = News.objects.filter(category__name="লাইভ").exclude(id__in=excluded_news_ids).last()

    # Hero and secondary news
    hero_news = News.objects.exclude(id__in=excluded_news_ids).order_by('-id')[1:5]
    secondary_news = News.objects.exclude(id__in=excluded_news_ids).order_by('-id')[5:9]

    # Categories
    live_category = Category.objects.get(name="লাইভ")
    elected_category = Category.objects.get(name="নির্বাচিত খবর")

    # Elected news
    last_elected_news = News.objects.filter(category=elected_category).exclude(id__in=excluded_news_ids).order_by('-id').first()
    elected_news = News.objects.filter(category=elected_category).exclude(id__in=excluded_news_ids).order_by('-id')[1:5]

    # Section list (excluding most-read and active)
    sections = NavbarItem.objects.filter(is_active=False).exclude(title="সর্বাধিক পঠিত").order_by('position')

    # Most read news (based on NewsView model)
    most_read_news_ids = list(
        NewsView.objects.order_by('-count')[:5]
        .values_list('news_id', flat=True)
    )
    most_read_news = News.objects.filter(id__in=most_read_news_ids).exclude(id__in=excluded_news_ids)

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
                news_list = News.objects.filter(section=selected_section, sub_section=selected_subsection)
            else:
                news_list = News.objects.filter(section=selected_section)

        except NavbarItem.DoesNotExist:
            news_list = News.objects.none()
    else:
        news_list = News.objects.all()

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

    videos = News.objects.filter(section__title="ভিডিও")
    video_post = VideoPost.objects.all().order_by("-id")




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
    }

    return render(request, 'pages/news.html', context)



def news_detail(request, news_id):
    news = News.objects.get(id=news_id)

    news_view, created = NewsView.objects.get_or_create(news=news)
    news_view.count += 1
    news_view.save()

    navbar = NavbarItem.objects.all()
    related_news = News.objects.filter(section=news.section).exclude(id=news_id).order_by('-id')[:21]
  
    main_news = News.objects.filter(section=news.section, category__name="প্রধান খবর").exclude(id=news_id).order_by('-id')[:3]
    elected_news = News.objects.filter(section=news.section, category__name="নির্বাচিত খবর").exclude(id=news_id).order_by('-id')[:5]

    most_read_news_ids = list(
        NewsView.objects.order_by('-count')[:5]
        .values_list('news_id', flat=True)
    )

    most_read_news = [News.objects.get(id=news_id) for news_id in most_read_news_ids]


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

    main_news = News.objects.filter(category__name="প্রধান খবর").order_by('-id')[:3]
    elected_news = News.objects.filter(category__name="নির্বাচিত খবর").order_by('-id')[:5]


    most_read_news_ids = list(
        NewsView.objects.order_by('-count')[:5]
        .values_list('news_id', flat=True)
    )

    most_read_news = [News.objects.get(id=news_id) for news_id in most_read_news_ids]



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
    results = News.objects.filter(title__icontains=query) if query else []
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