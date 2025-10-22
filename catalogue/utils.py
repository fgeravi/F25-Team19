import requests

# helper function for retrieving products from Platzi
def fetch_products_from_api():
    url = "https://api.escuelajs.co/api/v1/products"  # Platzi Fake Store API
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []