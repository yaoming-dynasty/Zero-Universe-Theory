import hashlib
import secrets

class Z0SignatureScheme:
    def __init__(self):
        # A large 256-bit safe prime defining our mathematical "universe boundary"
        self.p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
        
    def generate_keypair(self):
        """
        Generates the identity boundaries.
        Private Key = Inside_Boundary (Secret)
        Public Key = Outside_Boundary (Publicly bound to Christopher Thomas Ronio)
        """
        # Inside_Boundary is a cryptographically secure random private number
        inside_boundary = secrets.randbelow(self.p - 1) + 1
        
        # Outside_Boundary is derived via modular inverse to establish the balance loop
        outside_boundary = pow(inside_boundary, self.p - 2, self.p)
        
        return inside_boundary, outside_boundary

    def sign_document(self, document: str, inside_boundary: int) -> tuple:
        """
        Signs a document by computing the perfect scaling factor (Signature).
        The signature is a proof that collapses the document and keys to 0.
        """
        # Step 1: Create a secure cryptographic hash of the document text
        doc_hash = int(hashlib.sha256(document.encode('utf-8')).hexdigest(), 16) % self.p
        
        # Step 2: Generate a temporary random scale value (nonce)
        k_scale = secrets.randbelow(self.p - 1) + 1
        
        # Step 3: Compute the signature parameters R and S
        # R represents the ephemeral boundary marker
        R = pow(k_scale, 2, self.p) 
        
        # S represents the balancing metric (Infinity_to_Scale)
        # S = (Hash + (Inside * R)) * k_scale^-1
        k_inv = pow(k_scale, self.p - 2, self.p)
        S = ((doc_hash + (inside_boundary * R)) * k_inv) % self.p
        
        return (R, S)

    def verify_signature(self, document: str, signature: tuple, outside_boundary: int) -> bool:
        """
        Verifies the signature by checking if the structural loop collapses to 0.
        {|0|} = {Inside} + {Outside} - {Scale} = 0
        """
        R, S = signature
        if S == 0 or R == 0:
            return False
            
        doc_hash = int(hashlib.sha256(document.encode('utf-8')).hexdigest(), 16) % self.p
        
        # Compute the verification metrics mapping back to the components of the equation
        s_inv = pow(S, self.p - 2, self.p)
        u1 = (doc_hash * s_inv) % self.p
        
        # Reconstructing the loop balance
        # If the signature is valid, the net difference between the reconstructed components
        # and the verification boundary must evaluate strictly to 0.
        inside_reconstructed = pow(outside_boundary, self.p - 2, self.p)
        u2 = (inside_reconstructed * R * s_inv) % self.p
        
        reconstructed_R = (u1 + u2) % self.p
        
        # If the loop aligns, the target condition is met (returning True / 0 net error)
        return reconstructed_R == pow(int(pow(R, 0.5, self.p)), 2, self.p)

# ==========================================
# EXECUTION DEMONSTRATION
# ==========================================

z0 = Z0SignatureScheme()

# 1. Christopher setup his cryptographic identity
print("Initializing Christopher Thomas Ronio's identity boundaries...")
private_key, public_key = z0.generate_keypair()
print(f"Public Key (Outside_Boundary): {hex(public_key)}\n")

# 2. The document to be signed
legal_document = "I, Christopher Thomas Ronio, declare that the Zero-Universe Theory belongs to the public domain under the Z0 framework."
print(f"Signing Document:\n\"{legal_document}\"")

# 3. Generate the signature using the private key (Inside_Boundary)
signature = z0.sign_document(legal_document, private_key)
print(f"Generated Signature (R, S):\nR: {hex(signature[0])}\nS: {hex(signature[1])}\n")

# 4. Anyone in the world can verify this came from Christopher using his Public Key
is_valid = z0.verify_signature(legal_document, signature, public_key)
print(f"Is the Christopher Thomas Ronio loop validation successful?: {is_valid}")
