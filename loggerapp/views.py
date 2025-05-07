from rest_framework import viewsets
from .models import Person, Attendance
from .serializers import AttendanceSerializer, PersonAttendanceSerializer

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all().order_by('-date')
    serializer_class = AttendanceSerializer


class PersonViewSet(viewsets.ModelViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonAttendanceSerializer
