from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default="💬")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class FAQ(models.Model):
    question = models.CharField(max_length=500, db_index=True)
    answer = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='faqs'
    )
    keywords = models.CharField(
        max_length=500, blank=True,
        help_text="Comma-separated keywords for better matching"
    )
    priority = models.IntegerField(default=0, help_text="Higher = shown first")
    is_active = models.BooleanField(default=True)
    views = models.IntegerField(default=0)
    helpful_count = models.IntegerField(default=0)
    not_helpful_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', '-views']

    def __str__(self):
        return self.question[:80]


class Conversation(models.Model):
    session_key = models.CharField(max_length=64, db_index=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    user_agent = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return f"Session {self.session_key[:8]}"


class Message(models.Model):
    SENDER_CHOICES = [('user', 'User'), ('bot', 'Bot')]
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    text = models.TextField()
    matched_faq = models.ForeignKey(
        FAQ, on_delete=models.SET_NULL, null=True, blank=True
    )
    confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class UnansweredQuery(models.Model):
    """Store queries bot couldn't answer - goldmine for improving FAQs."""
    query = models.CharField(max_length=500)
    count = models.IntegerField(default=1)
    last_asked = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-count']
        verbose_name_plural = "Unanswered queries"

    def __str__(self):
        return f"{self.query} ({self.count})"