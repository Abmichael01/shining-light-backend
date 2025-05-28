# core/admin.py
from django.contrib import admin
from .models import School
from .models import Class

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']
    prepopulated_fields = {"slug": ("name",)}  # Auto-generates slug from name
    ordering = ['name']
    readonly_fields = ['slug']
    fieldsets = (
        (None, {
            'fields': ('name', 'slug')
        }),
    )

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'school', 'slug']
    list_filter = ['school']
    search_fields = ['name']
    ordering = ['school', 'name']
    readonly_fields = ['slug']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'school', 'slug')
        }),
    )