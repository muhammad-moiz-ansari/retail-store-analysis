# Dispatch rating sheet (blind)

For the C3 dispatch evaluation (`python -m backend.dispatch_eval`). Fill this in **before** running the evaluator or reading
`backend/dispatch_scenarios.json`, `backend/dispatch.py` or their tests: the scenario names and notes there describe the
expected answer, so they are left out here.

## How to rate

In each scenario one customer is waiting unattended in the **target zone**. Write the ID of the one employee you would
send, or `none` if you would send nobody. Judge it as a store manager would; there is no trick and no wrong reason.

- **Rostered**: on today's roster. A person who is not rostered is not on shift.
- **Home zone**: the zone they are rostered to; *floater* means rostered with no fixed zone.
- **Available**: marked available on the roster (for example, not on break).
- **Busy**: already working on another task.

Every employee is on the floor all day. Zones and the minimum staff each zone should keep:

| Zone | Name | Minimum staff |
|---|---|---|
| z1 | Entrance Lobby | 1 |
| z2 | Aisle 1 - Snacks | 1 |
| z3 | Aisle 2 - Beverages | 1 |
| z4 | Aisle 3 - Household | 1 |
| z5 | Promo Display | 0 |
| z6 | Checkout Counter | 2 |

## S01: customer waiting in z2 (Aisle 1 - Snacks)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| ali | yes | z2 (Aisle 1 - Snacks) | yes | no |

**Your choice:** 

## S02: customer waiting in z2 (Aisle 1 - Snacks)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| ali | yes | z2 (Aisle 1 - Snacks) | yes | yes |
| sara | yes | floater | yes | no |

**Your choice:** 

## S03: customer waiting in z3 (Aisle 2 - Beverages)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| ali | yes | z2 (Aisle 1 - Snacks) | yes | no |

**Your choice:** 

## S04: customer waiting in z3 (Aisle 2 - Beverages)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| ali | yes | z2 (Aisle 1 - Snacks) | yes | no |
| bilal | yes | z2 (Aisle 1 - Snacks) | yes | no |

**Your choice:** 

## S05: customer waiting in z4 (Aisle 3 - Household)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| ali | yes | z2 (Aisle 1 - Snacks) | no | no |
| sara | yes | floater | no | no |

**Your choice:** 

## S06: customer waiting in z4 (Aisle 3 - Household)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| temp | no | - | yes | no |

**Your choice:** 

## S07: customer waiting in z1 (Entrance Lobby)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| a | yes | z6 (Checkout Counter) | yes | no |
| b | yes | z6 (Checkout Counter) | yes | no |
| c | yes | z6 (Checkout Counter) | yes | no |

**Your choice:** 

## S08: customer waiting in z1 (Entrance Lobby)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| a | yes | z6 (Checkout Counter) | yes | no |
| b | yes | z6 (Checkout Counter) | yes | no |

**Your choice:** 

## S09: customer waiting in z2 (Aisle 1 - Snacks)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| p | yes | z5 (Promo Display) | yes | no |

**Your choice:** 

## S10: customer waiting in z3 (Aisle 2 - Beverages)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| f | yes | floater | yes | no |
| t | yes | z3 (Aisle 2 - Beverages) | yes | no |

**Your choice:** 

## S11: customer waiting in z3 (Aisle 2 - Beverages)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| x | yes | z2 (Aisle 1 - Snacks) | yes | no |
| y | yes | z2 (Aisle 1 - Snacks) | yes | no |
| f | yes | floater | yes | no |

**Your choice:** 

## S12: customer waiting in z4 (Aisle 3 - Household)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| a | yes | z2 (Aisle 1 - Snacks) | yes | no |
| b | yes | z2 (Aisle 1 - Snacks) | yes | no |
| c | yes | z6 (Checkout Counter) | yes | no |
| d | yes | z6 (Checkout Counter) | yes | no |
| e | yes | z6 (Checkout Counter) | yes | no |
| g | yes | z6 (Checkout Counter) | yes | no |

**Your choice:** 

## S13: customer waiting in z2 (Aisle 1 - Snacks)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| ali | yes | z2 (Aisle 1 - Snacks) | yes | yes |
| bilal | yes | z2 (Aisle 1 - Snacks) | yes | no |

**Your choice:** 

## S14: customer waiting in z2 (Aisle 1 - Snacks)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| a | yes | z2 (Aisle 1 - Snacks) | yes | yes |
| b | yes | floater | yes | yes |

**Your choice:** 

## S15: customer waiting in z4 (Aisle 3 - Household)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| t | yes | z4 (Aisle 3 - Household) | no | no |
| a | yes | z1 (Entrance Lobby) | yes | no |
| b | yes | z1 (Entrance Lobby) | yes | no |

**Your choice:** 

## S16: customer waiting in z1 (Entrance Lobby)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| door | yes | z1 (Entrance Lobby) | yes | no |
| f | yes | floater | yes | no |

**Your choice:** 

## S17: customer waiting in z6 (Checkout Counter)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| a | yes | z6 (Checkout Counter) | yes | no |
| b | yes | z2 (Aisle 1 - Snacks) | yes | no |

**Your choice:** 

## S18: customer waiting in z3 (Aisle 2 - Beverages)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| zara | yes | floater | yes | no |
| adam | yes | floater | yes | no |

**Your choice:** 

## S19: customer waiting in z4 (Aisle 3 - Household)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| a | yes | z1 (Entrance Lobby) | yes | no |
| b | yes | z1 (Entrance Lobby) | yes | no |
| c | yes | z2 (Aisle 1 - Snacks) | yes | no |
| d | yes | z2 (Aisle 1 - Snacks) | yes | no |

**Your choice:** 

## S20: customer waiting in z5 (Promo Display)

| Employee | Rostered | Home zone | Available | Busy |
|---|---|---|---|---|
| a | yes | z1 (Entrance Lobby) | yes | no |
| b | yes | z2 (Aisle 1 - Snacks) | yes | no |
| c | yes | z3 (Aisle 2 - Beverages) | yes | no |
| d | yes | z3 (Aisle 2 - Beverages) | yes | no |
| e | yes | floater | yes | no |
| f | yes | z6 (Checkout Counter) | yes | no |
| g | yes | z6 (Checkout Counter) | yes | no |

**Your choice:** 
