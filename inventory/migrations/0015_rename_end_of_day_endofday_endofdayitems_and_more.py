# Generated by Django 5.0.6 on 2024-08-15 09:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0014_end_of_time_items_expected'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='end_of_day',
            new_name='EndOfDay',
        ),
        migrations.CreateModel(
            name='EndOfDayItems',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dish_name', models.CharField(max_length=50)),
                ('total_portions', models.IntegerField()),
                ('total_sold', models.IntegerField()),
                ('staff_portions', models.IntegerField()),
                ('wastage', models.FloatField()),
                ('leftovers', models.FloatField()),
                ('expected', models.FloatField()),
                ('end_of_day', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='inventory.endofday')),
            ],
        ),
        migrations.DeleteModel(
            name='end_of_time_items',
        ),
    ]