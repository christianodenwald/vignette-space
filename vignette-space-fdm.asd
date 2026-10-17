;;; Project-local loading of the FDM repository's generated Lisp files.
;;; Keep evaluation setup separate from the upstream Moonli system definition.
(asdf:defsystem "vignette-space-fdm"
  :depends-on ("moonli" "picl")
  :pathname #p"factual_difference_making/moonli/"
  :serial t
  :components ((:module "src"
                :components ((:file "00-package")
                             (:file "01-utils")
                             (:file "02-fdm")
                             (:file "03-natural-deduction")
                             (:file "04-inferential-networks")
                             (:file "05-deviancy")
                             (:file "06-settles")
                             (:file "high-level-utils")
                             (:file "07-is-cause")))
               (:file "fdm-models")
               (:file "tests")))
