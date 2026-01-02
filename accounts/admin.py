from django.contrib import admin
from .models import PendingUser, User
# Register your models here.
admin.site.register(PendingUser)
admin.site.register(User)