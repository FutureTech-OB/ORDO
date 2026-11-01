// Checkpointable full-scale driver; original movement/update/save functions remain.
static int target_periods=20001;
static int checkpoint_every=500;
static unsigned int run_seed=0;
static int run_index=0;
static int start_period=0;
static t_user* users=nullptr;
static auto wall_start=std::chrono::steady_clock::now();

static void progress(int t,const char* status){
    std::ofstream f("progress.json.tmp");
    uint64_t visits=0;for(int i=0;i<N;i++)visits+=users[i].checkpoint_visited();
    double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-wall_start).count();
    f<<"{\"status\":\""<<status<<"\",\"replicate\":"<<run_index<<",\"seed\":"<<run_seed
     <<",\"population\":"<<N<<",\"period\":"<<t<<",\"target_periods\":"<<target_periods
     <<",\"completed_agent_updates\":"<<(uint64_t)t*N<<",\"threads\":"<<omp_get_max_threads()
     <<",\"pid\":"<<getpid()<<",\"attempt_elapsed_s\":"<<elapsed
     <<",\"attempt_start_period\":"<<start_period<<",\"mean_visited_sites\":"<<(double)visits/N<<"}\n";
    f.close();std::filesystem::rename("progress.json.tmp","progress.json");
}

static void checkpoint_write(int t){
    std::ofstream s("checkpoint.bin.tmp",std::ios::binary|std::ios::trunc);
    const uint64_t magic=0x434d4d46554c4c31ULL;write_value(s,magic);
    write_value(s,N);write_value(s,t);write_value(s,target_periods);write_value(s,run_seed);write_value(s,run_index);
    write_value(s,memory_flag);write_value(s,alpha);write_value(s,rho0);
    for(int mode=0;mode<5;mode++)for(int i=0;i<A;i++){
        int value=mode==0?pop[i]:mode==1?pre_pop[i]:mode==2?avg_pop[i]:mode==3?snap_shots[0][i]:pop_temp[i].combine(plus<int>());
        write_value(s,value);
    }
    for(int i=0;i<N;i++)users[i].checkpoint_write(s);
    s.flush();s.close();if(!s)throw std::runtime_error("Checkpoint close failed.");
    std::filesystem::rename("checkpoint.bin.tmp","checkpoint.bin");
}

static int checkpoint_read(){
    std::ifstream s("checkpoint.bin",std::ios::binary);uint64_t magic;read_value(s,magic);
    if(magic!=0x434d4d46554c4c31ULL)throw std::runtime_error("Checkpoint version differs.");
    int n,t,periods,index,memory;unsigned int seed;double a,r;
    read_value(s,n);read_value(s,t);read_value(s,periods);read_value(s,seed);read_value(s,index);
    read_value(s,memory);read_value(s,a);read_value(s,r);
    if(n!=N||periods!=target_periods||seed!=run_seed||index!=run_index||memory!=memory_flag||a!=alpha||r!=rho0||t<0||t>periods)
        throw std::runtime_error("Checkpoint configuration differs.");
    int total=0,flow_total=0;
    for(int mode=0;mode<5;mode++)for(int i=0;i<A;i++){
        int value;read_value(s,value);
        if(mode==0){pop[i]=value;total+=value;}
        else if(mode==1)pre_pop[i]=value;
        else if(mode==2)avg_pop[i]=value;
        else if(mode==3)snap_shots[0][i]=value;
        else {pop_temp[i].local()=value;flow_total+=value;}
    }
    if(total!=N||flow_total!=0)throw std::runtime_error("Checkpoint population mass differs.");
    for(int i=0;i<N;i++)users[i].checkpoint_read(s);
    if(s.peek()!=std::char_traits<char>::eof())throw std::runtime_error("Checkpoint has trailing bytes.");
    // Remove only uncommitted original-format output files in this run's cwd.
    const std::regex filename("(p|z|zp|r|ap|az|azp|ar)([0-9]+)\\.dat");
    for(auto& item:std::filesystem::directory_iterator(".")){
        std::smatch match;std::string name=item.path().filename().string();
        if(item.is_regular_file()&&std::regex_match(name,match,filename)&&std::stoi(match[2])>=t)std::filesystem::remove(item.path());
    }
    return t;
}

int main(int argc,char**argv){
    try{
        if(argc<3)throw std::runtime_error("usage: cmm_full SEED REPLICATE [--resume] [--smoke=N,PERIODS] [--checkpoint=N]");
        N=30000;run_seed=std::stoul(argv[1]);run_index=std::stoi(argv[2]);memory_flag=1;rho0=1e-12;alpha=-2.55;
        bool resume=false,smoke=false;
        for(int k=3;k<argc;k++){
            std::string option=argv[k];
            if(option=="--resume")resume=true;
            else if(option.rfind("--smoke=",0)==0){smoke=true;auto comma=option.find(',');N=std::stoi(option.substr(8,comma-8));target_periods=std::stoi(option.substr(comma+1));}
            else if(option.rfind("--checkpoint=",0)==0)checkpoint_every=std::stoi(option.substr(13));
            else throw std::runtime_error("Unknown option.");
        }
        if(N<1||N>30000||target_periods<1||target_periods>20001||checkpoint_every<1)throw std::runtime_error("Invalid declared bounds.");
        if(!smoke&&(N!=30000||target_periods!=20001))throw std::runtime_error("Full configuration required.");
        std::cout<<"configuration N="<<N<<" T="<<target_periods<<" seed="<<run_seed<<" replicate="<<run_index<<" smoke_only="<<smoke<<std::endl;
        snap_shots=new int*[1];snap_shots[0]=new int[A]();users=new t_user[N];initCutoffRegion();
        if(resume)start_period=checkpoint_read();
        else {
            fill_n(pop,A,0);fill_n(pre_pop,A,0);fill_n(avg_pop,A,0);::srand48(run_seed);
            for(int i=0;i<N;i++){users[i].srand48((int32_t)::lrand48());users[i].init(vec2(L/2,L/2));}
            checkpoint_write(0);
        }
        wall_start=std::chrono::steady_clock::now();progress(start_period,"running");
        for(int t=start_period+1;t<=target_periods;t++){
            auto begin=std::chrono::steady_clock::now();update(t);
            parallel_for(0,N,[&](int i){users[i].run_one_step(t);});
            if((t%500)>=(500-window_output))for(int i=0;i<A;i++)avg_pop[i]+=pop[i];
            if(t%500==1&&t>1)save("",t);
            // Source history capacity was5000. Stop rather than silently claim
            // results after a capacity overflow (source insert prints an error).
            for(int i=0;i<N;i++)if(users[i].checkpoint_visited()!=users[i].checkpoint_frequency_size())throw std::runtime_error("Original visit-array capacity exceeded.");
            if(t%checkpoint_every==0||t==target_periods)checkpoint_write(t);
            progress(t,t==target_periods?"complete":"running");
            std::cout<<t<<"\t"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<std::endl;
        }
        if(smoke){std::ofstream a("audit_agents.csv");for(int i=0;i<N;i++)users[i].audit_write(a);}
        for(int i=0;i<N;i++)users[i].checkpoint_cleanup();delete[]users;delete[]snap_shots[0];delete[]snap_shots;
        for(auto& x:tables)x.second.deletTable();tables.clear();return 0;
    }catch(const std::exception&error){std::cerr<<"ERROR "<<error.what()<<std::endl;return 1;}
}
