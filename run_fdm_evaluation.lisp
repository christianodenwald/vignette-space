(defparameter *driver-directory*
  (make-pathname :name nil :type nil :defaults *load-truename*))
(defparameter *project-root*
  (truename *driver-directory*))
(defparameter *cases-path* (truename (second sb-ext:*posix-argv*)))
(defparameter *results-path* (pathname (third sb-ext:*posix-argv*)))

(load (merge-pathnames ".lisp/setup.lisp" *project-root*))
(uiop:chdir *project-root*)
(asdf:load-asd (merge-pathnames "vignette-space-fdm.asd" *project-root*))
(asdf:load-system "vignette-space-fdm")

(in-package :factual-difference-making)

(defun actual-literal (variable value)
  (if (zerop value) (list 'not variable) variable))

(defun count-cases (path)
  (with-open-file (input path)
    (loop for case = (read input nil nil)
          while case
          count 1)))

(defun print-progress (completed total)
  (format *error-output* "~C[Moonli FDM] ~D/~D (~,1F%)~C"
          #\Return completed total (* 100.0 (/ completed total)) #\Return)
  (finish-output *error-output*))

(defun print-case-start (case-number total case)
  (destructuring-bind (model-id expression a b c cause-type cause effect) case
    (declare (ignore expression cause-type effect))
    (format *error-output*
            "[Moonli FDM] Starting case ~D/~D: model=~A A=~D B=~D C=~D cause=~S~%"
            case-number total model-id a b c cause)
    (finish-output *error-output*)))

(defun write-tsv-row (stream fields)
  ;; Quoted TSV preserves tabs, newlines, and quotes inside diagnostic fields.
  (loop for field in fields
        for first = t then nil
        do (unless first (write-char #\Tab stream))
           (write-char #\" stream)
           (loop for character across field
                 do (when (char= character #\")
                      (write-char #\" stream))
                    (write-char character stream))
           (write-char #\" stream))
  (terpri stream))

(defun evaluate-case (stream case)
  (destructuring-bind (model-id expression a b c cause-type cause effect) case
    (declare (ignore cause-type))
    (let* ((actual-literals
             (mapcar #'ensure-literal
                     (list (actual-literal 'a a)
                           (actual-literal 'b b)
                           (actual-literal 'c c))))
           (defaults (mapcar #'complement-literal actual-literals))
           (fdm-model
             (make-extended-fdm-model
              :name (intern (string-upcase model-id) :keyword)
              :streq (alexandria:alist-hash-table
                      (list (cons 'c expression)))
              :literals actual-literals
              :defaults defaults)))
      (multiple-value-bind (agnostic-model inferential-network)
          (is-cause fdm-model cause effect)
        (write-tsv-row
         stream
         (list "RESULT"
               (format nil "~A|~D|~D|~A" model-id a b
                       (literal-variable (ensure-literal cause)))
               (if agnostic-model "True" "False")
               (if agnostic-model (prin1-to-string agnostic-model) "")
               (if inferential-network
                   (prin1-to-string inferential-network)
                   "")))))))

(with-open-file (input cl-user::*cases-path*)
  (with-open-file (output cl-user::*results-path*
                          :direction :output
                          :if-exists :supersede)
    (let ((total (count-cases cl-user::*cases-path*))
          (completed 0))
      (format *error-output* "[Moonli FDM] Evaluating ~D cases...~%" total)
      (loop for case = (read input nil nil)
            while case
            do (print-case-start (1+ completed) total case)
               (evaluate-case output case)
               (incf completed)
               (print-progress completed total))
      (terpri *error-output*)
      (format *error-output* "[Moonli FDM] Finished ~D cases.~%" completed))))
