# Generated by Django 5.2 on 2025-05-16 03:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ocr", "0011_ocrconfig"),
    ]

    operations = [
        migrations.AlterField(
            model_name="detection",
            name="config",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="ocr.ocrconfig",
            ),
        ),
    ]
