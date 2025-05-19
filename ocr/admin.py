from django.contrib import admin

from ocr.models import Detection, Document, OCRConfig, Page, Tag, Truth, Vessel

# Register your models here.
admin.site.register(Document)
admin.site.register(Page)
admin.site.register(Detection)
admin.site.register(Truth)
admin.site.register(Vessel)
admin.site.register(Tag)
admin.site.register(OCRConfig)
