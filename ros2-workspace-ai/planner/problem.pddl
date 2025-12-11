(define (problem apartment-example)
  (:domain apartment)

  (:objects
    livingroom kitchen bedroom bathroom cinemaroom gamingroom garden cup book remote towel phone panadol pillow freshbuzz popcorn ps5controller chewy
  )

  (:init
    (room livingroom) (room kitchen) (room bedroom) (room bathroom) (room cinemaroom) (room gamingroom) (room garden) (object cup) (object book) (object remote) (object towel) (object phone) (object panadol) (object pillow) (object freshbuzz) (object popcorn) (object ps5controller) (object chewy) (robot-at cinemaroom) (empty-hand) (in-room cup kitchen) (in-room book bedroom) (in-room remote livingroom) (in-room towel bathroom) (in-room phone livingroom) (in-room panadol cinemaroom) (in-room pillow bedroom) (in-room freshbuzz bathroom) (in-room popcorn cinemaroom) (in-room ps5controller gamingroom) (in-room chewy garden) (connected livingroom garden) (connected garden livingroom) (connected livingroom cinemaroom) (connected cinemaroom livingroom) (connected livingroom bedroom) (connected bedroom livingroom) (connected livingroom kitchen) (connected kitchen livingroom) (connected livingroom bathroom) (connected bathroom livingroom) (connected bedroom gamingroom) (connected gamingroom bedroom) (connected kitchen cinemaroom) (connected cinemaroom kitchen)
  )

  (:goal
    (in-room chewy kitchen)
  )
)
