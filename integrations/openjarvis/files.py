"""User-authorized directory roots, relative paths, verified non-overwriting writes."""
import hashlib
import os
from pathlib import Path
import shutil


class Files:
    def __init__(self,settings,workspace):
        self.settings=settings
        self.workspace=Path(workspace).absolute()

    def roots(self):
        configured=self.settings.get('fileRoots',{})
        roots={'workspace':str(self.workspace)}
        if isinstance(configured,dict):
            roots.update({str(k):str(v) for k,v in configured.items() if isinstance(v,str)})
        return roots

    def path(self,root,path='.'):
        directory=self.roots().get(root)
        if not directory: raise ValueError('Diretório não autorizado; consulte operation=roots')
        base=Path(directory).expanduser().absolute()
        if not base.is_dir() or base.is_symlink(): raise ValueError('Raiz precisa ser diretório real existente')
        relative=Path(path)
        if relative.is_absolute() or any(p in {'..','.git','.ssh','.aws','venv'} or p.startswith('.') for p in relative.parts if p!='.'):
            raise ValueError('Caminhos ocultos, absolutos ou ascendentes não são permitidos')
        current=base
        for part in relative.parts:
            current=current/part
            if current.is_symlink(): raise ValueError('Links não são permitidos')
        if not current.resolve().is_relative_to(base.resolve()): raise ValueError('Arquivo fora da raiz autorizada')
        if current.exists() and current.is_file() and current.stat().st_nlink!=1: raise ValueError('Links físicos não são permitidos')
        return current

    @staticmethod
    def receipt(path):
        return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'verified':True}

    def execute(self,args):
        op=args['operation']
        if op=='roots': return {'roots':self.roots()}
        path=self.path(args.get('root','workspace'),args.get('path','.'))
        if op=='list':
            if not path.is_dir(): raise ValueError('Não é diretório')
            return {'entries':[{'name':p.name,'directory':p.is_dir()} for p in sorted(path.iterdir()) if not p.name.startswith('.') and not p.is_symlink()][:100]}
        if op=='read':
            if not path.is_file() or path.stat().st_size>100000: raise ValueError('Leitura exige arquivo de texto até 100 KB')
            return {'path':str(path),'content':path.read_text(encoding='utf-8')[:12000],'source':'user_file_untrusted'}
        if not self.settings.get('localAutonomyEnabled',True): raise ValueError('Escrita local desativada')
        if op=='mkdir':
            path.mkdir(mode=0o700,exist_ok=True)
            return {'path':str(path),'directory':True}
        if op=='write':
            content=args.get('content','')
            if not content or len(content)>8000: raise ValueError('Conteúdo de 1 a 8000 caracteres')
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'w',encoding='utf-8') as file: file.write(content)
            return self.receipt(path)
        if op=='copy':
            destination=self.path(args.get('root','workspace'),args['destination'])
            if not path.is_file() or path.stat().st_size>10_000_000: raise ValueError('Cópia exige arquivo até 10 MB')
            fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as output,path.open('rb') as source: shutil.copyfileobj(source,output)
            if path.read_bytes()!=destination.read_bytes(): raise RuntimeError('Cópia falhou na comparação')
            return self.receipt(destination)
        raise ValueError('Operação de arquivos não permitida')
