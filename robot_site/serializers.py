from rest_framework import serializers
from .models import Site, Robot, EquipmentParameter

class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = '__all__'

class RobotSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    
    class Meta:
        model = Robot
        fields = '__all__'

class EquipmentParameterSerializer(serializers.ModelSerializer):
    robot_name = serializers.CharField(source='robot.name', read_only=True)
    
    class Meta:
        model = EquipmentParameter
        fields = '__all__'

