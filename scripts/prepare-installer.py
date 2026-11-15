# SPDX-License-Identifier: GPL-3.0-only
"""Build the language RTFs and a safe exact-file uninstall manifest, then NSIS."""
from pathlib import Path
import argparse,hashlib,subprocess

parser=argparse.ArgumentParser()
parser.add_argument('--payload',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--compiler',type=Path,required=True)
parser.add_argument('--test-build',action='store_true')
args=parser.parse_args()
source=Path(__file__).resolve().parents[1]
payload=args.payload.resolve()
assert (payload/'StrigoiAetherMap.exe').is_file()
assert (payload/'source/strigoi-aether-map-source.zip').is_file()
build=args.output.resolve().parent/'installer-build'
build.mkdir(parents=True,exist_ok=True)
digest=hashlib.sha256()
languages=('pt_BR','en_US','es-419')
for language in languages:
    path=source/f'app/assets/legal/terms-{language}.txt'
    original=path.read_bytes()
    digest.update(original)
    def escape(text):
        return ''.join('\\'+c if c in '\\{}' else ('\\u'+str(ord(c) if ord(c)<32768 else ord(c)-65536)+'?' if ord(c)>127 else c) for c in text)
    paragraphs=path.read_text(encoding='utf-8-sig').splitlines()
    rtf='{\\rtf1\\ansi\\ansicpg1252\\deff0{\\fonttbl{\\f0 Segoe UI;}}\\f0\\fs20\n'
    for index,line in enumerate(paragraphs):
        heading=index==0 or (line and line[0].isdigit() and '. ' in line[:4])
        clause=line.startswith(('Na extensão permitida pela legislação aplicável, o autor','To the extent permitted by applicable law, the author','En la medida permitida por la legislación aplicable, el autor'))
        rtf+=('\\b ' if heading or clause else '')+escape(line)+('\\b0' if heading or clause else '')+'\\par\n'
    rtf+='}'
    (build/f'terms-{language}.rtf').write_text(rtf,encoding='ascii')
manifest=build/'uninstall-files.nsh'
files=sorted(p.relative_to(payload) for p in payload.rglob('*') if p.is_file())
dirs=sorted((p.relative_to(payload) for p in payload.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True)
def nsis_path(path):
    value=str(path)
    assert not any(c in value for c in ['$', '"', '\r', '\n']),value
    return value
manifest.write_text('; Generated exact owned files; never RMDir /r\n'+
    '\n'.join(f'Delete "$INSTDIR\\{nsis_path(p)}"' for p in files)+'\n'+
    '\n'.join(f'RMDir "$INSTDIR\\{nsis_path(p)}"' for p in dirs)+'\n',encoding='utf-8-sig')
arguments=[str(args.compiler),'/V2',f'/DPAYLOAD={payload}',f'/DOUTPUT={args.output.resolve()}',
           f'/DUNINSTALL_MANIFEST={manifest}',f'/DTERMS_HASH={digest.hexdigest()}']
if args.test_build:arguments.append('/DTEST_BUILD')
# Localized license files are resolved relative to the script.
script=(source/'installer/StrigoiAetherMap.nsi').read_text(encoding='utf-8')
for language in languages:
    name=f'terms-{language}.rtf'
    script=script.replace(f'"{name}"',f'"{build/name}"')
script=script.replace('"..\\app\\assets\\azphelumbra.ico"',f'"{source}/app/assets/azphelumbra.ico"')
script=script.replace('"install-npcap.ps1"',f'"{source / "installer" / "install-npcap.ps1"}"')
generated=build/('setup-test.nsi' if args.test_build else 'setup.nsi')
generated.write_text(script,encoding='utf-8-sig')
arguments.append(str(generated))
subprocess.run(arguments,check=True)
print('Installer built:',args.output,flush=True)
