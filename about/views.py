from django.shortcuts import render

def about_view(request):
    context = {
        "team_number": "19",
        "version": "Sprint 3",         
        "release_date": "TBD",      
        "product_name": "TBD",        
        "product_description": "TBD",   

        # Placeholder team roster; add/edit as needed
        "team_members": [
            {"name": "Dan Geravi", "role": "Developer", "email": "fgeravi@clemson.edu"},
            {"name": "Member 2",   "role": "Developer", "email": "tbd@example.com"},
            {"name": "Member 3",   "role": "Developer", "email": "tbd@example.com"},
            {"name": "Member 4",   "role": "Developer", "email": "tbd@example.com"},
        ],

        "repo_url": "https://github.com/fgeravi/F25-Team19",
    }
    return render(request, "about/about.html", context)
