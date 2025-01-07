from django.core.management.base import BaseCommand
from django.db.models import Count
from finance.models import Change

class Command(BaseCommand):
    help = 'Remove duplicate entries based on the name field'

    def handle(self, *args, **kwargs):
        duplicates = (
            Change.objects.values('name')
            .annotate(name_count=Count('name'))
            .filter(name_count__gt=1)
        )

        for duplicate in duplicates:
            name = duplicate['name']
            entries = Change.objects.filter(name=name)
            entries_to_delete = entries[1:]  

            for entry in entries_to_delete:
                entry.delete()

        self.stdout.write(self.style.SUCCESS('Successfully removed duplicates'))