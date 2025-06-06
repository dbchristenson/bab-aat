# Generated by Django 5.2.1 on 2025-06-03 14:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ocr", "0015_remove_tag_detections_detection_tag_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="detection",
            name="tag",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="detections",
                to="ocr.tag",
            ),
        ),
    ]
