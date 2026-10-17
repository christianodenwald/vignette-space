;;; Run the upstream FDM checks and this project's regression tests.
;;; Usage: sbcl --script test_fdm_regressions.lisp
(defparameter *test-project-root*
  (make-pathname :name nil :type nil :defaults *load-truename*))
(load (merge-pathnames ".lisp/setup.lisp" *test-project-root*))
(asdf:load-asd (merge-pathnames "vignette-space-fdm.asd" *test-project-root*))
(asdf:load-system "vignette-space-fdm")

(in-package :factual-difference-making)

(5am:def-suite* :vignette-space-fdm-regressions)

;;; Inferential networks: nested Boolean expressions and missing effect nodes

(5am:def-test nested-boolean-parent-deductions ()
  ;; The first equation is evaluator case 29. Both equations depend only on A:
  ;; the first is NOT A, and the second is A. B must not become a cause simply
  ;; because it occurs in alternative syntactic branches.
  (dolist (expression '((or (and b (not a)) (and (not a) (not b)))
                        (and (or b a) (or a (not b)))))
    (dolist (a-value '(nil t))
      (dolist (b-value '(nil t))
        (let* ((a-literal (if a-value 'a '(not a)))
               (b-literal (if b-value 'b '(not b)))
               (c-value (if (eq (first expression) 'or)
                            (not a-value)
                            a-value))
               (effect (if c-value 'c '(not c)))
               (literals (mapcar #'ensure-literal
                                 (list a-literal b-literal effect)))
               (model (make-extended-fdm-model
                       :streq (alexandria:alist-hash-table
                               (list (cons 'c expression)))
                       :literals literals
                       :defaults (mapcar #'complement-literal literals))))
          (5am:is-true (is-cause model a-literal effect))
          (5am:is-false (is-cause model b-literal effect)))))))

(5am:def-test negative-identity-parent ()
  ;; A negative effect whose RHS is a symbol needs the negative parent node.
  (let ((model (make-extended-fdm-model
                :streq (alexandria:alist-hash-table '((c . a)))
                :literals '((not a) (not c))
                :defaults '(a c))))
    (5am:is-true (is-cause model '(not a) '(not c)))))

(5am:def-test missing-inferential-network-effect ()
  ;; A malformed network must fail explicitly instead of recursing forever.
  (let ((network (make-instance 'inferential-network
                                :effect-node nil
                                :node-table (make-hash-table :test #'equalp))))
    (5am:signals error (infnet-root-nodes network))))

;;; Structural descendants: Boolean operators can have any number of operands

(5am:def-test expression-variables-boolean-arities ()
  (let ((streq (make-hash-table)))
    (dolist (operator '(and or))
      (dolist (example '((() ())
                         ((a) (a))
                         ((a (not b)) (a b))
                         ((a (not b) d) (a b d))
                         ((a (not b) d a) (a b d))))
        (destructuring-bind (operands expected) example
          (5am:is
           (equal expected
                  (sort (expression-variables (cons operator operands) streq)
                        #'string< :key #'symbol-name))))))))

(5am:def-test multi-operand-transitive-descendants ()
  (let ((streq (alexandria:alist-hash-table
               '((d . (and a b a))
                 (c . (or d (not b) a))))))
    (5am:is (equal '(a b c d)
                     (sort (expression-variables 'c streq)
                           #'string< :key #'symbol-name)))
    (5am:is (equal '(c d)
                     (sort (streq-descendents streq 'a)
                           #'string< :key #'symbol-name)))))

(5am:def-test three-disjunct-cause ()
  ;; Evaluator case 59: NOT A causes C with A=0, B=1, C=1.
  (let ((model (make-extended-fdm-model
                :streq (alexandria:alist-hash-table
                        '((c . (or (and a (not b))
                                   (and b (not a))
                                   (and (not a) (not b))))))
                :literals '((not a) b c)
                :defaults '(a (not b) (not c)))))
    (5am:is-true (is-cause model '(not a) 'c))))

(let ((upstream-passed (5am:run! :factual-difference-making))
      (regressions-passed (5am:run! :vignette-space-fdm-regressions)))
  (unless (and upstream-passed regressions-passed)
    (sb-ext:exit :code 1)))
