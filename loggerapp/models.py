from django.db import models

class Person(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Attendance(models.Model):
    person = models.ForeignKey(Person, related_name='attendances', on_delete=models.CASCADE)
    date = models.DateField()
    entry_time = models.TimeField(null=True, blank=True)
    exit_time = models.TimeField(null=True, blank=True)
    work_hours = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.person.name} - {self.date}"
