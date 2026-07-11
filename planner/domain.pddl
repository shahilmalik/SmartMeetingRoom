(define (domain smart-meeting-room)
  (:requirements :strips :typing :negative-preconditions)
  (:types room)

  (:predicates
    (occupied ?r - room)
    (empty ?r - room)
    (temp-comfortable ?r - room)
    (temp-hot ?r - room)
    (temp-cold ?r - room)
    (co2-high ?r - room)
    (co2-ok ?r - room)
    (lights-on ?r - room)
    (lights-off ?r - room)
    (lights-dim ?r - room)
    (lights-bright ?r - room)
    (ventilation-on ?r - room)
    (ventilation-off ?r - room)
    (ac-cooling ?r - room)
    (ac-off ?r - room)
    (blinds-open ?r - room)
    (blinds-closed ?r - room)
    (device-powered ?r - room)
    (device-off ?r - room)
    (comfortable ?r - room)
    (energy-saving ?r - room)
  )

  (:action ventilate
    :parameters (?r - room)
    :precondition (and (co2-high ?r) (ventilation-off ?r))
    :effect (and (ventilation-on ?r) (not (ventilation-off ?r)) (co2-ok ?r) (not (co2-high ?r)))
  )

  (:action stop-ventilation
    :parameters (?r - room)
    :precondition (and (ventilation-on ?r) (co2-ok ?r) (empty ?r))
    :effect (and (ventilation-off ?r) (not (ventilation-on ?r)))
  )

  (:action cool-room
    :parameters (?r - room)
    :precondition (and (temp-hot ?r) (ac-off ?r) (occupied ?r))
    :effect (and (ac-cooling ?r) (not (ac-off ?r)) (temp-comfortable ?r) (not (temp-hot ?r)))
  )

  (:action heat-room
    :parameters (?r - room)
    :precondition (and (temp-cold ?r) (ventilation-off ?r) (occupied ?r))
    :effect (and (ventilation-on ?r) (not (ventilation-off ?r)) (temp-comfortable ?r) (not (temp-cold ?r)))
  )

  (:action stop-cooling
    :parameters (?r - room)
    :precondition (and (ac-cooling ?r) (temp-comfortable ?r))
    :effect (and (ac-off ?r) (not (ac-cooling ?r)))
  )

  (:action brighten-lights
    :parameters (?r - room)
    :precondition (and (occupied ?r) (lights-dim ?r))
    :effect (and (lights-bright ?r) (lights-on ?r) (not (lights-dim ?r)) (not (lights-off ?r)))
  )

  (:action dim-lights
    :parameters (?r - room)
    :precondition (and (occupied ?r) (lights-bright ?r))
    :effect (and (lights-dim ?r) (not (lights-bright ?r)))
  )

  (:action turn-off-lights
    :parameters (?r - room)
    :precondition (and (empty ?r) (lights-on ?r))
    :effect (and (lights-off ?r) (not (lights-on ?r)) (not (lights-bright ?r)) (not (lights-dim ?r)))
  )

  (:action open-blinds
    :parameters (?r - room)
    :precondition (and (occupied ?r) (blinds-closed ?r))
    :effect (and (blinds-open ?r) (not (blinds-closed ?r)))
  )

  (:action close-blinds
    :parameters (?r - room)
    :precondition (and (empty ?r) (blinds-open ?r))
    :effect (and (blinds-closed ?r) (not (blinds-open ?r)))
  )

  (:action power-down-device
    :parameters (?r - room)
    :precondition (and (empty ?r) (device-powered ?r))
    :effect (and (device-off ?r) (not (device-powered ?r)))
  )

  (:action power-up-device
    :parameters (?r - room)
    :precondition (and (occupied ?r) (device-off ?r))
    :effect (and (device-powered ?r) (not (device-off ?r)))
  )

  (:action achieve-comfort
    :parameters (?r - room)
    :precondition (and (occupied ?r) (temp-comfortable ?r) (co2-ok ?r) (lights-bright ?r) (device-powered ?r))
    :effect (comfortable ?r)
  )

  (:action achieve-energy-saving
    :parameters (?r - room)
    :precondition (and (empty ?r) (lights-off ?r) (ventilation-off ?r) (ac-off ?r) (device-off ?r) (blinds-closed ?r))
    :effect (energy-saving ?r)
  )
)
