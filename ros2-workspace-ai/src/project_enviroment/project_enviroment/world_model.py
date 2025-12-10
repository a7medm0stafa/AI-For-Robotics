# world_model.py

# Coordinates are in robot base frame or map frame (for now fixed & simple)

OBJECT_PICK_POSES = {
    "cup":        [0.25, 0.0, 0.15],
    "book":       [0.25, 0.05, 0.15],
    "remote":     [0.22, -0.05, 0.15],
    "phone":      [0.23, 0.03, 0.15],
}

ROOM_PLACE_POSES = {
    "kitchen":     [0.30, 0.0, 0.20],
    "bedroom":     [0.0, -0.05, 0.20],
    "livingroom":  [0.28, 0.04, 0.20],
    "bathroom":    [0.30, -0.04, 0.20],
}
