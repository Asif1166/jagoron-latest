from django.contrib import admin

from home.models import *

# Register your models here.
@admin.register(NavbarItem)
class NavbarItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'link', 'position', 'is_active')  
    list_editable = ('position', 'is_active')  
    ordering = ('position',)  
    list_per_page = 20  
    search_fields = ('title', 'link')
    list_filter = ('is_active',)

    
admin.site.register(Category)
admin.site.register(NewsView)

class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_views', 'get_publish_status', 'created_by', 'created_at', 'scheduled_publish_at', 'updated_by', 'updated_at')
    list_filter = ('scheduled_publish_at', 'created_at', 'created_by')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Content', {
            'fields': ('section', 'sub_section', 'category', 'top_sub_title', 'title', 'sub_title', 'sub_content', 'news_content')
        }),
        ('Images', {
            'fields': ('heading_image', 'heading_image_title', 'main_image', 'main_image_title')
        }),
        ('Metadata', {
            'fields': ('reporter', 'created_by', 'updated_by', 'created_at', 'updated_at')
        }),
        ('Publishing', {
            'fields': ('scheduled_publish_at',),
            'description': 'Leave empty to publish immediately, or set a future date/time to schedule publication.'
        }),
    )

    def get_views(self, obj):
        return obj.views.count if hasattr(obj, 'views') else 0
    get_views.short_description = 'Views'
    
    def get_publish_status(self, obj):
        if obj.is_scheduled:
            from django.utils import timezone
            return f"⏰ Scheduled ({obj.scheduled_publish_at.strftime('%Y-%m-%d %H:%M')})"
        elif obj.is_published:
            return "✅ Published"
        else:
            return "❌ Not Published"
    get_publish_status.short_description = 'Status'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at')
        return self.readonly_fields + readonly_fields

    def save_model(self, request, obj, form, change):
        if change:
            # If updating, preserve existing images if no new ones were uploaded
            old_obj = News.objects.get(pk=obj.pk)
            
            # Check if heading_image field was cleared or not provided
            if 'heading_image' in form.changed_data:
                # Field was in the form, check if it has a value
                if not form.cleaned_data.get('heading_image'):
                    # No new image, preserve the old one
                    obj.heading_image = old_obj.heading_image
            else:
                # Field not in form data, preserve the old one
                obj.heading_image = old_obj.heading_image
            
            # Check if main_image field was cleared or not provided
            if 'main_image' in form.changed_data:
                # Field was in the form, check if it has a value
                if not form.cleaned_data.get('main_image'):
                    # No new image, preserve the old one
                    obj.main_image = old_obj.main_image
            else:
                # Field not in form data, preserve the old one
                obj.main_image = old_obj.main_image
        
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()

    class Media:
        js = ('js/news_admin.js',)

admin.site.register(News, NewsAdmin)
admin.site.register(SiteInfo)
admin.site.register(Default_pages)



admin.site.site_header = "Jagoron News Panel"
admin.site.site_title = "Jagoron News Admin" 
admin.site.index_title = "Welcome to Jagoron News"

admin.site.register(VideoPost)
admin.site.register(SubSection)
admin.site.register(SpecialNewTitle)
admin.site.register(SpecialNewSection)
admin.site.register(NewsReaction)
admin.site.register(Review)

