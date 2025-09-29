from django.shortcuts import render

def about_view(request):
    context = {
        "team_number": 19,
        "version": 3,  #sprint 
        "release_date": "TBD",
        "product_name": "TBD",
        "product_description": "TBD",
    }
    return render(request, "about/about.html", context)
