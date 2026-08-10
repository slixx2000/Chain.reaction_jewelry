from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from . import views
from .forms import LoginForm, StyledPasswordResetForm, StyledSetPasswordForm

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('contact/', views.contact, name='contact'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html', authentication_form=LoginForm), name='login'),
    path('logout/', views.logout, name='logout'),

    # Password reset. Without these a customer who forgets their password has
    # no way back into their account.
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='core/password_reset.html',
        email_template_name='core/email/password_reset.txt',
        subject_template_name='core/email/password_reset_subject.txt',
        form_class=StyledPasswordResetForm,
        success_url=reverse_lazy('core:password_reset_done'),
    ), name='password_reset'),
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