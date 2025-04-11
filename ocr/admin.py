from django.contrib import admin

from ocr.models import Detection, Document, Page, Truth, Vessel

# Register your models here.
admin.site.register(Document)
admin.site.register(Page)
admin.site.register(Detection)
admin.site.register(Truth)
admin.site.register(Vessel)
