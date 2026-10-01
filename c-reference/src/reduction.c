#include "reduction.h"
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/evp.h>

Array array_new(size_t n) {
    Array a = {0};
    a.len = n;
    a.data = n ? (uint64_t*)calloc(n, sizeof(uint64_t)) : NULL;
    return a;
}
Array array_clone(const Array *a) {
    Array out = array_new(a->len);
    if (a->len) memcpy(out.data, a->data, a->len * sizeof(uint64_t));
    return out;
}
void array_free(Array *a) { free(a->data); a->data=NULL; a->len=0; }

uint64_t field_add(uint64_t a, uint64_t b) {
    __uint128_t s = (__uint128_t)a + b;
    return (uint64_t)(s % GOLDILOCKS_P);
}
uint64_t field_sub(uint64_t a, uint64_t b) {
    return a >= b ? a-b : (uint64_t)((__uint128_t)a + GOLDILOCKS_P - b);
}
uint64_t field_mul(uint64_t a, uint64_t b) {
    return (uint64_t)(((__uint128_t)a * b) % GOLDILOCKS_P);
}

Operation *op_leaf(const uint64_t *data, size_t n) {
    Operation *o = (Operation*)calloc(1,sizeof(Operation));
    o->type = OP_LEAF;
    o->leaf = array_new(n);
    if (n) memcpy(o->leaf.data,data,n*sizeof(uint64_t));
    return o;
}
Operation *op_node(OpType type, size_t child_count, ...) {
    Operation *o = (Operation*)calloc(1,sizeof(Operation));
    o->type = type; o->child_count = child_count;
    o->children = child_count ? (Operation**)calloc(child_count,sizeof(Operation*)) : NULL;
    va_list ap; va_start(ap, child_count);
    for(size_t i=0;i<child_count;i++) o->children[i] = va_arg(ap, Operation*);
    va_end(ap);
    return o;
}
void op_set_aux(Operation *op,size_t aux){op->aux=aux;}
void op_free(Operation *op){
    if(!op) return;
    for(size_t i=0;i<op->child_count;i++) op_free(op->children[i]);
    free(op->children); array_free(&op->leaf); free(op);
}

static Array eval_child(const Operation *op,size_t i,Metrics *m,size_t depth){return op_eval(op->children[i],m,depth+1);} 
static size_t minz(size_t a,size_t b){return a<b?a:b;}

