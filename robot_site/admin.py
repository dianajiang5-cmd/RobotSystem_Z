from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, Site, Robot, EquipmentParameter, MaintenanceRecord, Alert, OperationLog

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone', 'role', 'department', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'phone', 'department')
    fieldsets = UserAdmin.fieldsets + (
        ('额外信息', {
            'fields': ('phone', 'role', 'department', 'avatar')
        }),
    )
    list_per_page = 20

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'location', 'contact_person', 'contact_phone', 'is_active', 'robot_count', 'online_robot_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'location', 'contact_person')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20
    
    def robot_count(self, obj):
        return obj.robot_count
    robot_count.short_description = '机器人数量'
    
    def online_robot_count(self, obj):
        return obj.online_robot_count
    online_robot_count.short_description = '在线数量'

@admin.register(Robot)
class RobotAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'robot_type', 'site', 'status', 'ip_address', 'is_active', 'age_in_months', 'is_under_warranty', 'created_at')
    list_filter = ('robot_type', 'status', 'site', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'model_number', 'serial_number', 'manufacturer')
    readonly_fields = ('created_at', 'updated_at', 'id')
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'code', 'robot_type', 'site', 'status', 'description')
        }),
        ('技术参数', {
            'fields': ('ip_address', 'model_number', 'manufacturer', 'serial_number')
        }),
        ('维护信息', {
            'fields': ('purchase_date', 'warranty_period', 'last_maintenance', 'next_maintenance')
        }),
        ('位置信息', {
            'fields': ('location_description', 'latitude', 'longitude')
        }),
        ('系统信息', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    list_per_page = 20
    
    def age_in_months(self, obj):
        return obj.age_in_months
    age_in_months.short_description = '使用月数'
    
    def is_under_warranty(self, obj):
        return obj.is_under_warranty
    is_under_warranty.boolean = True
    is_under_warranty.short_description = '在保修期内'

@admin.register(EquipmentParameter)
class EquipmentParameterAdmin(admin.ModelAdmin):
    list_display = ('robot', 'parameter_name', 'parameter_value', 'unit', 'is_normal', 'collected_at')
    list_filter = ('parameter_name', 'is_normal', 'collected_at')
    search_fields = ('robot__name', 'parameter_name')
    readonly_fields = ('collected_at',)
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('robot')

@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ('robot', 'maintenance_type', 'title', 'technician', 'priority', 'cost', 'maintenance_date', 'is_completed', 'created_at')
    list_filter = ('maintenance_type', 'priority', 'is_completed', 'maintenance_date')
    search_fields = ('robot__name', 'title', 'technician', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('robot')

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('robot', 'title', 'level', 'is_resolved', 'resolved_by', 'resolved_at', 'created_at')
    list_filter = ('level', 'is_resolved', 'created_at')
    search_fields = ('robot__name', 'title', 'message')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('robot', 'resolved_by')

@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'object_id', 'ip_address', 'created_at')
    list_filter = ('action', 'model_name', 'created_at')
    search_fields = ('user__username', 'description', 'object_id')
    readonly_fields = ('created_at', 'user', 'action', 'model_name', 'object_id', 'description', 'ip_address', 'user_agent')
    list_per_page = 20
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

# 自定义管理站点标题
admin.site.site_header = '机器人管理系统后台'
admin.site.site_title = '机器人管理系统'
admin.site.index_title = '系统管理'