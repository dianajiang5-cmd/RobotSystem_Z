from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, TemplateView
from django.db.models import Count, Q, Avg, Max, Min
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Site, Robot, EquipmentParameter, MaintenanceRecord, Alert, OperationLog
from .serializers import (
    SiteSerializer, RobotSerializer, EquipmentParameterSerializer,
   )

# ==================== 前端页面视图 ====================

class IndexView(TemplateView):
    """首页"""
    template_name = 'robot_site/index.html'

class DashboardView(LoginRequiredMixin, TemplateView):
    """仪表盘"""
    template_name = 'robot_site/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 基础统计
        total_robots = Robot.objects.count()
        online_robots = Robot.objects.filter(status='online').count()
        total_sites = Site.objects.count()
        active_alerts = Alert.objects.filter(is_resolved=False).count()
        
        # 状态统计
        status_stats = Robot.objects.values('status').annotate(count=Count('id'))
        status_display_map = {
            'online': '在线',
            'offline': '离线', 
            'maintenance': '维护中',
            'fault': '故障',
            'testing': '测试中'
        }
        for stat in status_stats:
            stat['status_display'] = status_display_map.get(stat['status'], stat['status'])
        
        # 类型统计
        type_stats = Robot.objects.values('robot_type').annotate(count=Count('id'))
        
        # 最近数据
        recent_alerts = Alert.objects.select_related('robot').filter(is_resolved=False).order_by('-created_at')[:10]
        recent_params = EquipmentParameter.objects.select_related('robot').order_by('-collected_at')[:10]
        recent_robots = Robot.objects.select_related('site').order_by('-created_at')[:5]
        
        # 维护统计
        maintenance_stats = MaintenanceRecord.objects.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(is_completed=True)),
            this_month=Count('id', filter=Q(maintenance_date__month=timezone.now().month))
        )
        
        context.update({
            'stats': {
                'total_robots': total_robots,
                'online_robots': online_robots,
                'total_sites': total_sites,
                'active_alerts': active_alerts,
                'online_rate': round(online_robots / total_robots * 100, 2) if total_robots > 0 else 0,
            },
            'status_stats': status_stats,
            'type_stats': type_stats,
            'recent_alerts': recent_alerts,
            'recent_params': recent_params,
            'recent_robots': recent_robots,
            'maintenance_stats': maintenance_stats,
        })
        return context

