import secrets
import string


def generate_otp(length=6):
    """Generate a cryptographically secure numeric OTP.

    Uses :func:`secrets.choice` instead of :func:`random.choices` so that
    the generated code is not predictable from a known PRNG state.

    Args:
        length: Number of digits in the OTP (default 6).

    Returns:
        A string of *length* random decimal digits.
    """
    return ''.join(secrets.choice(string.digits) for _ in range(length))
