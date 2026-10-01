#include "reduction.h"
#include <assert.h>
#include <stdio.h>
int main(void){
  uint64_t a[]={1,2,3,4}, b[]={4,3,2,1}; Metrics m={0};
  Operation *s=op_node(OP_REDUCE_SUM,1,op_leaf(a,4)); Array r=op_eval(s,&m,1); assert(r.len==1 && r.data[0]==10); array_free(&r); op_free(s);
  assert(field_add(GOLDILOCKS_P-1,2)==1);
  assert(field_sub(1,2)==GOLDILOCKS_P-1);
  assert(field_mul(GOLDILOCKS_P-1,GOLDILOCKS_P-1)==1);
  Operation *f=op_node(OP_FIELD_ADD,2,op_leaf(a,4),op_leaf(b,4)); m=(Metrics){0}; r=op_eval(f,&m,1); for(size_t i=0;i<4;i++)assert(r.data[i]==5); array_free(&r); op_free(f);
  puts("ALL TESTS PASS"); return 0;
}
