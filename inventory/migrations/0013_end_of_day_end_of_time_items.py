# Generated by Django 5.0.6 on 2024-08-15 09:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0012_purchaseorderitem_note'),
    ]

    operations = [
        migrations.CreateModel(
            name='end_of_day',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='end_of_time_items',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('production_line_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='inventory.productionitems')),
            ],
        ),
    ]