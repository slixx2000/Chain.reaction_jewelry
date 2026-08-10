from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django_ratelimit.decorators import ratelimit
from . import views
from .forms import LoginForm, StyledPasswordResetForm, StyledSetPasswordForm

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('contact/', views.contact, name='contact'),
    path('terms/', views.legal, {'page': 'terms'}, name='terms'),
    path('privacy/', views.legal, {'page': 'privacy'}, name='privacy'),
    path('returns/', views.legal, {'page': 'returns'}, name='returns'),
    path('signup/', views.signup, name='signup'),
    # Brute force is throttled per IP and per username, so one attacker cannot
    # spread attempts across usernames, nor lock a victim out from one address.
    path('login/', ratelimit(key='ip', rate='10/5m', method='POST', block=True)(
        ratelimit(key='post:username', rate='5/5m', method='POST', block=True)(
            auth_views.LoginView.as_view(
                template_name='core/login.html', authentication_form=LoginForm)
        )), name='login'),
    path('logout/', views.logout, name='logout'),

    # Password reset. Without these a customer who forgets their password has
    # no way back into their account.
    path('password-reset/', ratelimit(key='ip', rate='3/h', method='POST', block=True)(
        ratelimit(key='post:email', rate='3/h', method='POST', block=True)(
        auth_views.PasswordResetView.as_view(
        template_name='core/password_reset.html',
        email_template_name='core/email/password_reset.txt',
        subject_template_name='core/email/password_reset_subject.txt',
        form_class=StyledPasswordResetForm,
        success_url=reverse_lazy('core:password_reset_done'),
    ))), name='password_reset'),
    path('password-reset/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='core/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='core/password_reset_confirm.html',
        form_class=StyledSetPasswordForm,
        success_url=reverse_lazy('core:password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='core/password_reset_complete.html',
    ), name='password_reset_complete'),
]