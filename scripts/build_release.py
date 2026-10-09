from pathlib import Path
import zipfile, hashlib
root=Path(__file__).resolve().parents[1]
archive=root/'downloads/StableRotate-1.9.1.zip'
archive.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name in ('__init__.py','i18n.py'):
        z.write(root/'StableRotate'/name,'StableRotate/'+name)
    z.write(root/'LICENSE','StableRotate/LICENSE')
    z.write(root/'docs/USER_GUIDE.md','StableRotate/USER_GUIDE.md')
(root/'downloads/SHA256SUMS.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n',encoding='utf-8')
print(archive)
