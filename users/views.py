from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import UserRegisterForm
from django.contrib.auth.decorators import login_required
from .forms import AccountForm, DriverProfileForm, SponsorProfileForm, DriverCreationForm, DriverImportForm, SponsorCreationForm
from .forms import LockedOutAuthenticationForm
from .forms import NotificationPreferenceForm
from django.contrib.auth.decorators import login_required
from .models import DriverNotification  # NEW import
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import DriverNotification
# Password Change addition
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.utils.crypto import get_random_string
from django.utils import timezone
from audit.models import PasswordChange
from .models import SponsorProfile, DriverProfile, User, DriverChangeAudit, Organization, DriverSponsor
from django.contrib.admin.views.decorators import staff_member_required
from .forms import DriverEditForm
from django.db.models import Q
import csv 
from django.http import HttpResponse
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm  # make sure this exists in users/forms.py per earlier step


@login_required
def home(request):
    organization = None
    driver_sponsorships = None

    # Driver
    if getattr(request.user, "is_driver", False):
        driver_profile = DriverProfile.objects.filter(user=request.user).first()
        if driver_profile:
            driver_sponsorships = DriverSponsor.objects.filter(
                driver=driver_profile,
                approved=True
            )

    # Sponsor
    elif getattr(request.user, "is_sponsor", False):
        sponsor_profile = getattr(request.user, "sponsorprofile", None)
        if sponsor_profile and sponsor_profile.organization:
            organization = sponsor_profile.organization

    return render(request, "users/home.html", {
        "organization": organization,
        "driver_sponsorships": driver_sponsorships,
    })


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Set role based on selection
            account_type = form.cleaned_data['account_type']
            if account_type == 'driver':
                user.is_driver = True
            elif account_type == 'sponsor':
                user.is_sponsor = True

            user.save()  # save the user

            # Optionally, create the profile automatically
            if user.is_driver:
                from .models import DriverProfile
                DriverProfile.objects.create(user=user)
            elif user.is_sponsor:
                from .models import SponsorProfile
                from .models import SponsorProfile
                organization = form.cleaned_data.get('organization')
                if not organization:
                    # fallback: pick first organization or show error
                    organization = Organization.objects.first()
                    SponsorProfile.objects.create(user=user, organization=organization)

            messages.success(request, f'Account created for {user.username}!')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/registration/register.html', {'form': form})


# --- Notifications stuff ---

@login_required
def notifications_list(request):
    """List the current user's notifications."""
    notifs = DriverNotification.objects.filter(driver_user=request.user)
    return render(request, 'users/notifications/list.html', {'notifications': notifs})


@login_required
def notification_mark_read(request, pk: int):
    """Mark a single notification as read for the current user."""
    notif = get_object_or_404(DriverNotification, pk=pk, driver_user=request.user)
    if not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        messages.success(request, "Notification marked as read.")
    return redirect('notifications_list')

# account management view
@login_required
def account_management(request):
    user = request.user

    user_form = AccountForm(request.POST or None, instance=user)

    driver_form = None
    sponsor_form = None

    if getattr(user, "is_driver", False):
        driver_profile = getattr(user, "driverprofile", None)
        if driver_profile:
            driver_form = DriverProfileForm(request.POST or None, instance=driver_profile)

    if getattr(user, "is_sponsor", False):
        sponsor_profile = getattr(user, "sponsorprofile", None)
        if sponsor_profile:
            sponsor_form = SponsorProfileForm(request.POST or None, instance=sponsor_profile)

    if request.method == "POST":
        forms = [user_form]
        if driver_form: forms.append(driver_form)
        if sponsor_form: forms.append(sponsor_form)

        if all(f.is_valid() for f in forms):
            for f in forms:
                f.save()
            messages.success(request, "Your account has been updated successfully.")
            return redirect("account_management")
        else:
            messages.error(request, "Please correct the errors below.")

    context = {
        "user_form": user_form,
        "driver_form": driver_form,
        "sponsor_form": sponsor_form,
    }
    return render(request, "users/account_management.html", context)

