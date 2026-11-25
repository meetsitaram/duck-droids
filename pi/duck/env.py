"""The duck Pi's user, address and key for the PC-side scripts, from the repo root's .env (git-ignored; template .env.example).
Values already in the environment win. No package needed: KEY=VALUE lines, # comments, ~ expanded."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load(path=os.path.join(ROOT, '.env')):
    if os.path.isfile(path):
        for line in open(path, encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), os.path.expanduser(v.strip().strip('"\'')))
    return {k: os.environ.get(k) for k in ('DUCK_USER', 'DUCK_HOST', 'DUCK_KEY')}
