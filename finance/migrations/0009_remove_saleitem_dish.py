# Generated by Django 4.2.16 on 2024-12-07 11:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0008_saleitem_dish'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='saleitem',
            name='dish',
        ),
    ]