# Password Change Audit
class AuditedPasswordChangeView(PasswordChangeView):
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Get request info
        user = self.request.user
        ip = self.request.META.get('REMOTE_ADDR')
        user_agent = self.request.META.get('HTTP_USER_AGENT')

        # Log the event
        PasswordChange.objects.create(
            username=user.username,
            ip_address=ip,
            user_agent=user_agent,
            timestamp=timezone.now()
        )
        return response

@login_required
def manage_drivers_view(request):
    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('home')

    try:
        sponsor_profile = request.user.sponsorprofile
        sponsor_organization = sponsor_profile.organization

        # filtering inputs
        search_query = request.GET.get('q', '')
        status_query = request.GET.get('status', '')

        drivers = DriverSponsor.objects.filter(
            driver__organization=sponsor_organization,
            approved=True
        ).select_related('driver__user')

        # search filter
        if search_query:
            drivers = drivers.filter(
                Q(driver__user__username__icontains=search_query) |
                Q(driver__user__first_name__icontains=search_query) |
                Q(driver__user__last_name__icontains=search_query)
            )

        # status filter
        if status_query == "active":
            drivers = drivers.filter(driver__user__is_active=True)
        elif status_query == "inactive":
            drivers = drivers.filter(driver__user__is_active=False)

    except SponsorProfile.DoesNotExist:
        messages.error(request, "Your sponsor profile could not be found.")
        return redirect('home')

    context = {
        'drivers': drivers
    }
    return render(request, 'users/manage_drivers.html', context)

@login_required
def edit_point_value_view(request):
    """
    Sponsor can change how much 1 point is worth in dollars
    for THEIR organization only.
    """
    # Must be a sponsor
    if not getattr(request.user, "is_sponsor", False):
        messages.error(request, "You do not have permission to edit point settings.")
        return redirect("home")

    # Get sponsor's org
    sponsor_profile = getattr(request.user, "sponsorprofile", None)
    if not sponsor_profile or not sponsor_profile.organization:
        messages.error(request, "You are not assigned to an organization.")
        return redirect("home")

    org = sponsor_profile.organization

    from .forms import OrganizationPointValueForm
    if request.method == "POST":
        form = OrganizationPointValueForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            messages.success(request, "Point value updated for your organization.")
            return redirect("edit_point_value")
    else:
        form = OrganizationPointValueForm(instance=org)

    return render(request, "users/sponsor/edit_point_value.html", {
        "form": form,
        "org": org,
    })


@login_required
def edit_driver_view(request, driver_id):
    # Only sponsors can access this view
    if not getattr(request.user, "is_sponsor", False):
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('home')

    try:
        sponsor_profile = request.user.sponsorprofile
    except SponsorProfile.DoesNotExist:
        messages.error(request, "Sponsor profile not found.")
        return redirect('home')

    # Ensure the driver is approved under this sponsor
    driver_sponsor = get_object_or_404(
        DriverSponsor,
        driver__user__id=driver_id,
        sponsor=sponsor_profile,
        approved=True
    )
    driver_user = driver_sponsor.driver.user

    if request.method == 'POST':
        form = DriverEditForm(request.POST, instance=driver_user)
        if form.is_valid():
            # Log changes before saving
            for field in form.changed_data:
                DriverChangeAudit.objects.create(
                    sponsor=request.user,
                    driver=driver_user,
                    field_name=field,
                    old_value=form.initial.get(field),
                    new_value=form.cleaned_data.get(field)
                )
            
            form.save()
            messages.success(request, f"Successfully updated profile for {driver_user.username}.")
            return redirect('manage_drivers')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DriverEditForm(instance=driver_user)

    context = {
        'form': form,
        'driver_user': driver_user
    }
    return render(request, 'users/edit_driver.html', context)


