# serializers/report_serializer.py
from rest_framework import serializers
from inventory_app.models.report import Report

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'file', 'generated_at', 'user']
        read_only_fields = ['user']
