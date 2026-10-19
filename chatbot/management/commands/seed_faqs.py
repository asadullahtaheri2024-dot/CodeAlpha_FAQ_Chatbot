# chatbot/management/commands/seed_faqs.py
from django.core.management.base import BaseCommand
from pathlib import Path
from django.conf import settings
from django.core.management import call_command


class Command(BaseCommand):
    help = "Seed initial FAQ data from chatbot/data/faqs.json"

    def handle(self, *args, **opts):
        path = Path(settings.BASE_DIR) / 'chatbot' / 'data' / 'faqs.json'
        self.stdout.write(f"Seeding from {path}...")
        call_command('import_faqs', file=str(path))