@login_required
def notification_preferences(request):
    # Only drivers have these prefs right now
    if not getattr(request.user, "is_driver", False):
        messages.error(request, "Only drivers can manage notification preferences.")
        return redirect("home")

    driver_profile = getattr(request.user, "driverprofile", None)
    if not driver_profile:
        messages.error(request, "Driver profile not found.")
        return redirect("home")

    if request.method == "POST":
        form = NotificationPreferenceForm(request.POST, instance=driver_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your notification settings have been updated.")
            return redirect("notification_preferences")
    else:
        form = NotificationPreferenceForm(instance=driver_profile)

    return render(
        request,
        "users/notifications/preferences.html",
        {
            "form": form,
        },
    )

@login_required
def add_driver_view(request):
    if not getattr(request.user, "is_sponsor", False):
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('home')

    try:
        sponsor_profile = request.user.sponsorprofile
        sponsor_organization = sponsor_profile.organization
    except SponsorProfile.DoesNotExist:
        messages.error(request, "Your sponsor profile could not be found.")
        return redirect('home')

    if request.method == 'POST':
        form = DriverCreationForm(request.POST)
        if form.is_valid():
            # Save the driver
            new_driver_user = form.save(organization=sponsor_organization)

            # Create a DriverSponsor relationship (approved by default)
            from .models import DriverSponsor
            DriverSponsor.objects.create(
                driver=new_driver_user.driverprofile,
                sponsor=sponsor_profile,
                approved=True
            )

            messages.success(request, f"New driver '{new_driver_user.username}' has been added successfully.")
            return redirect('manage_drivers')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DriverCreationForm()

    context = {
        'form': form
    }
    return render(request, 'users/add_driver.html', context)

@login_required
def add_sponsor_view(request):
    if not getattr(request.user, "is_sponsor", False):
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('home')

    try:
        sponsor_profile = request.user.sponsorprofile
        sponsor_organization = sponsor_profile.organization
    except SponsorProfile.DoesNotExist:
        messages.error(request, "Your sponsor profile could not be found.")
        return redirect('home')

    if request.method == 'POST':
        form = SponsorCreationForm(request.POST)
        if form.is_valid():
            new_sponsor_user = form.save(organization=sponsor_organization)

            messages.success(request, f"New sponsor user '{new_sponsor_user.username}' has been added successfully.")
            return redirect('manage_drivers')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SponsorCreationForm()

    context = {
        'form': form
    }
    return render(request, 'users/add_sponsor.html', context)





@login_required
def import_drivers_view(request):
    if not getattr(request.user, "is_sponsor", False):
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('home')

    try:
        sponsor_profile = request.user.sponsorprofile
        sponsor_organization = sponsor_profile.organization
    except SponsorProfile.DoesNotExist:
        messages.error(request, "Your sponsor profile could not be found.")
        return redirect('home')

    error_messages = []
    success_messages = []

    if request.method == 'POST':
        form = DriverImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']

            try:
                lines = uploaded_file.read().decode('utf-8').splitlines()

                for i, line in enumerate(lines):
                    line_num = i + 1
                    try:
                        parts = line.strip().split('|')

                        if len(parts) != 5:
                            error_messages.append(
                                f"Line {line_num}: Invalid format. Must be 5 values per line (e.g., D||FirstName|LastName|Email)."
                            )
                            continue

                        user_type, _, first_name, last_name, email = parts

                        if user_type not in ['D', 'S']:
                            error_messages.append(f"Line {line_num}: Invalid user type '{user_type}'.")
                            continue
                        if not all([first_name, last_name, email]):
                            error_messages.append(
                                f"Line {line_num}: First name, last name, and email are required."
                            )
                            continue
                        if User.objects.filter(email=email).exists():
                            error_messages.append(
                                f"Line {line_num}: User with email '{email}' already exists."
                            )
                            continue

                        temp_password = get_random_string(10)

                        user = User.objects.create_user(
                            username=email,
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            password=temp_password
                        )

                        if user_type == 'D':
                            user.is_driver = True
                            driver_profile = DriverProfile.objects.create(
                                user=user, organization=sponsor_organization
                            )

                            # Automatically create a DriverSponsor relationship
                            from .models import DriverSponsor
                            DriverSponsor.objects.create(
                                driver=driver_profile,
                                sponsor=sponsor_profile,
                                approved=True
                            )

                        elif user_type == 'S':
                            user.is_sponsor = True
                            SponsorProfile.objects.create(user=user, organization=sponsor_organization)

                        user.save()
                        success_messages.append(
                            f"Successfully created user for {email}. Temporary password: {temp_password}"
                        )

                    except Exception as e:
                        error_messages.append(f"Line {line_num}: An unexpected error occurred - {e}")

            except Exception as e:
                messages.error(request, f"Could not read the uploaded file. Error: {e}")

    else:
        form = DriverImportForm()

    context = {
        'form': form,
        'error_messages': error_messages,
        'success_messages': success_messages,
    }
    return render(request, 'users/import_drivers.html', context)


@login_required
def export_drivers_csv(request):
    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('home')

    try:
        sponsor_profile = request.user.sponsorprofile
        sponsor_organization = sponsor_profile.organization

        drivers_query = DriverSponsor.objects.filter(
            driver__organization=sponsor_organization,
            approved=True
        ).select_related('driver__user').order_by('driver__user__username')

        search_query = request.GET.get('q', '')
        status_query = request.GET.get('status', '')

        if search_query:
            drivers_query = drivers_query.filter(
                Q(driver__user__username__icontains=search_query) |
                Q(driver__user__first_name__icontains=search_query) |
                Q(driver__user__last_name__icontains=search_query)
            )

        if status_query == "active":
            drivers_query = drivers_query.filter(driver__user__is_active=True)
        elif status_query == "inactive":
            drivers_query = drivers_query.filter(driver__user__is_active=False)

        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="drivers_export_{timezone.now().strftime("%Y-%m-%d")}.csv"'},
        )

        writer = csv.writer(response)
        
        writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Status'])

        for ds in drivers_query:
            user = ds.driver.user
            status = "Active" if user.is_active else "Inactive"
            writer.writerow([user.username, user.email, user.first_name, user.last_name, status])

        return response

    except SponsorProfile.DoesNotExist:
        messages.error(request, "Your sponsor profile could not be found.")
        return redirect('home')
    

