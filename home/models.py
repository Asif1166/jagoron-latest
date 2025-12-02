from django.db import models
from ckeditor.fields import RichTextField
from django.conf import settings
from PIL import Image
import os
import logging
from django.core.files.images import get_image_dimensions
from django.core.exceptions import ValidationError
from urllib.parse import urlparse, parse_qs
import random
import string

# Create your models here.
class NavbarItem(models.Model):
    title = models.CharField(max_length=100)
    link = models.CharField(max_length=100)
    position = models.IntegerField(help_text="Position of the menu item")
    is_active = models.BooleanField(default=True)

    def get_absolute_url(self):
        return f'/news/?section={self.id}'

    def __str__(self):
        return self.title
    
class SubSection(models.Model):
    section = models.ForeignKey(NavbarItem, on_delete=models.CASCADE, blank=True, null=True)
    title = models.CharField(max_length=100, blank=True, null=True)
    position = models.IntegerField(help_text="Position of the sub section")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
        

    def __str__(self):
        return self.title

class Category(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

logger = logging.getLogger(__name__)


def validate_image(image):
    if not image:
        return

    max_width = 10000
    max_height = 10000
    max_size = 30 * 1024 * 1024

    if image.size > max_size:
        raise ValidationError(f'Max file size is {max_size/1024/1024}MB')

    width, height = get_image_dimensions(image)
    if width > max_width or height > max_height:
        raise ValidationError(f'Max dimensions are {max_width}x{max_height}')

class News(models.Model):
    section = models.ForeignKey(NavbarItem, on_delete=models.CASCADE, blank=True, null=True)
    sub_section = models.ForeignKey(SubSection, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ManyToManyField(Category, blank=True)
    
    top_sub_title = models.CharField(max_length=1000, blank=True, null=True)
    title = models.CharField(max_length=1000, blank=True, null=True)
    sub_title = models.CharField(max_length=1000, blank=True, null=True)


    sub_content = models.TextField(max_length=1000, blank=True, null=True)
    news_content = RichTextField(blank=True, null=True, config_name='custom_config')
    
    heading_image = models.ImageField(
        upload_to="news/", 
        validators=[validate_image]
    )
    heading_image_title = models.CharField(max_length=1000, blank=True, null=True)

    main_image = models.ImageField(
        upload_to="news/", 
        blank=True, 
        null=True, 
        validators=[validate_image]
    )
    main_image_title = models.CharField(max_length=1000, blank=True, null=True)
    

    reporter = models.CharField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        save_needed = False

        try:
            if self.heading_image:
                new_path = self.convert_to_webp(self.heading_image)
                if new_path:
                    self.heading_image.name = new_path
                    save_needed = True

            if self.main_image:
                new_path = self.convert_to_webp(self.main_image)
                if new_path:
                    self.main_image.name = new_path
                    save_needed = True

            if save_needed:
                super().save(*args, **kwargs)

        except Exception as e:
            logger.error(f"Error processing images for News ID {self.id}: {e}")

        # try:
        #     if self.heading_image:
        #         self.compress_and_resize_image(self.heading_image.path)
        #         save_needed = True

        #     if self.main_image:
        #         self.compress_and_resize_image(self.main_image.path)
        #         save_needed = True

        #     if save_needed:
        #         super().save(*args, **kwargs)

        # except Exception as e:
        #     logger.error(f"Error processing images for News ID {self.id}: {e}")


    def convert_to_webp(self, image_field):
        try:
            image_path = image_field.path
            img = Image.open(image_path)

            if img.mode != 'RGB':
                img = img.convert('RGB')

            # max_size = (600, 600)
            max_size = (1200, 800) # 🆕 Example: Increased Max Size
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            base, ext = os.path.splitext(image_path)
            webp_path = base + '.webp'

            # img.save(webp_path, 'WEBP', quality=70, optimize=True)
            img.save(webp_path, 'WEBP', quality=90, optimize=True) # <- INCREASED QUALITY

            if os.path.exists(image_path):
                os.remove(image_path)

            relative_path = image_field.name
            relative_base, _ = os.path.splitext(relative_path)
            return relative_base + '.webp'

        except Exception as e:
            logger.error(f"Error converting image to WebP: {e}")
            return None

    def compress_and_resize_image(self, image_path):
        try:
            with Image.open(image_path) as img:
                original_format = img.format
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # max_size = (600, 600)
                max_size = (1280, 720)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

                quality = 70
                min_quality = 30
                max_file_size = 50 * 1024

                while True:
                    temp_path = image_path + '.temp'
                    img.save(
                        temp_path, 
                        format=original_format, 
                        quality=quality, 
                        optimize=True
                    )
                    
                    file_size = os.path.getsize(temp_path)
                    
                    if file_size <= max_file_size or quality <= min_quality:
                        os.replace(temp_path, image_path)
                        break

                    quality -= 5

                logger.info(f"Image compressed: {image_path}, Final quality: {quality}")

        except Exception as e:
            logger.error(f"Error compressing image {image_path}: {e}")

    def delete(self, *args, **kwargs):

        if self.heading_image:
            try:
                if os.path.isfile(self.heading_image.path):
                    os.remove(self.heading_image.path)
            except Exception as e:
                logger.error(f"Error deleting heading image: {e}")

        if self.main_image:
            try:
                if os.path.isfile(self.main_image.path):
                    os.remove(self.main_image.path)
            except Exception as e:
                logger.error(f"Error deleting main image: {e}")

        super().delete(*args, **kwargs)

    def get_absolute_url(self):
        return f'/news/detail/{self.id}/'

    def __str__(self):
        return self.title or 'Untitled News'

    class Meta:
        verbose_name_plural = "News"
        ordering = ['-created_at']


class NewsView(models.Model):
    news = models.OneToOneField(News, on_delete=models.CASCADE, related_name="views")
    count = models.IntegerField(default=0)


class SiteInfo(models.Model):
    logo = models.ImageField(upload_to="logo/", blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)


class Default_pages(models.Model):
    title = models.CharField(max_length=100, blank=True, null=True)
    news_content = RichTextField(blank=True, null=True, config_name='custom_config')
    
    link = models.CharField(max_length=250, blank=True, null=True)

    def __str__(self):
        return self.title or 'Default_pages'

    class Meta:
        verbose_name_plural = "Default_pages"


class VideoPost(models.Model):
    section = models.ForeignKey(
        NavbarItem,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=None,
        editable=False
    )
    video_title = models.CharField(max_length=1000, blank=True, null=True)
    youtube_link = models.URLField()

    def save(self, *args, **kwargs):
        if not self.section:
            self.section = NavbarItem.objects.filter(title="ভিডিও").first()

        parsed_url = urlparse(self.youtube_link)
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get('v', [None])[0]
        if video_id:
            self.youtube_link = f"https://www.youtube.com/embed/{video_id}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.video_title or 'No Title'
    

    @property
    def embed_url(self):
        parsed_url = urlparse(self.youtube_link)
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get('v', [None])[0]
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"
        return None
    





class ShortURL(models.Model):
    original_url = models.URLField()
    short_code = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    clicks = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.short_code} -> {self.original_url}"
    
    @classmethod
    def create_short_url(cls, original_url):
        existing = cls.objects.filter(original_url=original_url).first()
        if existing:
            return existing
            
        def generate_code():
            chars = string.ascii_letters + string.digits
            return ''.join(random.choice(chars) for _ in range(6))
            
        code = generate_code()
        while cls.objects.filter(short_code=code).exists():
            code = generate_code()
            
        short_url = cls.objects.create(
            original_url=original_url,
            short_code=code
        )
        return short_url
    
class SpecialNewTitle(models.Model):
    title = models.CharField(max_length=250, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title or 'No Title'
    

class SpecialNewSection(models.Model):
    special_news_title = models.ForeignKey(SpecialNewTitle, on_delete=models.CASCADE, blank=True, null=True)
    news = models.ForeignKey(News, on_delete=models.CASCADE, blank=True, null=True)

    main_news = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)




class NewsReaction(models.Model):
    REACTIONS = (
        ('love', '❤️ Love'),
        ('clap', '👏 Clap'),
        ('smile', '🙂 Smile'),
        ('sad', '😞 Sad'),
    )

    news = models.ForeignKey('News', on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reaction = models.CharField(max_length=10, choices=REACTIONS)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} reacted with {self.reaction}"
    

class Review(models.Model):
    news = models.ForeignKey(News, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    comment = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review by {self.user} on {self.news.title}'

    


