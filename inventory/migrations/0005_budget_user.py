# Generated by Django 4.2.16 on 2025-01-05 14:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inventory", "0004_budget_budgetitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="budget",
            name="user",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="budge_user",
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
    ]