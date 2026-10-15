from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.utils import timezone

class User(AbstractUser):
    """自定义用户模型"""
    ROLE_CHOICES = (
        ('admin', '系统管理员'),
        ('operator', '操作员'),
        ('viewer', '观察员'),
        ('maintainer', '维护人员'),
    )
    
    phone = models.CharField('手机号', max_length=15, blank=True)
    role = models.CharField('角色', max_length=20, choices=ROLE_CHOICES, default='viewer')
    department = models.CharField('部门', max_length=100, blank=True)
    avatar = models.ImageField('头像', upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class Site(models.Model):
    """站点模型"""
    name = models.CharField('站点名称', max_length=100)
    code = models.CharField('站点代码', max_length=20, unique=True)
    location = models.CharField('位置', max_length=200)
    description = models.TextField('描述', blank=True)
    contact_person = models.CharField('联系人', max_length=50, blank=True)
    contact_phone = models.CharField('联系电话', max_length=15, blank=True)
    is_active = models.BooleanField('是否激活', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'site'
        verbose_name = '站点'
        verbose_name_plural = verbose_name
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def robot_count(self):
        return self.robots.count()
    
    @property
    def online_robot_count(self):
        return self.robots.filter(status='online').count()

class Robot(models.Model):
    """机器人模型"""
    STATUS_CHOICES = (
        ('online', '在线'),
        ('offline', '离线'),
        ('maintenance', '维护中'),
        ('fault', '故障'),
        ('testing', '测试中'),
    )
    
    ROBOT_TYPE_CHOICES = (
        ('industrial', '工业机器人'),
        ('service', '服务机器人'),
        ('medical', '医疗机器人'),
        ('cleaning', '清洁机器人'),
        ('inspection', '巡检机器人'),
        ('logistics', '物流机器人'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('机器人名称', max_length=100)
    code = models.CharField('机器人编号', max_length=50, unique=True)
    robot_type = models.CharField('机器人类型', max_length=20, choices=ROBOT_TYPE_CHOICES)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='robots', verbose_name='所属站点')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='offline')
    
    # 技术参数
    ip_address = models.GenericIPAddressField('IP地址', protocol='IPv4')
    model_number = models.CharField('型号', max_length=50)
    manufacturer = models.CharField('制造商', max_length=100)
    serial_number = models.CharField('序列号', max_length=100, unique=True)
    
    # 维护信息
    purchase_date = models.DateField('购买日期')
    warranty_period = models.IntegerField('保修期(月)', default=12)
    last_maintenance = models.DateField('上次维护时间', blank=True, null=True)
    next_maintenance = models.DateField('下次维护时间', blank=True, null=True)
    
    # 位置信息
    location_description = models.CharField('位置描述', max_length=200, blank=True)
    latitude = models.DecimalField('纬度', max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField('经度', max_digits=9, decimal_places=6, blank=True, null=True)
    
    # 系统字段
    is_active = models.BooleanField('是否激活', default=True)
    description = models.TextField('描述', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'robot'
        verbose_name = '机器人'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['robot_type']),
            models.Index(fields=['site']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def age_in_months(self):
        """计算机器人使用月数"""
        from dateutil.relativedelta import relativedelta
        return relativedelta(timezone.now().date(), self.purchase_date).months
    
    @property
    def is_under_warranty(self):
        """是否在保修期内"""
        return self.age_in_months <= self.warranty_period

class EquipmentParameter(models.Model):
    """设备参数模型"""
    robot = models.ForeignKey(Robot, on_delete=models.CASCADE, related_name='parameters', verbose_name='机器人')
    parameter_name = models.CharField('参数名称', max_length=100)
    parameter_value = models.FloatField('参数值')
    unit = models.CharField('单位', max_length=20)
    threshold_min = models.FloatField('阈值下限')
    threshold_max = models.FloatField('阈值上限')
    is_normal = models.BooleanField('是否正常', default=True)
    collected_at = models.DateTimeField('采集时间', auto_now_add=True)
    
    class Meta:
        db_table = 'equipment_parameter'
        verbose_name = '设备参数'
        verbose_name_plural = verbose_name
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['robot', 'collected_at']),
            models.Index(fields=['is_normal']),
        ]
    
    def save(self, *args, **kwargs):
        # 自动检查参数是否在正常范围内
        if self.parameter_value < self.threshold_min or self.parameter_value > self.threshold_max:
            self.is_normal = False
        else:
            self.is_normal = True
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.robot.name} - {self.parameter_name}: {self.parameter_value}{self.unit}"

class MaintenanceRecord(models.Model):
    """维护记录模型"""
    MAINTENANCE_TYPE_CHOICES = (
        ('routine', '例行维护'),
        ('repair', '故障维修'),
        ('upgrade', '升级维护'),
        ('inspection', '巡检'),
        ('calibration', '校准'),
    )
    
    PRIORITY_CHOICES = (
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '紧急'),
    )
    
    robot = models.ForeignKey(Robot, on_delete=models.CASCADE, related_name='maintenance_records', verbose_name='机器人')
    maintenance_type = models.CharField('维护类型', max_length=20, choices=MAINTENANCE_TYPE_CHOICES)
    title = models.CharField('维护标题', max_length=200)
    description = models.TextField('维护描述')
    technician = models.CharField('技术人员', max_length=50)
    priority = models.CharField('优先级', max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # 维护详情
    cost = models.DecimalField('维护费用', max_digits=10, decimal_places=2, default=0)
    maintenance_date = models.DateField('维护日期')
    maintenance_duration = models.IntegerField('维护时长(小时)', default=1)
    next_maintenance_date = models.DateField('下次维护日期', blank=True, null=True)
    
    # 结果
    is_completed = models.BooleanField('是否完成', default=True)
    result = models.TextField('维护结果', blank=True)
    parts_replaced = models.TextField('更换零件', blank=True)
    
    created_at = models.DateTimeField('记录时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'maintenance_record'
        verbose_name = '维护记录'
        verbose_name_plural = verbose_name
        ordering = ['-maintenance_date']
    
    def __str__(self):
        return f"{self.robot.name} - {self.title}"

class Alert(models.Model):
    """告警模型"""
    LEVEL_CHOICES = (
        ('info', '信息'),
        ('warning', '警告'),
        ('error', '错误'),
        ('critical', '严重'),
    )
    
    robot = models.ForeignKey(Robot, on_delete=models.CASCADE, related_name='alerts', verbose_name='机器人')
    title = models.CharField('告警标题', max_length=200)
    message = models.TextField('告警信息')
    level = models.CharField('告警级别', max_length=10, choices=LEVEL_CHOICES)
    
    # 告警状态
    is_resolved = models.BooleanField('是否已解决', default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='解决人')
    resolved_at = models.DateTimeField('解决时间', blank=True, null=True)
    resolution_notes = models.TextField('解决说明', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'alert'
        verbose_name = '告警'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['is_resolved']),
        ]
    
    def __str__(self):
        return f"{self.robot.name} - {self.title}"
    
    def resolve(self, user, notes=""):
        """解决告警"""
        self.is_resolved = True
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save()

class OperationLog(models.Model):
    """操作日志模型"""
    ACTION_CHOICES = (
        ('create', '创建'),
        ('update', '更新'),
        ('delete', '删除'),
        ('login', '登录'),
        ('logout', '登出'),
        ('maintenance', '维护'),
        ('alert', '告警处理'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    action = models.CharField('操作类型', max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField('模型名称', max_length=50)
    object_id = models.CharField('对象ID', max_length=36, blank=True)
    description = models.TextField('操作描述')
    ip_address = models.GenericIPAddressField('IP地址', blank=True, null=True)
    user_agent = models.TextField('用户代理', blank=True)
    
    created_at = models.DateTimeField('操作时间', auto_now_add=True)
    
    class Meta:
        db_table = 'operation_log'
        verbose_name = '操作日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} - {self.model_name}"