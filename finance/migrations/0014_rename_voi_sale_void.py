# Generated by Django 4.2.16 on 2024-12-11 11:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0013_sale_voi'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sale',
            old_name='voi',
            new_name='void',
        ),
    ]