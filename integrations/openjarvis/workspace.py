"""Documents scoped to Athena's private workspace; never overwrite user files."""
import hashlib
import os
from pathlib import Path


class Workspace:
    def __init__(self, root):
        self.root = Path(root) / 'documents'
        if self.root.is_symlink():
            raise ValueError('Diretório de documentos não pode ser link')
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def path(self, name):
        if not isinstance(name, str) or not 1 <= len(name) <= 120 or name in {'.', '..'} or any(c in name for c in '/\\\x00'):
            raise ValueError('Use somente um nome de arquivo, sem diretórios')
        path = self.root / name
        if path.is_symlink() or (path.exists() and path.stat().st_nlink != 1):
            raise ValueError('Links não são permitidos')
        if self.root.is_symlink():
            raise ValueError('Diretório de documentos não pode ser link')
        return path

    def write(self, name, content):
        if not isinstance(content, str) or not content.strip() or len(content) > 8000:
            raise ValueError('Documento deve conter de 1 a 8000 caracteres')
        path = self.path(name)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            file.write(content)
        actual = path.read_bytes()
        if actual != content.encode('utf-8'):
            raise RuntimeError('Verificação de conteúdo falhou')
        return {'name': name, 'path': str(path), 'sha256': hashlib.sha256(actual).hexdigest(), 'verified': True}

    def read(self, name):
        path = self.path(name)
        if not path.is_file() or path.stat().st_size > 32000:
            raise ValueError('Arquivo inexistente ou excede 32 KB')
        return {'name': name, 'content': path.read_text(encoding='utf-8')[:8000], 'source': 'workspace_document'}

    def list(self):
        return {'files': [p.name for p in sorted(self.root.iterdir()) if p.is_file() and not p.is_symlink()][:100]}
