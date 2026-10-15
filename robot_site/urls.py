from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 创建路由器并注册视图集
router = DefaultRouter()
router.register(r'sites', views.SiteViewSet)
router.register(r'robots', views.RobotViewSet)
router.register(r'parameters', views.EquipmentParameterViewSet)
router.register(r'alerts', views.AlertViewSet)

urlpatterns = [
    # 页面路由
    path('', views.IndexView.as_view(), name='index'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('robots/', views.RobotListView.as_view(), name='robot_list'),
    path('robots/<uuid:pk>/', views.RobotDetailView.as_view(), name='robot_detail'),
    path('monitor/', views.ParameterMonitorView.as_view(), name='parameter_monitor'),
    
    # API路由
    path('api/', include(router.urls)),
    path('api/stats/', views.system_stats, name='system_stats'),
    path('api/robots/<uuid:robot_id>/health/', views.robot_health_check, name='robot_health_check'),
    
    # 工具页面
    path('api/docs/', views.IndexView.as_view(), name='api_docs'),  # 可以替换为实际的API文档页面
]

# 添加调试路由（仅在开发环境）
if False:  # 在实际项目中可以根据DEBUG设置
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]