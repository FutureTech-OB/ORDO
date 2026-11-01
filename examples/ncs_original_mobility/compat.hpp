// Linux portability shim for Microsoft's PPL; no mobility rule is implemented here.
#include <omp.h>
#include <vector>
#include <algorithm>
#include <functional>
#include <stdint.h>
#include <fstream>
#include <stdexcept>
#include <chrono>
#include <filesystem>
#include <regex>
#include <sys/stat.h>
#include <unistd.h>
namespace Concurrency {
template<class T> class combinable {
    std::vector<T> values;
public:
    combinable():values(omp_get_max_threads(),T()){}
    T& local(){return values[omp_get_thread_num()];}
    template<class F> T combine(F op)const {T result=T();for(const auto &v:values)result=op(result,v);return result;}
    void clear(){std::fill(values.begin(),values.end(),T());}
};
template<class F> void parallel_for(int start,int end,F work){
    #pragma omp parallel for schedule(static)
    for(int i=start;i<end;i++)work(i);
}
}
template<class T> void write_value(std::ostream& s,const T&v){s.write((const char*)&v,sizeof(v));if(!s)throw std::runtime_error("Checkpoint write failed.");}
template<class T> void read_value(std::istream& s,T&v){s.read((char*)&v,sizeof(v));if(!s)throw std::runtime_error("Checkpoint truncated.");}
