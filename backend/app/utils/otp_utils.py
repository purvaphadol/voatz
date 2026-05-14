import random

def generate_otp(length=6):
    return ''.join(random.choices('0123456789', k=length))
