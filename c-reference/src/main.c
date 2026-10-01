#define _POSIX_C_SOURCE 200809L
#include "reduction.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>

static uint64_t ns(void){struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return (uint64_t)t.tv_sec*1000000000ull+t.tv_nsec;}
static void fill(uint64_t *a,uint64_t *b,size_t n){uint64_t x=0x9e3779b97f4a7c15ULL;for(size_t i=0;i<n;i++){x^=x<<7;x^=x>>9;a[i]=x%1000;b[i]=(x>>11)%1000;}}

static Operation *make_subleq_tree(const uint64_t *A,const uint64_t *B,size_t n){
    Operation *sub=op_node(OP_SUBTRACT,2,op_leaf(B,n),op_leaf(A,n));
    Operation *cmp=op_node(OP_COMPARE_LE_ZERO,1,op_node(OP_SUBTRACT,2,op_leaf(B,n),op_leaf(A,n)));
    Operation *sel=op_node(OP_SELECT,2,sub,cmp);
    Operation *route=op_node(OP_ROUTE,1,sel);
    return op_node(OP_FIELD_REDUCE_SUM,1,route);
}

int main(int argc,char **argv){
    size_t n=argc>1?(size_t)strtoull(argv[1],0,10):4096;
    int reps=argc>2?atoi(argv[2]):50;
    uint64_t *A=malloc(n*sizeof(uint64_t)),*B=malloc(n*sizeof(uint64_t)); fill(A,B,n);
    Operation *root=make_subleq_tree(A,B,n);
    Metrics warm={0}; Array w=op_eval(root,&warm,1); uint64_t expected=w.len?w.data[0]:0; array_free(&w);
    uint64_t best=~0ull,total=0,last=0; Metrics m={0};
    for(int r=0;r<reps;r++){Metrics x={0};uint64_t t0=ns();Array out=op_eval(root,&x,1);uint64_t t1=ns();uint64_t dt=t1-t0;if(dt<best)best=dt;total+=dt;last=out.len?out.data[0]:0;array_free(&out);m=x;}
    printf("{\n");
    printf("  \"benchmark\": \"subleq-field-reduce\",\n");
    printf("  \"n\": %zu,\n",n);
    printf("  \"repetitions\": %d,\n",reps);
    printf("  \"correctness\": \"%s\",\n",last==expected?"PASS":"FAIL");
    printf("  \"result\": %llu,\n",(unsigned long long)last);
    printf("  \"best_ns\": %llu,\n",(unsigned long long)best);
    printf("  \"mean_ns\": %.2f,\n",(double)total/reps);
    printf("  \"elements_per_second_best\": %.2f,\n", best?((double)n*1e9/(double)best):0.0);
    printf("  \"nodes\": %zu,\n",m.nodes);
    printf("  \"leaves\": %zu,\n",m.leaves);
    printf("  \"tree_depth\": %zu,\n",m.max_depth);
    printf("  \"critical_path\": %zu,\n",m.critical_path);
    printf("  \"operation_nodes\": %zu,\n",m.operations);
    printf("  \"subleq_ops\": %zu,\n",m.subleq_ops);
    printf("  \"field_ops\": %zu,\n",m.field_ops);
    printf("  \"intermediate_arrays\": %zu\n",m.intermediate_arrays);
    printf("}\n");
    op_free(root);free(A);free(B);return last==expected?0:2;
}