@login_required
def view_sponsors_list(request):
    if not request.user.is_driver:
        messages.error(request, "You do not have permission to view this page.")
        return redirect('home')

    try:
        driver_profile = request.user.driverprofile
        driver_organization = driver_profile.organization

        if not driver_organization:
            messages.warning(request, "You are not currently associated with an organization.")
            sponsors = []
        else:
            sponsors = SponsorProfile.objects.filter(
                organization=driver_organization
            ).select_related('user').order_by('user__last_name', 'user__first_name')

    except DriverProfile.DoesNotExist:
        messages.error(request, "Your driver profile could not be found.")
        return redirect('home')

    context = {
        'sponsors': sponsors
    }
    return render(request, 'users/view_sponsors.html', context)

@login_required
def notification_delete(request, pk: int):
    """Delete a single notification owned by the current user."""
    notif = get_object_or_404(DriverNotification, pk=pk, driver_user=request.user)
    if request.method == "POST":
        notif.delete()
        messages.success(request, "Notification deleted.")
    return redirect('notifications_list')

@staff_member_required
def admin_import_users_view(request):
    error_messages = []
    success_messages = []
    
    organizations_in_session = {}

    if request.method == 'POST':
        form = DriverImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            try:
                lines = uploaded_file.read().decode('utf-8').splitlines()

                for i, line in enumerate(lines):
                    line_num = i + 1
                    try:
                        parts = line.strip().split('|')
                        user_type = parts[0]

                        if user_type == 'O':
                            if len(parts) != 2:
                                error_messages.append(f"Line {line_num}: Organization ('O') records must have the format O|OrganizationName.")
                                continue
                            org_name = parts[1]
                            if Organization.objects.filter(name=org_name).exists() or org_name in organizations_in_session:
                                error_messages.append(f"Line {line_num}: Organization '{org_name}' already exists.")
                                continue
                            
                            new_org = Organization.objects.create(name=org_name)
                            organizations_in_session[org_name] = new_org
                            success_messages.append(f"Successfully created organization: {org_name}")

                        elif user_type in ['D', 'S']:
                            if len(parts) != 5:
                                error_messages.append(f"Line {line_num}: User ('D' or 'S') records must have the format Type|OrgName|FirstName|LastName|Email.")
                                continue
                            
                            _, org_name, first_name, last_name, email = parts

                            if not all([org_name, first_name, last_name, email]):
                                error_messages.append(f"Line {line_num}: Organization, first name, last name, and email are required.")
                                continue
                            if User.objects.filter(email=email).exists():
                                error_messages.append(f"Line {line_num}: User with email '{email}' already exists.")
                                continue

                            organization = None
                            if org_name in organizations_in_session:
                                organization = organizations_in_session[org_name]
                            else:
                                try:
                                    organization = Organization.objects.get(name=org_name)
                                except Organization.DoesNotExist:
                                    error_messages.append(f"Line {line_num}: Organization '{org_name}' not found. It must exist or be created earlier in this file.")
                                    continue
                            
                            temp_password = get_random_string(10)
                            user = User.objects.create_user(username=email, email=email, first_name=first_name, last_name=last_name, password=temp_password)

                            if user_type == 'D':
                                user.is_driver = True
                                DriverProfile.objects.create(user=user, organization=organization)
                            elif user_type == 'S':
                                user.is_sponsor = True
                                SponsorProfile.objects.create(user=user, organization=organization)
                            
                            user.save()
                            success_messages.append(f"Successfully created {email} in '{org_name}'. Password: {temp_password}")
                        
                        else:
                            error_messages.append(f"Line {line_num}: Invalid record type '{user_type}'. Must be 'O', 'D', or 'S'.")

                    except Exception as e:
                        error_messages.append(f"Line {line_num}: An unexpected error occurred - {e}")

            except Exception as e:
                messages.error(request, f"Could not read or process the file. Error: {e}")
    else:
        form = DriverImportForm()

    context = {
        'form': form,
        'error_messages': error_messages,
        'success_messages': success_messages,
        'title': 'Import Users and Organizations',
        'has_permission': True,
    }
    return render(request, 'admin/users/user/import_users.html', context)

