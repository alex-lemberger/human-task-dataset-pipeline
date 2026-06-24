# Capture Rig Hardware — Buying List (Germany)

**Date:** 2026-06-24
**Context:** Real-hardware pose capture for the htdp pipeline (drives `OpenVRPoseSource`
in the `htdp-capture` app). Chosen lighthouse setup over Vive Ultimate Trackers and
over Rokoko Smartgloves — see [Decision rationale](#decision-rationale).

## Buying List

| # | Item | Qty | ~€ each | Subtotal | Role |
|---|------|-----|---------|----------|------|
| 1 | HTC Vive Tracker 3.0 | 4 | 109 | 436 | trackers: `right_wrist`, `left_wrist`, `torso`, `object` (USB dongle + cradle + cable included per unit) |
| 2 | SteamVR Base Station 2.0 | 2 | 159 | 318 | shared world origin (trivial frame calibration); 2 = occlusion-robust capture volume |
| 3 | Strap set (1 waist belt + 2 wrist) | 1 | ~35 | 35 | wrists + torso; object uses the 1/4" thread mount directly |
| 4 | Seagate Portable 5TB (STGX5000400) | 1 | 161 | 161 | dataset storage |

**Rig total ≈ 789 €** (capture only) · **≈ 950 €** with storage. Under the 1200 € budget.

## Links (Germany)

**Vive Tracker 3.0**
- Geizhals price-compare (ab €109): https://geizhals.de/htc-vive-tracker-3-0-99hass002-00-a2497060.html
- Amazon.de: https://www.amazon.de/-/en/99HASS002-00-HTC-VIVE-Tracker-3-0/dp/B08YY215VB
- Official VIVE shop: https://myshop.vive.com/vive_de/1920281.html
- What's in the box (dongle confirmed): https://www.vive.com/us/support/tracker3/category_howto/inside-the-box.html

**SteamVR Base Station 2.0**
- Steam Store (€159): https://store.steampowered.com/app/1059570/Valve_Indexbasisstation/?l=german
- Amazon.de: https://www.amazon.de/HTC-99H12161-001-Steam-Basisstation-2-0/dp/B085LXTCYZ
- Official VIVE shop: https://myshop.vive.com/vive_de/1920589.html

**Straps** (3.0-compatible belt + wrist sets)
- Amazon.de search: "KIWI design Vive Tracker 3.0 strap" / "AMVR" / "Rebuff Reality"
- The VOANZO Hüftgurt+Armband set (already in original cart) fits 3.0 too — same mount, cheap.

## Decision rationale

**Rokoko Smartgloves (1900 €) — rejected.** Capture different data, not better data:
finger articulation, NOT global 6-DOF body/object pose. IMU-based → no reliable absolute
world position (drift); can't track the manipulated object. The pipeline's IK arm replay,
BIDS motion export, and the 8-channel motion contract (`x,y,z,qw..qz,quality` per
tracker) all need world-frame wrist/torso/object poses. Gloves are a complementary
*addition* (in-hand dexterity), not a substitute for the positional spine.

**Vive Ultimate Trackers — rejected.** Inside-out self-tracking (no base stations).
Fights this pipeline:
- Each tracker builds its own room map → reconciling 4 trackers into one consistent
  world frame is fiddly and drifts. Lighthouse = one shared base-station origin (matches
  the deferred `frame_transform` calibration design exactly).
- SteamVR/OpenVR enumeration via Vive Streaming Hub + dongle is less proven than
  lighthouse pucks (which "just appear" in SteamVR — what `OpenVRPoseSource` assumes).
- Environment-sensitive (needs textured, well-lit rooms).
- Dongle/strap mismatches in the original cart (Ultimate uses a different mount than the
  2017/2018 straps; one dongle in the 3-pack, extra single tracker needs its own).

**Vive Tracker 3.0 + Base Station 2.0 — chosen.** mm-accurate, drift-free, single shared
world origin, rock-solid OpenVR enumeration, standard strap ecosystem. The proven
motion-capture-grade path for exactly the code in flight.

## Setup notes

1. **No HMD required.** SteamVR runs headless for trackers via the null-driver config
   (standard full-body/mocap setup). Tracker 3.0 dongles handle the radio link.
2. **Base-station placement:** 2 stations diagonally opposite, ~2 m high, angled down →
   ~3×3 m capture volume with occlusion resistance. 1 station only covers a small
   frontal zone.
3. **PC needs SteamVR (Windows).** This is the box the `OpenVRPoseSource` live mile runs
   on — `openvr.init()` executes there, not on the dev Mac (where `import openvr` fails:
   x86_64-only dylib). See the OpenVR plan/spec in `docs/superpowers/`.

## Related

- OpenVR adapter spec: `docs/superpowers/specs/2026-06-24-htdp-capture-openvr-design.md`
- OpenVR adapter plan: `docs/superpowers/plans/2026-06-24-htdp-capture-openvr.md`
- Capture app repo: `/Users/alexanderlemberger/htdp-capture`
