import bcrypt


class PasswordHasher:
    """
    Password hashing and verification service.
    """

    def hash(self, password: str) -> str:
        """
        Hash a plaintext password.
        Args:
            password (str): The plaintext password to hash.
        Returns:
            str: The hashed password.
        """
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify(self, password: str, hashed: str) -> bool:
        """
        Verify a plaintext password against a hashed password.
        Args:
            password (str): The plaintext password to verify.
            hashed (str): The hashed password to compare against.
        Returns:
            bool: True if the password matches the hash, False otherwise.
        """
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