Array op_eval(const Operation *op, Metrics *m, size_t depth) {
    m->nodes++; if(depth>m->max_depth)m->max_depth=depth; if(depth>m->critical_path)m->critical_path=depth;
    if(op->type==OP_LEAF){m->leaves++; return array_clone(&op->leaf);} 
    m->operations++;
    Array a={0},b={0},out={0};
    switch(op->type){
        case OP_MAP_IDENTITY:
            a=eval_child(op,0,m,depth); return a;
        case OP_SUBTRACT:
            a=eval_child(op,0,m,depth); b=eval_child(op,1,m,depth); out=array_new(minz(a.len,b.len));
            for(size_t i=0;i<out.len;i++) out.data[i]=(uint64_t)((int64_t)a.data[i]-(int64_t)b.data[i]);
            m->subleq_ops+=out.len; m->intermediate_arrays++; array_free(&a);array_free(&b); return out;
        case OP_COMPARE_LE_ZERO:
            a=eval_child(op,0,m,depth); out=array_new(a.len);
            for(size_t i=0;i<a.len;i++) out.data[i]=((int64_t)a.data[i]<=0)?1:0;
            m->subleq_ops+=a.len; m->intermediate_arrays++; array_free(&a); return out;
        case OP_SELECT:
            a=eval_child(op,0,m,depth); b=eval_child(op,1,m,depth); out=array_new(minz(a.len,b.len));
            for(size_t i=0;i<out.len;i++) out.data[i]=b.data[i]?a.data[i]:0;
            m->subleq_ops+=out.len; m->intermediate_arrays++; array_free(&a);array_free(&b); return out;
        case OP_ROUTE:
            a=eval_child(op,0,m,depth); out=array_new(a.len);
            {size_t j=0; for(size_t i=0;i<a.len;i++) if(a.data[i]!=0) out.data[j++]=a.data[i]; out.len=j;}
            m->subleq_ops+=a.len; m->intermediate_arrays++; array_free(&a); return out;
        case OP_REDUCE_SUM: case OP_FOLD_SUM: case OP_TREE_REDUCE_SUM:
            a=eval_child(op,0,m,depth); out=array_new(1); for(size_t i=0;i<a.len;i++) out.data[0]+=a.data[i]; array_free(&a); return out;
        case OP_SCAN_SUM:
            a=eval_child(op,0,m,depth); out=array_new(a.len); {uint64_t s=0;for(size_t i=0;i<a.len;i++){s+=a.data[i];out.data[i]=s;}} array_free(&a); return out;
        case OP_SEGMENTED_REDUCE_SUM:
            a=eval_child(op,0,m,depth); {size_t seg=op->aux?op->aux:4; size_t n=(a.len+seg-1)/seg; out=array_new(n); for(size_t i=0;i<a.len;i++)out.data[i/seg]+=a.data[i];} array_free(&a); return out;
        case OP_FIELD_ADD: case OP_FIELD_SUB: case OP_FIELD_MUL:
            a=eval_child(op,0,m,depth); b=eval_child(op,1,m,depth); out=array_new(minz(a.len,b.len));
            for(size_t i=0;i<out.len;i++){ if(op->type==OP_FIELD_ADD)out.data[i]=field_add(a.data[i],b.data[i]); else if(op->type==OP_FIELD_SUB)out.data[i]=field_sub(a.data[i],b.data[i]); else out.data[i]=field_mul(a.data[i],b.data[i]); }
            m->field_ops+=out.len; m->intermediate_arrays++; array_free(&a);array_free(&b); return out;
        case OP_FIELD_REDUCE_SUM:
            a=eval_child(op,0,m,depth); out=array_new(1); {uint64_t s=0;for(size_t i=0;i<a.len;i++){s=field_add(s,a.data[i]);m->field_ops++;}out.data[0]=s;} array_free(&a); return out;
        case OP_INNER: case OP_CONTRACT:
            a=eval_child(op,0,m,depth); b=eval_child(op,1,m,depth); out=array_new(1); {uint64_t s=0;size_t n=minz(a.len,b.len);for(size_t i=0;i<n;i++)s+=a.data[i]*b.data[i];out.data[0]=s;} array_free(&a);array_free(&b); return out;
        case OP_OUTER:
            a=eval_child(op,0,m,depth); b=eval_child(op,1,m,depth); out=array_new(a.len*b.len); for(size_t i=0;i<a.len;i++)for(size_t j=0;j<b.len;j++)out.data[i*b.len+j]=a.data[i]*b.data[j]; array_free(&a);array_free(&b); return out;
        case OP_SEAL_SHA256:
            a=eval_child(op,0,m,depth);
            {
                unsigned char digest[32]; unsigned int dlen=0;
                EVP_MD_CTX *ctx=EVP_MD_CTX_new();
                out=array_new(4);
                if(ctx && EVP_DigestInit_ex(ctx,EVP_sha256(),NULL)==1 &&
                   EVP_DigestUpdate(ctx,a.data,a.len*sizeof(uint64_t))==1 &&
                   EVP_DigestFinal_ex(ctx,digest,&dlen)==1 && dlen==32){
                    memcpy(out.data,digest,32);
                }
                if(ctx) EVP_MD_CTX_free(ctx);
            }
            array_free(&a); return out;
        default: return out;
    }
}

const char *op_name(OpType t){
    static const char *names[]={"leaf","reduce","scan","fold","map","subtract","compare","select","route","contract","inner","outer","tree-reduce","segmented-reduce","field-add","field-sub","field-mul","field-reduce","seal"};
    return names[(int)t];
}
