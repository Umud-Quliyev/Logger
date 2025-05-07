from rest_framework import serializers
from .models import Person, Attendance

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'


class PersonAttendanceSerializer(serializers.ModelSerializer):
    attendances = AttendanceSerializer(many=True, read_only=True)

    class Meta:
        model = Person
        fields = ['id', 'name', 'attendances']
