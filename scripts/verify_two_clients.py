"""Docker acceptance gate: two clients, one image, isolated data and a restore drill.

Creates only disposable, randomly named test projects; removes only their volumes.
Never accepts an existing production project/environment as an input.
"""
import json,os,secrets,socket,subprocess,time
from pathlib import Path
import requests

root=Path(__file__).resolve().parents[1]
suffix=secrets.token_hex(5)
projects=[]

def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def run(args,**kw):
    return subprocess.run(args,cwd=root,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kw).stdout

def compose(project,*args,**kw):
    env=os.environ.copy();env['CLIENT_ENV_FILE']=str(project['file'])
    return run(['docker','compose','--env-file',str(project['file']),'-f','compose.backend.yaml',*args],env=env,**kw)

try:
    run(['docker','build','-t','retail-api:0.3.0-backend','-f','backend/Dockerfile','.'])
    for client in ['a','b']:
        name=f'acceptance-{suffix}-{client}';number=port()
        run(['python3','scripts/new_backend_client.py',name,'--port',str(number)])
        project={'file':root/'client-deployments'/name/'.env','port':number};projects.append(project)
        compose(project,'up','-d','--no-build')
        with requests.Session() as http:
            http.trust_env=False
            for _ in range(120):
                try:
                    if http.get(f'http://127.0.0.1:{number}/api/v1/health/ready',timeout=2).status_code==200:break
                except requests.RequestException:pass
                time.sleep(1)
            else:raise RuntimeError('Backend readiness timed out.')
            compose(project,'exec','-T','api','python','manage.py','seed_demo',client)
            project['config']=http.get(f'http://127.0.0.1:{number}/api/v1/store/config',timeout=5).json()
        container=compose(project,'ps','-q','api').decode().strip()
        project['image']=run(['docker','inspect','--format','{{.Image}}',container]).decode().strip()
    assert projects[0]['image']==projects[1]['image'],'Clients must run identical image IDs'
    assert projects[0]['config']['business_name']!=projects[1]['config']['business_name']
    mutate="from apps.catalog.models import Category; Category.objects.create(code='isolation-probe',name='Isolation probe')"
    check="from apps.catalog.models import Category; assert not Category.objects.filter(code='isolation-probe').exists()"
    compose(projects[0],'exec','-T','api','python','manage.py','shell','-c',mutate)
    compose(projects[1],'exec','-T','api','python','manage.py','shell','-c',check)
    # An isolated test database restoration must preserve the client-A probe.
    backup=compose(projects[0],'exec','-T','db','pg_dump','-U','retail','-d','retail','--format=custom','--no-owner')
    compose(projects[0],'exec','-T','db','createdb','-U','retail','restore_check_acceptance')
    compose(projects[0],'exec','-T','db','pg_restore','-U','retail','-d','restore_check_acceptance','--exit-on-error','--no-owner',input=backup)
    count=compose(projects[0],'exec','-T','db','psql','-U','retail','-d','restore_check_acceptance','-Atc',"SELECT count(*) FROM catalog_category WHERE code='isolation-probe'").decode().strip()
    assert count=='1','Restoration did not preserve test data'
    print(json.dumps({'two_clients':'passed','same_image':projects[0]['image'],'database_isolation':'passed','restore_drill':'passed'}))
finally:
    for project in projects:
        try:compose(project,'down','--volumes','--remove-orphans')
        except subprocess.CalledProcessError:pass
        project['file'].unlink(missing_ok=True)
        try:project['file'].parent.rmdir()
        except OSError:pass
