# Generated by Django 4.2.16 on 2024-12-07 10:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_initial'),
        ('finance', '0003_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='saleitem',
            name='meal',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='inventory.meal'),
        ),
    ]