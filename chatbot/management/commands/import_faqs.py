"""
Bulk import FAQs from JSON or CSV.
"""
import json
import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from chatbot.models import Category, FAQ
from chatbot.search_engine import search_engine
from chatbot.autocomplete import autocomplete_index


class Command(BaseCommand):
    help = "Bulk import FAQs from JSON or CSV"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default=None, help='Path to JSON or CSV file')
        parser.add_argument('--format', type=str, choices=['json', 'csv'], default=None, help='Force format')
        parser.add_argument('--wipe', action='store_true', help='Delete all existing FAQs before import')
        parser.add_argument('--dry-run', action='store_true', help='Show what would happen without saving')

    def handle(self, *args, **options):
        file_path = options['file']
        fmt = options['format']

        if not file_path:
            file_path = Path(settings.BASE_DIR) / 'chatbot' / 'data' / 'faqs.json'

        file_path = Path(file_path)
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        if not fmt:
            fmt = file_path.suffix.lstrip('.').lower()

        self.stdout.write(self.style.HTTP_INFO(f"📂 Loading from {file_path}"))

        if fmt == 'json':
            categories, faqs = self._parse_json(file_path)
        else:
            categories, faqs = self._parse_csv(file_path)

        self.stdout.write(f"   Categories: {len(categories)}")
        self.stdout.write(f"   FAQs: {len(faqs)}")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))
            return

        with transaction.atomic():
            if options['wipe']:
                count = FAQ.objects.count()
                FAQ.objects.all().delete()
                self.stdout.write(self.style.WARNING(f"🗑  Wiped {count} existing FAQs"))

            # Ensure categories
            cat_map = {}
            for cat in categories:
                obj, _ = Category.objects.update_or_create(
                    name=cat['name'],
                    defaults={'icon': cat.get('icon', '💬'), 'order': cat.get('order', 0)}
                )
                cat_map[cat['name']] = obj

            created_count = 0
            updated_count = 0
            skipped_count = 0

            for index, item in enumerate(faqs, start=1):
                # 🚨 SAFETY CHECK: Validate the data before saving
                question = item.get('question', '').strip()
                answer = item.get('answer', '').strip()

                if not question or not answer:
                    skipped_count += 1
                    self.stdout.write(self.style.ERROR(
                        f"   ❌ Skipped FAQ #{index}: Missing 'question' or 'answer'. Found: {item}"
                    ))
                    continue

                category = cat_map.get(item.get('category'))

                obj, created = FAQ.objects.update_or_create(
                    question=question,
                    defaults={
                        'answer': answer,
                        'category': category,
                        'keywords': item.get('keywords', ''),
                        'priority': int(item.get('priority', 0)),
                        'is_active': True,
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        # Rebuild search indices
        self.stdout.write("🔄 Rebuilding search index...")
        search_engine.refresh()
        autocomplete_index.refresh()

        self.stdout.write(self.style.SUCCESS(
            f"✅ Done! Created: {created_count}, Updated: {updated_count}, Skipped (broken): {skipped_count}"
        ))
        self.stdout.write(self.style.SUCCESS(f"   Total FAQs in DB: {FAQ.objects.count()}"))

    @staticmethod
    def _parse_json(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        categories = data.get('categories', [])
        faqs = data.get('faqs', data.get('faq', []))

        if not categories:
            seen = set()
            for f_ in faqs:
                cat = f_.get('category', 'General')
                if cat and cat not in seen:
                    seen.add(cat)
                    categories.append({'name': cat, 'icon': '💬', 'order': 0})

        return categories, faqs

    @staticmethod
    def _parse_csv(path):
        categories = []
        faqs = []
        seen_cats = set()
        with open(path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cat = (row.get('category') or 'General').strip()
                if cat and cat not in seen_cats:
                    seen_cats.add(cat)
                    categories.append({'name': cat, 'icon': '💬', 'order': 0})

                faqs.append({
                    'question': row.get('question', '').strip(),
                    'answer': row.get('answer', '').strip(),
                    'category': cat,
                    'keywords': (row.get('keywords') or '').strip(),
                    'priority': int(row.get('priority') or 0),
                })
        return categories, faqs