"""
Custom throttle classes for rate limiting.

Provides different throttle rates for:
- Anonymous users (more restrictive)
- Authenticated users (less restrictive)
- Sensitive operations (login, password reset - very restrictive)
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, ScopedRateThrottle


class BurstRateThrottle(UserRateThrottle):
    """
    Allows short bursts of requests from authenticated users.
    Applied globally to all endpoints for authenticated users.
    """
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    """
    Limits sustained usage over a longer period for authenticated users.
    Applied globally to all endpoints for authenticated users.
    """
    scope = 'sustained'


class AnonBurstRateThrottle(AnonRateThrottle):
    """
    Allows short bursts of requests from anonymous users.
    More restrictive than authenticated users.
    """
    scope = 'anon_burst'


class AnonSustainedRateThrottle(AnonRateThrottle):
    """
    Limits sustained usage over a longer period for anonymous users.
    More restrictive than authenticated users.
    """
    scope = 'anon_sustained'


class LoginRateThrottle(AnonRateThrottle):
    """
    Very restrictive throttle for login attempts.
    Prevents brute force attacks on login endpoint.
    """
    scope = 'login'


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    Restrictive throttle for password reset requests.
    Prevents abuse of password reset emails.
    """
    scope = 'password_reset'


class PasswordChangeRateThrottle(UserRateThrottle):
    """
    Moderate throttle for password changes.
    Prevents abuse while allowing legitimate use.
    """
    scope = 'password_change'


class WriteOperationThrottle(UserRateThrottle):
    """
    Rate scope for write operations (POST, PUT, PATCH, DELETE).
    More restrictive than read operations.
    Apply via WriteThrottleMixin — not directly via throttle_classes — so that
    GET requests on the same view are not inadvertently write-throttled.
    """
    scope = 'write'


class WriteThrottleMixin:
    """
    Applies WriteOperationThrottle only to mutating HTTP methods
    (POST, PUT, PATCH, DELETE). GET/HEAD/OPTIONS use the global default throttles.

    Separates the *when-to-throttle* decision (here, in the view layer)
    from the *how-to-throttle* mechanics (WriteOperationThrottle scope/rate).
    Usage: inherit before the DRF generic view class.
    """
    def get_throttles(self):
        throttles = super().get_throttles()  # type: ignore[misc]
        if self.request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            throttles = [WriteOperationThrottle()] + throttles
        return throttles
