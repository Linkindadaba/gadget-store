from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.home, name='home'),
    path('category/<slug:slug>/', views.category, name='category'),
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('signup/', views.signup, name='signup'),
    path('account-settings/', views.account_settings, name='account_settings'),
    path('help-support/', views.help_support, name='help_support'),
    # New Features
    path('search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('track-order/', views.track_order, name='track_order'),
]
