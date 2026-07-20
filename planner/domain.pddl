(define (domain smart-meeting-room)
  (:requirements :strips :typing :negative-preconditions)
  (:types room)

  ; ── Coherent actuator model ─────────────────────────────────────────────
  ;   Room Lamp  (Plugwise socket) → lighting
  ;   Fan/Heater (Grove relay)     → air quality (CO2) + heating
  ;   AC         (simulated)       → cooling only
  ;   Blinds     (simulated)       → daylight harvesting + solar-heat blocking
  ; A room is "lit" from EITHER daylight (blinds open in daytime) OR the lamp.
  ; The blinds are a shared resource: opened for free daylight when it is dark
  ; and not hot, but kept CLOSED when hot so they do not fight the AC.

  (:predicates
    (occupied ?r - room)
    (empty ?r - room)
    (temp-comfortable ?r - room)
    (temp-hot ?r - room)
    (temp-cold ?r - room)
    (co2-high ?r - room)
    (co2-ok ?r - room)
    (ambient-dark ?r - room)
    (ambient-ok ?r - room)
    (ambient-bright ?r - room)
    (daylight-available ?r - room)
    (no-daylight ?r - room)
    (fan-on ?r - room)
    (fan-off ?r - room)
    (ac-cooling ?r - room)
    (ac-off ?r - room)
    (blinds-open ?r - room)
    (blinds-closed ?r - room)
    (lamp-on ?r - room)
    (lamp-off ?r - room)
    (room-lit ?r - room)
    (comfortable ?r - room)
    (energy-saving ?r - room)
  )

  ; ── Air quality: fan (relay) clears CO2 ─────────────────────────────────
  (:action ventilate
    :parameters (?r - room)
    :precondition (and (co2-high ?r) (fan-off ?r))
    :effect (and (fan-on ?r) (not (fan-off ?r)) (co2-ok ?r) (not (co2-high ?r)))
  )

  (:action stop-ventilation
    :parameters (?r - room)
    :precondition (and (fan-on ?r) (co2-ok ?r) (empty ?r))
    :effect (and (fan-off ?r) (not (fan-on ?r)))
  )

  ; ── Heating: fan/heater (relay) warms a cold room ───────────────────────
  (:action heat-room
    :parameters (?r - room)
    :precondition (and (temp-cold ?r) (occupied ?r))
    :effect (and (fan-on ?r) (not (fan-off ?r)) (temp-comfortable ?r) (not (temp-cold ?r)))
  )

  ; ── Cooling: block solar heat first, THEN run the AC ────────────────────
  (:action close-blinds-for-cooling
    :parameters (?r - room)
    :precondition (and (temp-hot ?r) (blinds-open ?r) (occupied ?r))
    :effect (and (blinds-closed ?r) (not (blinds-open ?r)) (not (room-lit ?r)))
  )

  (:action cool-room
    :parameters (?r - room)
    :precondition (and (temp-hot ?r) (ac-off ?r) (occupied ?r) (blinds-closed ?r))
    :effect (and (ac-cooling ?r) (not (ac-off ?r)) (temp-comfortable ?r) (not (temp-hot ?r)))
  )

  (:action stop-cooling
    :parameters (?r - room)
    :precondition (and (ac-cooling ?r) (temp-comfortable ?r))
    :effect (and (ac-off ?r) (not (ac-cooling ?r)))
  )

  ; ── Lighting: prefer FREE daylight, fall back to the lamp ───────────────
  ; Daytime & comfortable → open the blinds for natural light (no energy cost).
  (:action open-blinds-for-daylight
    :parameters (?r - room)
    :precondition (and (occupied ?r) (blinds-closed ?r) (ambient-dark ?r)
                       (daylight-available ?r) (not (temp-hot ?r)))
    :effect (and (blinds-open ?r) (not (blinds-closed ?r)) (room-lit ?r))
  )

  ; Night: no daylight to harvest → use the lamp.
  (:action turn-on-lamp-night
    :parameters (?r - room)
    :precondition (and (occupied ?r) (lamp-off ?r) (ambient-dark ?r) (no-daylight ?r))
    :effect (and (lamp-on ?r) (not (lamp-off ?r)) (room-lit ?r))
  )

  ; Daytime but hot: blinds must stay shut for cooling → use the lamp instead.
  (:action turn-on-lamp-hot
    :parameters (?r - room)
    :precondition (and (occupied ?r) (lamp-off ?r) (ambient-dark ?r) (temp-hot ?r))
    :effect (and (lamp-on ?r) (not (lamp-off ?r)) (room-lit ?r))
  )

  ; ── Empty-room energy saving ────────────────────────────────────────────
  (:action turn-off-lamp
    :parameters (?r - room)
    :precondition (and (empty ?r) (lamp-on ?r))
    :effect (and (lamp-off ?r) (not (lamp-on ?r)) (not (room-lit ?r)))
  )

  (:action close-blinds
    :parameters (?r - room)
    :precondition (and (empty ?r) (blinds-open ?r))
    :effect (and (blinds-closed ?r) (not (blinds-open ?r)) (not (room-lit ?r)))
  )

  ; ── Goals ───────────────────────────────────────────────────────────────
  (:action achieve-comfort
    :parameters (?r - room)
    :precondition (and (occupied ?r) (temp-comfortable ?r) (co2-ok ?r) (room-lit ?r))
    :effect (comfortable ?r)
  )

  (:action achieve-energy-saving
    :parameters (?r - room)
    :precondition (and (empty ?r) (lamp-off ?r) (fan-off ?r) (ac-off ?r) (blinds-closed ?r))
    :effect (energy-saving ?r)
  )
)
