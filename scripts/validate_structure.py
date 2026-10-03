#!/usr/bin/env python3
"""Check this project's flat frontmatter, links, IDs, and standalone skill graph.
This intentionally accepts only the simple one-line name/description schema used
here; skill-creator quick_validate.py is the additional general YAML validator.
"""
import ast
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]
LINK=re.compile(r'\[[^\]]*\]\(([^)]+)\)')
ID=re.compile(r'^## ((?:SD-[A-Z0-9]+|CLEAN|REVIEW)-\d{3})(?:\s|$)',re.M)
CONDITION=re.compile(r'^### (SD-[A-Z0-9]+-\d{3}\.C\d{2})[^\n]*\n(.*?)(?=^## |^### |\Z)',re.M|re.S)
FIELDS=('Apply when','Required / prohibited','Rationale','Implement','Unsafe → corrected','Positive check','Negative check','Evidence','Bounds / sources')

def main():
    errors=[];ids=[];conditions=[];checked=0;mappings=[]
    for skill in sorted((ROOT/'skills').iterdir()):
        if not skill.is_dir():continue
        entry=skill/'SKILL.md';text=entry.read_text()
        front=re.match(r'\A---\n(.*?)\n---\n',text,re.S)
        if not front:errors.append(str(entry)+': missing frontmatter');continue
        fields={}
        for line in front[1].splitlines():
            if not re.fullmatch(r'(name|description): [^\r\n]+',line):errors.append(str(entry)+': unsupported frontmatter form');continue
            key,value=line.split(': ',1)
            if key in fields:errors.append(str(entry)+': duplicate frontmatter key')
            fields[key]=value
        if fields.get('name')!=skill.name or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',skill.name):errors.append(str(entry)+': invalid name')
        if not fields.get('description'):errors.append(str(entry)+': missing description')
        reached=set();queue=[entry.resolve()]
        while queue:
            p=queue.pop()
            if p in reached:continue
            reached.add(p)
            if p.suffix!='.md':continue
            for target in LINK.findall(p.read_text()):
                if '://' in target:continue
                local=unquote(target.split('#')[0])
                q=(p.parent/local).resolve() if local else p
                if not q.is_relative_to(skill.resolve()):errors.append(str(p)+': external skill dependency '+target)
                elif not q.is_file():errors.append(str(p)+': missing '+target)
                else:queue.append(q)
        resources=[p for p in skill.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        for p in resources:
            if p.resolve() not in reached:errors.append(str(p)+': unreachable resource')
            if p.suffix=='.json':json.loads(p.read_text())
            if p.suffix=='.py':ast.parse(p.read_text())
            if p.suffix=='.md':
                content=p.read_text();ids.extend(ID.findall(content))
                for condition,body in CONDITION.findall(content):
                    conditions.append(condition)
                    if condition.split('.')[0] not in ID.findall(content):errors.append(str(p)+': condition lacks local parent '+condition)
                    for field in FIELDS:
                        if '**'+field+':**' not in body:errors.append(str(p)+': missing '+field+' in '+condition)
                if p.parent.name=='topics' and not CONDITION.search(content):errors.append(str(p)+': topic lacks conditions')
                if p.parent.name=='stacks':
                    for line in content.splitlines():
                        if '**Condition mapping:**' in line:
                            mapped=re.findall(r'SD-[A-Z0-9]+-\d{3}\.C\d{2}',line)
                            if not mapped:errors.append(str(p)+': empty condition mapping')
                            mappings.extend((str(p),identifier) for identifier in mapped)
                        if line.startswith('- Parent:'):errors.append(str(p)+': redundant parent metadata')
                    for block in re.split(r'(?=^## SD-)',content,flags=re.M)[1:]:
                        for field in ('Condition mapping','Apply when','Unsafe → corrected','Positive check','Negative check','Evidence'):
                            if '**'+field+':**' not in block:errors.append(str(p)+': profile missing '+field)
                        for field in ('Required implementation behavior','Rationale','Limit'):
                            if '- '+field+':' not in block:errors.append(str(p)+': profile missing '+field)
                        if not re.search(r'^- Implementation(?: option| options)?:',block,re.M):errors.append(str(p)+': profile missing implementation')
                        if not re.search(r'^- Sources?:',block,re.M):errors.append(str(p)+': profile missing source')
                if p.name=='acceptance-conditions.md':
                    for block in re.split(r'(?=^## (?:CLEAN|REVIEW)-)',content,flags=re.M)[1:]:
                        for field in FIELDS:
                            if '**'+field+':**' not in block:errors.append(str(p)+': workflow condition missing '+field)

                if re.search('[\u0400-\u04ff]',content):errors.append(str(p)+': unexpected Cyrillic text')
                if '[TODO:' in content:errors.append(str(p)+': unfinished placeholder')
        checked+=1
    for path,identifier in mappings:
        if identifier not in conditions:errors.append(path+': nonexistent mapped condition '+identifier)
    if len(ids)!=len(set(ids)):errors.append('duplicate requirement ID')
    if len(conditions)!=len(set(conditions)):errors.append('duplicate condition ID')
    root_docs=[ROOT/'README.md',ROOT/'tests/README.md']
    if (ROOT/'AGENTS.md').is_file():root_docs.append(ROOT/'AGENTS.md')
    for p in root_docs:
        text=p.read_text()
        for target in LINK.findall(text):
            if '://' not in target and not (p.parent/target.split('#')[0]).exists():errors.append(str(p)+': broken link '+target)
        if 'docs/roadmap.md' in text:errors.append(str(p)+': stale roadmap link')
    # Independent tools carry their own documentation and runtime packages.
    tools_checked=0
    for tool in sorted((ROOT/'tools').iterdir()):
        if not tool.is_dir():continue
        tools_checked+=1
        metadata=tool/'pyproject.toml'
        if not metadata.is_file():
            errors.append(str(tool)+': missing package metadata');continue
        if not re.search(r'^name = "'+re.escape(tool.name)+r'"$',metadata.read_text(),re.M):
            errors.append(str(metadata)+': package/directory name mismatch')
        for name in ('README.md','LICENSE'):
            if not (tool/name).is_file():errors.append(str(tool)+': missing '+name)
        for p in tool.rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts:continue
            if p.suffix=='.py':ast.parse(p.read_text())
            if p.suffix=='.json':json.loads(p.read_text())
            if p.suffix=='.md':
                content=p.read_text()
                for target in LINK.findall(content):
                    if '://' in target:continue
                    local=unquote(target.split('#')[0])
                    q=(p.parent/local).resolve() if local else p.resolve()
                    if not q.is_relative_to(tool.resolve()):errors.append(str(p)+': external tool dependency '+target)
                    elif not q.is_file():errors.append(str(p)+': missing '+target)
                if '[TODO:' in content:errors.append(str(p)+': unfinished placeholder')
                if re.search('[\u0400-\u04ff]',content):errors.append(str(p)+': unexpected Cyrillic text')
    if errors:
        print('\n'.join(errors));return 1
    print(json.dumps({'skills':checked,'tools':tools_checked,'unique_requirement_ids':len(ids),'topic_conditions':len(conditions),'status':'valid_structure','behavior_verified':False}));return 0

if __name__=='__main__':sys.exit(main())
