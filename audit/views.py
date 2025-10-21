from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from django.contrib import messages
from .models import KnownLoginLocations

# Create your views here.

def ack_all_locations(request):    
    KnownLoginLocations.objects.filter(user=request.user, acknowledged=False).update(acknowledged=True)
    messages.success(request, "Notification dismissed.")
    return redirect('/admin/')