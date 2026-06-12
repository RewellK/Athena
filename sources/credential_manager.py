import os


class CredentialManager:
    """Reads credentials from environment only. It never writes secrets."""

    def __init__(self, environ=None):
        self.environ = environ if environ is not None else os.environ

    def get(self, credential_key):
        if not credential_key:
            return None
        return self.environ.get(str(credential_key))

    def has(self, credential_key):
        return bool(self.get(credential_key))

    def describe_missing(self, credential_key):
        if not credential_key:
            return "Essa fonte não declarou uma chave de credencial."
        return f"Essa fonte exige a variável de ambiente {credential_key}, mas ela não está configurada."
