from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Service, Booking


@admin.register(User)
class AdminUser(UserAdmin):
    list_display = ['username', 'email', 'phone_number', 'is_provider', 'is_staff']
    search_fields = ['username', 'email', 'phone_number']
    list_filter = ['is_provider', 'is_staff', 'is_active']
    
    # Расширяем формы создания и редактирования пользователя
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('phone_number', 'is_provider')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительная информация', {'fields': ('phone_number', 'is_provider')}),
    )


@admin.register(Category)
class AdminCategory(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Service)
class AdminService(admin.ModelAdmin):
    list_display = ['name', 'price', 'provider', 'category', 'created_at']
    list_filter = ['category', 'provider', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price']
    ordering = ['-created_at']


@admin.register(Booking)
class AdminBooking(admin.ModelAdmin):
    list_display = ['client', 'service', 'booking_date', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['created_at']
    ordering = ['-booking_date']
    # Позволяет быстро фильтровать по месяцам/дням вверху страницы
    date_hierarchy = 'booking_date'