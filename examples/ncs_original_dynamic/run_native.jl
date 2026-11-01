# Full-length author-kernel Monte Carlo; network construction is reconstructed
# from the published Figure 3 caption, NOT supplied by the archived workflow.
using Random, Printf, SHA, Serialization

source_path=joinpath(@__DIR__,"upstream","Simulation.jl")
source=read(source_path,String)
const EXPECTED_SOURCE_SHA256="4c8e55fd29b927d795403acf7d0cdcf3100c60381eebf99906ebc2544770b415"
source_sha=bytes2hex(sha256(source))
if EXPECTED_SOURCE_SHA256!="TO_BE_PINNED" && source_sha!=EXPECTED_SOURCE_SHA256
    error("Pinned Simulation.jl changed")
end

function core_periphery(nc,np)
    iseven(nc) && nc>=4 || error("The original core has an even number of ring nodes")
    n=nc+np;w=zeros(Float64,n,n,2)
    for layer=1:2
        for i=1:nc
            j=mod1(i+1,nc);w[i,j,layer]=w[j,i,layer]=1.0
        end
        hubs=layer==1 ? (1:div(nc,2)) : (div(nc,2)+1:nc)
        for i=hubs,j=nc+1:n
            w[i,j,layer]=w[j,i,layer]=1.0
        end
    end
    return w
end

const OUT=Ref("")
const STARTED=Ref(time())
function emit_progress(completed,maxIter,state,network_state,reward,fecundity,frequency)
    maxIter < 100_000_000 && return # Numerical instrumentation test, not a scientific trajectory.
    elapsed=time()-STARTED[]
    open(OUT[]*".progress.jsonl","a") do io
        @printf(io,"{\"completed_iterations\":%d,\"target_iterations\":%d,\"elapsed_s\":%.6f,\"cooperators\":%d,\"network_state\":%d}\n",completed,maxIter,elapsed,count(==(1),state),network_state)
    end
    # An auditable full numerical/RNG snapshot. Current coordinator resumes
    # completed repeats and restarts an interrupted repeat from its fixed seed.
    # It does not claim to resume this original function from a mid-run snapshot.
    serialize(OUT[]*".checkpoint.jls",(completed=completed,target=maxIter,state=copy(state),
        network_state=network_state,reward=copy(reward),fecundity=copy(fecundity),
        frequency=copy(frequency),rng=copy(Random.default_rng()),elapsed_s=elapsed))
end

module OriginalKernel
include(joinpath(@__DIR__,"upstream","Simulation.jl"))
end

needle="        for iter = 1:maxIter"
count(needle,source)==1 || error("Author loop boundary changed")
instrumented=replace(source,needle=>needle*"\n            if iter % 1_000_000 == 1\n                Main.emit_progress(iter-1,maxIter,state,network_state,reward,fecundity,frequency)\n            end";count=1)
module InstrumentedKernel end
Base.include_string(InstrumentedKernel,instrumented,"source-identical-kernel-with-observation-hook.jl")

function main(args)
    length(args)==9 || error("nc np u tau delta network seed maxIter output_prefix")
    nc=parse(Int,args[1]);np=parse(Int,args[2]);u=parse(Float64,args[3]);tau=parse(Float64,args[4]);delta=parse(Float64,args[5])
    mode=args[6];seed=parse(Int,args[7]);steps=parse(Int,args[8]);OUT[]=args[9]
    mode in ("dynamic","static") || error("Invalid comparison group")
    w=core_periphery(nc,np);n=nc+np
    q=mode=="dynamic" ? [1-1/(tau*n) 1/(tau*n);1/(tau*n) 1-1/(tau*n)] : [1.0 0.0;0.0 1.0]
    A=[1.0 -1.0;2.0 0.0] # Published Extended Data Fig.2 donation game: b=2,c=1.
    # Compatibility/mechanics test only, not a reduced scientific run.
    Random.seed!(seed);a=OriginalKernel.game_on_dynamic_network(w,u,q,delta,1,1000,A)
    Random.seed!(seed);b=InstrumentedKernel.game_on_dynamic_network(w,u,q,delta,1,1000,A)
    a==b || error("Observation instrumentation changed native output")
    Random.seed!(seed);STARTED[]=time()
    frequency=InstrumentedKernel.game_on_dynamic_network(w,u,q,delta,1,steps,A)
    elapsed=time()-STARTED[]
    temp=OUT[]*".result.tmp"
    open(temp,"w") do io
        @printf(io,"{\"status\":\"complete\",\"iterations\":%d,\"burnin_iterations\":%d,\"nc\":%d,\"np\":%d,\"u\":%.17g,\"tau\":%.17g,\"delta\":%.17g,\"network\":\"%s\",\"seed\":%d,\"cooperation_frequency\":%.17g,\"defection_frequency\":%.17g,\"elapsed_s\":%.6f,\"source_sha256\":\"%s\",\"instrumentation_exact_test\":true,\"construction\":\"published_caption_reconstruction\",\"julia\":\"%s\"}\n",steps,Int(.05*steps),nc,np,u,tau,delta,mode,seed,frequency[1],frequency[2],elapsed,source_sha,string(VERSION))
    end
    mv(temp,OUT[]*".result.json";force=false)
end
main(ARGS)
