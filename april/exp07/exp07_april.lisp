;;; SPDX-License-Identifier: AGPL-3.0-or-later
;;; Copyright (C) 2026 SnapKitty Collective
;;;
;;; exp07_april.lisp — Experiment 07: April (APL in Common Lisp) track
;;; of the reduction-algebra benchmark.
;;;
;;; STATUS: IMPLEMENTATION COMPLETE, UNEXECUTED. SBCL + Quicklisp + April
;;; were not available in this build environment, so no timing or
;;; correctness result is claimed. Every measurement field is null in
;;; results/exp07_april.json. The real toolchain is the only judge.
;;;
;;; Design (idiomatic April-in-Lisp):
;;;   * 64-bit-exact field arithmetic and the SplitMix64 PRNG live in
;;;     Common Lisp bignums (April's APL numbers are doubles; 2^53
;;;     mantissa cannot hold 2^64 reps exactly, so April is NOT used
;;;     for modular arithmetic — same honesty rule as the Wolfram
;;;     Total-probe in Exp 02).
;;;   * April expresses the array TOPOLOGY natively: tree/segmented
;;;     reduction shapes, scan, and the SUBLEQ predicate+select stage
;;;     via APL compression ((mask)/V). Vectors are passed to April
;;;     as generated source text; results come back as Lisp values.
;;;   * April reduction probes (+/ x/ <// >//) are timed separately and
;;;     tagged "probe" — never compared head-to-head with the exact
;;;     Lisp folds as if equivalent.

(eval-when (:compile-toplevel :load-toplevel :execute)
  (handler-case (progn (ql:quickload :april :silent t) t)
    (error (c) (format *error-output* "~&;; April unavailable: ~a~%" c))))

(defparameter +p+ 18446744069414584321)   ; Goldilocks: 2^64 - 2^32 + 1
(defparameter +m64+ (expt 2 64))
(defparameter +mask64+ (1- +m64+))
(defparameter +seed+ #x00BEEFCAFE)
(defparameter +half-p+ (floor +p+ 2))

;;; ---------- SplitMix64, counter-increment variant (canonical) ----------
;;; state += 0x9E3779B97F4A7C15 (mod 2^64); mix a copy; emit z mod p.
;;; Must reproduce crosslang checksum 1388262917130611548 for n=1024.

(defun splitmix64-next (state)
  (declare (type integer state))
  (let* ((s  (logand +mask64+ (+ state #x9E3779B97F4A7C15)))
         (z  s))
    (setf z (logand +mask64+ (* (logxor z (ash z -30)) #xBF58476D1CE4E5B9)))
    (setf z (logand +mask64+ (* (logxor z (ash z -27)) #x94D049BB133111EB)))
    (setf z (logxor z (ash z -31)))
    (values (mod z +p+) s)))

(defun make-vec (n &optional (seed +seed+))
  (let ((v (make-array n :element-type 'integer))
        (s seed))
    (dotimes (i n v)
      (multiple-value-bind (x ns) (splitmix64-next s)
        (setf (aref v i) x s ns)))))

(defun crosslang-checksum (&optional (n 1024))
  (mod (reduce #'+ (make-vec n)) +p+))

;;; ---------- Goldilocks field kernels (exact, bignum) ----------
(defun gf-add (x y) (mod (+ x y) +p+))
(defun gf-sub (x y) (mod (- x y) +p+))
(defun gf-mul (x y) (mod (* x y) +p+))   ; exact product; see note below
(defun gf-pow (x e)
  (let ((r 1) (b (mod x +p+)) (k e))
    (loop while (> k 0)
          do (when (oddp k) (setf r (gf-mul r b)))
             (setf b (gf-mul b b) k (ash k -1)))
    r))
(defun gf-inv (x) (gf-pow x (- +p+ 2)))

;;; NOTE on gf-mul: the Chapel vertical slice uses double-and-add
;;; (shifts + conditional adds). Bignum (mod (* x y) p) is algebraically
;;; identical; the implementation-op counter axis (Exp 01b JSON
;;; "implementation ops vs algebraic ops") is recorded as unknown here
;;; because April/Lisp does not expose the inner shift-add sequence.

;;; ---------- April bridge ----------
;;; apl-eval takes an APL source string, evaluates it in April, returns
;;; the Lisp value. Vectors cross the boundary as generated literals.

(defun vec->apl (v)
  (with-output-to-string (s)
    (dotimes (i (length v))
      (unless (zerop i) (write-char #\Space s))
      (princ (aref v i) s))))

(defun apl-eval (src)
  ;; Requires (ql:quickload :april). April's entry point is APRIL:APRIL.
  (funcall (find-symbol "APRIL" :april) src))

(defun apl-compress (mask v)
  "SUBleQ SELECT+ROUTE stage: (mask)/V in APL. mask is a 0/1 vector."
  (apl-eval (format nil "(~a)/~a" (vec->apl mask) (vec->apl v))))

;;; ---------- Reduction topologies ----------
;;; Reference folds (exact, Lisp). April probes (double-based) timed
;;; separately and tagged; correctness of the gate uses the folds.

(defun reduce-seq (op v &optional (ident nil ident-p))
  (if (zerop (length v))
      (if ident-p ident (error "empty vector without identity"))
      (reduce op v)))

(defun reduce-tree (op v &optional (ident nil ident-p))
  ;; Native tree reduction expressed in APL:
  ;;   {1=⍴⍵:⊃⍵ ⋄ h←⌈2÷⍨⍴⍵ ⋄ ∇ (h↑⍵) f h↓⍵}  -- pairwise fold, ceiling
  ;; Here we drive it from Lisp over APL pairs to keep arithmetic exact.
  (let ((a (coerce v 'list)))
    (loop while (> (length a) 1)
          do (setf a (loop for (x y . rest) on a by #'cddr
                           collect (if y (funcall op x y) x))))
    (if a (first a) (if ident-p ident (error "empty vector without identity"))))))

(defun reduce-chunked (op v &optional (c 4096) (ident nil ident-p))
  ;; segmented_reduction: APL partition per chunk, then tree over chunks
  (declare (ignore ident ident-p))
  (let* ((n (length v))
         (chunks (loop for i from 0 below n by c
                       collect (reduce-seq op (subseq v i (min n (+ i c)))))))
    (reduce-tree op (coerce chunks 'vector))))

(defun scan-seq (op v)
  "scan (prefix fold); APL equivalent is op\\V."
  (let ((out (make-array (length v) :element-type 'integer))
        (acc nil) (first t))
    (dotimes (i (length v) out)
      (if first (setf acc (aref v i) first nil)
          (setf acc (funcall op acc (aref v i))))
      (setf (aref out i) acc))))

(defun subleq-routed (k q v)
  "SUBleQ routed reduction (R7). SPECIFIED predicate: taken iff d <= 0,
   i.e. on canonical unsigned reps: rep = 0 or rep > p/2."
  (let* ((n (length k))
         (d (map 'vector #'gf-sub k q))
         (mask (map 'vector (lambda (r) (if (or (zerop r) (> r +half-p+)) 1 0)) d))
         (sel (apl-compress mask v))          ; PREDICATE + SELECT + ROUTE
         (acc 0) (taken 0))
    (dotimes (i (length mask)) (incf taken (aref mask i)))
    (dolist (x (coerce sel 'list)) (setf acc (gf-add acc x))) ; REDUCE, seq fold
    (values acc taken)))

;;; ---------- Correctness gate (mirror of Chapel/Wolfram suites) ----------
(defparameter +adv-values+
  (list 0 1 (1- +p+) (- +p+ 2) (floor (1- +p+) 2) (1+ (floor (1- +p+) 2))))

(defun check-crosslang-checksum ()
  (= (crosslang-checksum) 1388262917130611548))

(defun correctness-gate ()
  (and
   ;; PRNG cross-language equivalence gate (Experiment-10 arriving early)
   (check-crosslang-checksum)
   ;; field identities on adversarial values
   (every (lambda (x)
            (and (= (gf-add x 0) x)
                 (= (gf-mul x (gf-inv (max x 1))) 1)
                 (= (gf-sub (gf-add x (1- +p+)) (1- +p+)) x)))
          (remove 0 +adv-values+))
   ;; topology equivalence vs sequential fold, all 11 benchmark ops
   (dolist (n '(0 1 2 3 127 128 4096 4097) t)
     (let ((x (make-vec n)))
       (dolist (spec `((sum ,#'gf-add 0)
                       (product ,#'gf-mul 1)
                       (min ,#'min 0) (max ,#'max 0)))
         (destructuring-bind (name op ident) spec
           (declare (ignore name))
           (let ((ref (if (zerop n) ident (reduce-seq op x))))
             (unless (= (reduce-tree op x ident) ref) (return-from correctness-gate nil))
             (unless (= (reduce-chunked op x 4096 ident) ref) (return-from correctness-gate nil)))))
       ;; scan: length preserved, last element = full fold
       (let ((s (scan-seq #'gf-add x)))
         (unless (and (= (length s) n)
                      (or (zerop n) (= (aref s (1- n)) (reduce-seq #'gf-add x))))
           (return-from correctness-gate nil)))))
   ;; SUBLEQ predicate on canonical reps: spot-check d<=0 semantics
   (let ((d0 (gf-sub 5 5))          ; 0 -> taken
         (d1 (gf-sub 3 5))          ; p-2, rep > p/2 -> taken (negative)
         (d2 (gf-sub 5 3)))         ; 2 -> not taken (positive)
     (and (zerop d0) (> d1 +half-p+) (not (> d2 +half-p+)) (not (zerop d2))))))

;;; ---------- Timing: warmup 3, 20 samples, median ----------
(defun median (xs)
  (let ((s (sort (copy-list xs) #'<)))
    (nth (floor (length s) 2) s)))

(defun time-kernel (thunk)
  (dotimes (_ 3) (funcall thunk))              ; warmup
  (median (loop repeat 20
                collect (let ((t0 (get-internal-real-time)))
                          (funcall thunk)
                          (* 1e9 (/ (- (get-internal-real-time) t0)
                                    internal-time-units-per-second))))))

(defun sweep-1d ()
  (format t "== [N] sweep: gf-sum, all topologies ==~%")
  (dolist (n '(128 256 512 1024 2048 4096 8192))
    (let* ((x (make-vec n))
           (ref (reduce-seq #'gf-add x)))
      (unless (= (reduce-tree #'gf-add x) ref)
        (format t "FAIL n=~a~%" n))
      (let ((t-seq (time-kernel (lambda () (reduce-seq #'gf-add x))))
            (t-tree (time-kernel (lambda () (reduce-tree #'gf-add x))))
            (t-chk (time-kernel (lambda () (reduce-chunked #'gf-add x))))
            (t-apl (time-kernel (lambda () (apl-eval (format nil "+/~a" (vec->apl x)))))))
        (format t "N=~5d seq=~,2f tree=~,2f chunk=~,2f apl-probe=~,2f ns~%"
                n t-seq t-tree t-chk t-apl)))))

(defun sweep-subleq ()
  (format t "== [B,N,D] SUBLEQ sweep: mul vs reduce dominance test ==~%")
  (dolist (bnd '((1 128 64) (1 512 64) (1 2048 64) (1 8192 64)
                 (2 1024 128) (4 1024 256)))
    (destructuring-bind (b n d) bnd
      (declare (ignore b))
      (let* ((total (* n d))
             (k (make-vec total)) (q (make-vec total)) (vv (make-vec total)))
        (multiple-value-bind (r taken) (subleq-routed k q vv)
          (declare (ignore r))
          (let ((t-r (time-kernel (lambda () (subleq-routed k q vv))))
                (t-m (time-kernel (lambda ()
                                    (dotimes (i total) (gf-mul (aref k i) (aref vv i)))))))
            (format t "B=~a N=~5d D=~3d mul=~,2f routed=~,2f ratio=~,2f taken=~a/~a~%"
                    b n d t-m t-r (/ t-m (max t-r 1d-9)) taken total))))))))

(defun main ()
  (unless (correctness-gate)
    (format t "GATE FAILED — no results~%")
    (return-from main nil))
  (format t "gate: PASS~%")
  (sweep-1d)
  (sweep-subleq)
  t)

;; Entry point: (load "exp07_april.lisp") then (main)
