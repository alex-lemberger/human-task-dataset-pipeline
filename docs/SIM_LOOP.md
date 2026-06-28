# Pixels to a Friction Grasp — a Visuomotor Sim Loop

A Franka Panda picks a cube and places it on a target in MuJoCo — **from a single camera
image, under true contact physics**, with a policy that was never told where the cube or the
target are. It reads them from pixels.

This is a from-scratch robot-learning loop: scripted physics teacher → imitation demos →
action-chunking transformer policy → closed-loop rollout, built and debugged end-to-end. The
interesting part is not that it works — it's the specific ways it *looked* like it worked while
being broken, and how each was caught.

| policy | observation | held-out success | mean place error |
|--------|-------------|------------------|------------------|
| baseline (scripted physics teacher) | privileged state | 6/6 (100%) | 0.008 m |
| state ACT | joints + eef + **cube xyz + target xyz** + finger width | 4/6 (67%) | 0.097 m |
| **visuomotor ACT** | **96×96 camera image + proprioception only** | **4/6 (67%)** | 0.089 m |

> *Mean place error is over all 6 held-out positions, so it is dominated by the 2 grasp-slip
> failures (~0.25 m each); the 4 successful placements land within 0.006–0.019 m. That a constant
> ~0.5-m-region task scores a sub-0.1-m mean is the placement quality, not the failure rate —
> read the success column for "did it work," the error column for "how clean when it did."*

The visuomotor policy **matches** the state-based policy while seeing none of the privileged
coordinates.

- **Visuomotor policy rollout** (the headline — pixels in, friction grasp out):
  [`docs/demo/m25_visuomotor_rollout.mp4`](demo/m25_visuomotor_rollout.mp4)
- Eval numbers: [`docs/demo/m25_visuomotor_eval.json`](demo/m25_visuomotor_eval.json)
- Scripted physics teacher rollout: [`docs/demo/m25_physics_pick_place.mp4`](demo/m25_physics_pick_place.mp4)

## The loop

```
sample cube pose (in the friction-grasp success zone)
        │
        ▼
scripted physics teacher  ──►  position-servo actuators + mj_step + friction grasp
        │                      (no kinematic attach — the cube is held by finger contact)
        ▼
LeRobot-format demos       ──►  per-step state, action chunk, AND a 96×96 front-camera frame
        │
        ▼
ACT policy (transformer)   ──►  state ACT  |  visuomotor ACT (CNN over the image + proprio)
        │
        ▼
closed-loop rollout        ──►  same physics, same friction grasp, same camera path
                               policy localises the cube from pixels and places it
```

The teacher, the demos, and the rollout all run the *same* physics and render through the *same*
camera function — so nothing the policy trains on differs from what it sees at test time.

## What made it credible (and what didn't)

Every milestone shipped a metric that was green before the system was right. The work was mostly
in distrusting the metric.

- **The 5-DOF wall.** Started on an SO-ARM100 (5-DOF). The pick-place metrics passed, but the
  rendered video showed the gripper pointing *up*, missing the cube, links clipping through the
  table. A position-only `place_error` read 0.0 because the cube was being teleported by a weld
  regardless of where the fingers were. Three separate false-greens, all from checking position
  and not contact. Then the real wall: a 5-DOF arm *physically cannot* orient a gripper top-down
  at a tabletop target — proven by a mount-height sweep (15–27 cm error everywhere). Swapped to a
  7-DOF Franka Panda, which is also the imitation-learning standard.

- **The normalization landmine.** The first imitation policy scored 0% closed-loop while
  predicting *perfectly* on demo observations open-loop. The cause: a constant observation
  feature (finger width — the kinematic teacher never moved the fingers, so its std was ~0). A
  tiny mismatch at rollout, divided by ~0 during normalization, produced an astronomically large
  input that destroyed the policy. Fix: drop constant features. (When the physics teacher *did*
  actuate the fingers, the feature carried real signal and came back.)

- **Kinematic vs. physics action mismatch.** A kinematic teacher (joint angles forced into
  `qpos`) produces actions that position-servo actuators cannot track (1.76 rad error). Teacher
  and executor must agree. This drove the whole M2.5 rewrite: replace the kinematic shortcut with
  a true friction grasp on *both* sides — teacher and rollout — so the same actions mean the same
  thing.

- **Friction compounds error.** Under a true friction grasp, held-out success is 67%, not the
  100% the kinematic attach reported. A slightly-off approach slips the grasp; the attach used to
  paper over exactly that. The lower number is the honest one.

- **A blank camera still renders something.** The image gate doesn't assert "frame is non-blank"
  — a camera pointed at a wall passes that. It asserts the red cube's pixels are present, so a
  misaimed camera can't silently train a blind policy.

## How it's built

- **Physics & control** — MuJoCo (vendored Menagerie Franka), differential IK via `mink` to turn
  Cartesian waypoints into joint targets, position-servo actuators stepped with `mj_step`. The
  grasp is finger friction on a high-friction cube, not a weld.
- **Data** — demos in LeRobot dataset layout (Parquet for low-dim state/action; 96×96 RGB image
  stacks as aligned `.npy` sidecars, the way LeRobot sidecars video).
- **Policy** — a compact action-chunking transformer (ACT): observation → memory token → decoder
  with learned queries → a chunk of actions, executed receding-horizon. The visuomotor variant
  adds a small 3-stride CNN over the image, fused with proprioception. PyTorch, MPS.
- **Robustness** — observation-noise / image-jitter augmentation (DART-style) against the
  covariate shift that compounds in closed loop.
- **Tests** — TDD throughout, including two end-to-end guards that train a policy and assert
  nonzero held-out success under physics (the state loop and the visuomotor loop). Each milestone
  has a short result doc under [`docs/m2/`](m2/).

```bash
uv sync --extra replay --extra dev
htdp gen-demos       --out demos --n-train 40            # physics teacher + 96×96 images
htdp train-visuomotor --demos demos --out vm.pt --steps 6000
htdp eval-visuomotor  --demos demos --policy vm.pt       # success vs physics baseline
htdp render-physics   --video out.mp4                    # teacher rollout from the front camera
```

## Honest limitations

- Held-out positions are **in-distribution interpolation** — the same ~7×10 cm region the policy
  trained on, not novel poses or distractors.
- One object, one fixed third-person camera, no domain randomization — so no sim-to-real claim.
- 67% is a real friction-grasp number, not a polished demo number; the remaining failures are
  grasp slips on off-center approaches.

## Where it could go

Wrist camera; domain randomization (lighting / texture / object color) for a sim-to-real story;
or driving a real SO-ARM100 now that the loop is validated in sim. The point of stopping here:
the loop is closed and honest end-to-end — pixels to a friction grasp, no kinematic shortcut and
no privileged state.

---
*Origin: this began as a consent-based human-task capture pipeline (see the
[README](../README.md)); the manipulation sim loop is the part re-scoped toward robot-learning
engineering.*
