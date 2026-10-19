from django.contrib import admin

# Register your models here.................
from django.contrib import admin
from django.core.management import call_command
from .models import Category, FAQ, Conversation, Message, UnansweredQuery
from .search_engine import search_engine
from .autocomplete import autocomplete_index
from django.contrib import messages


def rebuild_all_indexes():
    search_engine.refresh()
    autocomplete_index.refresh()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'order')
    list_editable = ('icon', 'order')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'priority', 'views',
                    'helpful_count', 'not_helpful_count', 'is_active')
    list_filter = ('is_active', 'category')
    search_fields = ('question', 'answer', 'keywords')
    list_editable = ('priority', 'is_active')
    actions = ['rebuild_indexes']

    @admin.action(description="🔄 Rebuild search & autocomplete indexes")
    def rebuild_indexes(self, request, queryset):
        rebuild_all_indexes()
        self.message_user(request, "✅ Indexes rebuilt.", messages.SUCCESS)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        rebuild_all_indexes()


@admin.register(UnansweredQuery)
class UnansweredAdmin(admin.ModelAdmin):
    list_display = ('query', 'count', 'last_asked')
    ordering = ('-count',)


admin.site.register(Conversation)
admin.site.register(Message)