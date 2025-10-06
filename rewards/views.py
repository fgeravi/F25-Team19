from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import PointChangeAudit
from users.models import DriverProfile, User, SponsorProfile
from django.shortcuts import redirect
from django.contrib import messages
from .models import award_points_to_driver
from django.utils import timezone
from datetime import timedelta 
from django.db.models import Sum 


@login_required
def point_dashboard(request):
    if not request.user.is_driver:
        return redirect('home')

    try:
        driver_profile = request.user.driverprofile
        current_balance = driver_profile.current_points
        transactions = PointChangeAudit.objects.filter(driver=request.user)
        seven_days_ago = timezone.now() - timedelta(days=7)

        weekly_earnings = PointChangeAudit.objects.filter(
            driver=request.user,
            date__gte=seven_days_ago,
            point_change_amt__gt=0
        ).aggregate(total=Sum('point_change_amt'))['total'] or 0


    except DriverProfile.DoesNotExist:
        current_balance = 0
        transactions = []
        
    context = {
        'current_balance': current_balance,
        'transactions': transactions,
        'weekly_earnings': weekly_earnings,
    }
    
    return render(request, 'rewards/dashboard.html', context)



@login_required
def add_points_view(request):
    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')

    if request.method == 'POST':
        try:
            driver_id = request.POST.get('driver')
            points = int(request.POST.get('points'))
            reason = request.POST.get('reason')
            
            sponsor_user = request.user
            driver_user = User.objects.get(pk=driver_id, is_driver=True)

            success, message = award_points_to_driver(
                sponsor_user=sponsor_user,
                driver_user=driver_user,
                points=points,
                reason=reason
            )

            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)

        except User.DoesNotExist:
            messages.error(request, "The selected driver does not exist.")
        except ValueError:
            messages.error(request, "Please enter a valid number for points.")
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            
        return redirect('rewards:add_points')

    drivers = User.objects.filter(is_driver=True, is_active=True)
    context = {
        'drivers': drivers
    }
    return render(request, 'rewards/add_points.html', context)
# Create your views here.
