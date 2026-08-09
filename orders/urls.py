from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('my-orders/', views.order_history, name='history'),
    path('webhook/bila/', views.bila_webhook, name='bila_webhook'),
    path('<str:reference>/', views.order_status, name='status'),
    path('<str:reference>/state/', views.order_state, name='state'),
]
