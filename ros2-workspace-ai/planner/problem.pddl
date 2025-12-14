(define (problem apartment-example)
  (:domain apartment)

  (:objects
    livingroom diningroom bedroom storageroom studyroom door cup book remote phone panadol pillow chewy
  )

  (:init
    (room livingroom) (room diningroom) (room bedroom) (room storageroom) (room studyroom) (room door) (object cup) (object book) (object remote) (object phone) (object panadol) (object pillow) (object chewy) (robot-at livingroom) (empty-hand) (in-room cup diningroom) (in-room book studyroom) (in-room remote livingroom) (in-room phone livingroom) (in-room panadol bedroom) (in-room pillow bedroom) (in-room chewy storageroom) (connected studyroom bedroom) (connected bedroom studyroom) (connected diningroom storageroom) (connected storageroom diningroom) (connected livingroom studyroom) (connected studyroom livingroom) (connected livingroom diningroom) (connected diningroom livingroom) (connected livingroom door) (connected door livingroom)
  )

  (:goal
    (robot-at diningroom)
  )
)
