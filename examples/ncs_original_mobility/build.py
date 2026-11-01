"""Generate the full-scale Linux port from pinned upstream code, with visible patch."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import re

from examples.ncs_mobility.build import FILES,COMMIT


def paper_driver(text):
    """Declared SI parameter overrides plus a non-moving output flush after20k."""
    text=text.replace('static int target_periods=20001;','static int target_periods=20000;\nstatic bool final_flushed=false;')
    text=text.replace('0x434d4d46554c4c31ULL','0x434d4d46554c4c32ULL')
    text=text.replace('write_value(s,memory_flag);write_value(s,alpha);write_value(s,rho0);','write_value(s,memory_flag);write_value(s,alpha);write_value(s,rho0);write_value(s,final_flushed);')
    text=text.replace('read_value(s,memory);read_value(s,a);read_value(s,r);','read_value(s,memory);read_value(s,a);read_value(s,r);read_value(s,final_flushed);')
    text=text.replace('std::stoi(match[2])>=t','std::stoi(match[2])>=t+(final_flushed?1:0)')
    text=text.replace('memory_flag=1;rho0=1e-12;alpha=-2.55;','memory_flag=1;rho0=0.0;alpha=-2.55;delta=0.1;')
    text=text.replace('target_periods!=20001','target_periods!=20000')
    text=text.replace('progress(t,t==target_periods?"complete":"running");','progress(t,t==target_periods?"flush_pending":"running");')
    text=text.replace('        if(smoke){std::ofstream a(','''        if(!final_flushed){
            update(target_periods+1);save("",target_periods+1);final_flushed=true;checkpoint_write(target_periods);
        }
        progress(target_periods,"complete");
        if(smoke){std::ofstream a(''')
    text=text.replace('"configuration N="','"profile=paper_SI_delta0.1_rho0_zero configuration N="')
    return text


def generate(output,source=Path('.buildtmp/ncs-mobility-native'),profile='code'):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);manifest={}
    for name,sha in FILES.items():
        raw=(source/name).read_bytes()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=sha:raise ValueError('Upstream source changed: '+name)
        (output/name).write_bytes(raw);manifest[name]=dict(git_blob_sha=sha,sha256=hashlib.sha256(raw).hexdigest())
    original=(source/'main.cpp').read_bytes().decode('gb18030',errors='replace').replace('\r\n','\n')
    text=original[:original.index('int run(const char* dirname)')]
    text=text.replace('#include <ppl.h>','#include "compat.hpp"').replace('#include <windows.h>','// Linux: unused Windows header omitted.')
    text=text.replace('#include <hash_map>','// Unused deprecated hash_map omitted.').replace('#include <direct.h>','// Linux mkdir is provided by sys/stat.h.')
    text=text.replace('#include "drand48.h"','#define srand48 cmm_srand48\n#define drand48 cmm_drand48\n#define lrand48 cmm_lrand48\n#include "drand48.h"')
    text=re.sub(r'\bgamma\b','cmm_gamma',text)
    needle='unsigned long int seed = seed_pre >> 16;'
    if text.count(needle)!=1:raise ValueError('Windows RNG word-width target changed.')
    text=text.replace(needle,'uint32_t seed = (uint32_t)(seed_pre >> 16); // Windows unsigned-long narrowing retained.')
    needle='while((freq_temp>this->frequency[index_temp-1])&&index_temp>0)'
    if text.count(needle)!=1:raise ValueError('Sorted-array patch target changed.')
    text=text.replace(needle,'while(index_temp>0&&(freq_temp>this->frequency[index_temp-1]))')
    # Add serialization methods without changing existing mobility methods.
    begin=text.index('class SortedArray');end=text.index('inline myvec vec2',begin)
    sorted_source=text[begin:end]
    marker='\t\tvoid PrintTable()'
    addition='''        void checkpoint_write(std::ostream &s) const {
            write_value(s,cur);for(int i=0;i<cur;i++){write_value(s,label[i]);write_value(s,frequency[i]);}
        }
        void checkpoint_read(std::istream &s) {
            read_value(s,cur);if(cur<1||cur>capacity)throw std::runtime_error("Invalid sorted history size.");
            for(int i=0;i<cur;i++){read_value(s,label[i]);read_value(s,frequency[i]);if(label[i]<0||label[i]>=A||frequency[i]<1)throw std::runtime_error("Invalid visit history.");}
        }
        int checkpoint_count() const {return cur;}
'''
    if sorted_source.count(marker)!=1:raise ValueError('Sorted-array serialization target changed.')
    text=text[:begin]+sorted_source.replace(marker,addition+marker)+text[end:]
    marker='public:\n\tt_user()'
    addition='''public:
    void checkpoint_write(std::ostream &s) {
        write_value(s,pos);write_value(s,visited_num);int64_t st=seed_pre,tm=times;write_value(s,st);write_value(s,tm);loc_freq->checkpoint_write(s);
    }
    void checkpoint_read(std::istream &s) {
        read_value(s,pos);read_value(s,visited_num);int64_t st,tm;read_value(s,st);read_value(s,tm);seed_pre=st;times=tm;
        if(pos<0||pos>=A||visited_num<1||visited_num>backet_num||tm<1)throw std::runtime_error("Invalid agent checkpoint.");
        loc_freq=new SortedArray(backet_num);loc_freq->checkpoint_read(s);
        if(loc_freq->checkpoint_count()!=visited_num)throw std::runtime_error("History length mismatch.");
        unvisited_flag.set();int label,freq;
        if(memory_flag)for(int j=0;j<visited_num;j++){loc_freq->select(j,label,freq);unvisited_flag[label]=false;}
    }
    void checkpoint_cleanup(){delete loc_freq;loc_freq=nullptr;}
    int checkpoint_visited()const{return visited_num;}
    int checkpoint_position()const{return pos;}
    int checkpoint_frequency_size()const{return loc_freq->checkpoint_count();}
    void audit_write(std::ostream &s) {
        s<<pos<<","<<visited_num<<","<<times<<","<<seed_pre;
        int label,freq;for(int j=0;j<visited_num;j++){loc_freq->select(j,label,freq);s<<","<<label<<","<<freq;}s<<"\\n";
    }
\tt_user()'''
    if text.count(marker)!=1:raise ValueError('Agent serialization target changed.')
    text=text.replace(marker,addition)
    shutil.copy2(Path(__file__).with_name('compat.hpp'),output/'compat.hpp')
    driver=Path(__file__).with_name('driver.cpp').read_text(encoding='utf-8')
    if profile=='paper':driver=paper_driver(driver)
    elif profile!='code':raise ValueError('Use code or paper profile.')
    (output/'driver.cpp').write_text(driver,encoding='utf-8')
    text+='\n#include "driver.cpp"\n';(output/'full_native.cpp').write_text(text,encoding='utf-8')
    (output/'port.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='author/main.cpp',tofile='full_native.cpp')),encoding='utf-8')
    shutil.copy2(Path(__file__),output/'generator.py')
    manifest=dict(profile=profile,upstream_commit=COMMIT,upstream_files=manifest,generated_sha256=hashlib.sha256((output/'full_native.cpp').read_bytes()).hexdigest(),
        effective_parameters=dict(N=30000,L=300,memory=True,delta=.1 if profile=='paper' else 1,rho0=0 if profile=='paper' else 1e-12,code_alpha=-2.55,gamma=.21,movement_periods=20000 if profile=='paper' else 20001),
        adaptation='Full original mobility methods through update retained; original entrypoint replaced by full-scale checkpointed driver.',
        compatibility=['PPL combinable/parallel_for mapped to OpenMP thread-local accumulators','Omit platform-specific unused includes','Fixed-width checkpoint records','Namespace author RNG and gamma identifiers to avoid POSIX symbols','Compile signed integer RNG overflow with -fwrapv','Preserve Windows32-bit unsigned-long RNG narrowing on LinuxLP64'],
        safety=['Bounds condition reordered to avoid freq[-1] read','new[]/delete[] and explicit per-agent SortedArray cleanup','Checkpoint size/label validation'],
        retained_quirks=['Integer-truncated cutoff distance','Repeated wrapped cutoff entries','Integer sum accumulator in alias construction','Original pa_return >= cut boundary','Original output center selection and append formats'],
        source_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*') if p.is_file()})
    manifest['build_artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
    (output/'build_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--profile',choices=('code','paper'),default='code')
    a=p.parse_args();print(json.dumps(generate(a.output,profile=a.profile),indent=2))
