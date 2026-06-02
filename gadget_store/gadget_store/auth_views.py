from django.contrib.auth import views as auth_views
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

# Rate-limited wrappers for Django auth class-based views

@method_decorator(ratelimit(key='ip', rate='10/m', block=True), name='dispatch')
class RateLimitedLoginView(auth_views.LoginView):
    pass

@method_decorator(ratelimit(key='ip', rate='6/h', block=True), name='dispatch')
class RateLimitedPasswordResetView(auth_views.PasswordResetView):
    pass

@method_decorator(ratelimit(key='ip', rate='12/h', block=True), name='dispatch')
class RateLimitedPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    pass
