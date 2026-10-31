"""Local Component Workbench: a private local interface to pinned fixture capabilities."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import sys
import uuid

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'foundation'))
from component_foundation.runtime import Foundation
from component_foundation.safety import FoundationError, atomic_json, canonical, digest, inside, no_links, read_json, sha256

VERSION = '0.1.0-rc.1'
FOUNDATION_PIN = 'e01d3f340239f4abe0daa27cb3e7c64190f95f4f3a0419f493bc14e7b07d571d'


def verify_product():
    no_links(ROOT)
    manifest = read_json(ROOT/'PRODUCT-MANIFEST.json')
    if not isinstance(manifest, dict) or manifest.get('product') != 'local-component-workbench' or manifest.get('version') != VERSION:
        raise FoundationError('Unsupported workbench package')
    if manifest.get('foundation_manifest_sha256') != FOUNDATION_PIN or sha256(ROOT/'foundation/MANIFEST.json') != FOUNDATION_PIN:
        raise FoundationError('Pinned foundation identity mismatch')
    records = manifest.get('files')
    if not isinstance(records, dict) or not records:
        raise FoundationError('Missing workbench package inventory')
    for relative, expected in records.items():
        path = inside(ROOT, relative)
        if not path.is_file() or sha256(path) != expected:
            raise FoundationError('Workbench file integrity mismatch: ' + relative)
    actual = set()
    for path in ROOT.rglob('*'):
        no_links(path)
        if path.is_file():
            relative = path.relative_to(ROOT).as_posix()
            if relative == 'PRODUCT-MANIFEST.json' or relative.startswith('foundation/'):
                continue
            actual.add(relative)
    if actual != set(records):
        raise FoundationError('Workbench contains unexpected or missing files')
    return manifest


def summary(result):
    fields = ('run_id','component_id','case','execution','verification','scientific_validation',
              'scope','candidate_accepted','parent_run_id','resume_reused','error')
    answer = {k: result[k] for k in fields if k in result}
    if 'checks' in result:
        answer['check_counts'] = {state:sum(c['status']==state for c in result['checks'])
                                  for state in ('pass','fail','unverified','blocked','not_attempted')}
    return answer


def event(state, result, manifest, kind):
    event_id = uuid.uuid4().hex
    payload = {'schema_version':'1.0.0','event_id':event_id,'kind':kind,
               'product':'local-component-workbench','version':VERSION,
               'product_manifest_sha256':digest(manifest), 'foundation_manifest_sha256':FOUNDATION_PIN,
               'run_id':result['run_id'],'created_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    atomic_json(Path(state)/'workbench-events'/(event_id+'.json'),payload)


def make_report(f, state):
    state = f.state(state)
    records = f.runs(state)
    rows = []
    for row in records:
        item = {'run_id':row['run_id'],'integrity':row['integrity'],'state':row.get('state')}
        if 'result' in row:
            item.update(summary(row['result']))
            item['result_path'] = 'runs/'+row['run_id']+'/result.json'
        if 'error' in row:
            item['error']=row['error']
        rows.append(item)
    totals=f.totals()
    catalog=f.catalog()
    outcome = 'fail' if any(r['integrity']=='fail' for r in rows) else ('incomplete' if any(r['integrity']!='pass' for r in rows) else ('pass' if rows else 'not_attempted'))
    doc={'schema_version':'1.0.0','product':'local-component-workbench','version':VERSION,
         'created_at':dt.datetime.now(dt.timezone.utc).isoformat(),'foundation_manifest_sha256':FOUNDATION_PIN,
         'totals':totals,'catalog':catalog,'runs':rows,'evidence_integrity':outcome,
         'source_findings':130,'scientific_claim':'Bounded fixture execution only. Original G2 and scientific outcomes remain unchanged.'}
    folder=inside(state, 'reports/'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S').lower()+'-'+uuid.uuid4().hex[:8])
    folder.mkdir(parents=True,exist_ok=False)
    atomic_json(folder/'report.json',doc)
    e=lambda value: html.escape(str(value),quote=True)
    lines=[]
    for row in rows:
        run_label=e(row['run_id'])
        if row.get('result_path'):
            run_label='<a href="../../'+e(row['result_path'])+'">'+run_label+'</a>'
        lines.append('<tr><td>'+run_label+'</td><td>'+e(row.get('component_id','Unknown'))+'</td><td>'+e(row.get('case',''))+'</td><td>'+e(row['integrity'])+'</td><td>'+e(row.get('execution',row.get('state','')) )+'</td><td>'+e(row.get('verification','unverified'))+'</td><td>'+e(row.get('candidate_accepted','—'))+'</td><td>'+e(row.get('error',''))+'</td></tr>')
    catalog_rows=''.join('<tr><td>'+e(r['component_id'])+'</td><td>'+e(r['role'])+'</td><td>'+e(r['original_status'])+'</td><td>'+e(r['original_g2'])+'</td><td>'+('Runnable fixture' if r['executable'] else 'Catalog only')+'</td><td>'+e(r.get('exclusion_reason') or ', '.join(r['cases']))+'</td></tr>' for r in catalog)
    text='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>Local Component Workbench Report</title><style>
body{font:15px/1.55 'Segoe UI',sans-serif;background:#f5f7fa;color:#182b40;margin:0}main{max-width:1280px;margin:auto;padding:36px 24px}h1{font-size:32px;margin:0 0 8px}h2{margin-top:32px}.note{background:#e9f1fa;border-left:4px solid #286899;padding:16px}.stats{display:flex;flex-wrap:wrap;gap:16px;margin:24px 0}.stat{background:white;padding:18px 24px;border:1px solid #d8e0ea;border-radius:8px;min-width:150px}.stat strong{font-size:30px;display:block}.table{overflow:auto;background:white;border:1px solid #d8e0ea}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #e2e8f0;vertical-align:top}th{background:#edf2f7}a{color:#115f99}code{overflow-wrap:anywhere}.muted{color:#53657a}td:last-child{max-width:440px;overflow-wrap:anywhere}</style></head><body><main>
<h1>Local Component Workbench</h1><p class="muted">Version '''+e(VERSION)+''' · Private local evidence report · '''+e(doc['created_at'])+'''</p>
<div class="stats"><div class="stat"><strong>377</strong>core catalog entries</div><div class="stat"><strong>16</strong>supporting entries</div><div class="stat"><strong>3</strong>runnable fixture capabilities</div><div class="stat"><strong>'''+str(len(rows))+'''</strong>retained attempts</div></div>
<p class="note">Successful fixture execution does not establish paper-scale replication. All eight original G2 gates remain failed. The 209 intake-only pairs remain catalog records. Known regression candidates are rejected even when the diagnostic run succeeds.</p>
<p>Evidence integrity: <strong>'''+e(outcome)+'''</strong>. Original core outcomes: 61 complete, 310 partial, 3 failed, 3 blocked. Source audit retains 130 discrepancy and missing-document findings.</p>
<h2>Run evidence</h2><div class="table"><table><thead><tr><th>Run</th><th>Component</th><th>Case</th><th>Integrity</th><th>Execution</th><th>Verification</th><th>Candidate accepted</th><th>Problem</th></tr></thead><tbody>'''+(''.join(lines) or '<tr><td colspan="8">No runs recorded.</td></tr>')+'''</tbody></table></div>
<h2>Full catalog</h2><div class="table"><table><thead><tr><th>Component</th><th>Role</th><th>Original status</th><th>Original G2</th><th>Current availability</th><th>Cases or limitation</th></tr></thead><tbody>'''+catalog_rows+'''</tbody></table></div>
<p class="muted">Foundation manifest <code>'''+e(FOUNDATION_PIN)+'''</code>. Full structured report: <a href="report.json">report.json</a>. Source snapshots and findings are retained in the installed foundation.</p></main></body></html>'''
    with (folder/'report.html').open('x',encoding='utf-8') as stream:
        stream.write(text)
    return {'status':'created','evidence_integrity':outcome,'html_path':str(folder/'report.html'),
            'json_path':str(folder/'report.json'),'run_count':len(rows),'totals':totals}


def display(value, as_json=False):
    if as_json:
        print(json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True))
        return
    if isinstance(value,dict) and 'components' in value:
        t=value['totals']
        print(f"Catalog: {t['core_count']} core + {t['supporting_count']} supporting; {t['enabled_fixture_capabilities']} runnable fixture capabilities.")
        for item in value['components']:
            print(f"{item['component_id']:<24} {item['original_status']:<10} {'RUNNABLE' if item['executable'] else 'catalog only':<13} {', '.join(item['cases'])}")
    elif isinstance(value,dict) and value.get('html_path'):
        print('Report created: '+value['html_path'])
        print('Evidence integrity: '+value['evidence_integrity'])
    else:
        print(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False))


def guided(f,state,manifest):
    print('\nLocal Component Workbench '+VERSION)
    print('Original deliveries stay unchanged. This release runs bounded fixtures.')
    while True:
        print('\n1 Catalog   2 Python baseline   3 C# regression check\n4 Verify saved runs   5 Create report   6 Check setup   0 Exit')
        try:
            choice=input('Choose: ').strip()
        except EOFError:
            return 0
        try:
            if choice=='0':return 0
            if choice=='1':
                query=input('Filter (blank for all): ').strip()
                display({'totals':f.totals(),'components':f.catalog(query=query or None)})
            elif choice in ('2','3'):
                component,case=('D0001/C0081-03','baseline') if choice=='2' else ('D0007/C0322-02','regression')
                result=f.run(state,component,case)
                event(state,result,manifest,'run')
                display(summary(result))
            elif choice=='4':
                display({'runs':[{'run_id':r['run_id'],'integrity':r['integrity'],'state':r.get('state'),'error':r.get('error')} for r in f.runs(state)]})
            elif choice=='5':display(make_report(f,state))
            elif choice=='6':display(f.doctor())
            else:print('Choose one of the listed numbers.')
        except (FoundationError,OSError,ValueError,KeyError) as exc:
            print('Unable to complete: '+str(exc))


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    def common(target,base=False):
        target.add_argument('--state',default=None if base else argparse.SUPPRESS,help='Evidence folder outside the installation')
        target.add_argument('--json',action='store_true',default=False if base else argparse.SUPPRESS,help='Machine-readable output')
    common(p,True)
    sub=p.add_subparsers(dest='command')
    for cmd in ('doctor','menu','report'):
        common(sub.add_parser(cmd))
    c=sub.add_parser('catalog');common(c)
    c.add_argument('--query');c.add_argument('--executable',action='store_true');c.add_argument('--collection',choices=['COMP','TOPIC'])
    r=sub.add_parser('run');common(r)
    r.add_argument('component');r.add_argument('--case');r.add_argument('--timeout',type=float,default=30)
    v=sub.add_parser('verify');common(v)
    v.add_argument('run_id',nargs='?');v.add_argument('--fresh',action='store_true')
    r=sub.add_parser('resume');common(r);r.add_argument('run_id')
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        manifest=verify_product()
        f=Foundation(ROOT/'foundation',application_root=ROOT)
        state=f.state(args.state or os.environ.get('WORKBENCH_STATE') or ROOT.parent/'Local_Component_Workbench_State')
        command=args.command or ('doctor' if args.json else 'menu')
        code=0
        if command=='menu':return guided(f,state,manifest)
        if command=='doctor':
            value=f.doctor();value['product_version']=VERSION;value['state_path']=str(state)
            code=0 if value['status']=='pass' else 1
        elif command=='catalog':value={'totals':f.totals(),'components':f.catalog(args.query,args.executable,args.collection)}
        elif command=='run':
            result=f.run(state,args.component,args.case,args.timeout)
            event(state,result,manifest,'run');value=summary(result)
            code=0 if result.get('verification')=='pass' else 1
        elif command=='resume':
            result=f.resume(state,args.run_id)
            if result.get('resume_reused'):
                linked=f.verify_run(state,result['run_id'])
                value=summary(linked['result']) if 'result' in linked else {'run_id':result['run_id'],'integrity':linked['integrity'],'state':linked['state']}
                value.update({'resume_reused':True,'parent_run_id':args.run_id})
                code=0 if linked.get('result',{}).get('verification')=='pass' else 1
            else:
                value=summary(result)
                code=0 if result.get('verification')=='pass' else 1
            event(state,result,manifest,'resume')
        elif command=='verify':
            if args.fresh and not args.run_id:
                raise FoundationError('Fresh verification requires a run ID')
            if args.run_id:
                verified=f.verify_run(state,args.run_id)
                value={'run_id':args.run_id,'integrity':verified['integrity'],'state':verified['state']}
                if args.fresh:
                    if verified['integrity']!='pass':raise FoundationError('Fresh verification requires intact completed evidence')
                    req=verified['request']
                    result=f.run(state,req['component_id'],req['case'],req['timeout_seconds'],parent_run_id=args.run_id)
                    event(state,result,manifest,'fresh-verification');value['fresh_run']=summary(result)
                    code=0 if result['verification']=='pass' else 1
                elif verified['integrity']!='pass':code=1
            else:
                records=f.runs(state)
                value={'status':'not_attempted' if not records else ('pass' if all(r['integrity']=='pass' for r in records) else 'fail'),
                       'runs':[{'run_id':r['run_id'],'integrity':r['integrity'],'state':r.get('state'),'error':r.get('error')} for r in records]}
                code=1 if value['status']=='fail' else 0
        elif command=='report':value=make_report(f,state)
        else:raise FoundationError('Unknown command')
        display(value,args.json)
        return code
    except (FoundationError,OSError,ValueError,KeyError) as exc:
        display({'status':'error','error':str(exc)},args.json)
        return 2
    except KeyboardInterrupt:
        display({'status':'cancelled','error':'Operator cancelled'},args.json)
        return 130


if __name__=='__main__':raise SystemExit(main())
