(define (domain apartment)
  (:requirements :strips)
  (:predicates
    (room ?r)
    (object ?o)
    (robot-at ?r)
    (in-room ?o ?r)
    (connected ?r1 ?r2)
    (holding ?o)
    (empty-hand)
  )

  ;; MOVE
  (:action move
    :parameters (?from ?to)
    :precondition (and (robot-at ?from) (connected ?from ?to))
    :effect (and (not (robot-at ?from)) (robot-at ?to))
  )

  ;; PICK
  (:action pick
    :parameters (?o ?r)
    :precondition (and (robot-at ?r) (in-room ?o ?r) (empty-hand))
    :effect (and (holding ?o) (not (in-room ?o ?r)) (not (empty-hand)))
  )

  ;; PLACE
  (:action place
    :parameters (?o ?r)
    :precondition (and (robot-at ?r) (holding ?o))
    :effect (and (in-room ?o ?r) (empty-hand) (not (holding ?o)))
  )

  
)