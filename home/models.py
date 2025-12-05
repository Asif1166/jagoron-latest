from django.db import models
from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField
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

class PublishedNewsManager(models.Manager):
    """Manager to filter only published news"""
    def get_queryset(self):
        from django.utils import timezone
        now = timezone.now()
        return super().get_queryset().filter(
            models.Q(scheduled_publish_at__isnull=True) | 
            models.Q(scheduled_publish_at__lte=now)
        )

class News(models.Model):
    section = models.ForeignKey(NavbarItem, on_delete=models.CASCADE, blank=True, null=True)
    sub_section = models.ForeignKey(SubSection, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ManyToManyField(Category, blank=True)
    
    # Managers
    objects = models.Manager()  # Default manager (includes all news)
    published = PublishedNewsManager()  # Manager for published news only
    
    top_sub_title = models.CharField(max_length=1000, blank=True, null=True)
    title = models.CharField(max_length=1000, blank=True, null=True)
    sub_title = models.CharField(max_length=1000, blank=True, null=True)


    sub_content = models.TextField(max_length=1000, blank=True, null=True)
    news_content = RichTextUploadingField(blank=True, null=True, config_name='custom_config')
    
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
    scheduled_publish_at = models.DateTimeField(blank=True, null=True, help_text="Schedule this news to be published at a specific date and time")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
    
    @property
    def is_published(self):
        """Check if news is published (scheduled time has passed or no schedule set)"""
        from django.utils import timezone
        if self.scheduled_publish_at:
            return timezone.now() >= self.scheduled_publish_at
        return True  # If no schedule, consider it published
    
    @property
    def is_scheduled(self):
        """Check if news is scheduled for future publication"""
        from django.utils import timezone
        if self.scheduled_publish_at:
            return timezone.now() < self.scheduled_publish_at
        return False

    def save(self, *args, **kwargs):
        # Track if new images were uploaded
        heading_image_uploaded = False
        main_image_uploaded = False
        
        # Preserve existing images if this is an update and no new image is provided
        if self.pk:
            try:
                old_instance = News.objects.get(pk=self.pk)
                old_heading_image = old_instance.heading_image
                old_main_image = old_instance.main_image
                
                # Check if heading_image was actually uploaded (new file)
                # In Django admin, if no file is uploaded, the field might be False, empty string, or None
                # We need to check if there's actually a file object
                current_heading = self.heading_image
                
                # Check if heading_image is empty/False/None (no file uploaded)
                if not current_heading or current_heading == False or (hasattr(current_heading, 'name') and not current_heading.name):
                    # No new image provided, preserve the old one
                    if old_heading_image:
                        self.heading_image = old_heading_image
                else:
                    # There's a value, check if it's different from old one
                    current_heading_name = getattr(current_heading, 'name', '') or ''
                    old_heading_name = getattr(old_heading_image, 'name', '') or ''
                    
                    # If names are different, a new file was uploaded
                    if current_heading_name != old_heading_name:
                        heading_image_uploaded = True
                    # If file object exists (has _file attribute), it's a new upload
                    elif hasattr(current_heading, '_file') and current_heading._file:
                        heading_image_uploaded = True
                
                # Check if main_image was actually uploaded (new file)
                current_main = self.main_image
                
                # Check if main_image is empty/False/None (no file uploaded)
                if not current_main or current_main == False or (hasattr(current_main, 'name') and not current_main.name):
                    # No new image provided, preserve the old one
                    if old_main_image:
                        self.main_image = old_main_image
                else:
                    # There's a value, check if it's different from old one
                    current_main_name = getattr(current_main, 'name', '') or ''
                    old_main_name = getattr(old_main_image, 'name', '') or ''
                    
                    # If names are different, a new file was uploaded
                    if current_main_name != old_main_name:
                        main_image_uploaded = True
                    # If file object exists (has _file attribute), it's a new upload
                    elif hasattr(current_main, '_file') and current_main._file:
                        main_image_uploaded = True
                    
            except News.DoesNotExist:
                heading_image_uploaded = bool(self.heading_image and getattr(self.heading_image, 'name', None))
                main_image_uploaded = bool(self.main_image and getattr(self.main_image, 'name', None))
        else:
            # New instance, check if images are provided
            heading_image_uploaded = bool(self.heading_image and getattr(self.heading_image, 'name', None))
            main_image_uploaded = bool(self.main_image and getattr(self.main_image, 'name', None))
        
        super().save(*args, **kwargs)
        
        save_needed = False

        try:
            # Only process heading_image if a new one was uploaded
            if heading_image_uploaded and self.heading_image:
                try:
                    # Safely check if file exists and is accessible
                    if self.heading_image and hasattr(self.heading_image, 'path'):
                        try:
                            image_path = self.heading_image.path
                            if os.path.exists(image_path):
                                new_path = self.convert_to_webp(self.heading_image)
                                if new_path:
                                    self.heading_image.name = new_path
                                    save_needed = True
                            else:
                                # File doesn't exist, skip processing
                                logger.warning(f"Heading image file not found: {image_path}")
                        except (ValueError, OSError, FileNotFoundError) as path_error:
                            # File path is invalid or file doesn't exist
                            logger.warning(f"Cannot access heading_image path: {path_error}")
                            # Don't process if file doesn't exist
                except (ValueError, AttributeError, OSError, FileNotFoundError) as e:
                    # If path doesn't exist or file wasn't uploaded, skip processing
                    logger.debug(f"Skipping heading_image processing: {e}")

            # Only process main_image if a new one was uploaded
            if main_image_uploaded and self.main_image:
                try:
                    # Safely check if file exists and is accessible
                    if self.main_image and hasattr(self.main_image, 'path'):
                        try:
                            image_path = self.main_image.path
                            if os.path.exists(image_path):
                                new_path = self.convert_to_webp(self.main_image)
                                if new_path:
                                    self.main_image.name = new_path
                                    save_needed = True
                            else:
                                # File doesn't exist, skip processing
                                logger.warning(f"Main image file not found: {image_path}")
                        except (ValueError, OSError, FileNotFoundError) as path_error:
                            # File path is invalid or file doesn't exist
                            logger.warning(f"Cannot access main_image path: {path_error}")
                            # Don't process if file doesn't exist
                except (ValueError, AttributeError, OSError, FileNotFoundError) as e:
                    # If path doesn't exist or file wasn't uploaded, skip processing
                    logger.debug(f"Skipping main_image processing: {e}")

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
            # Safely get the image path
            if not hasattr(image_field, 'path'):
                return None
            
            image_path = image_field.path
            if not os.path.exists(image_path):
                logger.warning(f"Image file not found for conversion: {image_path}")
                return None
            
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_video_id(self):
        """Extract video ID from various YouTube URL formats"""
        if not self.youtube_link:
            return None
        
        url = self.youtube_link.strip()
        
        # If already an embed URL, extract ID from it
        if '/embed/' in url:
            video_id = url.split('/embed/')[-1].split('?')[0].split('&')[0].split('#')[0]
            # Clean video ID (should be 11 characters)
            if len(video_id) == 11:
                return video_id
        
        # Parse URL
        parsed_url = urlparse(url)
        
        # Handle youtu.be short URLs (e.g., https://youtu.be/VIDEO_ID)
        if 'youtu.be' in parsed_url.netloc:
            video_id = parsed_url.path.strip('/').split('?')[0].split('&')[0].split('#')[0]
            if len(video_id) == 11:
                return video_id
        
        # Handle youtube.com/watch?v= format
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get('v', [None])[0]
        if video_id:
            # Clean video ID
            video_id = str(video_id).split('&')[0].split('#')[0]
            if len(video_id) == 11:
                return video_id
        
        # Handle youtube.com/v/ format
        if '/v/' in parsed_url.path:
            video_id = parsed_url.path.split('/v/')[-1].split('?')[0].split('&')[0].split('#')[0]
            if len(video_id) == 11:
                return video_id
        
        # Handle mobile YouTube URLs (m.youtube.com)
        if 'm.youtube.com' in parsed_url.netloc:
            query_params = parse_qs(parsed_url.query)
            video_id = query_params.get('v', [None])[0]
            if video_id:
                video_id = str(video_id).split('&')[0].split('#')[0]
                if len(video_id) == 11:
                    return video_id
        
        # Try to extract from path if it looks like a video ID
        path_parts = [p for p in parsed_url.path.split('/') if p]
        for part in path_parts:
            if len(part) == 11 and part.replace('-', '').replace('_', '').isalnum():
                return part
        
        return None
    
    def save(self, *args, **kwargs):
        if not self.section:
            self.section = NavbarItem.objects.filter(title="ভিডিও").first()

        # Convert to embed URL if not already
        video_id = self.get_video_id()
        if video_id and '/embed/' not in self.youtube_link:
            self.youtube_link = f"https://www.youtube.com/embed/{video_id}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.video_title or 'No Title'
    
    @property
    def embed_url(self):
        """Get the embed URL for the YouTube video"""
        video_id = self.get_video_id()
        if video_id:
            # Return clean embed URL without any extra parameters
            return f"https://www.youtube.com/embed/{video_id}"
        # If we can't extract video ID, check if it's already an embed URL
        if self.youtube_link and '/embed/' in self.youtube_link:
            # Clean the existing embed URL
            url = self.youtube_link.split('/embed/')[-1].split('?')[0].split('&')[0].split('#')[0]
            if len(url) == 11:
                return f"https://www.youtube.com/embed/{url}"
        # Return None if we can't create a valid embed URL
        return None
    
    @property
    def watch_url(self):
        """Get the YouTube watch URL for the video"""
        video_id = self.get_video_id()
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
        return None
    
    def fix_youtube_url(self):
        """Fix and update the YouTube URL to proper embed format"""
        video_id = self.get_video_id()
        if video_id:
            old_url = self.youtube_link
            self.youtube_link = f"https://www.youtube.com/embed/{video_id}"
            if old_url != self.youtube_link:
                self.save(update_fields=['youtube_link'])
                return True
        return False
    





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

    