class RobotListView(LoginRequiredMixin, ListView):
    """机器人列表页"""
    model = Robot
    template_name = 'robot_site/robot_list.html'
    context_object_name = 'robots'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = Robot.objects.select_related('site').order_by('-created_at')
        
        # 状态筛选
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 类型筛选
        type_filter = self.request.GET.get('type')
        if type_filter:
            queryset = queryset.filter(robot_type=type_filter)
        
        # 站点筛选
        site_filter = self.request.GET.get('site')
        if site_filter:
            queryset = queryset.filter(site_id=site_filter)
        
        # 搜索
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(model_number__icontains=search_query) |
                Q(manufacturer__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = dict(Robot.STATUS_CHOICES)
        context['type_choices'] = dict(Robot.ROBOT_TYPE_CHOICES)
        context['sites'] = Site.objects.filter(is_active=True)
        return context

class RobotDetailView(LoginRequiredMixin, DetailView):
    """机器人详情页"""
    model = Robot
    template_name = 'robot_site/robot_detail.html'
    context_object_name = 'robot'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        robot = self.get_object()
        
        # 最近参数
        recent_parameters = robot.parameters.order_by('-collected_at')[:20]
        
        # 维护记录
        maintenance_records = robot.maintenance_records.order_by('-maintenance_date')[:10]
        
        # 告警记录
        recent_alerts = robot.alerts.order_by('-created_at')[:10]
        
        # 参数统计
        param_stats = robot.parameters.values('parameter_name').annotate(
            avg_value=Avg('parameter_value'),
            max_value=Max('parameter_value'),
            min_value=Min('parameter_value'),
            latest_value=Max('collected_at')
        )
        
        context.update({
            'recent_parameters': recent_parameters,
            'maintenance_records': maintenance_records,
            'recent_alerts': recent_alerts,
            'param_stats': param_stats,
        })
        return context

class ParameterMonitorView(LoginRequiredMixin, TemplateView):
    """参数监控页面"""
    template_name = 'robot_site/parameter_monitor.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取所有在线的机器人及其最新参数
        online_robots = Robot.objects.filter(status='online').select_related('site')
        
        robot_data = []
        for robot in online_robots:
            latest_params = robot.parameters.order_by('-collected_at')[:5]
            robot_data.append({
                'robot': robot,
                'latest_params': latest_params,
                'abnormal_count': robot.parameters.filter(is_normal=False).count()
            })
        
        context['robot_data'] = robot_data
        return context

# ==================== API 视图 ====================

class SiteViewSet(viewsets.ModelViewSet):
    """站点API"""
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    @action(detail=True, methods=['get'])
    def robots(self, request, pk=None):
        """获取站点的机器人列表"""
        site = self.get_object()
        robots = site.robots.all()
        serializer = RobotSerializer(robots, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """站点统计信息"""
        sites = Site.objects.annotate(
            robot_count=Count('robots'),
            online_count=Count('robots', filter=Q(robots__status='online'))
        )
        data = []
        for site in sites:
            data.append({
                'id': site.id,
                'name': site.name,
                'code': site.code,
                'robot_count': site.robot_count,
                'online_count': site.online_count,
                'online_rate': round(site.online_count / site.robot_count * 100, 2) if site.robot_count > 0 else 0
            })
        return Response(data)

class RobotViewSet(viewsets.ModelViewSet):
    """机器人API"""
    queryset = Robot.objects.all()
    serializer_class = RobotSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 过滤参数
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        robot_type = self.request.query_params.get('type')
        if robot_type:
            queryset = queryset.filter(robot_type=robot_type)
        
        site = self.request.query_params.get('site')
        if site:
            queryset = queryset.filter(site_id=site)
        
        return queryset.select_related('site')
    
    @action(detail=True, methods=['get'])
    def parameters(self, request, pk=None):
        """获取机器人的参数列表"""
        robot = self.get_object()
        parameters = robot.parameters.order_by('-collected_at')
        
        # 时间范围过滤
        hours = request.query_params.get('hours', 24)
        if hours:
            time_threshold = timezone.now() - timedelta(hours=int(hours))
            parameters = parameters.filter(collected_at__gte=time_threshold)
        
        page = self.paginate_queryset(parameters)
        if page is not None:
            serializer = EquipmentParameterSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = EquipmentParameterSerializer(parameters, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def alerts(self, request, pk=None):
        """获取机器人的告警列表"""
        robot = self.get_object()
        alerts = robot.alerts.order_by('-created_at')
        
        # 过滤已解决/未解决
        resolved = request.query_params.get('resolved')
        if resolved is not None:
            alerts = alerts.filter(is_resolved=resolved.lower() == 'true')
        
        page = self.paginate_queryset(alerts)
        if page is not None:
            serializer = AlertSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """改变机器人状态"""
        robot = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Robot.STATUS_CHOICES):
            return Response(
                {'error': f'无效的状态: {new_status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        robot.status = new_status
        robot.save()
        
        # 记录操作日志
        OperationLog.objects.create(
            user=request.user,
            action='update',
            model_name='Robot',
            object_id=str(robot.id),
            description=f'将机器人 {robot.name} 状态改为 {robot.get_status_display()}',
            ip_address=self.get_client_ip(request)
        )
        
        return Response({'message': '状态更新成功', 'new_status': new_status})
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class EquipmentParameterViewSet(viewsets.ModelViewSet):
    """设备参数API"""
    queryset = EquipmentParameter.objects.all()
    serializer_class = EquipmentParameterSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 机器人过滤
        robot_id = self.request.query_params.get('robot')
        if robot_id:
            queryset = queryset.filter(robot_id=robot_id)
        
        # 时间范围过滤
        hours = self.request.query_params.get('hours')
        if hours:
            time_threshold = timezone.now() - timedelta(hours=int(hours))
            queryset = queryset.filter(collected_at__gte=time_threshold)
        
        # 参数名称过滤
        param_name = self.request.query_params.get('parameter_name')
        if param_name:
            queryset = queryset.filter(parameter_name=param_name)
        
        return queryset.select_related('robot')

class AlertViewSet(viewsets.ModelViewSet):
    """告警API"""
    queryset = Alert.objects.all()
    #serializer_class = AlertSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 状态过滤
        resolved = self.request.query_params.get('resolved')
        if resolved is not None:
            queryset = queryset.filter(is_resolved=resolved.lower() == 'true')
        
        # 级别过滤
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        # 机器人过滤
        robot_id = self.request.query_params.get('robot')
        if robot_id:
            queryset = queryset.filter(robot_id=robot_id)
        
        return queryset.select_related('robot', 'resolved_by')
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """解决告警"""
        alert = self.get_object()
        notes = request.data.get('notes', '')
        
        alert.resolve(request.user, notes)
        serializer = self.get_serializer(alert)
        return Response(serializer.data)

# ==================== 工具API ====================

@api_view(['GET'])
def system_stats(request):
    """系统统计信息"""
    # 基础统计
    total_robots = Robot.objects.count()
    online_robots = Robot.objects.filter(status='online').count()
    total_sites = Site.objects.count()
    active_alerts = Alert.objects.filter(is_resolved=False).count()
    
    # 状态分布
    status_distribution = Robot.objects.values('status').annotate(count=Count('id'))
    
    # 类型分布
    type_distribution = Robot.objects.values('robot_type').annotate(count=Count('id'))
    
    # 今日数据
    today = timezone.now().date()
    today_alerts = Alert.objects.filter(created_at__date=today).count()
    today_maintenance = MaintenanceRecord.objects.filter(maintenance_date=today).count()
    
    # 参数统计
    abnormal_params = EquipmentParameter.objects.filter(is_normal=False).count()
    total_params = EquipmentParameter.objects.count()
    
    return Response({
        'basic_stats': {
            'total_robots': total_robots,
            'online_robots': online_robots,
            'total_sites': total_sites,
            'active_alerts': active_alerts,
            'online_rate': round(online_robots / total_robots * 100, 2) if total_robots > 0 else 0,
        },
        'status_distribution': list(status_distribution),
        'type_distribution': list(type_distribution),
        'today_stats': {
            'alerts': today_alerts,
            'maintenance': today_maintenance,
        },
        'parameter_stats': {
            'abnormal': abnormal_params,
            'total': total_params,
            'abnormal_rate': round(abnormal_params / total_params * 100, 2) if total_params > 0 else 0,
        }
    })

@api_view(['GET'])
def robot_health_check(request, robot_id):
    """机器人健康检查"""
    robot = get_object_or_404(Robot, id=robot_id)
    
    # 检查最新参数
    latest_params = robot.parameters.order_by('-collected_at')[:10]
    abnormal_params = [p for p in latest_params if not p.is_normal]
    
    # 检查未解决的告警
    unresolved_alerts = robot.alerts.filter(is_resolved=False)
    
    # 检查维护状态
    needs_maintenance = False
    if robot.next_maintenance and robot.next_maintenance <= timezone.now().date():
        needs_maintenance = True
    
    health_status = 'healthy'
    if unresolved_alerts.exists() or abnormal_params:
        health_status = 'warning'
    if unresolved_alerts.filter(level='critical').exists():
        health_status = 'critical'
    
    return Response({
        'robot_id': str(robot.id),
        'robot_name': robot.name,
        'health_status': health_status,
        'abnormal_parameters': len(abnormal_params),
        'unresolved_alerts': unresolved_alerts.count(),
        'needs_maintenance': needs_maintenance,
        'last_updated': robot.updated_at,
        'details': {
            'abnormal_params': [
                {
                    'name': p.parameter_name,
                    'value': p.parameter_value,
                    'unit': p.unit,
                    'collected_at': p.collected_at
                } for p in abnormal_params
            ],
            'unresolved_alerts': [
                {
                    'title': alert.title,
                    'level': alert.level,
                    'created_at': alert.created_at
                } for alert in unresolved_alerts
            ]
        }
    })