def login_view(request):
    form = LoginForm(request=request, data=request.POST or None)
    msg = None

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        remember = form.cleaned_data.get("remember_me", False)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            request.session.set_expiry(0 if not remember else None)
            redirect_to = request.POST.get('next') or 'home'
            return redirect(redirect_to)
        else:
            msg = "Invalid credentials."

    return render(request, "users/registration/login.html", {"form": form, "message": msg})

@login_required
def driver_performance_view(request):
    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')

    sponsor_profile = getattr(request.user, "sponsorprofile", None)
    if not sponsor_profile:
        messages.error(request, "Your sponsor profile could not be found.")
        return redirect("home")

    sort_param = request.GET.get('sort', '-points') 
    valid_sorts = ['driver', '-driver', 'points', '-points']
    if sort_param not in valid_sorts:
        sort_param = '-points'

    if 'driver' in sort_param:
        order_by_field = 'driver__user__username' if sort_param == 'driver' else '-driver__user__username'
    else:
        order_by_field = sort_param  
    sponsorships = (
        DriverSponsor.objects
        .filter(sponsor=sponsor_profile, approved=True)
        .select_related('driver__user') 
        .order_by(order_by_field)
    )

    context = {
        'sponsorships': sponsorships,
        'current_sort': sort_param,
    }
    return render(request, 'users/driver_performance.html', context)
