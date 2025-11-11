from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import IssueReportForm
from .models import IssueReport 

@login_required
def submit_issue_view(request):
    if request.method == 'POST':
        form = IssueReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            
            if request.user.is_driver:
                report.reporter_role = IssueReport.ReporterRole.DRIVER
            elif request.user.is_sponsor:
                report.reporter_role = IssueReport.ReporterRole.SPONSOR
            
            report.save()
            messages.success(request, "Your issue report has been submitted successfully. Our team will review it shortly.")
            return redirect('home')
    else:
        form = IssueReportForm()

    return render(request, 'submit_issue.html', {'form': form})