from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import PointChangeAudit
from users.models import DriverProfile

@login_required
def point_dashboard(request):
    if not request.user.is_driver:
        return redirect('home')

    try:
        driver_profile = request.user.driverprofile
        current_balance = driver_profile.current_points
        transactions = PointChangeAudit.objects.filter(driver=request.user)
    except DriverProfile.DoesNotExist:
        current_balance = 0
        transactions = []
        
    context = {
        'current_balance': current_balance,
        'transactions': transactions,
    }
    
    return render(request, 'rewards/dashboard.html', context)
# Create your views here.
