// ORDO adapter around the pinned MIT author kernel. See build.py for provenance.
#include <stdint.h>
#include <stdexcept>

static t_user *bridge_users=nullptr;
static int bridge_round=0;

extern "C" __declspec(dllexport) void cmm_close() {
    if (bridge_users) {
        for (int i=0;i<N;i++) bridge_users[i].bridge_cleanup();
        delete[] bridge_users;bridge_users=nullptr;
    }
    if (snap_shots) { delete[] snap_shots[0];delete[] snap_shots;snap_shots=nullptr; }
    for (auto &x:tables) x.second.deletTable();tables.clear();
}

extern "C" __declspec(dllexport) int cmm_init(int n,unsigned int seed,int memory,double coupling) {
    if (n<1||n>2000||memory<0||memory>1||coupling<0) return -1;
    cmm_close();N=n;rho0=coupling;memory_flag=memory;bridge_round=0;
    fill_n(pop,A,0);fill_n(pre_pop,A,0);fill_n(avg_pop,A,0);
    for (int i=0;i<A;i++) pop_temp[i].clear();
    snap_shots=new int*[1];snap_shots[0]=new int[A]();
    bridge_users=new t_user[N];initCutoffRegion();::srand48((long)seed);
    for(int i=0;i<N;i++) {
        bridge_users[i].srand48((long)::lrand48());
        bridge_users[i].init(vec2(L/2,L/2));
    }
    return 0;
}

extern "C" __declspec(dllexport) int cmm_step() {
    if(!bridge_users||bridge_round>=1000) return -1;
    update(++bridge_round);
    for(int i=0;i<N;i++) bridge_users[i].run_one_step(bridge_round);
    return bridge_round;
}

static vector<uint64_t> bridge_state() {
    vector<uint64_t> v;v.push_back(bridge_round);v.push_back(N);
    // Sparse arrays include pending flow: author pop is flushed at the next update.
    for(int mode=0;mode<3;mode++) {
        size_t start=v.size();v.push_back(0);uint64_t count=0;
        for(int i=0;i<A;i++) {
            int x=mode==0?pop[i]:mode==1?pre_pop[i]:pop_temp[i].combine(plus<int>());
            if(x) {v.push_back(i);v.push_back((uint64_t)(int64_t)x);count++;}
        }
        v[start]=count;
    }
    for(int i=0;i<N;i++) {
        t_user &u=bridge_users[i];v.push_back(u.bridge_position());v.push_back(u.bridge_visited());
        v.push_back(u.bridge_times());v.push_back(u.bridge_seed());
        for(int j=0;j<u.bridge_visited();j++) {int label,freq;u.bridge_entry(j,label,freq);v.push_back(label);v.push_back(freq);}
    }
    return v;
}

extern "C" __declspec(dllexport) int cmm_state_size() {return (int)bridge_state().size();}
extern "C" __declspec(dllexport) int cmm_copy_state(uint64_t *out,int capacity) {
    vector<uint64_t> state=bridge_state();if(capacity<(int)state.size())return -1;
    copy(state.begin(),state.end(),out);return (int)state.size();
}

#ifdef BRIDGE_EXE
int main(int argc,char **argv) {
    if(argc!=6)return 2;
    int n=atoi(argv[1]),seed=atoi(argv[2]),memory=atoi(argv[3]),steps=atoi(argv[5]);
    if(cmm_init(n,seed,memory,atof(argv[4]))<0||steps<1||steps>1000)return 3;
    for(int t=1;t<=steps;t++) {
        cmm_step();vector<uint64_t> s=bridge_state();
        cout<<"[";
        for(size_t i=0;i<s.size();i++){if(i)cout<<",";cout<<s[i];}
        cout<<"]\n";
    }
    cmm_close();return 0;
}
#endif
