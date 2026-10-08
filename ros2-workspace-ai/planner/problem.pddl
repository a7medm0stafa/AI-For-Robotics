(define (problem apartment-example)
  (:domain apartment)

  (:objects
    livingroom diningroom bedroom storageroom studyroom bathroom cup book remote phone panadol pillow chewy
  )

  (:init
    (room livingroom) (room diningroom) (room bedroom) (room storageroom) (room studyroom) (room bathroom) (object cup) (object book) (object remote) (object phone) (object panadol) (object pillow) (object chewy) (robot-at storageroom) (holding chewy) (in-room cup diningroom) (in-room book bedroom) (in-room remote livingroom) (in-room phone livingroom) (in-room panadol livingroom) (in-room pillow bedroom) (connected livingroom studyroom) (connected studyroom livingroom) (connected diningroom storageroom) (connected storageroom diningroom) (connected studyroom bedroom) (connected bedroom studyroom) (connected diningroom bathroom) (connected bathroom diningroom) (connected livingroom diningroom) (connected diningroom livingroom)
  )

  (:goal
    (in-room chewy diningroom)
  )
)
