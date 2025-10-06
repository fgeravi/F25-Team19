"""from django.shortcuts import render
def about_view(request):
    context = {
        "team_number": "19",
        "version": "Sprint 3",         
        "release_date": "TBD",      
        "product_name": "TBD",        
        "product_description": "TBD",   

        #Team Roster
        "team_members": [
            {"name": "Dan Geravi", "role": "Developer", "email": "fgeravi@clemson.edu"},
            {"name": "Zach Wooten",   "role": "Developer", "email": "zbwoote@g.clemson.edu"},
            {"name": "Nathan Kitchens",   "role": "Developer", "email": "nkitche@g.clemson.edu"},
            {"name": "Nate WIllis",   "role": "Developer", "email": "nlw2@clemson.edu"},
            {"name": "Tian Xue",   "role": "Developer", "email": "xue7@clemson.edu"},
        ],

        "repo_url": "https://github.com/fgeravi/F25-Team19",
    }
    return render(request, "about/about.html", context)"""

from django.shortcuts import render
from .models import About

TEAM_NUMBER = 19

def about_page(request, team=19):
    row = (About.objects
           .filter(team_num=team)
           .order_by('-version_number')
           .first())
    team = getattr(row, 'team_num', None)
    return render(request, "about/about.html", {"row": row, "team": team})


