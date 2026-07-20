from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Service, Booking

@admin.register(User)
class AdminUser(UserAdmin): # Наследуемся от стандартного UserAdmin
    list_display = ['username', 'email', 'phone_number', 'is_provider', 'is_staff']
    search_fields = ['username', 'email', 'phone_number']
    # Добавляем наше поле phone_number в форму редактирования в админке
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Fields', {'fields': ('phone_number', 'is_provider')}),
    )

@admin.register(Category)
class AdminCategory(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ['name', 'slug']

@admin.register(Service)
class AdminService(admin.ModelAdmin):
    list_display = ['name', 'price', 'provider', 'category']
    list_filter = ['category', 'provider']
    search_fields = ['name', 'description']
    list_editable = ['price'] # Позволяет менять цену в списке

@admin.register(Booking)
class AdminBooking(admin.ModelAdmin):
    list_display = ['client', 'service', 'booking_date', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['created_at'] # Дату создания нельзя менять вручную
