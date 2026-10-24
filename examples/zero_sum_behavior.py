import secrets

def generate_key_pair(secret_message_int):
    # Inside_Boundary is our secret data
    inside = secret_message_int 
    
    # Outside_Boundary is a randomly generated mask (noise)
    outside = secrets.randbits(256)
    
    # Infinity_to_Scale is the balancing key that forces the system to equal 0
    # In a modular system (like a clock), this creates the perfect loop
    MODULUS = 2**256
    scale = (inside + outside) % MODULUS
    
    return outside, scale

def verify_identity(inside, outside, scale):
    MODULUS = 2**256
    # Check if the core equation balances perfectly to 0 (the empty state)
    result = (inside + outside - scale) % MODULUS
    return result == 0

# Example Usage:
secret_password = 987654321
outside_noise, scale_key = generate_key_pair(secret_password)

# The verification returns True (0), confirming the system is perfectly balanced
print("Is the cryptographic loop valid?:", verify_identity(secret_password, outside_noise, scale_key))
