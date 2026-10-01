#ifndef REDUCTION_H
#define REDUCTION_H
#include <stddef.h>
#include <stdint.h>

#define GOLDILOCKS_P UINT64_C(18446744069414584321)

typedef struct {
    uint64_t *data;
    size_t len;
} Array;

typedef enum {
    OP_LEAF,
    OP_REDUCE_SUM,
    OP_SCAN_SUM,
    OP_FOLD_SUM,
    OP_MAP_IDENTITY,
    OP_SUBTRACT,
    OP_COMPARE_LE_ZERO,
    OP_SELECT,
    OP_ROUTE,
    OP_CONTRACT,
    OP_INNER,
    OP_OUTER,
    OP_TREE_REDUCE_SUM,
    OP_SEGMENTED_REDUCE_SUM,
    OP_FIELD_ADD,
    OP_FIELD_SUB,
    OP_FIELD_MUL,
    OP_FIELD_REDUCE_SUM,
    OP_SEAL_SHA256
} OpType;

typedef struct Operation Operation;
struct Operation {
    OpType type;
    Operation **children;
    size_t child_count;
    Array leaf;
    size_t aux;
};

typedef struct {
    size_t nodes;
    size_t leaves;
    size_t max_depth;
    size_t critical_path;
    size_t operations;
    size_t subleq_ops;
    size_t field_ops;
    size_t intermediate_arrays;
} Metrics;

Array array_new(size_t n);
Array array_clone(const Array *a);
void array_free(Array *a);
Operation *op_leaf(const uint64_t *data, size_t n);
Operation *op_node(OpType type, size_t child_count, ...);
void op_set_aux(Operation *op, size_t aux);
void op_free(Operation *op);
Array op_eval(const Operation *op, Metrics *m, size_t depth);
uint64_t field_add(uint64_t a, uint64_t b);
uint64_t field_sub(uint64_t a, uint64_t b);
uint64_t field_mul(uint64_t a, uint64_t b);
const char *op_name(OpType t);

#endif
